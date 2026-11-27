
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT))
import sandbox  # noqa: E402
from restore_gui.service.store import parse_app_ref, _as_apps, _as_versions, _parse_json, _looks_like_2fa  # noqa: E402
from restore_gui.service.updater import parse_version, is_newer, _safe_extract, UpdateError  # noqa: E402
from restore_gui.service import prefs, secrets, paths  # noqa: E402
from restore_gui.service.ipa import inspect, list_files  # noqa: E402
import zipfile
import tempfile
import plistlib


class ParseRefTests(unittest.TestCase):
    def test_id(self):
        self.assertEqual(parse_app_ref("492224193")["kind"], "id")
        self.assertEqual(parse_app_ref("https://apps.apple.com/ru/app/x/id492224193")["value"], "492224193")

    def test_bundle_and_term(self):
        self.assertEqual(parse_app_ref("com.example.app")["kind"], "bundle")
        self.assertEqual(parse_app_ref("сбербанк")["kind"], "term")
        self.assertEqual(parse_app_ref("  ")["kind"], "empty")


class JsonTests(unittest.TestCase):
    def test_parse_and_apps(self):
        data = _parse_json('{"count":1,"apps":[{"id":1,"name":"Mail","bundleId":"com.a.mail"}]}')
        rows = _as_apps(data)
        self.assertEqual(rows[0]["id"], "1")
        self.assertEqual(rows[0]["bundle"], "com.a.mail")

    def test_versions(self):
        rows = _as_versions({"versions": [{"displayVersion": "1.2", "externalVersionId": "99", "releaseDate": "2020-01-01"}]})
        self.assertEqual(rows[0]["title"], "1.2")
        self.assertEqual(rows[0]["value"], "99")

    def test_2fa(self):
        self.assertTrue(_looks_like_2fa("Please enter auth-code"))
        self.assertFalse(_looks_like_2fa("login failed"))


class PrefsSecretsTests(unittest.TestCase):
    def test_prefs_roundtrip(self):
        prefs.save({"themeMode": "dark", "accentName": "ocean", "heroineName": "vera",
                    "country": "us", "deleteAfterInstall": True, "notifyDone": False,
                    "autoUpdate": False, "skipVersion": "1.2.3", "ipaDir": str(paths.default_ipa_dir())})
        data = prefs.load()
        self.assertEqual(data["themeMode"], "dark")
        self.assertEqual(data["heroineName"], "vera")
        self.assertFalse(data["notifyDone"])

    def test_passphrase(self):
        first = secrets.load_passphrase()
        second = secrets.load_passphrase()
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 16)


class UpdaterTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(parse_version("v2.0.0"), (2, 0, 0))
        self.assertTrue(is_newer("2.0.1", "2.0.0"))
        self.assertFalse(is_newer("1.9.9", "2.0.0"))

    def test_zip_rejects_parent(self):
        folder = Path(tempfile.mkdtemp())
        archive = folder / "bad.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../evil.txt", "no")
        with self.assertRaises(UpdateError):
            _safe_extract(archive, folder / "out")


class IpaTests(unittest.TestCase):
    def test_inspect_and_list(self):
        folder = Path(tempfile.mkdtemp())
        payload = folder / "build"
        app = payload / "Payload" / "Demo.app"
        app.mkdir(parents=True)
        (app / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleDisplayName": "Демо",
            "CFBundleIdentifier": "com.example.demo",
            "CFBundleShortVersionString": "1.0",
        }))
        ipa = folder / "Demo.ipa"
        with zipfile.ZipFile(ipa, "w") as zf:
            zf.write(app / "Info.plist", "Payload/Demo.app/Info.plist")
        info = inspect(ipa)
        self.assertEqual(info["name"], "Демо")
        self.assertEqual(info["bundle"], "com.example.demo")
        rows = list_files(folder)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Демо")


if __name__ == "__main__":
    unittest.main()


from restore_gui.backend import _allowed_url, _reduce_motion  # noqa: E402
from restore_gui import theme  # noqa: E402
import restore_apps as core  # noqa: E402


