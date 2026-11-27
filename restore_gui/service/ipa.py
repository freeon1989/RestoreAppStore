
"""Локальные файлы IPA: список, разбор Info.plist, очистка папки."""
from __future__ import annotations

import plistlib
import zipfile
from pathlib import Path


def list_files(folder: Path) -> list[dict]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    rows = []
    for path in sorted(folder.glob("*.ipa"), key=lambda p: p.stat().st_mtime, reverse=True):
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
        })
    return rows


def inspect(path: Path) -> dict:
    path = Path(path)
    info = {"name": path.stem, "bundle": "", "version": "", "icon": ""}
    try:
        with zipfile.ZipFile(path) as zf:
            plist_name = next((n for n in zf.namelist() if n.startswith("Payload/") and n.endswith(".app/Info.plist")), None)
            if not plist_name:
                return info
            data = plistlib.loads(zf.read(plist_name))
            info["name"] = str(data.get("CFBundleDisplayName") or data.get("CFBundleName") or path.stem)
            info["bundle"] = str(data.get("CFBundleIdentifier") or "")
            info["version"] = str(data.get("CFBundleShortVersionString") or data.get("CFBundleVersion") or "")
    except (OSError, zipfile.BadZipFile, plistlib.InvalidFileException, KeyError, ValueError):
        return info
    return info


def clear_folder(folder: Path) -> int:
    folder = Path(folder)
    if not folder.is_dir():
        return 0
    n = 0
    for path in folder.glob("*.ipa"):
        try:
            path.unlink()
            n += 1
        except OSError:
            pass
    return n


def already_has(folder: Path, stem_parts: list[str]) -> Path | None:
    folder = Path(folder)
    if not folder.is_dir():
        return None
    tokens = [p.lower() for p in stem_parts if p]
    for path in folder.glob("*.ipa"):
        name = path.stem.lower()
        if tokens and all(tok in name for tok in tokens):
            return path
    return None


def _subtitle(info: dict, path: Path) -> str:
    size = path.stat().st_size
    if size >= 1024 * 1024:
        human = f"{size / (1024 * 1024):.1f} МБ"
    else:
        human = f"{max(1, size // 1024)} КБ"
    parts = [part for part in (info.get("version"), human) if part]
    return " · ".join(parts) or human
