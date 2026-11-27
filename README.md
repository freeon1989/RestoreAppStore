<p align="center">
  <img src="assets/icon.png" width="96" alt="RestoreAppStore">
</p>

<h1 align="center">RestoreAppStore для Windows</h1>

<p align="center">
  Скачивание приложений из истории покупок вашего Apple ID<br>
  и установка IPA на iPhone — если Apple по-прежнему отдаёт файл.
</p>

<p align="center">
  <a href="https://github.com/freeon1989/RestoreAppStore/releases/latest/download/RestoreAppStore-win-x64.exe"><img src="https://img.shields.io/badge/Скачать-Windows%2010%2F11%20x64-C4452D?style=for-the-badge&logo=windows&logoColor=white" alt="Скачать для Windows"></a>
</p>

<p align="center">
  <a href="https://github.com/freeon1989/RestoreAppStore/releases/latest"><img src="https://img.shields.io/github/v/release/freeon1989/RestoreAppStore?label=%D1%80%D0%B5%D0%BB%D0%B8%D0%B7" alt="Последний релиз"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/исходники-MIT-green.svg" alt="Исходники MIT"></a> <a href="licenses/GPL-3.0.txt"><img src="https://img.shields.io/badge/сборка-GPL--3.0-blue.svg" alt="Сборка GPL-3.0"></a>
  <a href="https://github.com/freeon1989/RestoreAppStore/releases/latest"><img src="https://img.shields.io/badge/платформа-Windows%2010%2F11%20x64-0078D6?logo=windows&logoColor=white" alt="Windows 10/11 x64"></a>
</p>

RestoreAppStore — самостоятельная программа для 64-битной Windows 10 или 11. Установка не требуется: достаточно скачать exe и запустить.

*A Windows 10/11 x64 app to re-download titles from your own App Store purchase history and, if you want, install the IPA on an iPhone.*

> [!IMPORTANT]
> Программа скачивает приложения с серверов Apple **под вашим Apple ID** и только те, что **уже есть в истории покупок этого аккаунта**. Чужое или никогда не скачанное приложение Apple не отдаст, и программа не пытается это обойти.

## Скачать