class AllowedUrlTests(unittest.TestCase):
    def test_apple_devices_https(self):
        self.assertTrue(_allowed_url(core.APPLE_DEVICES_STORE_URL))
        self.assertTrue(_allowed_url("https://apps.microsoft.com/store/detail/apple-devices-preview/9NP83LWLPZ9K"))
        self.assertTrue(_allowed_url(core.APPLE_DEVICES_STORE_URL.lower()))

    def test_apple_devices_deep_link(self):
        self.assertTrue(_allowed_url(core.APPLE_DEVICES_STORE_DEEP))
        self.assertFalse(_allowed_url("ms-windows-store://pdp/?ProductId=9ABCDEF"))
        self.assertFalse(_allowed_url("ms-windows-store://pdp/?ProductId="))

    def test_rejects_other_hosts(self):
        self.assertFalse(_allowed_url("https://evil.example/9NP83LWLPZ9K"))
        self.assertFalse(_allowed_url("https://apps.microsoft.com/detail/9NOTAPPLE"))
        self.assertFalse(_allowed_url("http://apps.microsoft.com/detail/9NP83LWLPZ9K"))


class HeroineOrbTests(unittest.TestCase):
    def test_all_ten_orbs(self):
        for key in ("mira", "nora", "liora", "vera", "kira"):
            for dark in (False, True):
                orb = theme.heroine_orb(key, dark)
                self.assertIsInstance(orb["x"], float, msg=f"{key} dark={dark}")
                self.assertGreater(orb["x"], 0)
                self.assertLess(orb["x"], 1)
                self.assertGreater(orb["y"], 0)
                self.assertLess(orb["y"], 1)
                self.assertGreater(orb["r"], 0.04)
                self.assertLess(orb["r"], 0.15)
                self.assertTrue(orb["color"].startswith("#"))
        self.assertEqual(theme.heroine_orb("off"), {})
        self.assertEqual(theme.heroine_orb(""), {})

    def test_reduce_motion_env(self):
        import os
        old = os.environ.get("QML_REDUCE_MOTION")
        try:
            os.environ["QML_REDUCE_MOTION"] = "1"
            self.assertTrue(_reduce_motion())
            os.environ["QML_REDUCE_MOTION"] = "0"
            self.assertFalse(_reduce_motion())
        finally:
            if old is None:
                os.environ.pop("QML_REDUCE_MOTION", None)
            else:
                os.environ["QML_REDUCE_MOTION"] = old


from restore_gui.service.store import public_command, redact_text, _looks_like_2fa, Store, StoreError  # noqa: E402


class CommandRedactTests(unittest.TestCase):
    def test_hides_secrets(self):
        cmd = ["ipatool-cpp.exe", "--format", "json", "--keychain-passphrase", "s3cret",
               "auth", "login", "-e", "user@example.com", "-p", "hunter2", "--auth-code", "123456"]
        public = public_command(cmd)
        joined = " ".join(public)
        self.assertNotIn("s3cret", joined)
        self.assertNotIn("hunter2", joined)
        self.assertNotIn("123456", joined)
        self.assertNotIn("user@example.com", joined)
        self.assertIn("***", joined)
        self.assertIn("login", joined)

    def test_redact_text(self):
        text = "password=hunter2 token: abc email me@example.com"
        out = redact_text(text)
        self.assertNotIn("hunter2", out)
        self.assertNotIn("me@example.com", out)
        self.assertIn("***", out)

    def test_2fa_prompt(self):
        self.assertTrue(_looks_like_2fa("Enter 2FA code: "))
        self.assertTrue(_looks_like_2fa("Need an auth-code"))
        self.assertFalse(_looks_like_2fa("login failed: invalid password"))


import time
import textwrap


class StoreRunTests(unittest.TestCase):
    def _script(self, body: str) -> Path:
        folder = Path(tempfile.mkdtemp())
        path = folder / "fake-ipatool"
        path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_stop_on_2fa_prompt(self):
        script = self._script("""
            import sys, time
            sys.stderr.write("Enter 2FA code: \\n")
            sys.stderr.flush()
            time.sleep(30)
            sys.exit(1)
        """)
        store = Store(exe=script, passphrase="")
        start = time.time()
        with self.assertRaises(StoreError) as ctx:
            store.run(["auth", "login", "-e", "x", "-p", "y"], timeout=10, stop_on_2fa=True)
        self.assertTrue(ctx.exception.needs_2fa)
        self.assertLess(time.time() - start, 8)

    def test_timeout_stops_process(self):
        script = self._script("""
            import time
            time.sleep(30)
        """)
        store = Store(exe=script, passphrase="")
        start = time.time()
        with self.assertRaises(StoreError) as ctx:
            store.run(["x"], timeout=1)
        self.assertIn("1 с", str(ctx.exception))
        self.assertLess(time.time() - start, 8)


