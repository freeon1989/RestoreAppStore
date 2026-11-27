"""Оформление Ink: светлая и тёмная палитры, цвет акцента и шрифт Manrope (restore_gui/fonts, лицензия OFL).
QML получает палитру словарём (palette(), в QML — P): цвета задаются только здесь."""
import sys
from PySide6.QtCore import Property, QObject, Signal

FONT = "Manrope"
MONO = "Menlo" if sys.platform == "darwin" else "Consolas"
AVATARS = ("#C4452D", "#3B4C8A", "#8A5A32", "#5A6B3A", "#6B4C6F", "#2F6F62", "#8A4A32", "#3A5A6B")

VERSIONS_PAGE = 15

LIGHT = {
    "bg": "#F3EEE6",
    "topbar": "#EBE4D8",
    "card": "#FFFBF6",
    "cardHover": "#F4EDE3",
    "field": "#FFFBF6",
    "second": "#EDE6DB",
    "secondHover": "#E3DACD",
    "rail": "#EBE4D8",
    "border": "#E0D6C8",
    "borderLight": "#C9BDAE",
    "shade": "#661C1814",
    "text": "#1C1814",
    "muted": "#6B6258",
    "disabled": "#A89F94",
    "logText": "#4A453E",
    "ok": "#2F7D4A", "okBg": "#E3F0E6", "okDim": "#B5D4BE",
    "warn": "#A86A16", "warnDim": "#F3E1C0",
    "danger": "#B42318", "dangerBg": "#F8E4E1",
}

DARK = {
    "bg": "#161311",
    "topbar": "#1C1916",
    "card": "#221E1A",
    "cardHover": "#2C2722",
    "field": "#221E1A",
    "second": "#2A2622",
    "secondHover": "#35302B",
    "rail": "#1C1916",
    "border": "#3A342E",
    "borderLight": "#524A43",
    "shade": "#CC000000",
    "text": "#F3EEE6",
    "muted": "#A89F94",
    "disabled": "#6B635A",
    "logText": "#D4CDBF",
    "ok": "#6FBF86", "okBg": "#1C3324", "okDim": "#2A4A34",
    "warn": "#E0A857", "warnDim": "#3F3018",
    "danger": "#E07068", "dangerBg": "#3A1E1C",
}

# Ключи emerald/ocean/rose/amber сохранены: они пишутся в settings.json.
ACCENTS = {
    "emerald": ("Терракота",
                {"accent": "#C4452D", "accentHover": "#A83824", "accentText": "#9A3420", "accentDim": "#E8C4BA",
                 "accentSoft": "#F8E6E1", "grad1": "#C4452D", "grad2": "#9A3420"},
                {"accent": "#E26A52", "accentHover": "#ED7F68", "accentText": "#F0A090", "accentDim": "#5A2E26",
                 "accentSoft": "#3A221C", "grad1": "#E26A52", "grad2": "#C4452D"}),
    "ocean": ("Чернила",
              {"accent": "#3B4C8A", "accentHover": "#2F3E74", "accentText": "#2A3868", "accentDim": "#C5CBE0",
               "accentSoft": "#E6E8F2", "grad1": "#3B4C8A", "grad2": "#2A3868"},
              {"accent": "#8FA0E0", "accentHover": "#A3B2EA", "accentText": "#B8C4F0", "accentDim": "#2A3358",
               "accentSoft": "#1C2238", "grad1": "#8FA0E0", "grad2": "#3B4C8A"}),
    "rose": ("Яшма",
             {"accent": "#9A4060", "accentHover": "#833550", "accentText": "#7A324B", "accentDim": "#E4C4CE",
              "accentSoft": "#F6E8EC", "grad1": "#9A4060", "grad2": "#7A324B"},
             {"accent": "#D4849A", "accentHover": "#E09AAD", "accentText": "#E8B4C2", "accentDim": "#4A2834",
              "accentSoft": "#321C24", "grad1": "#D4849A", "grad2": "#9A4060"}),
    "amber": ("Охра",
              {"accent": "#B56A1A", "accentHover": "#9A5914", "accentText": "#8A5012", "accentDim": "#EAD3B0",
               "accentSoft": "#F7ECDA", "grad1": "#B56A1A", "grad2": "#8A5012"},
              {"accent": "#E0A04A", "accentHover": "#EBB45F", "accentText": "#F0C47A", "accentDim": "#4A3514",
               "accentSoft": "#32240E", "grad1": "#E0A04A", "grad2": "#B56A1A"}),
}
DEFAULT_ACCENT = "emerald"


