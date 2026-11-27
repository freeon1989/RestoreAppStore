"""Единое отображение цены: бесплатно — «Бесплатно», иначе сумма в одном формате."""
from __future__ import annotations

import re


def format_price(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    lowered = text.lower().replace("\xa0", " ").replace("₽", "руб")
    if lowered in {"free", "gratis", "бесплатно", "get", "получить"}:
        return "Бесплатно"
    # 0, $ 0,00, 0.00, 0 руб., USD 0
    compact = re.sub(r"[^\d,.\-]", "", text).replace(",", ".")
    try:
        if compact not in {"", ".", "-", "-."} and float(compact) == 0:
            return "Бесплатно"
    except ValueError:
        pass
    if re.fullmatch(r"(usd|eur|\$|€)?\s*0([.,]0+)?\s*(руб\.?|rub|₽|usd|eur|\$|€)?", lowered):
        return "Бесплатно"
    # уже по-русски
    if re.search(r"руб", lowered):
        return re.sub(r"\s+", " ", text).replace("руб.", "руб.").strip()
    # $ 4.99 / USD 4,99
    money = re.search(r"(\d+[.,]\d+|\d+)", text)
    if "$" in text or "usd" in lowered:
        if money:
            amount = money.group(1).replace(".", ",")
            return f"{amount} $"
        return text
    if "€" in text or "eur" in lowered:
        if money:
            amount = money.group(1).replace(".", ",")
            return f"{amount} €"
        return text
    return text
