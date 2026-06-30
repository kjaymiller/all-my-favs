"""URL-route buttons: per-fav links to other services.

Routes are declared as data in a JSON file (see ``app/plugins.json``). Each entry matches
favs by a URL regex and renders a button that sends the fav's fields to another service —
either as **url params** (``GET``, a plain link with a query string) or as **body params**
(``POST``, a form the browser submits). Either way it's the browser that navigates to the
url; nothing fires server-side, so there are no secrets to manage.

Add one by appending an entry to the JSON; no code change required.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

from app.config import settings
from app.models import Bookmark


@dataclass(frozen=True)
class PluginRule:
    label: str
    pattern: re.Pattern[str]
    url: str
    method: str = "GET"
    params: dict[str, str] = field(default_factory=dict)

    def matches(self, bm: Bookmark) -> bool:
        return bool(self.pattern.search(bm.url or ""))

    def rendered_params(self, bm: Bookmark) -> dict[str, str]:
        """Each param value with the fav's fields interpolated in."""
        return {key: _render(value, bm) for key, value in self.params.items()}

    def href(self, bm: Bookmark) -> str:
        """Link target for a GET route: ``url`` with the params as a query string."""
        query = self.rendered_params(bm)
        if not query:
            return self.url
        sep = "&" if "?" in self.url else "?"
        return f"{self.url}{sep}{urlencode(query)}"


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
    """Load and compile the route list. A missing/empty file yields no routes."""
    p = Path(path)
    if not p.is_file():
        return []
    raw = json.loads(p.read_text())
    return [
        PluginRule(
            label=entry["label"],
            pattern=re.compile(entry["pattern"], re.IGNORECASE),
            url=entry["url"],
            method=entry.get("method", "GET").upper(),
            params=dict(entry.get("params", {})),
        )
        for entry in raw.get("plugins", [])
    ]


PLUGINS: list[PluginRule] = load_plugins(settings.plugins_config)


def plugins_for(bm: Bookmark) -> list[PluginRule]:
    return [rule for rule in PLUGINS if rule.matches(bm)]
