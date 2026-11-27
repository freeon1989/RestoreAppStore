"""Витрины App Store: названия стран, разбор storeFront и тексты для пользователя."""
from __future__ import annotations

# Код страны → имя по-русски. Порядок — как в селекторе каталога.
STOREFRONTS: list[tuple[str, str]] = [
    ("ru", "Россия"),
    ("us", "США"),
    ("kz", "Казахстан"),
    ("by", "Беларусь"),
    ("tr", "Турция"),
    ("de", "Германия"),
    ("gb", "Великобритания"),
    ("am", "Армения"),
    ("ge", "Грузия"),
    ("ua", "Украина"),
    ("az", "Азербайджан"),
    ("ae", "ОАЭ"),
    ("pl", "Польша"),
    ("cz", "Чехия"),
    ("nl", "Нидерланды"),
    ("fr", "Франция"),
    ("it", "Италия"),
    ("es", "Испания"),
    ("at", "Австрия"),
    ("ch", "Швейцария"),
    ("fi", "Финляндия"),
    ("se", "Швеция"),
    ("jp", "Япония"),
    ("kr", "Корея"),
    ("au", "Австралия"),
    ("ca", "Канада"),
    ("in", "Индия"),
]

# Для поиска иконок: сначала соседние и крупные витрины.
ICON_STOREFRONTS: list[str] = [
    "ru", "us", "kz", "by", "tr", "de", "gb", "am", "ge", "ua", "az", "ae",
    "pl", "cz", "nl", "fr", "it", "es", "at", "ch", "fi", "se", "no", "dk",
    "jp", "kr", "tw", "hk", "sg", "au", "ca", "mx", "br", "in",
]

# Числовой X-Apple-Store-Front → ISO-код.
STOREFRONT_IDS: dict[str, str] = {
    "143441": "us", "143442": "fr", "143443": "de", "143444": "gb",
    "143445": "at", "143446": "be", "143447": "fi", "143448": "gr",
    "143449": "ie", "143450": "it", "143451": "lu", "143452": "nl",
    "143453": "pt", "143454": "es", "143455": "ca", "143456": "se",
    "143457": "no", "143458": "dk", "143459": "ch", "143460": "au",
    "143461": "nz", "143462": "jp", "143463": "hk", "143464": "sg",
    "143465": "cn", "143466": "kr", "143467": "in", "143468": "mx",
    "143469": "ru", "143470": "tw", "143472": "za", "143473": "my",
    "143474": "ph", "143475": "th", "143476": "id", "143478": "pl",
    "143479": "sa", "143480": "tr", "143481": "ae", "143482": "hu",
    "143483": "cl", "143487": "ro", "143489": "cz", "143491": "il",
    "143492": "ua", "143494": "by", "143496": "sk", "143503": "br",
    "143508": "kz", "143509": "am", "143510": "az", "143557": "ge",
    "143563": "md", "143564": "lt", "143565": "lv", "143566": "ee",
    "143615": "ge",
}

_NAMES = dict(STOREFRONTS)
_NAMES.update({
    "no": "Норвегия", "dk": "Дания", "tw": "Тайвань", "hk": "Гонконг",
    "sg": "Сингапур", "mx": "Мексика", "br": "Бразилия", "be": "Бельгия",
    "ie": "Ирландия", "pt": "Португалия", "gr": "Греция", "nz": "Новая Зеландия",
    "cn": "Китай", "my": "Малайзия", "ph": "Филиппины", "th": "Таиланд",
    "id": "Индонезия", "sa": "Саудовская Аравия", "hu": "Венгрия",
    "cl": "Чили", "ro": "Румыния", "il": "Израиль", "sk": "Словакия",
    "za": "ЮАР", "lt": "Литва", "lv": "Латвия", "ee": "Эстония", "md": "Молдова",
})


def codes() -> list[str]:
    return [code for code, _name in STOREFRONTS]


def name(code: str) -> str:
    key = (code or "").strip().lower()
    return _NAMES.get(key, key.upper() if key else "")


def rows() -> list[dict]:
    return [{"value": code, "title": title} for code, title in STOREFRONTS]


def index_of(code: str) -> int:
    key = (code or "ru").strip().lower()
    for i, (item, _name) in enumerate(STOREFRONTS):
        if item == key:
            return i
    return 0


def parse_storefront(value) -> str:
    """Код страны из ответа auth info: 'us', '143441-1,29' или число."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) == 2 and text.isalpha():
        return text.lower()
    # "143441-1,29" или "143441"
    numeric = text.split("-", 1)[0].split(",", 1)[0].strip()
    if numeric in STOREFRONT_IDS:
        return STOREFRONT_IDS[numeric]
    lower = text.lower()
    if lower in _NAMES:
        return lower
    return ""


def is_region_error(text: str) -> bool:
    blob = (text or "").lower()
    return any(token in blob for token in (
        "not available for download in your region",
        "not available in your region",
        "your region/storefront",
        "in your storefront",
        "storefront change",
    ))


def unavailable_message(countries: list[str] | None = None) -> str:
    names = [name(code) for code in (countries or []) if name(code)]
    if len(names) == 1:
        where = names[0]
        return f"Приложение доступно только в App Store {where} — войдите в Apple ID этой страны"
    if names:
        where = ", ".join(names)
        return f"Приложение доступно только в App Store ({where}) — войдите в Apple ID этой страны"
    return "Приложение недоступно в витрине текущего Apple ID — войдите в Apple ID страны, где оно продаётся"


def switch_hint(email: str, country: str) -> str:
    label = name(country) or country
    who = (email or "").strip() or "другой аккаунт"
    if label:
        return f"Это приложение есть в витрине аккаунта {who} ({label}). Переключитесь, чтобы скачать."
    return f"Это приложение можно скачать из аккаунта {who}. Переключитесь, чтобы скачать."


def availability_text(present: list[str], missing: list[str]) -> str:
    have = [name(code) for code in present if name(code)]
    gone = [name(code) for code in missing if name(code)]
    parts = []
    if have:
        parts.append("Есть в App Store: " + ", ".join(have))
    if gone:
        parts.append("Нет в: " + ", ".join(gone))
    return ". ".join(parts)
