
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
