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
    found = lookup_many([app_id], country, fallback=False)
    return found.get(str(app_id))


def lookup_many(app_ids: list[str], country: str = "ru", *, fallback: bool = False) -> dict[str, dict]:
    country = (country or "ru").lower()
    ids = _unique_ids(app_ids)
    if not ids:
        return {}
    if fallback:
        return lookup_anywhere(ids, prefer=country)
    return _lookup_ids(ids, country)


def lookup_anywhere(app_ids: list[str], prefer: str = "ru", *, force: bool = False,
                    bundles: dict[str, str] | None = None) -> dict[str, dict]:
    """Искать метаданные и иконки по нескольким витринам. Ненайденные кэшируются на 2 часа."""
    from . import regions
    ids = _unique_ids(app_ids)
    out: dict[str, dict] = {}
    if not ids:
        return out
    miss = set() if force else _missed(ids)
    pending = [app_id for app_id in ids if app_id not in miss]
    order = _storefront_order(prefer)
    for country in order:
        if not pending:
            break
        try:
            found = _lookup_ids(pending, country)
        except ITunesError:
            continue
        out.update(found)
        pending = [app_id for app_id in pending if app_id not in out]
    if pending and bundles:
        leftover = []
        for app_id in pending:
            bundle = (bundles or {}).get(app_id) or ""
            if not bundle:
                leftover.append(app_id)
                continue
            row = lookup_bundle(bundle, prefer)
            if row:
                # сохраняем исходный track id покупки
                row = dict(row)
                row["id"] = app_id
                out[app_id] = row
            else:
                leftover.append(app_id)
        pending = leftover
    if pending and not force:
        _remember_miss(pending)
    return out


def lookup_bundle(bundle: str, prefer: str = "ru") -> dict | None:
    bundle = (bundle or "").strip()
    if not bundle:
        return None
    for country in _storefront_order(prefer):
        url = "https://itunes.apple.com/lookup?" + urllib.parse.urlencode({"bundleId": bundle, "country": country})
        try:
            data = json.loads(_get(url).decode("utf-8"))
        except ITunesError:
            continue
        results = data.get("results") if isinstance(data, dict) else []
        for item in results or []:
            if isinstance(item, dict):
                row = _from_itunes(item, country)
                if row.get("id") or row.get("bundle"):
                    return row
    return None


def availability(app_id: str, countries: list[str] | None = None) -> dict:
    """В каких витринах приложение есть (для карточки)."""
    from . import regions
    app_id = str(app_id or "").strip()
    countries = countries or [code for code, _name in regions.STOREFRONTS[:12]]
    present, missing = [], []
    if not app_id:
        return {"present": present, "missing": missing, "text": ""}
    for country in countries:
        try:
            found = _lookup_ids([app_id], country)
        except ITunesError:
            continue
        if app_id in found:
            present.append(country)
        else:
            missing.append(country)
    from .regions import availability_text
    return {"present": present, "missing": missing, "text": availability_text(present, missing)}


def clear_miss_cache() -> None:
    path = _miss_path()
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def _unique_ids(app_ids: list[str]) -> list[str]:
    ids, seen = [], set()
    for raw in app_ids:
        app_id = str(raw or "").strip()
        if app_id and app_id not in seen:
            seen.add(app_id)
            ids.append(app_id)
    return ids


def _lookup_ids(ids: list[str], country: str) -> dict[str, dict]:
    country = (country or "ru").lower()
    out: dict[str, dict] = {}
    for start in range(0, len(ids), 100):
        chunk = ids[start:start + 100]
        url = (
            "https://itunes.apple.com/lookup?"
            + urllib.parse.urlencode({"id": ",".join(chunk), "country": country})
        )
        data = json.loads(_get(url).decode("utf-8"))
        results = data.get("results") if isinstance(data, dict) else []
        for item in results or []:
            if isinstance(item, dict):
                row = _from_itunes(item, country)
                if row["id"]:
                    out[row["id"]] = row
    return out


def _storefront_order(prefer: str) -> list[str]:
    from . import regions
    prefer = (prefer or "ru").lower()
    order = []
    for code in [prefer, "us", *regions.ICON_STOREFRONTS]:
        if code and code not in order:
            order.append(code)
    return order


def _miss_path():
    from . import paths
    folder = paths.data_dir() / "cache"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "lookup-miss.json"


def _missed(ids: list[str]) -> set[str]:
    import time
    path = _miss_path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    now = time.time()
    ttl = 2 * 3600
    out = set()
    for app_id in ids:
        stamp = data.get(app_id)
        if isinstance(stamp, (int, float)) and now - stamp < ttl:
            out.add(app_id)
    return out


def _remember_miss(ids: list[str]) -> None:
    import time
    path = _miss_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    now = time.time()
    for app_id in ids:
        data[str(app_id)] = now
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


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
            found_us = lookup_anywhere(missing, prefer="us")
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


def _artwork(item: dict) -> str:
    for key in ("artworkUrl512", "artworkUrl100", "artworkUrl60", "artworkUrl160", "artwork", "artworkUrl"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith("https://"):
            return value
    return ""


def _from_itunes(item: dict, country: str = "ru") -> dict:
    return {
        "id": str(item.get("trackId") or item.get("id") or ""),
        "name": str(item.get("trackName") or item.get("name") or ""),
        "bundle": str(item.get("bundleId") or ""),
        "version": str(item.get("version") or ""),
        "price": format_price(item.get("formattedPrice") or item.get("price") or ""),
        "date": str(item.get("releaseDate") or ""),
        "kind": str(item.get("primaryGenreName") or item.get("kind") or ""),
        "genre": str(item.get("primaryGenreName") or ""),
        "icon": _artwork(item),
        "developer": str(item.get("artistName") or item.get("sellerName") or ""),
        "onStore": True,
        "country": country,
    }
