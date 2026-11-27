# Сторонние компоненты

Исходный код RestoreAppStore написан заново и доступен на условиях MIT, © 2026 freeon1989 (см. [LICENSE](LICENSE)).

Готовая программа (`RestoreAppStore-win-x64.exe` и zip) включает также перечисленные ниже компоненты. Из‑за Unicorn Engine (GPL-2.0, внутри ipatool-cpp) и pymobiledevice3 (GPL-3.0) **собранный пакет распространяется под GNU GPL версии 3** ([licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)).

| Компонент | Лицензия | Для чего | Источник |
|---|---|---|---|
| ipatool-cpp | MIT | вход в Apple ID, история покупок, версии, скачивание IPA | https://github.com/Sorvigolova/ipatool |
| Unicorn Engine (внутри ipatool-cpp) | GPL-2.0 | подпись запросов App Store | https://github.com/unicorn-engine/unicorn |
| pymobiledevice3 | GPL-3.0-or-later | установка IPA на iPhone по USB | https://github.com/doronz88/pymobiledevice3 |
| pytun-pmd3 | GPL-3.0-or-later | зависимость pymobiledevice3 | https://github.com/doronz88/pytun-pmd3 |
| Qt for Python (PySide6) и Qt 6 | LGPL-3.0 | интерфейс | https://code.qt.io |
| Шрифт Manrope | SIL OFL 1.1 (`restore_gui/fonts/OFL.txt`) | шрифт интерфейса | https://github.com/googlefonts/manrope |
| segno | BSD-3-Clause | QR-код «Поддержать разработчика» | https://github.com/heuer/segno |
| Python | PSF License | среда выполнения | https://www.python.org |
| PyInstaller (загрузчик) | GPL-2.0-or-later с исключением для сборок | упаковка в exe | https://github.com/pyinstaller/pyinstaller |
| ICU 72.1 | ICU License (`licenses/LICENSE-ICU.txt`) | нужен Qt 6 на Windows | https://github.com/unicode-org/icu |

Полные тексты: `licenses/`. Движок ipatool-cpp — `licenses/IPATOOL_CPP_LICENSE.txt`.