def palette(dark=False, accent=DEFAULT_ACCENT):
    """Палитра для QML: поверхности и текст по теме + цвета выбранного акцента."""
    name, light_acc, dark_acc = ACCENTS.get(accent, ACCENTS[DEFAULT_ACCENT])
    return {"font": FONT, "mono": MONO, "dark": dark, **(DARK if dark else LIGHT), **(dark_acc if dark else light_acc)}


QML = palette()


class Palette(QObject):
    """Живой объект палитры для QML: при смене темы свойства уведомляют делегаты."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._d = palette()

    def set(self, data):
        self._d = dict(data)
        self.changed.emit()

    @Property(str, notify=changed)
    def font(self):
        return str(self._d["font"])

    @Property(str, notify=changed)
    def mono(self):
        return str(self._d["mono"])

    @Property(str, notify=changed)
    def bg(self):
        return str(self._d["bg"])

    @Property(str, notify=changed)
    def topbar(self):
        return str(self._d["topbar"])

    @Property(str, notify=changed)
    def card(self):
        return str(self._d["card"])

    @Property(str, notify=changed)
    def cardHover(self):
        return str(self._d["cardHover"])

    @Property(str, notify=changed)
    def field(self):
        return str(self._d["field"])

    @Property(str, notify=changed)
    def second(self):
        return str(self._d["second"])

    @Property(str, notify=changed)
    def secondHover(self):
        return str(self._d["secondHover"])

    @Property(str, notify=changed)
    def rail(self):
        return str(self._d["rail"])

    @Property(str, notify=changed)
    def border(self):
        return str(self._d["border"])

    @Property(str, notify=changed)
    def borderLight(self):
        return str(self._d["borderLight"])

    @Property(str, notify=changed)
    def shade(self):
        return str(self._d["shade"])

    @Property(str, notify=changed)
    def text(self):
        return str(self._d["text"])

    @Property(str, notify=changed)
    def muted(self):
        return str(self._d["muted"])

    @Property(str, notify=changed)
    def disabled(self):
        return str(self._d["disabled"])

    @Property(str, notify=changed)
    def logText(self):
        return str(self._d["logText"])

    @Property(str, notify=changed)
    def ok(self):
        return str(self._d["ok"])

    @Property(str, notify=changed)
    def okBg(self):
        return str(self._d["okBg"])

    @Property(str, notify=changed)
    def okDim(self):
        return str(self._d["okDim"])

    @Property(str, notify=changed)
    def warn(self):
        return str(self._d["warn"])

    @Property(str, notify=changed)
    def warnDim(self):
        return str(self._d["warnDim"])

    @Property(str, notify=changed)
    def danger(self):
        return str(self._d["danger"])

    @Property(str, notify=changed)
    def dangerBg(self):
        return str(self._d["dangerBg"])

    @Property(str, notify=changed)
    def accent(self):
        return str(self._d["accent"])

    @Property(str, notify=changed)
    def accentHover(self):
        return str(self._d["accentHover"])

    @Property(str, notify=changed)
    def accentText(self):
        return str(self._d["accentText"])

    @Property(str, notify=changed)
    def accentDim(self):
        return str(self._d["accentDim"])

    @Property(str, notify=changed)
    def accentSoft(self):
        return str(self._d["accentSoft"])

    @Property(str, notify=changed)
    def grad1(self):
        return str(self._d["grad1"])

    @Property(str, notify=changed)
    def grad2(self):
        return str(self._d["grad2"])

    @Property(bool, notify=changed)
    def dark(self):
        return bool(self._d["dark"])
