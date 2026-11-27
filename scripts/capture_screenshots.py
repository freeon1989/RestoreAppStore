#!/usr/bin/env python3
"""Снимки интерфейса в демонстрационном режиме: без сети, без настоящего Apple ID."""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import sandbox  # noqa: E402 — до restore_apps, изолированные папки

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if not os.environ.get("DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QObject, QMetaObject, QPoint, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QCursor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PIL import Image, ImageGrab  # noqa: E402

from restore_gui import app as gui  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

def pump(app, n=12):
    for _ in range(n):
        app.processEvents()


def settle(app, seconds=0.8):
    pump(app, 10)
    time.sleep(seconds)
    pump(app, 10)


def qimage_to_pil(qimg: QImage) -> Image.Image:
    qimg = qimg.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.bits()
    buf = bytes(ptr) if not hasattr(ptr, "tobytes") else ptr.tobytes()
    # PySide6 QImage.bits() may be a memoryview / sip.array
    try:
        raw = ptr.tobytes()
    except AttributeError:
        raw = bytes(ptr)
    return Image.frombytes("RGBA", (w, h), raw)


def as_item(obj):
    if isinstance(obj, QQuickItem):
        return obj
    # findChildren returns QObject*; try to use the same pointer as QQuickItem
    return obj

def grab_item(item, timeout_ms=2000):
    item = as_item(item)
    if not hasattr(item, "grabToImage"):
        print("  no grabToImage on", type(item), item.metaObject().className())
        return None
    result = []
    loop = QEventLoop()

    def done(img):
        if img is not None:
            result.append(img.image())
        loop.quit()

    ok = item.grabToImage(done)
    if not ok:
        return None
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result:
        return None
    return qimage_to_pil(result[0])


def save(win, name, overlay_item=None):
    path = OUT / name
    QCursor.setPos(QPoint(2, 2))
    try:
        QTest.mouseMove(win, QPoint(8, 8))
    except Exception:
        pass
    app = QApplication.instance()
    pump(app, 16)
    # Кадр самого окна Qt — в нём Popup.Item и Drawer.
    qimg = win.grabWindow()
    im = qimage_to_pil(qimg)
    # grabWindow уже включает Popup.Item и Drawer
    im.convert("RGB").save(str(path), "PNG")
    print(f"wrote {path} {path.stat().st_size}")


def find(win, prefix):
    for typ in (QQuickItem, QObject):
        for o in win.findChildren(typ):
            if o.metaObject().className().startswith(prefix):
                return o
    raise RuntimeError(f"не найден {prefix}")


def mute_transitions(item):
    """Убрать анимацию появления, чтобы попап уже был непрозрачным в кадре."""
    with_enter = []
    for o in [item, *item.findChildren(QObject)]:
        if hasattr(o, "setProperty"):
            # enter/exit — свойства Popup
            pass
    if hasattr(item, "setProperty"):
        item.setProperty("enter", None)
        item.setProperty("exit", None)
        item.setProperty("opacity", 1.0)


def main():
    app = QApplication.instance() or QApplication([])
    engine, b = gui.create(app, background=False, visible=True)
    if not engine.rootObjects():
        sys.exit("не удалось загрузить QML")
    win = engine.rootObjects()[0]
    assert isinstance(win, QQuickWindow)
    win.setProperty("width", 1240)
    win.setProperty("height", 840)
    win.setProperty("x", 0)
    win.setProperty("y", 0)
    win.show()
    win.raise_()
    print("platform", app.platformName())
    b.themeMode = "light"
    b.accentName = "emerald"
    b.heroineName = "mira"
    # Демо-состояние: вымышленный аккаунт, без пароля и без сети
    b.seed_demo()
    settle(app)

    b.showPage("home")
    settle(app, 1.4)
    save(win, "home.png")

    b.showPage("apps")
    settle(app)
    save(win, "apps.png")

    b.showPage("home")
    settle(app, 0.5)
    b.openDetail("popular", 0)
    b.detailChecks = {
        "acc": {"text": "✓ есть в истории (демо-данные)", "kind": "ok"},
        "phone": {"text": "подключён (демо)", "kind": "ok"},
        "store": {"text": "удалено из App Store (ru)", "kind": "warn"},
    }
    b.versionMode = "none"
    settle(app, 1.0)
    detail = find(win, "DetailPanel")
    mute_transitions(detail)
    if not detail.property("visible"):
        QMetaObject.invokeMethod(detail, "open", Qt.DirectConnection)
        settle(app, 0.6)
    print("detail visible", detail.property("visible"), "w", detail.property("width"), "h", detail.property("height"), "x", detail.property("x"))
    save(win, "detail.png", overlay_item=detail)
    b.closeDetail()
    pump(app, 10)

    b.showPage("home")
    b.closeDetail()
    settle(app, 0.5)
    sw = find(win, "SettingsWindow")
    mute_transitions(sw)
    sw.setProperty("section", 0)
    QMetaObject.invokeMethod(sw, "open", Qt.DirectConnection)
    settle(app, 1.0)
    print("settings visible", sw.property("visible"), "w", sw.property("width"), "h", sw.property("height"), "x", sw.property("x"), "y", sw.property("y"), "opacity", sw.property("opacity"))
    save(win, "settings.png", overlay_item=sw)
    QMetaObject.invokeMethod(sw, "close", Qt.DirectConnection)
    sw.setProperty("visible", False)
    settle(app)

    b.themeMode = "dark"
    b.showPage("home")
    settle(app, 1.4)
    save(win, "dark.png")

    b.themeMode = "light"
    b.deviceState = "none"
    b.deviceText = "Подключите iPhone кабелем"
    b.showPage("home")
    settle(app, 1.0)
    save(win, "device-hint.png")
    b.deviceState = "ok"
    b.deviceText = "iPhone (демо)"

    b.loggedIn, b.account = False, ""
    b.openLogin("Демонстрация окна входа. Пароль вводить не нужно.")
    settle(app, 1.0)
    login = None
    for o in win.findChildren(QQuickItem):
        name = o.metaObject().className()
        if name.startswith("Modal") or name.startswith("login"):
            if o.property("visible"):
                login = o
                break
    popups = []
    for o in win.findChildren(QQuickItem):
        cn = o.metaObject().className()
        if "Popup" in cn or cn.startswith("Modal") or cn.startswith("Settings"):
            vis = o.property("visible")
            if vis:
                popups.append((cn, o, o.property("width"), o.property("height")))
    print("visible popups", [(c, w, h) for c, _, w, h in popups])
    login_item = next((o for c, o, w, h in popups if not c.startswith("Settings") and w and h), None)
    if login_item:
        mute_transitions(login_item)
    save(win, "login.png", overlay_item=login_item)
    print("done")


if __name__ == "__main__":
    main()
