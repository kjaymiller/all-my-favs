"""Tests for the URL-route buttons (app/plugins.py).

A route sends a fav's fields to another service either as **url params** (GET — a link
with a query string) or as **body params** (POST — form fields). These exercise both,
plus matching, placeholder interpolation, and ruleset loading.
"""

import json
import re
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from app.plugins import PluginRule, load_plugins


def make_bm(**overrides):
    """A duck-typed stand-in for a Bookmark (plugins only read these attributes)."""
    fields = {
        "url": "https://youtu.be/abc123",
        "title": "A Video",
        "description": "watch this",
        "domain": "youtu.be",
        "tags": ["python", "web"],
    }
    fields.update(overrides)
    tags = [SimpleNamespace(name=name) for name in fields.pop("tags")]
    return SimpleNamespace(tags=tags, **fields)


def rule(method="GET", pattern=".", url="https://svc.example/add", params=None):
    return PluginRule(
        label="Send",
        pattern=re.compile(pattern, re.IGNORECASE),
        url=url,
        method=method,
        params=params or {},
    )


# --- matching -------------------------------------------------------------

def test_matches_on_url_regex_case_insensitive():
    yt = rule(pattern=r"youtube\.com|youtu\.be")
    assert yt.matches(make_bm(url="https://YouTu.be/x")) is True
    assert yt.matches(make_bm(url="https://example.com/x")) is False


def test_matches_dot_pattern_matches_every_url():
    assert rule(pattern=".").matches(make_bm(url="https://anything.test")) is True


def test_matches_handles_missing_url():
    assert rule(pattern="x").matches(make_bm(url=None)) is False


# --- url params (GET) -----------------------------------------------------

def test_get_href_appends_params_as_query_string():
    r = rule(
        method="GET",
        url="https://cms.example/new",
        params={"url": "{url}", "description": "{description}"},
    )
    href = r.href(make_bm(url="https://youtu.be/abc123", description="watch this"))
    base, query = href.split("?", 1)
    assert base == "https://cms.example/new"
    parsed = parse_qs(query)
    assert parsed["url"] == ["https://youtu.be/abc123"]
    assert parsed["description"] == ["watch this"]


def test_get_href_url_encodes_values():
    r = rule(method="GET", url="https://cms.example/new", params={"q": "{title}"})
    href = r.href(make_bm(title="a & b?c"))
    # The raw value must be percent-encoded, not leak into the query structure.
    assert "a & b?c" not in href
    assert parse_qs(urlsplit(href).query)["q"] == ["a & b?c"]


def test_get_href_uses_ampersand_when_url_already_has_query():
    r = rule(method="GET", url="https://cms.example/new?source=amf", params={"dom": "{domain}"})
    # the param is appended after the existing query, not with a second '?'
    assert "?source=amf&dom=" in r.href(make_bm())


def test_get_href_without_params_returns_url_unchanged():
    r = PluginRule(label="x", pattern=re.compile("."), url="https://cms.example/new")
    assert r.href(make_bm()) == "https://cms.example/new"


# --- body params (POST) ---------------------------------------------------

def test_post_rendered_params_interpolate_fav_fields():
    r = rule(method="POST", url="https://svc.example/add", params={"url": "{url}", "tags": "{tags}"})
    body = r.rendered_params(make_bm(url="https://youtu.be/abc123", tags=["a", "b"]))
    assert body == {"url": "https://youtu.be/abc123", "tags": "a,b"}


def test_post_method_normalized_to_uppercase_on_load(tmp_path):
    path = tmp_path / "plugins.json"
    path.write_text(
        json.dumps(
            {"plugins": [{"label": "L", "pattern": ".", "url": "https://x", "method": "post"}]}
        )
    )
    assert load_plugins(path)[0].method == "POST"


# --- placeholders ---------------------------------------------------------

def test_all_known_placeholders_interpolate():
    r = rule(
        params={"u": "{url}", "t": "{title}", "d": "{description}", "g": "{tags}", "dom": "{domain}"}
    )
    out = r.rendered_params(make_bm())
    assert out == {
        "u": "https://youtu.be/abc123",
        "t": "A Video",
        "d": "watch this",
        "g": "python,web",
        "dom": "youtu.be",
    }


def test_unknown_placeholder_renders_empty():
    assert rule(params={"x": "{nope}"}).rendered_params(make_bm()) == {"x": ""}


def test_missing_fields_render_empty_not_none():
    out = rule(params={"t": "{title}", "d": "{description}"}).rendered_params(
        make_bm(title=None, description=None)
    )
    assert out == {"t": "", "d": ""}


# --- loading --------------------------------------------------------------

def test_load_plugins_parses_both_methods(tmp_path):
    path = tmp_path / "plugins.json"
    path.write_text(
        json.dumps(
            {
                "plugins": [
                    {
                        "label": "Microblog",
                        "pattern": ".",
                        "url": "https://cms.example/new",
                        "params": {"url": "{url}"},
                    },
                    {
                        "label": "wytcher",
                        "pattern": r"youtu\.be",
                        "url": "https://svc.example/add",
                        "method": "POST",
                        "params": {"url": "{url}"},
                    },
                ]
            }
        )
    )
    rules = load_plugins(path)
    assert [r.label for r in rules] == ["Microblog", "wytcher"]
    assert rules[0].method == "GET"  # defaults to GET (url params)
    assert rules[1].method == "POST"  # body params


def test_load_plugins_defaults_method_to_get(tmp_path):
    path = tmp_path / "plugins.json"
    path.write_text(json.dumps({"plugins": [{"label": "L", "pattern": ".", "url": "https://x"}]}))
    assert load_plugins(path)[0].method == "GET"


def test_load_plugins_missing_file_returns_empty(tmp_path):
    assert load_plugins(tmp_path / "does-not-exist.json") == []


def test_load_plugins_empty_ruleset_returns_empty(tmp_path):
    path = tmp_path / "plugins.json"
    path.write_text(json.dumps({"plugins": []}))
    assert load_plugins(path) == []
