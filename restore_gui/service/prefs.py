
"""Сохранение настроек оформления и папок в JSON без секретов."""
from __future__ import annotations

import json
from pathlib import Path

from restore_gui import theme
from . import paths

KEYS = {
    "themeMode": ("system", lambda v: v in ("system", "light", "dark")),
    "accentName": (theme.DEFAULT_ACCENT, lambda v: v in theme.ACCENTS),
    "heroineName": (theme.DEFAULT_HEROINE, lambda v: v in theme.HEROINES),
    "country": ("ru", lambda v: isinstance(v, str) and 0 < len(v) <= 2),
    "deleteAfterInstall": (False, lambda v: isinstance(v, bool)),
    "notifyDone": (True, lambda v: isinstance(v, bool)),
    "autoUpdate": (True, lambda v: isinstance(v, bool)),
    "skipVersion": ("", lambda v: isinstance(v, str) and len(v) < 32),
}


def settings_path() -> Path:
    return paths.data_dir() / "settings.json"


def load() -> dict:
    data = {key: default for key, (default, _) in KEYS.items()}
    data["ipaDir"] = str(paths.default_ipa_dir())
    path = settings_path()
    if not path.is_file():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return data
    if not isinstance(raw, dict):
        return data
    for key, (default, ok) in KEYS.items():
        value = raw.get(key, default)
        data[key] = value if ok(value) else default
    folder = raw.get("ipaDir")
    if isinstance(folder, str) and folder and Path(folder).is_dir():
        data["ipaDir"] = folder
    return data


def save(data: dict) -> None:
    out = {}
    for key, (default, ok) in KEYS.items():
        value = data.get(key, default)
        out[key] = value if ok(value) else default
    default_ipa = str(paths.default_ipa_dir())
    folder = data.get("ipaDir") or default_ipa
    if folder != default_ipa:
        out["ipaDir"] = folder
    path = settings_path()
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
