
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
from restore_gui.models import (
    ACCOUNT_ROLES, APP_ROLES, FILE_ROLES, JOB_ROLES, STOREFRONT_ROLES, VERSION_ROLES, DictList,
)
from restore_gui.service import accounts
from restore_gui.service import codesign
from restore_gui.service import device as device_svc
from restore_gui.service import icons as icon_svc
from restore_gui.service import ipa as ipa_svc
from restore_gui.service import jobs as jobs_svc
from restore_gui.service import platform as platform_svc
from restore_gui.service import itunes
from restore_gui.service import paths
from restore_gui.service import prefs
from restore_gui.service import progress as progress_svc
from restore_gui.service import regions
from restore_gui.service import secrets
from restore_gui.service import updater
from restore_gui.service.install_errors import InstallError
from restore_gui.service.prices import format_price
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
    catalogLoadingChanged, catalogLoading = qprop(bool, "catalogLoading")
    catalogErrorChanged, catalogError = qprop(str, "catalogError")
    versionNeedPurchaseChanged, versionNeedPurchase = qprop(bool, "versionNeedPurchase")
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
    storefrontIndexChanged, storefrontIndex = qprop(int, "storefrontIndex")
    accountStorefrontChanged, accountStorefront = qprop(str, "accountStorefront")
    accountStorefrontNameChanged, accountStorefrontName = qprop(str, "accountStorefrontName")
    detailAvailabilityChanged, detailAvailability = qprop(str, "detailAvailability")
    detailSwitchHintChanged, detailSwitchHint = qprop(str, "detailSwitchHint")
    detailSwitchAccountIdChanged, detailSwitchAccountId = qprop(str, "detailSwitchAccountId")
    installHintChanged, installHint = qprop(str, "installHint")
    newerVersionReadyChanged, newerVersionReady = qprop(bool, "newerVersionReady")
    installAnywayReadyChanged, installAnywayReady = qprop(bool, "installAnywayReady")
    detailMacOnlyChanged, detailMacOnly = qprop(bool, "detailMacOnly")
    leftoverHintChanged, leftoverHint = qprop(str, "leftoverHint")
    leftoverCountChanged, leftoverCount = qprop(int, "leftoverCount")
    jobActiveChanged, jobActive = qprop(bool, "jobActive")
    jobOverallChanged, jobOverall = qprop(str, "jobOverall")
    downloadPctChanged, downloadPct = qprop(float, "downloadPct")
    downloadTextChanged, downloadText = qprop(str, "downloadText")
    installPctChanged, installPct = qprop(float, "installPct")
    installTextChanged, installText = qprop(str, "installText")
    jobCountChanged, jobCount = qprop(int, "jobCount")

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
        self._deviceText = "Подключите iPhone или iPad кабелем"
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
        self._catalogLoading = False
        self._catalogError = ""
        self._versionNeedPurchase = False
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
        self._storefrontIndex = 0
        self._accountStorefront = ""
        self._accountStorefrontName = ""
        self._detailAvailability = ""
        self._detailSwitchHint = ""
        self._detailSwitchAccountId = ""
        self._installHint = ""
        self._newerVersionReady = False
        self._installAnywayReady = False
        self._jobActive = False
        self._detailMacOnly = False
        self._leftoverHint = ""
        self._leftoverCount = 0
        self._enrich_token = 0
        self._active_job_keys: set[str] = set()
        self._leftovers_announced = False
        self._jobOverall = ""
        self._downloadPct = -1.0
        self._downloadText = ""
        self._installPct = -1.0
        self._installText = ""
        self._jobCount = 0
        self._current_account_id = ""
        self._adding_account = False
        self._login_home = None
        self._pending_ipa = None
        self._pending_login = None
        self._ask_kind = ""
        self._stop = threading.Event()
        self._jobs = []
        self._log_lines = []
        self._purchases: list[dict] = []
        self._device_apps: list[dict] = []
        self._last_device_log = None
        self._device_timer = None
        self._popular = DictList(APP_ROLES, self)
        self._apps = DictList(APP_ROLES, self)
        self._mine = DictList(APP_ROLES, self)
        self._clones = DictList(APP_ROLES, self)
        self._versions = DictList(VERSION_ROLES, self)
        self._ipa = DictList(FILE_ROLES, self)
        self._storefronts = DictList(STOREFRONT_ROLES, self)
        self._accounts = DictList(ACCOUNT_ROLES, self)
        self._jobList = DictList(JOB_ROLES, self)
        self._palette = theme.Palette(self)
        self._store = None
        self._load_prefs()
        self._storefronts.replace(regions.rows())
        self._storefrontIndex = regions.index_of(self._country)
        self._reload_accounts()
        self._refresh_palette()
        self.refresh_ipa()
        self._sweep_temps(announce=True)
        self._refresh_backup()
        self.themeModeChanged.connect(self._on_chrome_changed)
        self.accentNameChanged.connect(self._on_chrome_changed)
        self.heroineNameChanged.connect(self._on_chrome_changed)
        self.countryChanged.connect(self._on_country)
        self.deleteAfterInstallChanged.connect(self._persist)
        self.notifyDoneChanged.connect(self._persist)
        self.autoUpdateChanged.connect(self._persist)
        self.ipaDirChanged.connect(self._persist)
        if background:
            QTimer.singleShot(400, self._startup)

    def _store_client(self) -> Store:
        if self._store is None:
            home = paths.account_home(self._current_account_id or None)
            self._store = Store(passphrase=secrets.load_passphrase(), home=home)
        return self._store

    def _reset_store(self) -> None:
        if self._store is not None:
            self._store.cancel()
        self._store = None

    def _load_prefs(self) -> None:
        data = prefs.load()
        self._themeMode = data["themeMode"]
        self._accentName = data["accentName"]
        self._heroineName = data["heroineName"]
        self._country = data["country"] or "ru"
        self._storefrontIndex = regions.index_of(self._country)
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
    storefronts = Property(QObject, lambda self: self._storefronts, constant=True)
    accounts = Property(QObject, lambda self: self._accounts, constant=True)
    jobs = Property(QObject, lambda self: self._jobList, constant=True)
    defaultIpaDir = Property(str, lambda self: str(paths.default_ipa_dir()), constant=True)

    categoriesChanged = Signal()

    @Property("QVariantList", notify=categoriesChanged)
    def categories(self):
        return list(itunes.category_names())

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
        self._run(self._probe_device, self._on_device, mark_busy=False)
        if self._autoUpdate:
            QTimer.singleShot(1500, lambda: self.checkUpdates(silent=True))
        QTimer.singleShot(800, self._load_popular)
        self._device_timer = QTimer(self)
        self._device_timer.setInterval(8000)
        self._device_timer.timeout.connect(self._poll_device)
        self._device_timer.start()

    def _restore_session(self):
        data = accounts.load()
        current = data.get("current") or ""
        self._current_account_id = current
        self._reset_store()
        store = self._store_client()
        if not store.available():
            return {"logged": False, "email": "", "note": "ipatool-cpp не найден", "storefront": "", "account_id": current}
        info = store.info()
        if not info:
            # прежний tool-home мог остаться от прошлого входа
            if not current:
                info = Store(passphrase=secrets.load_passphrase(), home=paths.tool_home()).info()
            if not info:
                return {"logged": False, "email": "", "storefront": "", "account_id": current}
        email = str(info.get("email") or info.get("account") or "")
        storefront = regions.parse_storefront(info.get("storeFront") or info.get("storefront") or "")
        return {
            "logged": bool(info.get("success", True) and email),
            "email": email,
            "storefront": storefront,
            "account_id": current,
        }

    def _on_session(self, result, error):
        if error or not result:
            self._reload_accounts()
            return
        self._apply_account(result)
        if result.get("note"):
            self.log(result["note"])

    def _apply_account(self, result: dict) -> None:
        email = result.get("email") or ""
        storefront = result.get("storefront") or ""
        logged = bool(result.get("logged") and email)
        if logged:
            acc = accounts.upsert(email, storefront, account_id=result.get("account_id") or self._current_account_id or None)
            self._current_account_id = acc["id"]
            storefront = acc.get("storefront") or storefront
        self.loggedIn = logged
        self.account = email if logged else ""
        self.accountStorefront = storefront if logged else ""
        self.accountStorefrontName = regions.name(storefront) if logged and storefront else ""
        self._reload_accounts()

    def _reload_accounts(self) -> None:
        data = accounts.load()
        self._current_account_id = data.get("current") or self._current_account_id
        rows = []
        for item in data.get("accounts") or []:
            sf = item.get("storefront") or ""
            rows.append({
                "id": item["id"],
                "email": item["email"],
                "storefront": sf,
                "storefrontName": regions.name(sf),
                "current": item["id"] == self._current_account_id,
                "logged": item["id"] == self._current_account_id and self._loggedIn,
            })
        self._accounts.replace(rows)

    def _on_country(self, *_):
        self._storefrontIndex = regions.index_of(self._country)
        self.storefrontIndex = self._storefrontIndex
        self._persist()
        if self._page == "apps":
            self._load_catalog(self._category)

    def _probe_device(self):
        return device_svc.status(autopair=False)

    def _poll_device(self):
        if self._busy:
            return
        self._run(self._probe_device, self._on_device, mark_busy=False)

    def _on_device(self, result, error):
        if error or not result:
            state, text, udid = "none", "Подключите iPhone или iPad кабелем", ""
            detail = str(error) if error else ""
        else:
            state = result.get("state") or "none"
            text = result.get("text") or ""
            udid = result.get("udid") or ""
            detail = result.get("detail") or ""
            self._device_apps = result.get("apps") or []
        self.deviceState = state
        self.deviceText = _public_device_text(text, state)
        key = (state, text, device_svc.mask_udid(udid), (detail or "").strip())
        if key == self._last_device_log:
            return
        self._last_device_log = key
        if _looks_internal(text) or _looks_internal(detail):
            paths.write_app_log(f"устройство, скрытая ошибка: {detail or text}")
        if state == "ok":
            self.log(f"Устройство подключено: {self.deviceText}")
        elif state == "trust":
            self.log(self.deviceText or device_svc.TRUST_TEXT)
        else:
            message = self.deviceText or "iPhone или iPad не виден."
            if detail:
                message = f"{message} ({detail})"
            hint = " Если кабель уже подключён, установите «Устройства Apple» из Microsoft Store."
            if "Устройства Apple" not in message:
                message += hint
            self.log(message)

    def _load_popular(self):
        self._load_catalog("Все", also_popular=True)

    def _load_catalog(self, genre: str = "Все", *, also_popular: bool = False):
        if self._demo:
            return
        genre = genre or "Все"
        self.catalogLoading = True
        self.catalogError = ""

        def work():
            try:
                return itunes.catalog(self._country or "ru", genre=genre)
            except itunes.ITunesError as exc:
                raise RuntimeError(str(exc)) from exc

        def done(rows, error):
            self.catalogLoading = False
            if error:
                message = _public_error(error)
                self.catalogError = message
                self.log(f"Каталог: {error}")
                if not len(self._apps):
                    self._apps.replace([])
                return
            items = [self._row(item, genre=item.get("genre") or item.get("kind") or genre,
                               status=("нет в App Store" if item.get("onStore") is False else ""),
                               statusKind=("warn" if item.get("onStore") is False else ""))
                     for item in (rows or [])]
            self._apps.replace(items)
            if also_popular or genre == "Все":
                popular = [row for row in items if row.get("statusKind") != "warn"][:25] or items[:25]
                self._popular.replace(popular)
                self._fill_icons(self._popular)
            self.categoriesChanged.emit()
            self._fill_icons(self._apps)

        self._run(work, done)

    def _run(self, fn, done=None, *, mark_busy=True):
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
                    self.show_notice("Ошибка", _public_error(exc))
                if mark_busy:
                    self.busy = False
                self.taskFinished.emit()

            # Без объекта-контекста QTimer из рабочего потока не срабатывает
            # (в том потоке нет цикла событий) — кнопка «Входим…» зависала навсегда.
            QTimer.singleShot(0, self, finish)

        if mark_busy:
            self.busy = True
        thread = threading.Thread(target=wrap, daemon=True)
        self._jobs.append(thread)
        thread.start()

    def log(self, text: str) -> None:
        line = (text or "").strip()
        if not line:
            return
        self._log_lines.append(line)
        paths.write_app_log(line)
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
            self._load_catalog(self._category or "Все")
            return

        self.catalogLoading = True
        self.catalogError = ""

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
            self.catalogLoading = False
            if error:
                message = _public_error(error)
                self.catalogError = message
                self.log(f"Поиск: {error}")
                self.show_notice("Поиск", message)
                return
            items = [self._row(item, genre=item.get("genre") or item.get("kind") or "") for item in (rows or [])]
            self._apps.replace(items)
            self.categoriesChanged.emit()
            self._fill_icons(self._apps)

        self._run(work, done)

    @Slot(str)
    def setCategory(self, name):
        self.category = name or "Все"
        query = (getattr(self, "_last_query", "") or "").strip()
        if query:
            self.setQuery(query)
        else:
            self._load_catalog(self.category)

    @Slot(bool)
    def setOnlyRemoved(self, on):
        self.onlyRemoved = bool(on)
        self._refresh_mine()

    @Slot()
    @Slot()
    def connectDevice(self):
        def work():
            return device_svc.status(autopair=True, pair_timeout=45)

        self._run(work, self._on_device)

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
        if not self._loggedIn:
            self._adding_account = False
            self._login_home = None

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
        pending = {"email": email, "password": password}
        if self._adding_account or self._login_home:
            pending["home"] = self._login_home or paths.account_home(accounts._new_id(email))
            self._login_home = pending["home"]
        elif self._current_account_id:
            pending["account_id"] = self._current_account_id
            pending["home"] = paths.account_home(self._current_account_id)
        self._pending_login = pending
        self.log("Запускаю вход в Apple ID…")
        self._do_login((auth_code or "").strip() or None)

    def _do_login(self, code):
        pending = self._pending_login or {}

        def work():
            home = pending.get("home") or paths.account_home(pending.get("account_id") or self._current_account_id or None)
            store = Store(passphrase=secrets.load_passphrase(), home=home)
            result = store.login(pending.get("email", ""), pending.get("password", ""), code)
            # переключаем клиент на этот HOME только после успешного входа
            self._store = store
            return result

        def done(result, error):
            if error and isinstance(error, StoreError) and error.needs_2fa:
                self.loginNeedsCode = True
                self.loginNote = (
                    "Введите шестизначный код. Если уведомление на устройство не пришло, "
                    "откройте на iPhone или iPad: Настройки → ваше имя → Вход и безопасность → Получить код проверки."
                )
                self.log("Нужен код подтверждения Apple.")
                return
            if error:
                # поле кода оставляем, если Apple его уже запросила: повторный вход с --auth-code
                if not self.loginNeedsCode:
                    self._pending_login = None
                    self.loginNeedsCode = False
                self.log(str(error))
                self.show_notice("Вход", str(error))
                return
            self._pending_login = None
            self.loginNeedsCode = False
            email = (result or {}).get("email") or pending.get("email") or ""
            storefront = regions.parse_storefront((result or {}).get("storeFront") or (result or {}).get("storefront") or "")
            info = {}
            try:
                info = self._store_client().info() or {}
            except StoreError:
                info = {}
            storefront = storefront or regions.parse_storefront(info.get("storeFront") or info.get("storefront") or "")
            account_id = pending.get("account_id") or self._current_account_id
            self._apply_account({"logged": True, "email": email, "storefront": storefront, "account_id": account_id})
            self._adding_account = False
            self._login_home = None
            self.loginOpen = False
            self.log("Вход выполнен" + (f" · витрина {regions.name(storefront)}" if storefront else ""))

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
            self.accountStorefront = ""
            self.accountStorefrontName = ""
            self._purchases = []
            self._mine.replace([])
            self._reload_accounts()
            self.log("Вы вышли из Apple ID")

        self._run(work, done)

    @Slot()
    def addAccount(self):
        self._adding_account = True
        # новый HOME, чтобы не перезаписать сессию текущего аккаунта до успешного входа
        new_id = accounts._new_id("account")
        self._login_home = paths.account_home(new_id)
        self.openLogin("Войдите в другой Apple ID. Пароль на диск не сохраняется. Сессия хранится отдельно.")

    @Slot(str)
    def switchAccount(self, account_id):
        account_id = str(account_id or "")
        row = accounts.find(account_id)
        if not row:
            return
        self.detailOpen = False
        accounts.set_current(account_id)
        self._current_account_id = account_id
        self._reset_store()
        self._purchases = []
        self._mine.replace([])

        def work():
            info = self._store_client().info()
            email = str((info or {}).get("email") or (info or {}).get("account") or "") if info else ""
            storefront = regions.parse_storefront((info or {}).get("storeFront") or (info or {}).get("storefront") or "") if info else row.get("storefront") or ""
            return {"logged": bool(info and email), "email": email or row.get("email") or "", "storefront": storefront or row.get("storefront") or "", "account_id": account_id}

        def done(result, error):
            if error or not result or not result.get("logged"):
                self.loggedIn = False
                self.account = row.get("email") or ""
                self.accountStorefront = row.get("storefront") or ""
                self.accountStorefrontName = regions.name(self._accountStorefront)
                self._reload_accounts()
                self.openLogin(f"Войдите в {row.get('email') or 'этот Apple ID'}, чтобы скачивать из его витрины.")
                return
            self._apply_account(result)
            self.log(f"Переключились на {result.get('email')}")

        self._run(work, done)

    @Slot(str)
    def removeAccount(self, account_id):
        account_id = str(account_id or "")
        row = accounts.find(account_id)
        if not row:
            return

        def work():
            if account_id == self._current_account_id:
                try:
                    self._store_client().revoke()
                except StoreError:
                    pass
            accounts.delete_home(account_id)
            return accounts.remove(account_id)

        def done(data, error):
            if error:
                self.log(str(error))
            nxt = (data or {}).get("current") or ""
            self._current_account_id = nxt
            self._reset_store()
            if nxt:
                self.switchAccount(nxt)
            else:
                self.loggedIn = False
                self.account = ""
                self.accountStorefront = ""
                self.accountStorefrontName = ""
                self._purchases = []
                self._mine.replace([])
                self._reload_accounts()
            self.log("Аккаунт удалён. Пароль на диске не хранился.")

        self._run(work, done)

    @Slot(int)
    def setStorefrontIndex(self, index):
        codes = regions.codes()
        if 0 <= int(index) < len(codes):
            self.storefrontIndex = int(index)
            self.country = codes[int(index)]

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
                row["status"] = "на устройстве"
                row["statusKind"] = "ok"
            out.append(row)
        self._mine.replace(out)
        self._fill_icons(self._mine)

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
                self.show_notice("Установка", "Приложение установлено на устройство.")
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


    def _update_leftovers(self) -> None:
        leftover = ipa_svc.list_temps(Path(self._ipaDir))
        self.leftoverCount = len(leftover)
        self.leftoverHint = ipa_svc.leftover_hint(leftover)

    def _sweep_temps(self, *, announce: bool = False) -> None:
        # Только при запуске и по кнопке. Не трогать файлы во время текущей загрузки.
        if self._jobActive:
            self._update_leftovers()
            return
        folder = Path(self._ipaDir)
        result = ipa_svc.clean_temps(folder, include_huge=False)
        leftover = result.get("leftover") or []
        self.leftoverCount = len(leftover)
        self.leftoverHint = ipa_svc.leftover_hint(leftover)
        if leftover and announce and not self._leftovers_announced:
            self._leftovers_announced = True
            self.show_notice("Незавершённые загрузки", self._leftoverHint + " Откройте «Файлы .ipa» и нажмите «Удалить незавершённые».")
        else:
            self._leftovers_announced = True

    @Slot()
    def cleanLeftovers(self):
        if self._jobActive:
            self.show_notice("Папка IPA", "Дождитесь окончания текущей загрузки, затем удалите незавершённые файлы.")
            return
        result = ipa_svc.clean_temps(Path(self._ipaDir), include_huge=True)
        deleted = result.get("deleted") or 0
        self.refresh_ipa()
        if deleted:
            self.show_notice("Папка IPA", f"Удалено незавершённых файлов: {deleted}.")
        else:
            self.show_notice("Папка IPA", "Незавершённых загрузок нет.")

    def refresh_ipa(self):
        rows = ipa_svc.list_files(Path(self._ipaDir))
        for row in rows:
            row["tint"] = self._tint(row.get("title") or "")
            row["letter"] = (row.get("title") or "?")[:1].upper()
        self._ipa.replace(rows)
        self.ipaSummary = f"Файлов IPA: {len(rows)}" if rows else "Скачанных файлов нет"
        self._update_leftovers()

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
        self.versionNeedPurchase = False
        self.actionsEnabled = False
        self.detailAvailability = ""
        self.detailSwitchHint = ""
        self.detailSwitchAccountId = ""
        self.installHint = ""
        self.newerVersionReady = False
        self.installAnywayReady = False
        self.detailMacOnly = False
        self._enrich_token += 1
        self._pending_ipa = None
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
            avail = {"present": [], "missing": [], "text": ""}
            try:
                store_item = itunes.lookup(app["id"], self._country or "ru") if app["id"] else None
            except itunes.ITunesError:
                store_item = None
            if (not store_item or not platform_svc.from_metadata(store_item)) and app["id"]:
                try:
                    found = itunes.lookup_anywhere([app["id"]], prefer=self._country or "ru")
                    store_item = store_item or found.get(app["id"])
                except itunes.ITunesError:
                    pass
            if app["id"]:
                try:
                    avail = itunes.availability(app["id"])
                except itunes.ITunesError:
                    avail = {"present": [], "missing": [], "text": ""}
            plat = platform_svc.from_metadata(store_item) or platform_svc.from_metadata(app)
            versions = []
            err = ""
            if plat != "mac":
                try:
                    versions = self._store_client().list_versions(app_id=app["id"] or None, bundle=app["bundle"] or None)
                except StoreError as exc:
                    err = str(exc)
            return store_item, versions, err, avail, plat

        def done(result, error):
            if error:
                self.versionMode = "error"
                self.detailErr = _public_error(error)
                self.log(f"Версии: {error}")
                return
            store_item, versions, err, avail, plat = result
            checks = dict(self._detailChecks)
            if store_item:
                checks["store"] = {"text": f"есть в App Store {regions.name(self._country or 'ru')}", "kind": "ok"}
            else:
                checks["store"] = {"text": "нет в выбранной витрине каталога", "kind": "warn"}
            self.detailChecks = checks
            self._apply_availability(app["id"], avail)
            if plat == "mac" or platform_svc.is_mac(store_item):
                self.detailMacOnly = True
                self.versionMode = "none"
                self.actionsEnabled = False
                self.installHint = "Это приложение только для Mac. На iPhone и iPad его поставить нельзя."
                self.detailErr = ""
                return
            self.detailMacOnly = False
            if versions:
                self._show_versions(versions, app)
                return
            # пустой список часто значит «нет лицензии», а не «нет в истории»
            if store_item and self._loggedIn:
                self.versionNeedPurchase = True
                self.versionMode = "need_purchase"
                self.detailErr = err or ""
                self.actionsEnabled = True
                return
            if err:
                self.versionMode = "error"
                self.detailErr = _public_error(err)
                self.log(f"Версии: {err}")
                return
            self.versionMode = "none"
            self.actionsEnabled = bool(self._loggedIn)

        self._run(work, done)

    def _show_versions(self, versions, app=None):
        self.versionNeedPurchase = False
        app = app or self._detailApp or {}
        versions = [_with_legacy_flag(row, app.get("id")) for row in versions]
        self._versions.replace(versions)
        self.selectedVersion = versions[0]["value"]
        self.versionMode = "list"
        self.actionsEnabled = bool(self._loggedIn)
        app = app or self._detailApp or {}
        if any(not row.get("displayVersion") or not row.get("sub") for row in versions):
            self._enrich_token += 1
            token = self._enrich_token

            def work():
                def should_stop():
                    return token != self._enrich_token
                return self._store_client().enrich_versions(
                    list(versions), app_id=app.get("id") or None, bundle=app.get("bundle") or None,
                    should_stop=should_stop)

            def done(rows, error):
                if error or not rows or token != self._enrich_token:
                    return
                current = self.selectedVersion
                flagged = [_with_legacy_flag(row, app.get("id")) for row in rows]
                self._versions.replace(flagged)
                if current:
                    self.selectedVersion = current

            self._run(work, done, mark_busy=False)

    @Slot()
    def purchaseAndListVersions(self):
        app = self._detailApp or {}
        if not app.get("id") and not app.get("bundle"):
            return
        self.versionMode = "loading"
        self.versionNeedPurchase = False

        def work():
            self._store_client().purchase(app_id=app.get("id") or None, bundle=app.get("bundle") or None)
            return self._store_client().list_versions(app_id=app.get("id") or None, bundle=app.get("bundle") or None)

        def done(versions, error):
            if error:
                self.versionMode = "error"
                self.detailErr = _public_error(error)
                self.log(f"Получение приложения: {error}")
                self.show_notice("Версии", _public_error(error))
                return
            if not versions:
                self.versionMode = "none"
                self.actionsEnabled = bool(self._loggedIn)
                self.show_notice("Версии", "Лицензия получена, но список версий пуст.")
                return
            self._show_versions(versions, app)

        self.log("Получаю приложение в этом Apple ID…")
        self._run(work, done)

    @Slot()
    def closeDetail(self):
        self._enrich_token += 1
        self.detailOpen = False
        self.detailMacOnly = False

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
        if self._detailMacOnly or platform_svc.is_mac(app):
            self.show_notice("Только для Mac", "Это приложение только для Mac. На iPhone и iPad его поставить нельзя.")
            return
        self._download_many([{"appId": app.get("id"), "title": app.get("name"), "bundle": app.get("bundle"),
                              "version": self._selectedVersion}], install=install)

    def _need_iphone(self) -> bool:
        """True, если установку нельзя начать: телефон не виден, уже показали подсказку."""
        if self._deviceState == "ok":
            return False
        self.show_notice(
            "Устройство не видно",
            "Установите «Устройства Apple» из Microsoft Store, подключите кабель и нажмите «Доверять» на iPhone или iPad.",
        )
        return True

    def _download_many(self, rows, install=False):
        if install and self._need_iphone():
            return
        if self._jobActive:
            self.show_notice("Загрузка", "Дождитесь окончания текущей загрузки.")
            return
        overlap = jobs_svc.has_overlap(self._active_job_keys, rows)
        if overlap:
            self.show_notice("Загрузка", "Это приложение уже скачивается.")
            return
        folder = Path(self._ipaDir)
        folder.mkdir(parents=True, exist_ok=True)
        jobs = []
        keys = []
        for item in rows:
            title = item.get("title") or item.get("name") or item.get("appId") or item.get("id") or "приложение"
            version_id = item.get("version") or self._selectedVersion or None
            key = jobs_svc.job_key(item.get("appId") or item.get("id"), version_id)
            keys.append(key)
            jobs.append({
                "title": title,
                "phase": "очередь",
                "downloadText": "",
                "installText": "",
                "downloadPct": 0,
                "installPct": 0,
                "state": "queued",
                "appId": item.get("appId") or item.get("id") or "",
            })
        self._active_job_keys.update(keys)
        self._begin_jobs(jobs, install=install)
        self._enrich_token += 1  # остановить подгрузку метаданных
        try:
            self._store_client().pause_metadata(True)
        except Exception:
            pass

        def work():
            results = []
            legacy = None
            try:
                for index, item in enumerate(rows):
                    if self._stop.is_set():
                        break
                    title = item.get("title") or item.get("name") or item.get("appId") or "приложение"
                    self._job_status(index, state="download", phase="скачивание")
                    app_id = item.get("appId") or item.get("id")
                    bundle = item.get("bundle")
                    version_id = item.get("version") or self._selectedVersion or None

                    def on_dl(hit, i=index):
                        text = progress_svc.format_download(hit.get("pct"), hit.get("done"), hit.get("total"), hit.get("speed"))
                        self._job_status(i, downloadPct=hit.get("pct") if hit.get("pct") is not None else -1, downloadText=text, phase="скачивание", state="download")

                    try:
                        path = self._store_client().download_verified(
                            folder, title=title, app_id=app_id, bundle=bundle or None,
                            version_id=version_id, buy=self._purchase, on_progress=on_dl,
                        )
                    except StoreError as exc:
                        self._job_status(index, state="error", phase="ошибка", downloadText=_public_error(exc))
                        raise
                    check = ipa_svc.validate(path)
                    if check.get("platform") == "mac":
                        self._job_status(index, state="error", phase="только для Mac",
                                         downloadPct=100, downloadText="100 %",
                                         installText="Это приложение только для Mac. На iPhone и iPad его поставить нельзя.")
                        raise StoreError("Это приложение только для Mac. На iPhone и iPad его поставить нельзя.")
                    self._job_status(index, state="downloaded", phase="скачано", downloadPct=100, downloadText="100 %")
                    results.append(path)
                    if not install:
                        continue
                    verdict = codesign.inspect_ipa(path)
                    if verdict.get("legacy"):
                        _remember_legacy(app_id, version_id)
                        self._job_status(index, state="legacy", phase="старая подпись", installText=codesign.LEGACY_TEXT)
                        legacy = {"path": str(path), "title": title, "app_id": app_id, "version": version_id, "verdict": verdict}
                        continue

                    def on_inst(hit, i=index):
                        text = progress_svc.format_install(hit.get("pct"), hit.get("stage") or "")
                        self._job_status(i, installPct=hit.get("pct") if hit.get("pct") is not None else -1, installText=text, phase=hit.get("stage") or "установка", state="install")

                    try:
                        device_svc.install_ipa(path, on_progress=on_inst)
                    except Exception as inst_exc:
                        raw = str(getattr(inst_exc, "raw", "") or inst_exc)
                        kind = ""
                        try:
                            from restore_gui.service.install_errors import classify
                            kind = classify(raw)
                        except Exception:
                            kind = ""
                        if kind != "package_extract":
                            raise
                        # устройство не смогло распаковать — ещё одна попытка скачать и поставить
                        paths.write_app_log(f"установка: PackageExtractionFailed, повторная загрузка: {raw}")
                        self._job_status(index, state="download", phase="скачиваю заново",
                                         installText=ipa_svc.CORRUPT_TEXT, downloadPct=0, downloadText="скачиваю заново")
                        try:
                            path.unlink()
                        except OSError:
                            pass
                        path = self._store_client().download_verified(
                            folder, title=title, app_id=app_id, bundle=bundle or None,
                            version_id=version_id, buy=self._purchase, on_progress=on_dl,
                        )
                        device_svc.install_ipa(path, on_progress=on_inst)
                    self._job_status(index, state="done", phase="готово", installPct=100, installText="100 % · установка")
                    if self._deleteAfterInstall:
                        try:
                            path.unlink()
                        except OSError:
                            pass
                return {"paths": results, "legacy": legacy, "install": install}
            finally:
                try:
                    self._store_client().pause_metadata(False)
                except Exception:
                    pass

        def done(result, error):
            self._active_job_keys.difference_update(keys)
            self.refresh_ipa()
            self.jobActive = False
            try:
                self._store_client().pause_metadata(False)
            except Exception:
                pass
            if error:
                raw = getattr(error, "raw", "") or str(error)
                paths.write_app_log(f"загрузка/установка: {raw}")
                public = _public_error(error)
                self.log(public)
                self.installHint = public if isinstance(error, InstallError) or "0xe8" in raw.lower() or "signature" in raw.lower() or "storefront" in raw.lower() or "region" in raw.lower() else public
                if isinstance(error, InstallError) and error.kind == "legacy_signature":
                    self.installHint = error.public
                    self.newerVersionReady = bool(self._next_newer_version())
                self.show_notice("Загрузка" if not install else "Установка", public)
                return
            legacy = (result or {}).get("legacy")
            paths_ok = (result or {}).get("paths") or []
            if legacy:
                self.installHint = codesign.LEGACY_TEXT
                self.newerVersionReady = bool(self._next_newer_version())
                self.installAnywayReady = True
                self._pending_ipa = legacy
                self._mark_legacy_version(legacy.get("version"))
                self.show_notice("Установка", codesign.LEGACY_TEXT)
                return
            self.installHint = ""
            self.log(f"Готово файлов: {len(paths_ok)}")
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
            "скачивает IPA и ставит их на iPhone или iPad по кабелю.\n\n"
            "Чтобы Windows увидела устройство, установите приложение «Устройства Apple» (Apple Devices) "
            "из Microsoft Store, подключите кабель и на телефоне нажмите «Доверять».\n"
            f"Ссылка: {core.APPLE_DEVICES_STORE_URL}\n\n"
            "Пароль Apple ID на диск не записывается: сессию хранит ipatool-cpp в зашифрованном виде, "
            "а ключ к ней — в Windows Credential Manager или в файле, защищённом DPAPI. "
            "Можно добавить несколько Apple ID разных стран и переключаться между ними: "
            "Apple отдаёт файл только в витрине того аккаунта, под которым вы вошли.\n\n"
            "В каталоге можно выбрать страну витрины. Если приложения нет в текущем аккаунте, "
            "программа подскажет, каким из сохранённых Apple ID его скачать.\n\n"
            "Обновления берутся только с GitHub Releases, файл сверяется по SHA-256. "
            "Если что-то пойдёт не так, в «Настройки → О программе» можно вернуть предыдущую копию.\n\n"
            "Журналы: %LOCALAPPDATA%\\RestoreAppStore\\app.log и startup.log. "
            "Папку можно открыть в «Настройки → О программе». "
            "Если уведомление с кодом не приходит, получите код вручную: "
            "Настройки → ваше имя → Вход и безопасность → Получить код проверки. "
            "Диагностика кабеля: RestoreAppStore.exe --diag-device (пишет в app.log и сразу закрывается)."
        )


    def _apply_availability(self, app_id: str, avail: dict) -> None:
        present = list(avail.get("present") or [])
        self.detailAvailability = avail.get("text") or ""
        self.detailSwitchHint = ""
        self.detailSwitchAccountId = ""
        account_sf = self._accountStorefront or ""
        if account_sf and account_sf in present:
            return
        # если текущая витрина аккаунта не содержит приложение — подсказка сменить аккаунт
        other = accounts.find_by_storefronts(present, exclude=self._current_account_id)
        if other:
            self.detailSwitchHint = regions.switch_hint(other.get("email") or "", other.get("storefront") or "")
            self.detailSwitchAccountId = other["id"]
        elif present and account_sf and account_sf not in present:
            self.detailSwitchHint = regions.unavailable_message(present)

    def _begin_jobs(self, jobs: list[dict], *, install: bool) -> None:
        self._jobList.replace(jobs)
        self.jobCount = len(jobs)
        self.jobActive = True
        self.jobOverall = f"1 из {len(jobs)}" if jobs else ""
        self.downloadPct = 0
        self.downloadText = "Скачивание…"
        self.installPct = -1 if not install else 0
        self.installText = "Установка…" if install else ""
        self.installHint = ""
        self.newerVersionReady = False
        self.installAnywayReady = False

    def _job_status(self, index: int, **fields) -> None:
        def apply():
            row = self._jobList.at(index)
            if row:
                self._jobList._rows[index].update(fields)
                # обновить роли
                self._jobList.dataChanged.emit(self._jobList.index(index), self._jobList.index(index))
            if fields.get("downloadText") is not None or fields.get("downloadPct") is not None:
                if fields.get("downloadPct") is not None:
                    self.downloadPct = float(fields["downloadPct"]) if fields["downloadPct"] is not None else -1
                if fields.get("downloadText"):
                    self.downloadText = fields["downloadText"]
            if fields.get("installText") is not None or fields.get("installPct") is not None:
                if fields.get("installPct") is not None:
                    self.installPct = float(fields["installPct"]) if fields["installPct"] is not None else -1
                if fields.get("installText"):
                    self.installText = fields["installText"]
            total = max(1, len(self._jobList._rows))
            self.jobOverall = f"{index + 1} из {total}" + (f" · {row['title']}" if row and row.get("title") else "")
            self.jobCount = total
        QTimer.singleShot(0, self, apply)

    def _next_newer_version(self) -> dict | None:
        rows = list(getattr(self._versions, "_rows", []) or [])
        if not rows:
            return None
        current = self._selectedVersion
        ordered = sorted(rows, key=_version_sort_key)
        values = [str(row.get("value") or "") for row in ordered]
        if current not in values:
            return ordered[-1] if ordered else None
        idx = values.index(current)
        if idx + 1 < len(ordered):
            return ordered[idx + 1]
        return None

    def _mark_legacy_version(self, version_id) -> None:
        if not version_id:
            return
        for row in getattr(self._versions, "_rows", []) or []:
            if str(row.get("value") or "") == str(version_id):
                note = "старая подпись — iOS не примет"
                sub = row.get("sub") or ""
                if note not in sub:
                    sub = (sub + " · " if sub else "") + note
                self._versions.patch_by_value(str(version_id), legacy=True, note=note, sub=sub)

    @Slot()
    def selectNewerVersion(self):
        nxt = self._next_newer_version()
        if not nxt:
            self.show_notice("Версии", "Это самая новая версия в списке. Более новую Apple уже не отдаёт.")
            return
        self.selectedVersion = nxt["value"]
        self.installHint = f"Выбрана более новая версия {nxt.get('title') or nxt['value']}. Можно скачать и установить её."
        self.newerVersionReady = bool(self._next_newer_version())
        self.installAnywayReady = False
        self.versionMode = "list"

    @Slot()
    def installAnyway(self):
        pending = self._pending_ipa or {}
        path = Path(pending.get("path") or "")
        if not path.is_file():
            self.show_notice("Установка", "Сначала скачайте файл ещё раз.")
            return

        def work():
            def on_inst(hit):
                text = progress_svc.format_install(hit.get("pct"), hit.get("stage") or "")
                self._job_status(0, installPct=hit.get("pct") if hit.get("pct") is not None else -1, installText=text, phase=hit.get("stage") or "установка", state="install")
            self._begin_jobs([{"title": pending.get("title") or path.name, "phase": "установка", "downloadText": "уже скачано", "installText": "Установка…", "downloadPct": 100, "installPct": 0, "state": "install", "appId": pending.get("app_id") or ""}], install=True)
            device_svc.install_ipa(path, on_progress=on_inst)
            return path

        def done(_result, error):
            self.jobActive = False
            self.installAnywayReady = False
            if error:
                paths.write_app_log(f"установка: {getattr(error, 'raw', '') or error}")
                public = _public_error(error)
                self.installHint = public
                self.newerVersionReady = bool(self._next_newer_version())
                self.show_notice("Установка", public)
                return
            self.installHint = ""
            self.log("Установка завершена")
            if self._notifyDone:
                self.show_notice("Готово", "Установка завершена.")

        self._run(work, done)

    @Slot()
    def refreshIcons(self):
        itunes.clear_miss_cache()
        for model in (self._mine, self._apps, self._popular):
            self._fill_icons(model)
        self.log("Обновляю иконки, в том числе в других витринах App Store…")

    @Slot()
    def shutdown(self):
        self._stop.set()
        if self._device_timer is not None:
            self._device_timer.stop()
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
        remote_icon = item.get("icon") or item.get("artwork") or ""
        icon = remote_icon
        if icon and icon.startswith("https://"):
            local = icon_svc.cached_path(app_id, icon)
            if local:
                icon = paths.file_url(local)
        elif icon and not icon.startswith("file:"):
            local = icon_svc.cached_path(app_id, "")
            if local:
                icon = paths.file_url(local)
            else:
                icon = ""
        price = format_price(item.get("price") or "")
        developer = str(item.get("developer") or item.get("artist") or "")
        sub = " · ".join(part for part in (developer, price or item.get("version") or item.get("date") or "") if part)
        plat = item.get("platform") or platform_svc.from_metadata(item) or ""
        if plat == "mac":
            status = status or "только для Mac"
            statusKind = statusKind or "warn"
        return {
            "appId": app_id,
            "title": name,
            "sub": sub,
            "letter": (name or "?")[:1].upper(),
            "tint": self._tint(app_id or name),
            "icon": icon,
            "remoteIcon": remote_icon if str(remote_icon).startswith("https://") else "",
            "status": status,
            "statusKind": statusKind,
            "selected": False,
            "copies": item.get("copies") or "",
            "bundle": item.get("bundle") or "",
            "genre": genre or item.get("genre") or item.get("kind") or "",
            "price": price,
            "platform": plat,
        }

    def _fill_icons(self, model) -> None:
        rows = [dict(row) for row in getattr(model, "_rows", [])]
        if not rows:
            return
        country = self._country or "ru"

        def work():
            missing = [row["appId"] for row in rows if row.get("appId") and not str(row.get("icon") or "").startswith("file:")]
            found = {}
            need_lookup = []
            for row in rows:
                app_id = row.get("appId") or ""
                if not app_id:
                    continue
                if row.get("platform") == "mac" or row.get("status") == "только для Mac":
                    continue
                no_icon = app_id in missing and not str(row.get("remoteIcon") or "").startswith("https://")
                needs_platform = not row.get("platform")
                if no_icon or needs_platform:
                    need_lookup.append(app_id)
            need_lookup = list(dict.fromkeys(need_lookup))
            bundles = {row["appId"]: row.get("bundle") or "" for row in rows if row.get("appId") and row.get("bundle")}
            if need_lookup:
                try:
                    found = itunes.lookup_anywhere(need_lookup, prefer=country, bundles=bundles)
                except itunes.ITunesError as exc:
                    paths.write_app_log(f"иконки lookup: {exc}")
                    found = {}
            updates = []
            for row in rows:
                app_id = row.get("appId") or ""
                url = str(row.get("remoteIcon") or "")
                info = found.get(app_id) or {}
                extra = {}
                plat = platform_svc.from_metadata(info)
                if plat:
                    extra["platform"] = plat
                if plat == "mac":
                    extra["status"] = "только для Mac"
                    extra["statusKind"] = "warn"
                if not url.startswith("https://"):
                    url = str(info.get("icon") or "")
                path = None
                if url.startswith("https://"):
                    path = icon_svc.fetch(app_id, url)
                if path:
                    price = format_price(info.get("price") or row.get("price") or "")
                    developer = info.get("developer") or ""
                    if developer or price:
                        extra["sub"] = " · ".join(part for part in (developer, price or row.get("sub") or "") if part)
                    updates.append((app_id, paths.file_url(path), extra))
                elif extra:
                    updates.append((app_id, row.get("icon") or "", extra))
            return updates

        def done(updates, error):
            if error or not updates:
                return
            for app_id, icon, extra in updates:
                fields = dict(extra)
                if icon:
                    fields["icon"] = icon
                model.patch_by_id(app_id, **fields)

        self._run(work, done, mark_busy=False)

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