class LoginAuthCodeTests(unittest.TestCase):
    def test_login_passes_auth_code_flag(self):
        store = Store(exe=Path("/tmp/missing-ipatool"), passphrase="")
        captured = {}

        def fake_run(args, *, timeout=60, stop_on_2fa=False):
            captured["args"] = list(args)
            captured["stop_on_2fa"] = stop_on_2fa
            captured["timeout"] = timeout
            return {"success": True, "email": "user@example.com"}

        store.run = fake_run  # type: ignore[method-assign]
        store.login("user@example.com", "secret", "654321")
        self.assertIn("--auth-code", captured["args"])
        self.assertEqual(captured["args"][captured["args"].index("--auth-code") + 1], "654321")
        self.assertFalse(captured["stop_on_2fa"])

    def test_login_without_code_stops_on_2fa(self):
        store = Store(exe=Path("/tmp/missing-ipatool"), passphrase="")
        captured = {}

        def fake_run(args, *, timeout=60, stop_on_2fa=False):
            captured["args"] = list(args)
            captured["stop_on_2fa"] = stop_on_2fa
            raise StoreError("need code", needs_2fa=True)

        store.run = fake_run  # type: ignore[method-assign]
        with self.assertRaises(StoreError) as ctx:
            store.login("user@example.com", "secret")
        self.assertTrue(ctx.exception.needs_2fa)
        self.assertTrue(captured["stop_on_2fa"])
        self.assertNotIn("--auth-code", captured["args"])


from restore_gui.service.prices import format_price  # noqa: E402
from restore_gui.service.store import _as_versions  # noqa: E402
from restore_gui.service import itunes, icons, paths  # noqa: E402
from restore_gui.backend import _looks_internal, _public_device_text, _public_error  # noqa: E402


class PriceFormatTests(unittest.TestCase):
    def test_free(self):
        for raw in (0, 0.0, "0", "0.00", "0,00", "$ 0,00", "$0.00", "0 руб.", "0 руб", "Free"):
            self.assertEqual(format_price(raw), "Бесплатно", raw)

    def test_paid_keeps_rubles_and_normalizes_dollar(self):
        self.assertIn("руб", format_price("199 руб."))
        self.assertEqual(format_price("$ 4.99"), "4,99 $")


class VersionParseTests(unittest.TestCase):
    def test_external_version_identifiers(self):
        rows = _as_versions({"bundleID": "com.a", "externalVersionIdentifiers": [846810460, "846810461"]})
        self.assertEqual([row["value"] for row in rows], ["846810460", "846810461"])
        self.assertTrue(rows[0]["title"].startswith("Сборка"))

    def test_full_metadata_rows(self):
        rows = _as_versions({"versions": [{"displayVersion": "1.2", "externalVersionId": "99", "releaseDate": "2020-01-01T12:00:00Z"}]})
        self.assertEqual(rows[0]["title"], "1.2")
        self.assertIn("2020-01-01", rows[0]["sub"])


class CatalogHelpersTests(unittest.TestCase):
    def test_category_tabs(self):
        names = itunes.category_names()
        self.assertEqual(names[0], "Все")
        self.assertIn("Образование", names)
        self.assertIn("Развлечения", names)

    def test_icon_cache_dir(self):
        folder = icons.cache_dir()
        self.assertEqual(folder, paths.logs_dir() / "cache" / "icons")

    def test_hides_python_exceptions(self):
        self.assertTrue(_looks_internal("'coroutine' object is not iterable"))
        self.assertFalse(_looks_internal("Подключите кабель"))
        text = _public_device_text("'coroutine' object is not iterable", "none")
        self.assertNotIn("coroutine", text)
        self.assertIn("устройств", text.lower())
        self.assertNotIn("coroutine", _public_error(TypeError("'coroutine' object is not iterable")))
