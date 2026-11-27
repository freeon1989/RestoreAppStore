"""Публичный iTunes Search/Lookup и RSS топа — без ключа и без сторонних списков."""
from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request

from .prices import format_price

TIMEOUT = 25
UA = "RestoreAppStore/2.0 (+https://github.com/freeon1989/RestoreAppStore)"

# Жанры каталога (идентификаторы Apple) в том же порядке, что вкладки в интерфейсе.
CATALOG_GENRES: list[tuple[str, int | None]] = [
    ("Все", None),
    ("Бизнес", 6000),
    ("Еда и напитки", 6023),
    ("Образование", 6017),
    ("Покупки", 6024),
    ("Производительность", 6007),
    ("Развлечения", 6016),
    ("Социальные сети", 6005),
    ("Утилиты", 6002),
    ("Финансы", 6015),
    ("Фото и видео", 6008),
    ("Здоровье", 6013),
]

# Известные приложения, которых часто нет в российской витрине. Имя — запасное, если lookup пуст.
CURATED_APPS: list[tuple[int, str]] = [
    (389801252, "Instagram"),
    (310633997, "WhatsApp Messenger"),
    (284882215, "Facebook"),
    (333903271, "X"),
    (835599320, "TikTok"),
    (324684580, "Spotify"),
    (544007664, "YouTube"),
    (431946152, "Viber"),
    (414478124, "Waze"),
    (387682726, "Discord"),
]


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
    found = lookup_many([app_id], country)
    return found.get(str(app_id))


def lookup_many(app_ids: list[str], country: str = "ru") -> dict[str, dict]:
    country = (country or "ru").lower()
    ids = []
    seen = set()
    for raw in app_ids:
        app_id = str(raw or "").strip()
        if app_id and app_id not in seen:
            seen.add(app_id)
            ids.append(app_id)
    out: dict[str, dict] = {}
    for start in range(0, len(ids), 40):
        chunk = ids[start:start + 40]
        url = (
            "https://itunes.apple.com/lookup?"
            + urllib.parse.urlencode({"id": ",".join(chunk), "country": country})
        )
        data = json.loads(_get(url).decode("utf-8"))
        results = data.get("results") if isinstance(data, dict) else []
        for item in results or []:
            if isinstance(item, dict):
                row = _from_itunes(item)
                if row["id"]:
                    out[row["id"]] = row
    return out


def search(term: str, country: str = "ru", limit: int = 25, genre_id: int | None = None) -> list[dict]:
    query = {
        "term": term or "app",
        "entity": "software",
        "country": (country or "ru").lower(),
        "limit": max(1, min(int(limit), 50)),
    }
    if genre_id:
        query["genreId"] = int(genre_id)
    data = json.loads(_get(f"https://itunes.apple.com/search?{urllib.parse.urlencode(query)}").decode("utf-8"))
    results = data.get("results") if isinstance(data, dict) else []
    return [_from_itunes(item) for item in results if isinstance(item, dict)]


def top_free(country: str = "ru", limit: int = 25, genre_id: int | None = None) -> list[dict]:
    country = (country or "ru").lower()
    path = f"https://itunes.apple.com/{country}/rss/topfreeapplications/limit={int(limit)}"
    if genre_id:
        path += f"/genre={int(genre_id)}"
    data = json.loads(_get(path + "/json").decode("utf-8"))
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
        artist = str(((item.get("im:artist") or {}).get("label") or ""))
        out.append({
            "id": app_id,
            "name": name,
            "bundle": "",
            "version": "",
            "price": "Бесплатно",
            "date": "",
            "kind": genre,
            "genre": genre,
            "icon": icon,
            "developer": artist,
            "onStore": True,
        })
    return out


def catalog(country: str = "ru", genre: str = "Все", limit: int = 25) -> list[dict]:
    """Список для раздела «Каталог»: топ жанра, для «Все» ещё известные приложения вне витрины."""
    country = (country or "ru").lower()
    genre_id = None
    for name, ident in CATALOG_GENRES:
        if name == genre:
            genre_id = ident
            break
    rows = top_free(country, limit=limit, genre_id=genre_id)
    if genre in ("Все", "", None):
        rows = _merge(rows, _curated(country))
    elif not rows:
        rows = search("app", country, limit=limit, genre_id=genre_id)
    return rows


def still_on_store(app_id: str, country: str = "ru") -> bool:
    return lookup(app_id, country) is not None


def category_names() -> list[str]:
    return [name for name, _ident in CATALOG_GENRES]


def _curated(country: str) -> list[dict]:
    ids = [str(app_id) for app_id, _name in CURATED_APPS]
    names = {str(app_id): name for app_id, name in CURATED_APPS}
    found_ru: dict[str, dict] = {}
    found_us: dict[str, dict] = {}
    try:
        found_ru = lookup_many(ids, country)
    except ITunesError:
        pass
    missing = [app_id for app_id in ids if app_id not in found_ru]
    if missing:
        try:
            found_us = lookup_many(missing, "us")
        except ITunesError:
            pass
    out = []
    for app_id in ids:
        if app_id in found_ru:
            row = dict(found_ru[app_id])
            row["onStore"] = True
            out.append(row)
        elif app_id in found_us:
            row = dict(found_us[app_id])
            row["onStore"] = False
            row["genre"] = "Нет в российской витрине"
            row["kind"] = row.get("kind") or "Нет в российской витрине"
            out.append(row)
        else:
            out.append({
                "id": app_id,
                "name": names.get(app_id, app_id),
                "bundle": "",
                "version": "",
                "price": "",
                "date": "",
                "kind": "Нет в российской витрине",
                "genre": "Нет в российской витрине",
                "icon": "",
                "developer": "",
                "onStore": False,
            })
    return out


def _merge(primary: list[dict], extra: list[dict]) -> list[dict]:
    seen = {str(item.get("id") or "") for item in primary}
    out = list(primary)
    for item in extra:
        app_id = str(item.get("id") or "")
        if app_id and app_id not in seen:
            seen.add(app_id)
            out.append(item)
    return out


def _from_itunes(item: dict, country: str = "ru") -> dict:
    icon = str(item.get("artworkUrl512") or item.get("artworkUrl100") or item.get("artworkUrl60") or "")
    return {
        "id": str(item.get("trackId") or item.get("id") or ""),
        "name": str(item.get("trackName") or item.get("name") or ""),
        "bundle": str(item.get("bundleId") or ""),
        "version": str(item.get("version") or ""),
        "price": format_price(item.get("formattedPrice") or item.get("price") or ""),
        "date": str(item.get("releaseDate") or ""),
        "kind": str(item.get("primaryGenreName") or item.get("kind") or ""),
        "genre": str(item.get("primaryGenreName") or ""),
        "icon": icon,
        "developer": str(item.get("artistName") or ""),
        "onStore": True,
        "country": country,
    }
