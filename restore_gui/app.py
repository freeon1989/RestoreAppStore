
"""Запуск окна RestoreAppStore: Qt Quick + Backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from restore_gui.service import paths

QML_DIR = Path(__file__).resolve().parent / "qml"


def qt_environment() -> None:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    os.environ.setdefault("QT_D3D_NO_FLIP", "1")
    mei = Path(getattr(sys, "_MEIPASS", "") or "")
    if mei.name.startswith("_MEI"):
        os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")


def create(app, background=True, visible=True):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine

    from restore_gui.backend import Backend

    fonts = Path(__file__).resolve().parent / "fonts"
    for ttf in sorted(fonts.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    backend = Backend(background=background)
    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("P", backend.current_palette())
    backend.paletteChanged.connect(lambda: ctx.setContextProperty("P", backend.current_palette()))
    ctx.setContextProperty("startVisible", visible)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    return engine, backend


def single_instance():
    from PySide6.QtCore import QLockFile

    paths.data_dir().mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(paths.data_dir() / "restore.lock"))
    lock.setStaleLockTime(0)
    return lock if lock.tryLock(0) else None


def check_ui(report) -> int:
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    from PySide6.QtWidgets import QApplication

    messages = []

    def handler(kind, ctx, text):
        if kind != QtMsgType.QtDebugMsg and not str(ctx.category or "").startswith("qt.qpa.fonts"):
            messages.append(text)

    qInstallMessageHandler(handler)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    engine, _backend = create(app, background=False, visible=False)
    for _ in range(5):
        app.processEvents()
    ok = bool(engine.rootObjects()) and not messages
    Path(report).write_text(("OK" if ok else "FAIL") + "\n" + "\n".join(messages), encoding="utf-8")
    return 0 if ok else 1


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--apply-update":
        from restore_gui.service.updater import apply_update
        sys.exit(apply_update(sys.argv[2:]))
    if "--diag-device" in sys.argv:
        from restore_gui.service.device import write_diagnostics
        raise SystemExit(write_diagnostics())
    qt_environment()
    if "--check-ui" in sys.argv:
        report = sys.argv[sys.argv.index("--check-ui") + 1]
        try:
            sys.exit(check_ui(report))
        except Exception:
            import traceback
            Path(report).write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
            sys.exit(1)

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    import restore_apps as core

    app = QApplication(sys.argv)
    app.setApplicationName(core.DISPLAY_NAME)
    translator = QTranslator(app)
    if translator.load(QLocale("ru_RU"), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    icon = paths.resource("icon.ico")
    if icon:
        app.setWindowIcon(QIcon(str(icon)))
    lock = single_instance()
    if lock is None:
        QMessageBox.information(None, core.DISPLAY_NAME,
                                f"{core.DISPLAY_NAME} уже запущена — её окно открыто или ещё запускается.")
        sys.exit(0)
    engine, backend = create(app)
    if not engine.rootObjects():
        sys.exit("Не удалось загрузить интерфейс (qml/Main.qml).")
    app.aboutToQuit.connect(backend.shutdown)
    code = app.exec()
    lock.unlock()
    sys.exit(code)