def _looks_internal(text: str) -> bool:
    blob = (text or "").strip().lower()
    if not blob:
        return False
    tokens = (
        "coroutine", "traceback", "typeerror", "attributeerror", "exception:",
        "file \"", "line ", "object is not", "asyncio", "nonetype",
    )
    return any(token in blob for token in tokens)


def _public_error(exc) -> str:
    if isinstance(exc, InstallError):
        return exc.public
    text = str(exc or "").strip()
    from restore_gui.service.install_errors import classify, public_message
    kind = classify(text)
    if kind != "other":
        return public_message(text)
    from restore_gui.service.regions import is_region_error, unavailable_message
    if is_region_error(text):
        return unavailable_message()
    if not text or _looks_internal(text):
        return "Не удалось выполнить операцию. Подробности записаны в журнал."
    return text[:400]


def _public_device_text(text: str, state: str) -> str:
    raw = (text or "").strip()
    if _looks_internal(raw):
        if state == "trust":
            return device_svc.TRUST_TEXT
        return "Не удалось связаться с устройством. Подключите кабель и нажмите «Доверять» на iPhone или iPad."
    return raw


def _legacy_cache_path() -> Path:
    folder = paths.data_dir() / "cache"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "legacy-signatures.json"


def _remember_legacy(app_id, version_id) -> None:
    import json
    if not app_id or not version_id:
        return
    path = _legacy_cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data[f"{app_id}:{version_id}"] = True
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def _is_cached_legacy(app_id, version_id) -> bool:
    import json
    if not app_id or not version_id:
        return False
    path = _legacy_cache_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(isinstance(data, dict) and data.get(f"{app_id}:{version_id}"))


def _with_legacy_flag(row: dict, app_id) -> dict:
    item = dict(row)
    if _is_cached_legacy(app_id, item.get("value")):
        item["legacy"] = True
        note = "старая подпись — iOS не примет"
        item["note"] = note
        sub = item.get("sub") or ""
        if note not in sub:
            item["sub"] = (sub + " · " if sub else "") + note
    else:
        item.setdefault("legacy", False)
        item.setdefault("note", "")
    return item


def _version_sort_key(row: dict):
    import re
    from datetime import datetime
    raw_date = str(row.get("sub") or row.get("date") or "")
    stamp = datetime.min
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw_date)
    if m:
        try:
            stamp = datetime.fromisoformat(m.group(0))
        except ValueError:
            stamp = datetime.min
    ver = str(row.get("displayVersion") or row.get("title") or "")
    parts = []
    for bit in re.findall(r"\d+", ver):
        try:
            parts.append(int(bit))
        except ValueError:
            parts.append(0)
    parts += [0] * (4 - len(parts))
    ext = str(row.get("value") or "")
    ext_n = int(ext) if ext.isdigit() else 0
    return (stamp, tuple(parts[:4]), ext_n)
