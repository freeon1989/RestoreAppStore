
"""Публичный iTunes Search/Lookup и RSS топа — без ключа и без сторонних списков."""
from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request

TIMEOUT = 25
UA = "RestoreAppStore/2.0 (+https://github.com/freeon1989/RestoreAppStore)"


class ITunesError(Exception):
    pass


def _ctx():
    return ssl.create_default_context()


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ctx()) as resp:
            return resp.read()
    except OSError as exc:
        raise ITunesError(f"Нет ответа каталога App Store: {exc}") from exc


def lookup(app_id: str, country: str = "ru") -> dict | None:
    country = (country or "ru").lower()
    url = f"https://itunes.apple.com/lookup?id={urllib.parse.quote(str(app_id))}&country={urllib.parse.quote(country)}"
    data = json.loads(_get(url).decode("utf-8"))
    results = data.get("results") if isinstance(data, dict) else None
    if results:
        return _from_itunes(results[0])
    return None


def search(term: str, country: str = "ru", limit: int = 25) -> list[dict]:
    q = urllib.parse.urlencode({
        "term": term,
        "entity": "software",
        "country": (country or "ru").lower(),
        "limit": max(1, min(int(limit), 50)),
    })
    data = json.loads(_get(f"https://itunes.apple.com/search?{q}").decode("utf-8"))
    results = data.get("results") if isinstance(data, dict) else []
    return [_from_itunes(item) for item in results if isinstance(item, dict)]


def top_free(country: str = "ru", limit: int = 25) -> list[dict]:
    country = (country or "ru").lower()
    url = f"https://itunes.apple.com/{country}/rss/topfreeapplications/limit={int(limit)}/json"
    data = json.loads(_get(url).decode("utf-8"))
    entries = (((data or {}).get("feed") or {}).get("entry")) or []
    if isinstance(entries, dict):
        entries = [entries]
    out = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        app_id = str(((item.get("id") or {}).get("attributes") or {}).get("im:id") or "")
        name = str(((item.get("im:name") or {}).get("label") or ""))
        images = item.get("im:image") or []
        icon = ""
        if isinstance(images, list) and images:
            icon = str((images[-1] or {}).get("label") or "")
        genre = str(((item.get("category") or {}).get("attributes") or {}).get("label") or "")
        out.append({
            "id": app_id,
            "name": name,
            "bundle": "",
            "version": "",
            "price": "",
            "date": "",
            "kind": genre,
            "genre": genre,
            "icon": icon,
        })
    return out


def still_on_store(app_id: str, country: str = "ru") -> bool:
    return lookup(app_id, country) is not None


def _from_itunes(item: dict) -> dict:
    return {
        "id": str(item.get("trackId") or item.get("id") or ""),
        "name": str(item.get("trackName") or item.get("name") or ""),
        "bundle": str(item.get("bundleId") or ""),
        "version": str(item.get("version") or ""),
        "price": str(item.get("formattedPrice") or item.get("price") or ""),
        "date": str(item.get("releaseDate") or ""),
        "kind": str(item.get("primaryGenreName") or item.get("kind") or ""),
        "genre": str(item.get("primaryGenreName") or ""),
        "icon": str(item.get("artworkUrl100") or item.get("artworkUrl60") or ""),
    }
