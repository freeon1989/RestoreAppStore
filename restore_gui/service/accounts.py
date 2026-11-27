"""Список Apple ID на устройстве: только адрес и витрина, без паролей."""
from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from . import paths
from . import regions

SCHEMA_KEYS = ("id", "email", "storefront")


def _path() -> Path:
    return paths.data_dir() / "accounts.json"


def load() -> dict:
    data = {"current": "", "accounts": []}
    path = _path()
    if not path.is_file():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return data
    if not isinstance(raw, dict):
        return data
    rows = []
    for item in raw.get("accounts") or []:
        if not isinstance(item, dict):
            continue
        email = str(item.get("email") or "").strip()
        account_id = str(item.get("id") or "").strip()
        if not email or not account_id:
            continue
        # на диск пароль никогда не пишем — даже если старый файл его содержит
        rows.append({
            "id": account_id,
            "email": email,
            "storefront": regions.parse_storefront(item.get("storefront") or "") or str(item.get("storefront") or "").lower()[:2],
        })
    current = str(raw.get("current") or "")
    if current not in {row["id"] for row in rows}:
        current = rows[0]["id"] if rows else ""
    return {"current": current, "accounts": rows}


def save(data: dict) -> None:
    rows = []
    for item in data.get("accounts") or []:
        if not isinstance(item, dict):
            continue
        email = str(item.get("email") or "").strip()
        account_id = str(item.get("id") or "").strip()
        if not email or not account_id:
            continue
        rows.append({
            "id": account_id,
            "email": email,
            "storefront": str(item.get("storefront") or ""),
        })
    current = str(data.get("current") or "")
    if current not in {row["id"] for row in rows}:
        current = rows[0]["id"] if rows else ""
    payload = {"current": current, "accounts": rows}
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert(email: str, storefront: str = "", account_id: str | None = None) -> dict:
    data = load()
    email = (email or "").strip()
    storefront = regions.parse_storefront(storefront) or (storefront or "").strip().lower()
    found = None
    if account_id:
        found = next((row for row in data["accounts"] if row["id"] == account_id), None)
    if found is None and email:
        found = next((row for row in data["accounts"] if row["email"].lower() == email.lower()), None)
    if found is None:
        found = {
            "id": account_id or _new_id(email),
            "email": email,
            "storefront": storefront,
        }
        data["accounts"].append(found)
    else:
        if email:
            found["email"] = email
        if storefront:
            found["storefront"] = storefront
    data["current"] = found["id"]
    save(data)
    return dict(found)


def remove(account_id: str) -> dict:
    data = load()
    data["accounts"] = [row for row in data["accounts"] if row["id"] != account_id]
    if data["current"] == account_id:
        data["current"] = data["accounts"][0]["id"] if data["accounts"] else ""
    save(data)
    return data


def set_current(account_id: str) -> dict:
    data = load()
    if any(row["id"] == account_id for row in data["accounts"]):
        data["current"] = account_id
        save(data)
    return data


def find(account_id: str) -> dict | None:
    return next((row for row in load()["accounts"] if row["id"] == account_id), None)


def find_by_storefront(code: str, *, exclude: str = "") -> dict | None:
    code = (code or "").lower()
    if not code:
        return None
    for row in load()["accounts"]:
        if row["id"] == exclude:
            continue
        if (row.get("storefront") or "").lower() == code:
            return row
    return None


def find_by_storefronts(codes: list[str], *, exclude: str = "") -> dict | None:
    for code in codes:
        hit = find_by_storefront(code, exclude=exclude)
        if hit:
            return hit
    return None


def _new_id(email: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (email or "").split("@")[0].lower()).strip("-")[:24]
    return (slug + "-" if slug else "") + uuid.uuid4().hex[:10]


def home_for(account_id: str | None) -> Path:
    return paths.account_home(account_id)


def delete_home(account_id: str) -> None:
    if not account_id or account_id == "default":
        return
    path = paths.account_home(account_id)
    # только подкаталог аккаунта, не общий tool-home
    root = paths.data_dir() / "accounts"
    try:
        if root in path.parents or path.parent == root:
            shutil.rmtree(path.parent if path.name == "home" else path, ignore_errors=True)
    except OSError:
        pass
