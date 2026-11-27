"""Самый ранний запуск: лог, путь к плагину qwindows, переменные Qt — до QApplication.

На Windows без platforms/qwindows.dll Qt показывает
«no Qt platform plugin could be initialized» и завершается, не доходя до Python.
Этот модуль ищет плагин в распакованном exe, выставляет QT_QPA_PLATFORM_PLUGIN_PATH
и пишет %LOCALAPPDATA%\\RestoreAppStore\\startup.log. Подробный отладчик плагинов Qt — только при RESTORE_DEBUG=1.
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOG_DIR_NAME = "RestoreAppStore"
LOG_NAME = "startup.log"

_log_path: Path | None = None
_handler_installed = False


def log_path() -> Path:
    global _log_path
    if _log_path is not None:
        return _log_path
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    folder = Path(base) / LOG_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    _log_path = folder / LOG_NAME
    return _log_path


def log(msg: str) -> None:
    try:
        path = log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


def frozen_roots() -> list[Path]:
    roots: list[Path] = []
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        roots.append(Path(mei))
    exe = Path(sys.executable).resolve().parent
    roots += [exe / "_internal", exe]
    # исходники: site-packages рядом с интерпретатором
    roots.append(Path(sys.prefix) / "Lib" / "site-packages")
    seen: set[str] = set()
    out = []
    for p in roots:
        s = str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def find_platforms() -> Path | None:
    names = ("qwindows.dll", "qwindows.so", "libqwindows.so")
    for root in frozen_roots():
        for cand in (
            root / "PySide6" / "plugins" / "platforms",
            root / "plugins" / "platforms",
            root / "PySide6" / "Qt" / "plugins" / "platforms",
        ):
            if any((cand / n).is_file() for n in names):
                return cand
    return None


def configure() -> Path:
    """Вызвать до создания QApplication. Возвращает путь к журналу."""
    path = log_path()
    # новый запуск — перезаписываем журнал, чтобы он не рос
    try:
        path.write_text("", encoding="utf-8")
    except OSError:
        pass
    now = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S %z")
    log(f"=== RestoreAppStore start {now} ===")
    log(f"python={sys.version}")
    log(f"executable={sys.executable}")
    log(f"frozen={getattr(sys, 'frozen', False)}")
    log(f"_MEIPASS={getattr(sys, '_MEIPASS', '')}")
    log(f"cwd={Path.cwd()}")
    debug = os.environ.get("RESTORE_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    platforms = find_platforms()
    if platforms is None:
        log("ERROR: qwindows plugin not found in bundle")
    else:
        qwindows = any(p.name.lower().startswith("qwindows") for p in platforms.iterdir()) if platforms.is_dir() else False
        log(f"platforms={platforms.name} qwindows={'yes' if qwindows else 'NO'}")
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
        os.environ["QT_PLUGIN_PATH"] = str(platforms.parent)
    if debug:
        os.environ.setdefault("QT_DEBUG_PLUGINS", "1")
    _install_qt_log(verbose=debug)
    return path


def _install_qt_log(verbose: bool = False) -> None:
    global _handler_installed
    if _handler_installed:
        return
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception as exc:  # noqa: BLE001 — сам импорт Qt тоже пишем в журнал
        log(f"QtCore import failed: {exc}\n{traceback.format_exc()}")
        return

    def handler(kind, ctx, text):
        try:
            if not verbose and kind in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
                return
            cat = getattr(ctx, "category", "") or ""
            log(f"qt[{int(kind)}] {cat} {text}")
        except Exception:
            pass

    qInstallMessageHandler(handler)
    _handler_installed = True
    import atexit
    atexit.register(lambda: qInstallMessageHandler(None))
    log("Qt message handler installed")


def log_exception(prefix: str, exc: BaseException | None = None) -> None:
    log(prefix)
    log(traceback.format_exc() if exc is None else f"{exc}\n{traceback.format_exc()}")
