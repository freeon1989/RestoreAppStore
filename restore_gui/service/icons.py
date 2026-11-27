
"""Кэш иконок приложений из публичных URL iTunes."""
from __future__ import annotations

import hashlib
import ssl
import urllib.request
from pathlib import Path

from . import paths

UA = "RestoreAppStore/2.0 (+https://github.com/freeon1989/RestoreAppStore)"


def cache_dir() -> Path:
    folder = paths.data_dir() / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def local_path(app_id: str, url: str) -> Path | None:
    if not url or not url.startswith("https://"):
        return None
    digest = hashlib.sha256(f"{app_id}:{url}".encode("utf-8")).hexdigest()[:24]
    dest = cache_dir() / f"{digest}.png"
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as resp:
            data = resp.read()
        if not data:
            return None
        dest.write_bytes(data)
        return dest
    except OSError:
        return None
