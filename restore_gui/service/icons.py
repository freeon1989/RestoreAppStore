
"""Кэш иконок приложений из публичных URL iTunes.

Папка: %LOCALAPPDATA%\\RestoreAppStore\\cache\\icons.
Сеть только в рабочих потоках: cached_path() диск не качает.
"""
from __future__ import annotations

import hashlib
import ssl
import urllib.request
from pathlib import Path

from . import paths

UA = "RestoreAppStore/2.0 (+https://github.com/freeon1989/RestoreAppStore)"


def cache_dir() -> Path:
    folder = paths.logs_dir() / "cache" / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def cached_path(app_id: str, url: str = "") -> Path | None:
    """Уже скачанный файл, без обращения к сети."""
    dest = _dest(app_id, url)
    if dest is not None and dest.is_file() and dest.stat().st_size > 0:
        return dest
    # старый кэш без url в ключе
    if app_id:
        fallback = cache_dir() / f"{_digest(app_id, '')}.png"
        if fallback.is_file() and fallback.stat().st_size > 0:
            return fallback
    return None


def fetch(app_id: str, url: str) -> Path | None:
    """Скачать иконку в кэш. Вызывать не из потока интерфейса."""
    if not url or not url.startswith("https://"):
        return cached_path(app_id, url)
    hit = cached_path(app_id, url)
    if hit:
        return hit
    dest = _dest(app_id, url)
    if dest is None:
        return None
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


def local_path(app_id: str, url: str) -> Path | None:
    """Совместимость: только кэш, без сети (сеть — fetch)."""
    return cached_path(app_id, url)


def _digest(app_id: str, url: str) -> str:
    return hashlib.sha256(f"{app_id}:{url}".encode("utf-8")).hexdigest()[:24]


def _dest(app_id: str, url: str) -> Path | None:
    if not app_id and not url:
        return None
    return cache_dir() / f"{_digest(app_id or '', url or '')}.png"
