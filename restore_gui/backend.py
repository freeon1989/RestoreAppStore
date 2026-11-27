
"""Связь интерфейса QML с собственными службами RestoreAppStore."""
from __future__ import annotations

import hashlib
import os
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PySide6.QtCore import Property, QObject, Qt, QUrl, QTimer, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QApplication, QFileDialog

import restore_apps as core
from restore_gui import theme
from restore_gui.models import APP_ROLES, FILE_ROLES, VERSION_ROLES, DictList
from restore_gui.service import device as device_svc
from restore_gui.service import icons as icon_svc
from restore_gui.service import ipa as ipa_svc
from restore_gui.service import itunes
from restore_gui.service import paths
from restore_gui.service import prefs
from restore_gui.service import secrets
from restore_gui.service import updater
from restore_gui.service.store import Store, StoreError, parse_app_ref


def qprop(type_, name):
    changed = Signal()
    priv = "_" + name

    def getter(self):
        return getattr(self, priv)

    def setter(self, value):
        if getattr(self, priv) != value:
            setattr(self, priv, value)
            getattr(self, name + "Changed").emit()

    prop = Property(type_, getter, setter, notify=changed)
    return changed, prop


class Backend(QObject):
    logAppended = Signal(str)
    noticeRequested = Signal(str, str)
    paletteChanged = Signal()
    taskFinished = Signal()

    themeModeChanged, themeMode = qprop(str, "themeMode")
    accentNameChanged, accentName = qprop(str, "accentName")
    heroineNameChanged, heroineName = qprop(str, "heroineName")
    pageChanged, page = qprop(str, "page")
    loggedInChanged, loggedIn = qprop(bool, "loggedIn")
    accountChanged, account = qprop(str, "account")
    deviceStateChanged, deviceState = qprop(str, "deviceState")
    deviceTextChanged, deviceText = qprop(str, "deviceText")
    busyChanged, busy = qprop(bool, "busy")
    statusChanged, status = qprop(str, "status")
    selectedCountChanged, selectedCount = qprop(int, "selectedCount")
    selectedTextChanged, selectedText = qprop(str, "selectedText")
    categoryChanged, category = qprop(str, "category")
    logOpenChanged, logOpen = qprop(bool, "logOpen")
    countryChanged, country = qprop(str, "country")
    onlyRemovedChanged, onlyRemoved = qprop(bool, "onlyRemoved")
    purchaseChanged, purchase = qprop(bool, "purchase")
    loginOpenChanged, loginOpen = qprop(bool, "loginOpen")
    loginNoteChanged, loginNote = qprop(str, "loginNote")
    loginNeedsCodeChanged, loginNeedsCode = qprop(bool, "loginNeedsCode")
    askOpenChanged, askOpen = qprop(bool, "askOpen")
    askTitleChanged, askTitle = qprop(str, "askTitle")
    askPromptChanged, askPrompt = qprop(str, "askPrompt")
    detailOpenChanged, detailOpen = qprop(bool, "detailOpen")
    detailAppChanged, detailApp = qprop("QVariantMap", "detailApp")
    detailChecksChanged, detailChecks = qprop("QVariantMap", "detailChecks")
    cloneHeadChanged, cloneHead = qprop(str, "cloneHead")
    cloneHeadOkChanged, cloneHeadOk = qprop(bool, "cloneHeadOk")
    versionHeadChanged, versionHead = qprop(str, "versionHead")
    versionModeChanged, versionMode = qprop(str, "versionMode")
    detailErrChanged, detailErr = qprop(str, "detailErr")
    detailAnswerChanged, detailAnswer = qprop(str, "detailAnswer")
    moreTextChanged, moreText = qprop(str, "moreText")
    selectedVersionChanged, selectedVersion = qprop(str, "selectedVersion")
    actionsEnabledChanged, actionsEnabled = qprop(bool, "actionsEnabled")
    ipaDirChanged, ipaDir = qprop(str, "ipaDir")
    deleteAfterInstallChanged, deleteAfterInstall = qprop(bool, "deleteAfterInstall")
    notifyDoneChanged, notifyDone = qprop(bool, "notifyDone")
    ipaSummaryChanged, ipaSummary = qprop(str, "ipaSummary")
    updateTextChanged, updateText = qprop(str, "updateText")
    updateUrlChanged, updateUrl = qprop(str, "updateUrl")
    autoUpdateChanged, autoUpdate = qprop(bool, "autoUpdate")
    updateOpenChanged, updateOpen = qprop(bool, "updateOpen")
    updateVersionChanged, updateVersion = qprop(str, "updateVersion")
    updateNotesChanged, updateNotes = qprop(str, "updateNotes")
    backupTextChanged, backupText = qprop(str, "backupText")
    backupAvailableChanged, backupAvailable = qprop(bool, "backupAvailable")

    version = Property(str, lambda self: core.__version__, constant=True)
    displayName = Property(str, lambda self: core.DISPLAY_NAME, constant=True)
    supportUrl = Property(str, lambda self: core.SUPPORT_URL, constant=True)
    repoUrl = Property(str, lambda self: f"https://github.com/{core.REPO}", constant=True)
    appleDevicesUrl = Property(str, lambda self: core.APPLE_DEVICES_STORE_URL, constant=True)
    reduceMotion = Property(bool, lambda self: _reduce_motion(), constant=True)


    def __init__(self, background=True):
        super().__init__()
        self._demo = False
        self._themeMode = "system"
        self._accentName = theme.DEFAULT_ACCENT
        self._heroineName = theme.DEFAULT_HEROINE
        self._page = "home"
        self._loggedIn = False
        self._account = ""
        self._deviceState = "none"
        self._deviceText = "Подключите iPhone кабелем"
        self._busy = False
        self._status = ""
        self._selectedCount = 0
        self._selectedText = ""
        self._category = "Все"
        self._logOpen = False
        self._country = "ru"
        self._onlyRemoved = True
        self._purchase = False
        self._loginOpen = False
        self._loginNote = ""
        self._loginNeedsCode = False
        self._askOpen = False
        self._askTitle = ""
        self._askPrompt = ""
        self._detailOpen = False
        self._detailApp = {}
        self._detailChecks = {}
        self._cloneHead = "Копии"
        self._cloneHeadOk = False
        self._versionHead = "Версия"
        self._versionMode = "none"
        self._detailErr = ""
        self._detailAnswer = ""
        self._moreText = ""
        self._selectedVersion = ""
        self._actionsEnabled = False
        self._ipaDir = str(paths.default_ipa_dir())
        self._deleteAfterInstall = False
        self._notifyDone = True
        self._ipaSummary = "Скачанных файлов нет"
        self._updateText = ""
        self._updateUrl = ""
        self._autoUpdate = True
        self._updateOpen = False
        self._updateVersion = ""
        self._updateNotes = ""
        self._backupText = ""
        self._backupAvailable = False
        self._skipVersion = ""
        self._pending_login = None
        self._ask_kind = ""
        self._stop = threading.Event()
        self._jobs = []
        self._log_lines = []
        self._purchases: list[dict] = []
        self._device_apps: list[dict] = []
        self._popular = DictList(APP_ROLES, self)
        self._apps = DictList(APP_ROLES, self)
        self._mine = DictList(APP_ROLES, self)
        self._clones = DictList(APP_ROLES, self)
        self._versions = DictList(VERSION_ROLES, self)
        self._ipa = DictList(FILE_ROLES, self)
        self._palette = theme.Palette(self)
        self._store = None
        self._load_prefs()
        self._refresh_palette()
        self.refresh_ipa()
        self._refresh_backup()
        self.themeModeChanged.connect(self._on_chrome_changed)
        self.accentNameChanged.connect(self._on_chrome_changed)
        self.heroineNameChanged.connect(self._on_chrome_changed)
        self.countryChanged.connect(self._persist)
        self.deleteAfterInstallChanged.connect(self._persist)
        self.notifyDoneChanged.connect(self._persist)
        self.autoUpdateChanged.connect(self._persist)
        self.ipaDirChanged.connect(self._persist)
        if background:
            QTimer.singleShot(400, self._startup)

    def _store_client(self) -> Store:
        if self._store is None:
            self._store = Store(passphrase=secrets.load_passphrase())
        return self._store

    def _load_prefs(self) -> None:
        data = prefs.load()
        self._themeMode = data["themeMode"]
        self._accentName = data["accentName"]
        self._heroineName = data["heroineName"]
        self._country = data["country"] or "ru"
        self._deleteAfterInstall = data["deleteAfterInstall"]
        self._notifyDone = data["notifyDone"]
        self._autoUpdate = data["autoUpdate"]
        self._skipVersion = data.get("skipVersion") or ""
        self._ipaDir = data["ipaDir"]

    def _persist(self, *_):
        prefs.save({
            "themeMode": self._themeMode,
            "accentName": self._accentName,
            "heroineName": self._heroineName,
            "country": self._country,
            "deleteAfterInstall": self._deleteAfterInstall,
            "notifyDone": self._notifyDone,
            "autoUpdate": self._autoUpdate,
            "skipVersion": self._skipVersion,
            "ipaDir": self._ipaDir,
        })

    def _on_chrome_changed(self, *_):
        self._refresh_palette()
        self.heroinesChanged.emit()
        self.heroineUrlChanged.emit()
        self.heroineOrbChanged.emit()
        self._persist()

    def _is_dark(self) -> bool:
        if self._themeMode == "light":
            return False
        if self._themeMode == "dark":
            return True
        hints = QGuiApplication.styleHints()
        return hints.colorScheme() == hints.colorScheme().__class__.Dark

    def _refresh_palette(self) -> None:
        self._palette.set(theme.palette(self._is_dark(), self._accentName))
        try:
            scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(
                self._themeMode, Qt.ColorScheme.Unknown)
            QGuiApplication.styleHints().setColorScheme(scheme)
        except Exception:
            pass
        self.paletteChanged.emit()

    def current_palette(self):
        return self._palette

    pal = Property(QObject, lambda self: self._palette, constant=True)
    popular = Property(QObject, lambda self: self._popular, constant=True)
    apps = Property(QObject, lambda self: self._apps, constant=True)
    mine = Property(QObject, lambda self: self._mine, constant=True)
    clones = Property(QObject, lambda self: self._clones, constant=True)
    versions = Property(QObject, lambda self: self._versions, constant=True)
    ipaFiles = Property(QObject, lambda self: self._ipa, constant=True)
    defaultIpaDir = Property(str, lambda self: str(paths.default_ipa_dir()), constant=True)

    categoriesChanged = Signal()

    @Property("QVariantList", notify=categoriesChanged)
    def categories(self):
        genres = sorted({(row.get("genre") or row.get("kind") or "").strip()
                         for model in (self._apps, self._popular)
                         for row in model._rows if (row.get("genre") or row.get("kind"))})
        return ["Все"] + [g for g in genres if g]

    def _accent_list(self):
        rows = []
        dark = self._is_dark()
        for key, (title, light, dark_acc) in theme.ACCENTS.items():
            pal = dark_acc if dark else light
            rows.append({
                "key": key,
                "title": title,
                "color": pal["accent"],
                "grad1": pal["grad1"],
                "grad2": pal["grad2"],
            })
        return rows

    accents = Property("QVariantList", _accent_list, notify=themeModeChanged)

    heroinesChanged = Signal()
    heroineUrlChanged = Signal()
    heroineOrbChanged = Signal()

    @Property("QVariantList", notify=heroinesChanged)
    def heroines(self):
        dark = self._is_dark()
        rows = []
        for key, info in theme.HEROINES.items():
            rows.append({"key": key, "title": info["title"], "url": theme.heroine_url(key, dark)})
        return rows

    @Property(str, notify=heroineUrlChanged)
    def heroineUrl(self):
        return theme.heroine_url(self._heroineName, self._is_dark())

    @Property("QVariantMap", notify=heroineOrbChanged)
    def heroineOrb(self):
        return theme.heroine_orb(self._heroineName, self._is_dark())

    @Property(str, constant=True)
    def greeting(self):
        return "С возвращением" if self._loggedIn else "Добро пожаловать"

    @Property(str, constant=True)
    def qrUrl(self):
        found = paths.resource("cloudtips_qr.png")
        if found:
            return paths.file_url(found)
        try:
            import segno
            dest = paths.data_dir() / "support-qr.png"
            if not dest.is_file():
                segno.make(core.SUPPORT_URL, error="m").save(str(dest), scale=8, border=4)
            return paths.file_url(dest)
        except Exception:
            return ""

    def _startup(self):
        self._run(self._restore_session, self._on_session)
        self._run(self._probe_device, self._on_device)
        if self._autoUpdate:
            QTimer.singleShot(1500, lambda: self.checkUpdates(silent=True))
        QTimer.singleShot(800, self._load_popular)

    def _restore_session(self):
        store = self._store_client()
        if not store.available():
            return {"logged": False, "email": "", "note": "ipatool-cpp не найден"}
        info = store.info()
        if not info:
            return {"logged": False, "email": ""}
        email = str(info.get("email") or info.get("account") or "")
        return {"logged": bool(info.get("success", True) and email), "email": email}

    def _on_session(self, result, error):
        if error or not result:
            return
        self.loggedIn = bool(result.get("logged"))
        self.account = result.get("email") or ""
        if result.get("note"):
            self.log(result["note"])

    def _probe_device(self):
        return device_svc.status()

    def _on_device(self, result, error):
        if error or not result:
            self.deviceState, self.deviceText = "none", "Подключите iPhone кабелем"
            self.log("iPhone не виден. Если кабель уже подключён, установите «Устройства Apple» из Microsoft Store.")
            return
        self.deviceState = result.get("state") or "none"
        self.deviceText = result.get("text") or ""
        self._device_apps = result.get("apps") or []
        if self.deviceState != "ok":
            self.log("iPhone не виден. Если кабель уже подключён, установите «Устройства Apple» из Microsoft Store.")

    def _load_popular(self):
        if self._demo:
            return

        def work():
            try:
                return itunes.top_free(self._country or "ru")
            except itunes.ITunesError as exc:
                raise RuntimeError(str(exc)) from exc

        self._run(work, self._on_popular)

    def _on_popular(self, rows, error):
        if error or not rows:
            return
        self._popular.replace([self._row(item) for item in rows])
        self.categoriesChanged.emit()

    def _run(self, fn, done=None):
        # Один Event на задачу: stop() не должен подменять его, иначе «Остановить» не доходит до потока.
        self._stop.clear()

        def wrap():
            result, error = None, None
            try:
                if self._stop.is_set():
                    error = RuntimeError("остановлено")
                else:
                    result = fn()
            except Exception as exc:  # noqa: BLE001
                error = exc

            def finish():
                try:
                    if done:
                        done(result, error)
                except Exception as exc:  # noqa: BLE001
                    self.log(f"ошибка после операции: {exc}")
                    self.show_notice("Ошибка", str(exc)[:400])
                self.busy = False
                self.taskFinished.emit()

            # Без объекта-контекста QTimer из рабочего потока не срабатывает
            # (в том потоке нет цикла событий) — кнопка «Входим…» зависала навсегда.
            QTimer.singleShot(0, self, finish)

        self.busy = True
        thread = threading.Thread(target=wrap, daemon=True)
        self._jobs.append(thread)
        thread.start()

    def log(self, text: str) -> None:
        line = (text or "").strip()
        if not line:
            return
        self._log_lines.append(line)
        try:
            with paths.log_path().open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass
        self.logAppended.emit(line)

    def show_notice(self, title, text):
        self.noticeRequested.emit(title, text)

    @Slot()
    def openSettings(self):
        pass

    @Slot(str)
    def showPage(self, name):
        if name in ("home", "apps", "mine", "ipa"):
            self.page = name

    @Slot(str)
    def setQuery(self, text):
        self._last_query = text
        ref = parse_app_ref(text)
        if self._demo:
            return
        if ref["kind"] == "empty":
            self._apps.replace([])
            return

        def work():
            if ref["kind"] == "id":
                found = itunes.lookup(ref["value"], self._country or "ru")
                return [found] if found else []
            if ref["kind"] == "bundle":
                try:
                    return self._store_client().search(ref["value"])
                except StoreError:
                    return itunes.search(ref["value"], self._country or "ru")
            try:
                rows = self._store_client().search(ref["value"]) if self._loggedIn else []
            except StoreError:
                rows = []
            return rows or itunes.search(ref["value"], self._country or "ru")

        def done(rows, error):
            if error:
                self.log(str(error))
                self.show_notice("Поиск", str(error))
                return
            items = [self._row(item, genre=item.get("genre") or item.get("kind") or "") for item in (rows or [])]
            if self._category != "Все":
                items = [row for row in items if row.get("genre") == self._category]
            self._apps.replace(items)
            self.categoriesChanged.emit()

        self._run(work, done)

    @Slot(str)
    def setCategory(self, name):
        self.category = name or "Все"
        if getattr(self, "_last_query", ""):
            self.setQuery(self._last_query)

    @Slot(bool)
    def setOnlyRemoved(self, on):
        self.onlyRemoved = bool(on)
        self._refresh_mine()

    @Slot()
    def connectDevice(self):
        self.log("Проверяю iPhone…")
        self._run(self._probe_device, self._on_device)

    @Slot()
    @Slot(str)
    def openLogin(self, note=""):
        self.loginNeedsCode = False
        self.loginNote = note or "Войдите в Apple ID, с которого покупали приложения."
        self.loginOpen = True

    @Slot()
    def closeLogin(self):
        self.loginOpen = False
        self.loginNeedsCode = False

    @Slot(str, str)
    @Slot(str, str, str)
    def login(self, email, password, auth_code=""):
        email = (email or "").strip()
        if not email or not password:
            self.show_notice("Вход", "Введите адрес и пароль Apple ID")
            return
        if self.loginNeedsCode and not (auth_code or "").strip():
            self.show_notice("Вход", "Введите код подтверждения, который прислала Apple.")
            return
        self._pending_login = {"email": email, "password": password}
        try:
            self._store_client()
        except Exception as exc:  # noqa: BLE001
            self.log(str(exc))
            self.show_notice("Вход", str(exc)[:400])
            return
        self.log("Запускаю вход в Apple ID…")
        self._do_login((auth_code or "").strip() or None)

    def _do_login(self, code):
        pending = self._pending_login or {}

        def work():
            return self._store_client().login(pending.get("email", ""), pending.get("password", ""), code)

        def done(result, error):
            if error and isinstance(error, StoreError) and error.needs_2fa:
                self.loginNeedsCode = True
                self.loginNote = "Apple прислала код подтверждения. Введите его в поле ниже."
                self.log("Нужен код подтверждения Apple.")
                return
            self._pending_login = None
            self.loginNeedsCode = False
            if error:
                self.log(str(error))
                self.show_notice("Вход", str(error))
                return
            email = (result or {}).get("email") or pending.get("email") or ""
            self.loggedIn = True
            self.account = email
            self.loginOpen = False
            self.log("Вход выполнен")

        self._run(work, done)

    @Slot(str, bool)
    def answerAsk(self, text, ok):
        self.askOpen = False
        if self._ask_kind == "2fa":
            self._ask_kind = ""
            if ok and text.strip():
                self._do_login(text.strip())
            else:
                self._pending_login = None
                self.log("Вход отменён")

    @Slot()
    def logout(self):
        def work():
            try:
                self._store_client().revoke()
            except StoreError:
                pass

        def done(_result, _error):
            self.loggedIn = False
            self.account = ""
            self._purchases = []
            self._mine.replace([])
            self.log("Вы вышли из Apple ID")

        self._run(work, done)

    @Slot()
    def loadPurchases(self):
        if not self._loggedIn and not self._demo:
            self.openLogin("Сначала войдите в Apple ID, чтобы загрузить покупки.")
            return

        def work():
            return self._store_client().list_purchases(entire=True)

        def done(rows, error):
            if error:
                self.log(str(error))
                self.show_notice("Покупки", str(error))
                return
            self._purchases = rows or []
            self._refresh_mine(self._purchases)
            self.log(f"Покупок в истории: {len(self._purchases)}")

        self._run(work, done)

    @Slot()
    def findMine(self):
        if not self._loggedIn and not self._demo:
            self.openLogin("Сначала войдите в Apple ID.")
            return

        def work():
            rows = self._purchases or self._store_client().list_purchases(entire=True)
            missing = []
            for item in rows:
                app_id = item.get("id")
                if not app_id:
                    continue
                if not itunes.still_on_store(app_id, self._country or "ru"):
                    missing.append(item)
            return rows, missing

        def done(result, error):
            if error:
                self.log(str(error))
                self.show_notice("Проверка", str(error))
                return
            rows, missing = result
            self._purchases = rows
            self._refresh_mine(missing if self._onlyRemoved else rows, removed_ids={i.get("id") for i in missing})
            self.log(f"Пропавших из каталога: {len(missing)} из {len(rows)}")

        self.log("Сверяю покупки с каталогом App Store…")
        self._run(work, done)

    def _refresh_mine(self, rows=None, removed_ids=None):
        rows = rows if rows is not None else self._purchases
        installed = {app.get("id") or app.get("bundle") for app in self._device_apps}
        out = []
        for item in rows:
            row = self._row(item)
            app_id = row["appId"]
            if removed_ids is not None and app_id in removed_ids:
                row["status"] = "нет в App Store"
                row["statusKind"] = "warn"
            elif installed and (app_id in installed or item.get("bundle") in installed):
                row["status"] = "на iPhone"
                row["statusKind"] = "ok"
            out.append(row)
        self._mine.replace(out)

    @Slot()
    def netCheck(self):
        def work():
            itunes.top_free(self._country or "ru", limit=1)
            return True

        def done(_result, error):
            if error:
                self.show_notice("Сеть", str(error))
            else:
                self.show_notice("Сеть", "Каталог App Store доступен.")

        self._run(work, done)

    @Slot()
    def stop(self):
        self._stop.set()
        if self._store is not None:
            self._store.cancel()
        self.log("Остановка запрошена")

    @Slot(str, int)
    def toggleSelected(self, list_name, row):
        model = self._model(list_name)
        if model is None:
            return
        model.toggle(row)
        self._recount()

    @Slot()
    def clearSelection(self):
        for model in (self._popular, self._apps, self._mine, self._ipa):
            model.clear_selection()
        self._recount()

    def _recount(self):
        rows = []
        for model in (self._popular, self._apps, self._mine):
            rows.extend(model.selected_rows())
        self.selectedCount = len(rows)
        self.selectedText = f"Выбрано: {len(rows)}" if rows else ""

    @Slot()
    def installSelected(self):
        rows = []
        for model in (self._popular, self._apps, self._mine):
            rows.extend(model.selected_rows())
        if not rows:
            return
        self._download_many(rows, install=True)

    @Slot()
    def installFile(self):
        path, _ = QFileDialog.getOpenFileName(None, "Выберите IPA", self._ipaDir, "IPA (*.ipa)")
        if path:
            self.installIpa(path)

    @Slot(str)
    def installIpa(self, path):
        if self._need_iphone():
            return

        def work():
            device_svc.install_ipa(Path(path))
            return path

        def done(_result, error):
            if error:
                self.log(str(error))
                self.show_notice("Установка", str(error))
                return
            self.log(f"Установлено: {path}")
            if self._notifyDone:
                self.show_notice("Установка", "Приложение установлено на iPhone.")
            if self._deleteAfterInstall:
                try:
                    Path(path).unlink()
                    self.refresh_ipa()
                except OSError:
                    pass
            self.connectDevice()

        self._run(work, done)

    @Slot()
    def openFolder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._ipaDir))

    @Slot()
    def chooseIpaDir(self):
        folder = QFileDialog.getExistingDirectory(None, "Папка для IPA", self._ipaDir)
        if folder:
            self.ipaDir = folder
            self.refresh_ipa()

    @Slot()
    def resetIpaDir(self):
        self.ipaDir = str(paths.default_ipa_dir())
        self.refresh_ipa()

    @Slot()
    def clearIpa(self):
        n = ipa_svc.clear_folder(Path(self._ipaDir))
        self.refresh_ipa()
        self.log(f"Удалено файлов IPA: {n}")

    def refresh_ipa(self):
        rows = ipa_svc.list_files(Path(self._ipaDir))
        for row in rows:
            row["tint"] = self._tint(row.get("title") or "")
            row["letter"] = (row.get("title") or "?")[:1].upper()
        self._ipa.replace(rows)
        self.ipaSummary = f"Файлов IPA: {len(rows)}" if rows else "Скачанных файлов нет"

    @Slot(str, int)
    def openDetail(self, list_name, row):
        model = self._model(list_name)
        item = model.at(row) if model else None
        if not item:
            return
        app = {
            "id": item.get("appId") or item.get("id") or "",
            "name": item.get("title") or item.get("name") or "",
            "letter": item.get("letter") or "?",
            "tint": item.get("tint") or theme.AVATARS[0],
            "icon": item.get("icon") or "",
            "bundle": item.get("bundle") or "",
        }
        self.detailApp = app
        self.detailOpen = True
        self.versionMode = "loading"
        self.selectedVersion = ""
        self.actionsEnabled = False
        self.detailChecks = {
            "acc": {"text": "вход выполнен" if self._loggedIn else "нужен вход в Apple ID",
                    "kind": "ok" if self._loggedIn else "warn"},
            "phone": {"text": self._deviceText, "kind": "ok" if self._deviceState == "ok" else "warn"},
            "store": {"text": "проверяю каталог…", "kind": ""},
        }
        if self._demo:
            self.versionMode = "none"
            return

        def work():
            store_item = None
            try:
                store_item = itunes.lookup(app["id"], self._country or "ru") if app["id"] else None
            except itunes.ITunesError:
                store_item = None
            versions = []
            err = ""
            try:
                versions = self._store_client().list_versions(app_id=app["id"] or None, bundle=app["bundle"] or None)
            except StoreError as exc:
                err = str(exc)
            return store_item, versions, err

        def done(result, error):
            if error:
                self.versionMode = "error"
                self.detailErr = str(error)
                return
            store_item, versions, err = result
            checks = dict(self._detailChecks)
            if store_item:
                checks["store"] = {"text": "есть в App Store", "kind": "ok"}
            else:
                checks["store"] = {"text": "не найдено в текущей стране каталога", "kind": "warn"}
            self.detailChecks = checks
            if err and not versions:
                self.versionMode = "error"
                self.detailErr = err
                return
            if not versions:
                self.versionMode = "none"
                self.actionsEnabled = bool(self._loggedIn)
                return
            self._versions.replace(versions)
            self.selectedVersion = versions[0]["value"]
            self.versionMode = "list"
            self.actionsEnabled = bool(self._loggedIn)

        self._run(work, done)

    @Slot()
    def closeDetail(self):
        self.detailOpen = False

    @Slot()
    def detailRecheck(self):
        if self._detailApp:
            self.openDetail_from_app(self._detailApp)

    def openDetail_from_app(self, app):
        self._apps.replace([self._row({"id": app.get("id"), "name": app.get("name"), "bundle": app.get("bundle"), "icon": app.get("icon")})] + list(self._apps._rows))
        self.openDetail("apps", 0)

    @Slot()
    def detailMore(self):
        self.moreText = "Версии отдаёт ipatool-cpp. Старые сборки Apple может больше не подписывать."

    @Slot(bool)
    def detailAction(self, install):
        app = self._detailApp or {}
        self._download_many([{"appId": app.get("id"), "title": app.get("name"), "bundle": app.get("bundle"),
                              "version": self._selectedVersion}], install=install)

    def _need_iphone(self) -> bool:
        """True, если установку нельзя начать: телефон не виден, уже показали подсказку."""
        if self._deviceState == "ok":
            return False
        self.show_notice(
            "iPhone не виден",
            "Установите «Устройства Apple» из Microsoft Store, подключите кабель и нажмите «Доверять» на телефоне.",
        )
        return True

    def _download_many(self, rows, install=False):
        if install and self._need_iphone():
            return
        folder = Path(self._ipaDir)
        folder.mkdir(parents=True, exist_ok=True)

        def work():
            results = []
            for item in rows:
                if self._stop.is_set():
                    break
                app_id = item.get("appId") or item.get("id")
                bundle = item.get("bundle")
                title = item.get("title") or item.get("name") or app_id or "app"
                dest = folder / f"{_safe_name(title)}.ipa"
                path = self._store_client().download(
                    dest, app_id=app_id, bundle=bundle or None,
                    version_id=item.get("version") or None, buy=self._purchase,
                )
                results.append(path)
                if install:
                    device_svc.install_ipa(path)
                    if self._deleteAfterInstall:
                        try:
                            path.unlink()
                        except OSError:
                            pass
            return results

        def done(results, error):
            self.refresh_ipa()
            if error:
                self.log(str(error))
                self.show_notice("Загрузка", str(error))
                return
            self.log(f"Готово файлов: {len(results or [])}")
            if self._notifyDone:
                self.show_notice("Готово", "Установка завершена." if install else "IPA сохранён в папку загрузок.")

        self._run(work, done)

    @Slot()
    @Slot(bool)
    def checkUpdates(self, silent=False):
        def work():
            return updater.check_latest()

        def done(info, error):
            if error:
                self.updateText = str(error)
                self.updateUrl = ""
                if not silent:
                    self.show_notice("Обновления", str(error))
                return
            version = info.get("version") or ""
            self.updateUrl = info.get("html_url") or ""
            self._update_info = info
            if info.get("newer"):
                if silent and version == self._skipVersion:
                    self.updateText = f"Версия {version} пропущена"
                    return
                self.updateVersion = version
                self.updateNotes = info.get("notes") or ""
                self.updateText = f"Доступна {version}"
                self.updateOpen = True
            else:
                self.updateText = f"У вас последняя версия ({core.__version__})"
                if not silent:
                    self.show_notice("Обновления", self.updateText)

        self._run(work, done)

    @Slot(str)
    def answerUpdate(self, action):
        self.updateOpen = False
        info = getattr(self, "_update_info", None) or {}
        if action == "skip":
            self._skipVersion = self._updateVersion
            self._persist()
            self.updateText = f"Версия {self._updateVersion} пропущена"
            return
        if action == "later":
            return
        if action == "download":
            if not getattr(sys_frozen(), "frozen", False) and not getattr(__import__("sys"), "frozen", False):
                url = info.get("html_url") or self._updateUrl
                if url:
                    self.openUrl(url)
                    return

            def work():
                updater.install_update(info, log=self.log)

            def done(_result, error):
                if error:
                    self.log(str(error))
                    self.show_notice("Обновление", str(error))

            self._run(work, done)

    @Slot()
    def rollbackUpdate(self):
        def work():
            updater.rollback()

        def done(_result, error):
            if error:
                self.show_notice("Откат", str(error))

        self._run(work, done)

    def _refresh_backup(self):
        found = updater.backup_dir()
        self.backupAvailable = bool(found)
        self.backupText = f"Есть копия: {found.name}" if found else "Резервной копии нет"

    @Slot(str)
    def openUrl(self, url):
        if not _allowed_url(url):
            self.show_notice("Ссылка", "Этот адрес программа не открывает.")
            return
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def openAppleDevicesStore(self):
        """Сначала протокол Microsoft Store, если не открылся — страница в браузере."""
        if sys.platform == "win32":
            if QDesktopServices.openUrl(QUrl(core.APPLE_DEVICES_STORE_DEEP)):
                return
        QDesktopServices.openUrl(QUrl(core.APPLE_DEVICES_STORE_URL))

    @Slot(str)
    def copyText(self, text):
        QApplication.clipboard().setText(text or "")

    @Slot()
    def open_log(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.app_log_path())))

    @Slot()
    def openLogsFolder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.logs_dir())))

    @Slot(result=str)
    def helpText(self):
        return (
            f"{core.DISPLAY_NAME} {core.__version__}\n\n"
            "Программа входит в ваш Apple ID через ipatool-cpp, показывает историю покупок, "
            "скачивает IPA и ставит их на iPhone по кабелю.\n\n"
            "Чтобы Windows увидела iPhone, установите приложение «Устройства Apple» (Apple Devices) "
            "из Microsoft Store, подключите кабель и на телефоне нажмите «Доверять».\n"
            f"Ссылка: {core.APPLE_DEVICES_STORE_URL}\n\n"
            "Пароль Apple ID на диск не записывается: сессию хранит ipatool-cpp в зашифрованном виде, "
            "а ключ к ней — в Windows Credential Manager или в файле, защищённом DPAPI.\n\n"
            "Обновления берутся только с GitHub Releases, файл сверяется по SHA-256. "
            "Если что-то пойдёт не так, в «Настройки → О программе» можно вернуть предыдущую копию.\n\n"
            "Журналы: %LOCALAPPDATA%\\RestoreAppStore\\app.log и startup.log. "
            "Папку можно открыть в «Настройки → О программе»."
        )

    @Slot()
    def shutdown(self):
        self._stop.set()
        if self._store is not None:
            self._store.cancel()
        self._persist()

    def seed_demo(self) -> None:
        """Вымышленные данные для снимков и проверки интерфейса. Сеть не вызывается."""
        self._demo = True
        self.loggedIn = True
        self.account = "demo@example.com"
        self.deviceState = "ok"
        self.deviceText = "iPhone (демо)"
        demo = [
            {"id": "1", "name": "Почта", "genre": "Сервисы", "status": "в истории", "statusKind": "ok"},
            {"id": "2", "name": "Заметки", "genre": "Продуктивность", "status": "в истории", "statusKind": "ok"},
            {"id": "3", "name": "Карты", "genre": "Навигация", "status": "нет в App Store", "statusKind": "warn"},
            {"id": "4", "name": "Музыка", "genre": "Развлечения", "status": "в истории", "statusKind": "ok"},
        ]
        rows = [self._row(item, status=item["status"], statusKind=item["statusKind"], genre=item["genre"]) for item in demo]
        self._popular.replace(rows)
        self._apps.replace(rows)
        self._mine.replace(rows[2:3])
        self.categoriesChanged.emit()

    def _model(self, name):
        return {"popular": self._popular, "apps": self._apps, "mine": self._mine,
                "ipa": self._ipa, "clones": self._clones, "versions": self._versions}.get(name)

    def _row(self, item, status="", statusKind="", genre=""):
        app_id = str(item.get("id") or item.get("appId") or "")
        name = str(item.get("name") or item.get("title") or "")
        icon = item.get("icon") or ""
        if icon and icon.startswith("https://"):
            local = icon_svc.local_path(app_id, icon)
            if local:
                icon = paths.file_url(local)
        return {
            "appId": app_id,
            "title": name,
            "sub": item.get("price") or item.get("version") or item.get("date") or "",
            "letter": (name or "?")[:1].upper(),
            "tint": self._tint(app_id or name),
            "icon": icon,
            "status": status,
            "statusKind": statusKind,
            "selected": False,
            "copies": item.get("copies") or "",
            "bundle": item.get("bundle") or "",
            "genre": genre or item.get("genre") or item.get("kind") or "",
        }

    def _tint(self, key: str) -> str:
        digest = hashlib.sha256((key or "?").encode("utf-8")).digest()
        return theme.AVATARS[digest[0] % len(theme.AVATARS)]


