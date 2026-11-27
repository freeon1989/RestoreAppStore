"""Каталоги данных, ресурсов и встроенных инструментов."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import restore_apps as core


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None))


def exe_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundle_dir() -> Path:
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        return Path(mei)
    return exe_dir()


def data_dir() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        # в тестах sandbox подменяет LOCALAPPDATA — уважаем её и на Linux
        if os.environ.get("LOCALAPPDATA"):
            root = Path(os.environ["LOCALAPPDATA"])
    path = root / core.APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_ipa_dir() -> Path:
    here = exe_dir()
    portable = here / "ipa"
    if not _is_frozen() or _writable(here):
        portable.mkdir(parents=True, exist_ok=True)
        return portable
    path = data_dir() / "ipa"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resource(*parts: str) -> Path | None:
    """Первый существующий файл среди папки сборки, assets и каталога exe."""
    rel = Path(*parts)
    here = Path(__file__).resolve().parents[2]
    candidates = [
        bundle_dir() / rel,
        bundle_dir() / rel.name,
        here / "assets" / rel,
        here / "assets" / rel.name,
        here / rel,
        exe_dir() / rel,
        exe_dir() / rel.name,
    ]
    for item in candidates:
        if item.is_file():
            return item
    return None


def tool_home() -> Path:
    path = data_dir() / "tool-home"
    (path / "AppData" / "Local").mkdir(parents=True, exist_ok=True)
    (path / "AppData" / "Roaming").mkdir(parents=True, exist_ok=True)
    return path


def account_home(account_id: str | None = None) -> Path:
    """Отдельный HOME для сессии ipatool-cpp. default/пусто — прежний tool-home."""
    if not account_id or account_id == "default":
        return tool_home()
    import re
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(account_id))[:64] or "account"
    path = data_dir() / "accounts" / safe / "home"
    (path / "AppData" / "Local").mkdir(parents=True, exist_ok=True)
    (path / "AppData" / "Roaming").mkdir(parents=True, exist_ok=True)
    return path


def find_ipatool() -> Path | None:
    names = ("ipatool-cpp.exe", "ipatool-cpp", "ipatool.exe", "ipatool")
    for name in names:
        found = resource(name)
        if found:
            return found
    extra = [
        bundle_dir() / "ipatool-cpp.exe",
        exe_dir() / "ipatool-cpp.exe",
        Path(__file__).resolve().parents[2] / "build" / "res" / "ipatool-cpp.exe",
    ]
    for item in extra:
        if item.is_file():
            return item
    import shutil
    for name in names:
        hit = shutil.which(name)
        if hit:
            return Path(hit)
    return None


def file_url(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.resolve().as_uri()


def logs_dir() -> Path:
    """Журналы запуска и работы: %LOCALAPPDATA%\\RestoreAppStore."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
                    or Path.home() / ".local" / "share")
    path = base / "RestoreAppStore"
    path.mkdir(parents=True, exist_ok=True)
    return path


def app_log_path() -> Path:
    return logs_dir() / "app.log"


def write_app_log(text: str) -> None:
    """Строка в app.log. Вызывающий уже убрал пароли и коды."""
    line = (text or "").rstrip()
    if not line:
        return
    from datetime import datetime, timezone, timedelta
    stamp = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with app_log_path().open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {line}\n")
    except OSError:
        pass


def log_path() -> Path:
    """Прежний путь оставлен для совместимости; новый журнал — app_log_path()."""
    return app_log_path()
