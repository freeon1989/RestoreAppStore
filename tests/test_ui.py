
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT))
import sandbox  # noqa: E402

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if not os.environ.get("DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication  # noqa: E402
from restore_gui import app as gui  # noqa: E402
from restore_gui import theme  # noqa: E402


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_and_demo(self):
        engine, backend = gui.create(self.app, background=False, visible=False)
        self.assertTrue(engine.rootObjects())
        backend.seed_demo()
        self.assertTrue(backend.loggedIn)
        self.assertEqual(backend.account, "demo@example.com")
        self.assertGreaterEqual(len(backend.popular._rows), 1)
        backend.heroineName = "mira"
        backend.themeMode = "dark"
        self.assertIn("mira-dark.jpg", backend.heroineUrl)
        backend.themeMode = "light"
        self.assertIn("mira-light.jpg", backend.heroineUrl)
        backend.heroineName = "off"
        self.assertEqual(backend.heroineUrl, "")
        self.assertTrue(any(h["key"] == "kira" for h in backend.heroines))
        self.assertIn("Все", backend.categories)
        report = Path(tempfile.mkstemp(suffix=".txt")[1])
        self.assertEqual(gui.check_ui(str(report)), 0)
        self.assertTrue(report.read_text(encoding="utf-8").startswith("OK"))

    def test_heroine_assets(self):
        for key in ("mira", "nora", "liora", "vera", "kira"):
            for dark in (False, True):
                url = theme.heroine_url(key, dark)
                self.assertTrue(url, msg=f"missing {key} dark={dark}")


if __name__ == "__main__":
    unittest.main()