def _safe_name(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in " .-_()" else "_" for ch in text).strip()
    return cleaned[:80] or "app"


def _allowed_url(url: str) -> bool:
    parts = urlsplit(url or "")
    host = (parts.hostname or "").lower()
    scheme = (parts.scheme or "").lower()
    if parts.username:
        return False
    product = core.APPLE_DEVICES_PRODUCT_ID.lower()
    if scheme == "ms-windows-store":
        query = {k.lower(): v for k, v in parse_qs(parts.query).items()}
        pid = (query.get("productid") or [""])[0].lower()
        where = f"{parts.netloc}{parts.path}".lower()
        return "pdp" in where and pid == product
    if scheme != "https":
        return False
    if host == "apps.microsoft.com":
        return product in (parts.path or "").lower()
    allowed = (
        "github.com", "api.github.com", "objects.githubusercontent.com",
        "release-assets.githubusercontent.com", "pay.cloudtips.ru", "cloudtips.ru",
    )
    return host in allowed or host.endswith(".github.com")


def _reduce_motion() -> bool:
    """Учесть системную настройку анимации Windows и переменную QML_REDUCE_MOTION."""
    flag = os.environ.get("QML_REDUCE_MOTION", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            value = ctypes.c_int(1)
            # SPI_GETCLIENTAREAANIMATION = 0x1042: 0 значит анимации выключены
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0):
                return value.value == 0
        except Exception:  # noqa: BLE001 — на не-Windows или без API просто оставляем анимацию
            return False
    return False


def sys_frozen():
    import sys
    return sys
