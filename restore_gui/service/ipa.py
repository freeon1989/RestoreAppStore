"""Локальные файлы IPA: список, проверка архива, незавершённые загрузки."""
from __future__ import annotations

import os
import re
import uuid
import zipfile
import plistlib
from pathlib import Path

from . import platform as platform_svc

# Незавершённые загрузки ipatool и наши промежуточные файлы.
# Крупные (>100 МБ) не удаляем молча — предлагаем пользователю.
HUGE_TEMP_BYTES = 100 * 1024 * 1024
_TEMP_NAME = re.compile(
    r"""(?:
        \.tmp$
        |\.tmp\.
        |\.ipa\.tmp
        |\.tmp\.dl-
        |\.downloading-
        |\.inprogress-
        |\.partial
        |\.part$
    )""",
    re.IGNORECASE | re.VERBOSE,
)

CORRUPT_TEXT = "Файл IPA повреждён или скачан не полностью — скачиваю заново."
CORRUPT_AGAIN = "Файл IPA повреждён или скачан не полностью. Попробуйте ещё раз позже."


def is_temp_name(path: Path | str) -> bool:
    name = Path(path).name
    if name.startswith("."):
        return True
    return bool(_TEMP_NAME.search(name))


def list_files(folder: Path) -> list[dict]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    rows = []
    for path in sorted(folder.glob("*.ipa"), key=lambda p: p.stat().st_mtime, reverse=True):
        if is_temp_name(path):
            continue
        info = inspect(path)
        rows.append({
            "path": str(path),
            "title": info.get("name") or path.stem,
            "info": _subtitle(info, path),
            "letter": (info.get("name") or path.stem)[:1].upper(),
            "tint": "",
            "icon": info.get("icon") or "",
            "bundle": info.get("bundle") or "",
            "version": info.get("version") or "",
            "platform": info.get("platform") or "",
        })
    return rows


def inspect(path: Path) -> dict:
    path = Path(path)
    info = {"name": path.stem, "bundle": "", "version": "", "icon": "", "platform": ""}
    try:
        with zipfile.ZipFile(path) as zf:
            plat, plist_name, data = _payload_plist(zf)
            if plat:
                info["platform"] = plat
            if not data:
                return info
            info["name"] = str(data.get("CFBundleDisplayName") or data.get("CFBundleName") or path.stem)
            info["bundle"] = str(data.get("CFBundleIdentifier") or "")
            info["version"] = str(data.get("CFBundleShortVersionString") or data.get("CFBundleVersion") or "")
            if not info["platform"]:
                info["platform"] = platform_svc.from_plist(data)
    except (OSError, zipfile.BadZipFile, plistlib.InvalidFileException, KeyError, ValueError):
        return info
    return info


def validate(path: Path | None, *, expected_size: int | None = None) -> dict:
    """Проверить, что IPA — настоящий zip с Payload/*.app/Info.plist.

    expected_size — полный размер из прогресса ipatool, если известен.
    """
    result = {"ok": False, "error": CORRUPT_AGAIN, "path": str(path or ""), "size": 0, "platform": ""}
    if not path:
        result["error"] = CORRUPT_AGAIN
        return result
    path = Path(path)
    result["path"] = str(path)
    if not path.is_file():
        result["error"] = "Файл IPA не найден после скачивания."
        return result
    size = path.stat().st_size
    result["size"] = size
    if size < 64:
        result["error"] = CORRUPT_TEXT
        return result
    if expected_size and expected_size >= 1024 * 1024 and size < int(expected_size * 0.85):
        result["error"] = CORRUPT_TEXT
        return result
    if not zipfile.is_zipfile(path):
        result["error"] = CORRUPT_TEXT
        return result
    try:
        with zipfile.ZipFile(path) as zf:
            # BadZipFile, если нет центрального каталога
            names = zf.namelist()
            plat, plist_name, data = _payload_plist(zf)
            if _looks_like_mac_archive(names, plat, data):
                result["platform"] = "mac"
            elif plat:
                result["platform"] = plat
            elif data:
                result["platform"] = platform_svc.from_plist(data) or "ios"
            if result["platform"] == "mac":
                result["ok"] = True
                result["error"] = ""
                return result
            if not plist_name or data is None:
                result["error"] = CORRUPT_TEXT
                return result
            zf.read(plist_name)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, plistlib.InvalidFileException, KeyError, ValueError):
        result["error"] = CORRUPT_TEXT
        return result
    result["ok"] = True
    result["error"] = ""
    return result


def staging_path(folder: Path, app_id: str | None = None, version_id: str | None = None, title: str = "app") -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stem = _safe_token(title, 40) or "app"
    aid = _safe_token(app_id, 24) or "id"
    ver = _safe_token(version_id, 16) or "latest"
    unique = uuid.uuid4().hex[:10]
    return folder / f"{stem}.downloading-{aid}-{ver}-{unique}.ipa"


def publish(src: Path, dest: Path) -> Path:
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        os.replace(src, dest)
    return dest