**[Скачать RestoreAppStore для Windows (x64)](https://github.com/freeon1989/RestoreAppStore/releases/latest/download/RestoreAppStore-win-x64.exe)**

[exe, без установки](https://github.com/freeon1989/RestoreAppStore/releases/latest/download/RestoreAppStore-win-x64.exe)
· [страница последнего релиза](https://github.com/freeon1989/RestoreAppStore/releases/latest)
· [папка без распаковки в память: zip](https://github.com/freeon1989/RestoreAppStore/releases/latest/download/RestoreAppStore-win-x64.zip)
· [SHA-256 exe](https://github.com/freeon1989/RestoreAppStore/releases/latest/download/RestoreAppStore-win-x64.exe.sha256)
· [SHA-256 zip](https://github.com/freeon1989/RestoreAppStore/releases/latest/download/RestoreAppStore-win-x64.zip.sha256)

Актуальная версия: **2.0.6**. Нужна **64-битная Windows 10 или 11**.

Запустите скачанный `RestoreAppStore-win-x64.exe` либо распакуйте `RestoreAppStore-win-x64.zip` и откройте `RestoreAppStore\RestoreAppStore.exe`. Сборка не подписана цифровым сертификатом, поэтому Windows SmartScreen может показать предупреждение «Windows защитила ваш компьютер». Нажмите «Подробнее» → «Выполнить в любом случае».

Если окно не откроется или вход не удался, откройте `%LOCALAPPDATA%\RestoreAppStore` и пришлите `app.log` и `startup.log` (паролей и кодов в них нет). Папку журналов можно открыть из «Настройки → О программе».

Если уже стоит предыдущая версия, в программе откройте «Настройки → О программе → Проверить обновления».

SHA-256 файла `RestoreAppStore-win-x64.exe` (версия 2.0.6):

```
56321b4a76713bdc4cf562ded75fd86a601ae807d0e8e02d0b696ca1838ed59a
```

В PowerShell проверка такая:

```powershell
Get-FileHash .\RestoreAppStore-win-x64.exe -Algorithm SHA256
```

SHA-256 архива `RestoreAppStore-win-x64.zip` (версия 2.0.6):

```
7004290c463710312d7f0219849ace1be0b9a9e76a33d4def9d2fbd17cbae089
```


## Скриншоты

Снимки сняты в демонстрационном режиме (учётная запись `demo@example.com`, устройство «iPhone (демо)», на фоне героиня Мира в аниме-стиле). Это не настоящий Apple ID и не подключённый телефон. В светлой теме фон — светлая сказка, в тёмной — dark fantasy.

Главный экран (светлая тема):

![Главный экран RestoreAppStore](docs/screenshots/home.png)

<table>
  <tr>
    <td width="58%"><img src="docs/screenshots/apps.png" alt="Каталог приложений"></td>
    <td width="42%"><img src="docs/screenshots/detail.png" alt="Панель приложения"></td>
  </tr>
  <tr>
    <td align="center">Каталог с выбором витрины App Store</td>
    <td align="center">Панель приложения: версии и копии (демо-данные)</td>
  </tr>
  <tr>
    <td width="58%"><img src="docs/screenshots/progress.png" alt="Полосы скачивания и установки"></td>
    <td width="42%"><img src="docs/screenshots/storefront.png" alt="Настройки витрины и аккаунтов"></td>
  </tr>
  <tr>
    <td align="center">Две полосы прогресса: скачивание и установка</td>
    <td align="center">Витрина каталога и несколько Apple ID</td>
  </tr>
  <tr>
    <td width="58%"><img src="docs/screenshots/dark.png" alt="Тёмная тема"></td>
    <td width="42%"><img src="docs/screenshots/settings.png" alt="Настройки оформления"></td>
  </tr>
  <tr>
    <td align="center">Тёмная тема</td>
    <td align="center">Настройки: тема и цвет акцента</td>
  </tr>
  <tr>
    <td width="58%"><img src="docs/screenshots/login.png" alt="Окно входа в Apple ID"></td>
    <td width="42%"><img src="docs/screenshots/device-hint.png" alt="Подсказка про Устройства Apple"></td>
  </tr>
  <tr>
    <td align="center">Вход в Apple ID (демо, пароль вводить не нужно)</td>
    <td align="center">Если iPhone не виден: ссылка на «Устройства Apple»</td>
  </tr>
</table>

Оформление описано в [docs/design.md](docs/design.md).

## Возможности

- Боковая панель: «Главная», «Каталог», «Мои удалённые» (что нашлось в истории вашего Apple ID) и «Файлы .ipa».
- На главной — короткие шаги (вход, телефон, поиск в истории) и популярные приложения.
- Поиск по названию, App ID или ссылке App Store и категории из ответа каталога.
- История покупок вашего Apple ID и сверка с текущим каталогом: какие приложения из истории уже пропали из App Store.
- Выбор версии, которую отдаёт ipatool-cpp. Если сборка подписана старым форматом и современная iOS её не примет, программа предупредит до установки и предложит более новую версию.
- «Только скачать IPA» или «Скачать и установить» по кабелю, в том числе несколько приложений по очереди. Во время работы видны две полосы: скачивание (процент, объём, скорость, оставшееся время) и установка (процент и стадия). Готовый `.ipa` можно поставить и без повторного входа в Apple ID.
- Каталог можно смотреть в витрине другой страны (Россия, США, Казахстан и другие). Apple отдаёт файл только в витрине Apple ID: можно сохранить несколько аккаунтов и переключаться между ними. Пароли на диск не записываются.
- Иконки и названия разработчиков подтягиваются и из других витрин, если приложения уже нет в российском App Store.
- Скачанный IPA проверяется (архив и Info.plist) до установки: повреждённый файл программа скачает заново, а не отправит на устройство. Одну и ту же версию нельзя поставить в очередь дважды.
- При запуске программа убирает мелкие недокачанные файлы и предлагает удалить крупные незавершённые загрузки (например, обрывки Xcode).
- Приложения только для Mac (в том числе Xcode) помечаются и не ставятся на iPhone и iPad.
- Светлая и тёмная тема (или как в системе) и четыре цвета акцента: терракота, чернила, яшма, охра.
- Героиня на фоне в полный рост, в аниме-стиле, с живой позой и магией (Мира, Нора, Лиора, Вера, Кира): в светлой теме — светлая сказка и тёмный латекс, в тёмной — dark fantasy и светлый латекс. В настройках можно сменить или выключить.
- Обновление из GitHub Releases с проверкой SHA-256 и откатом на предыдущую копию: «Настройки → О программе».
- Понятные сообщения об ошибках по-русски и журнал внизу окна.

## Что нужно

- 64-битная **Windows 10 или 11**.
- Apple ID, под которым нужное приложение когда-то скачивалось.
- Чтобы **поставить** приложение на телефон: разблокированный iPhone, кабель USB и приложение «Устройства Apple». Подробности — в разделе «Перед началом».
- Чтобы **только скачать IPA**, телефон не обязателен.

## Перед началом

Чтобы Windows увидела iPhone по кабелю, нужно официальное приложение Apple «Устройства Apple» (Apple Devices) из Microsoft Store.

1. Установите [«Устройства Apple» из Microsoft Store](https://apps.microsoft.com/detail/9NP83LWLPZ9K) (издатель — Apple Inc., код продукта `9NP83LWLPZ9K`).
2. Подключите разблокированный iPhone кабелем USB.
3. На телефоне нажмите «Доверять этому компьютеру?».

Если программа не видит iPhone, на главном экране появится та же подсказка и кнопка, которая открывает Microsoft Store. Ссылку можно открыть и в «Настройки → О программе» или в справке.

Чтобы только скачать IPA, телефон не обязателен.

## Как пользоваться

1. Скачайте `RestoreAppStore-win-x64.exe` и сверьте SHA-256 с суммой выше или с файлом `.sha256` из того же релиза.
2. Запустите exe. Нажмите «Войти в Apple ID» и войдите в аккаунт, с которого раньше скачивали нужное приложение. Если Apple пришлёт код подтверждения, введите его в том же окне входа. Уведомление на устройство часто не приходит: откройте на iPhone или iPad «Настройки → ваше имя → Вход и безопасность → Получить код проверки». Программа ставит приложения и на iPad. Если устройство не видно или вход не удался, откройте «Настройки → О программе → Открыть папку журналов» и пришлите `app.log` и `startup.log`. Диагностика кабеля без окна: `RestoreAppStore.exe --diag-device` (результат в `app.log`).
3. Найдите приложение в «Популярном» на главной, в «Каталоге» (можно сменить страну витрины) или через «Найти мои приложения» — найденное появится в разделе «Мои удалённые». Если приложения нет в витрине текущего Apple ID, программа подскажет, каким из сохранённых аккаунтов его скачать, или попросит войти в Apple ID этой страны.
4. Откройте карточку приложения и выберите «Скачать и установить» или «Только скачать IPA». Внизу окна будут две полосы прогресса. Если выбранная версия слишком старая для вашей iOS, появится объяснение и кнопка «Выбрать более новую версию».

## Сборка из исходников

Нужны Python 3.12, зависимости из `requirements-build.txt` и `ipatool-cpp` 1.3.4 в `build/res/ipatool-cpp.exe` (см. контрольные суммы в [BUILD-CPP-ONLY.md](BUILD-CPP-ONLY.md)). Лицензии движка — в `licenses/`, перед сборкой их нужно скопировать в `build/res/`. Затем:

```text
python tools\write_version_info.py build\version_info.txt
python -m PyInstaller --noconfirm --clean RestoreAppStore.spec
```

Готовый файл: `dist\RestoreAppStore.exe`. Портативный однофайловый exe можно переименовать в `RestoreAppStore-win-x64.exe`.

Запуск без упаковки (нужен Python 3.12 и ipatool-cpp в `PATH` или рядом со скриптами):

```text
py -V:3.12 -m pip install PySide6 pymobiledevice3 segno
py -V:3.12 restore_apps_gui.py
```

Тесты логики, без сети, Apple ID и iPhone:

```text
py -V:3.12 -m unittest discover tests
```

## Лицензия

Исходный код RestoreAppStore — [MIT](LICENSE), © 2026 freeon1989. Готовая сборка для Windows из‑за сторонних компонентов (Unicorn внутри ipatool-cpp, pymobiledevice3) распространяется под [GPL-3.0](licenses/GPL-3.0.txt). Подробности — в [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Проект не связан с Apple. App Store, iPhone и iOS — товарные знаки Apple Inc. Используйте программу только для приложений из истории покупок своего Apple ID.
