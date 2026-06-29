"""Rule-based plugins: per-fav action buttons that fire a backend REST call.

Plugins are declared as data in a JSON ruleset (see ``app/plugins.json``). Each rule
matches favs by a URL regex and, when its button is clicked, all-my-favs makes the
configured outbound request (``GET`` query params or ``POST`` JSON body) server-side.

No client-side cross-origin calls: any secrets stay on the server. Add a plugin by
appending a rule to the JSON — no code change required.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.config import settings
from app.models import Bookmark

# Placeholder for a missing env var referenced via ${VAR}: leave the reference as-is.
_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _resolve_env(value: str) -> str:
    return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)


@dataclass(frozen=True)
class PluginRule:
    key: str
    label: str
    pattern: re.Pattern[str]
    url: str
    method: str = "GET"
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)

    def matches(self, bm: Bookmark) -> bool:
        return bool(self.pattern.search(bm.url or ""))


def _fields(bm: Bookmark) -> dict[str, str]:
    return {
        "url": bm.url or "",
        "title": bm.title or "",
        "description": bm.description or "",
        "tags": ",".join(t.name for t in bm.tags),
        "domain": bm.domain or "",
    }


def _render(template: str, bm: Bookmark) -> str:
    # defaultdict(str) so unknown {placeholders} render empty instead of raising.
    return template.format_map(defaultdict(str, _fields(bm)))


def load_plugins(path: str | os.PathLike[str]) -> list[PluginRule]:
    """Load and compile the plugin ruleset. A missing/empty file yields no plugins."""
    p = Path(path)
    if not p.is_file():
        return []
    raw = json.loads(p.read_text())
    rules: list[PluginRule] = []
    for entry in raw.get("plugins", []):
        rules.append(
            PluginRule(
                key=entry["key"],
                label=entry["label"],
                pattern=re.compile(entry["pattern"], re.IGNORECASE),
                url=_resolve_env(entry["url"]),
                method=entry.get("method", "GET").upper(),
                params=dict(entry.get("params", {})),
                headers={k: _resolve_env(v) for k, v in entry.get("headers", {}).items()},
            )
        )
    return rules


PLUGINS: list[PluginRule] = load_plugins(settings.plugins_config)


def plugins_for(bm: Bookmark) -> list[PluginRule]:
    return [rule for rule in PLUGINS if rule.matches(bm)]


def get_plugin(key: str) -> PluginRule | None:
    return next((rule for rule in PLUGINS if rule.key == key), None)


def run_plugin(rule: PluginRule, bm: Bookmark, *, timeout: float = 10.0) -> None:
    """Dispatch the rule's outbound request. Raises ``httpx.HTTPError`` on failure."""
    data = {k: _render(v, bm) for k, v in rule.params.items()}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        if rule.method == "GET":
            resp = client.get(rule.url, params=data, headers=rule.headers)
        else:
            resp = client.request(rule.method, rule.url, json=data, headers=rule.headers)
        resp.raise_for_status()