def remove_outputs(*paths: Path | None) -> None:
    for path in paths:
        if not path:
            continue
        path = Path(path)
        parent = path.parent
        name = path.name
        candidates = [path, Path(str(path) + ".tmp"), path.with_name(name + ".tmp")]
        if parent.is_dir():
            candidates.extend(parent.glob(name + ".tmp*"))
            # параллельные куски ipatool: file.ipa.tmp.dl-PID-...
            candidates.extend(parent.glob(name + ".tmp.dl-*"))
        seen = set()
        for item in candidates:
            try:
                key = str(item.resolve())
            except OSError:
                key = str(item)
            if key in seen or not item.is_file():
                continue
            seen.add(key)
            try:
                item.unlink()
            except OSError:
                pass


def find_output(dest: Path) -> Path | None:
    """Найти фактический файл после выхода ipatool: dest или его .tmp."""
    dest = Path(dest)
    candidates: list[Path] = []
    for item in (dest, Path(str(dest) + ".tmp"), dest.with_name(dest.name + ".tmp")):
        if item.is_file():
            candidates.append(item)
    if dest.parent.is_dir():
        for item in dest.parent.glob(dest.name + ".tmp*"):
            if item.is_file():
                candidates.append(item)
    # уникальные, сначала валидные zip, потом самые новые/крупные
    uniq: list[Path] = []
    seen = set()
    for item in candidates:
        try:
            key = str(item.resolve())
        except OSError:
            key = str(item)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    if not uniq:
        return None

    def sort_key(path: Path):
        valid = zipfile.is_zipfile(path)
        try:
            st = path.stat()
            return (1 if valid else 0, st.st_mtime, st.st_size)
        except OSError:
            return (0, 0, 0)

    uniq.sort(key=sort_key, reverse=True)
    return uniq[0]


def list_temps(folder: Path) -> list[dict]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    rows = []
    for path in folder.iterdir():
        if not path.is_file() or not is_temp_name(path):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        rows.append({"path": str(path), "name": path.name, "size": size, "huge": size >= HUGE_TEMP_BYTES})
    rows.sort(key=lambda r: r["size"], reverse=True)
    return rows


def clean_temps(folder: Path, *, include_huge: bool = False, skip: set[str] | None = None) -> dict:
    """Удалить незавершённые загрузки. Крупные — только если include_huge=True."""
    deleted = 0
    leftover = []
    skip = {os.path.normcase(os.path.abspath(p)) for p in (skip or set())}
    for item in list_temps(folder):
        path = Path(item["path"])
        try:
            key = os.path.normcase(os.path.abspath(path))
        except OSError:
            key = str(path)
        if key in skip:
            leftover.append(item)
            continue
        if item["huge"] and not include_huge:
            leftover.append(item)
            continue
        try:
            path.unlink()
            deleted += 1
        except OSError:
            leftover.append(item)
    return {"deleted": deleted, "leftover": leftover}


def leftover_hint(items: list[dict]) -> str:
    if not items:
        return ""
    first = items[0]
    size = _human(first["size"])
    name = first["name"]
    extra = f" и ещё {len(items) - 1}" if len(items) > 1 else ""
    return f"Найдена незавершённая загрузка «{name}» ({size}){extra}. Можно удалить, чтобы освободить место."


def _payload_plist(zf: zipfile.ZipFile) -> tuple[str, str | None, dict | None]:
    names = zf.namelist()
    plist_name = next((n for n in names if n.startswith("Payload/") and n.endswith(".app/Info.plist")), None)
    if not plist_name:
        mac_plist = next((n for n in names if n.endswith(".app/Info.plist") and ("Applications/" in n or n.startswith("Payload/"))), None)
        plist_name = mac_plist
    if not plist_name:
        if _looks_like_mac_archive(names, "", None):
            return "mac", None, None
        return "", None, None
    data = plistlib.loads(zf.read(plist_name))
    plat = platform_svc.from_plist(data)
    if _looks_like_mac_archive(names, plat, data):
        plat = "mac"
    return plat or "", plist_name, data


def _looks_like_mac_archive(names: list[str], plat: str, data: dict | None) -> bool:
    if plat == "mac":
        return True
    if any(n.startswith("Applications/") and n.endswith(".app/") or n.startswith("Applications/") and ".app/" in n for n in names):
        return True
    if any(n.lower().endswith(".pkg") for n in names) and not any(n.startswith("Payload/") for n in names):
        return True
    if data and platform_svc.from_plist(data) == "mac":
        return True
    return False


def _subtitle(info: dict, path: Path) -> str:
    human = _human(path.stat().st_size)
    parts = [part for part in (info.get("version"), human) if part]
    if info.get("platform") == "mac":
        parts.append("только для Mac")
    return " · ".join(parts) or human


def _human(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.1f} ГБ"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} МБ"
    return f"{max(1, size // 1024)} КБ"


def _safe_token(text, limit: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "", str(text or ""))
    return cleaned[:limit]


def already_has(folder: Path, stem_parts: list[str]) -> Path | None:
    folder = Path(folder)
    if not folder.is_dir():
        return None
    tokens = [p.lower() for p in stem_parts if p]
    for path in folder.glob("*.ipa"):
        if is_temp_name(path):
            continue
        name = path.stem.lower()
        if tokens and all(tok in name for tok in tokens):
            return path
    return None


def clear_folder(folder: Path) -> int:
    folder = Path(folder)
    if not folder.is_dir():
        return 0
    n = 0
    for path in list(folder.glob("*.ipa")) + list(folder.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".ipa" or is_temp_name(path):
            try:
                path.unlink()
                n += 1
            except OSError:
                pass
    return n
