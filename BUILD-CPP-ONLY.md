# Сборка портативной версии

Код приложения соответствует варианту 1.2.0-local.4 (C++ only), на основе RestoreIPA v1.2.0.
Этот релиз использует Windows x64 ipatool-cpp 1.3.4 от Sorvigolova.

1. Скачайте портативный RestoreAppStore.exe из https://github.com/ToXiTy13/RestoreIPA/releases/tag/v1.2.0.
2. Скачайте архив Windows x64 из https://github.com/Sorvigolova/ipatool/releases/tag/1.3.4.
   SHA-256 ZIP: f825512372346f2a29bd3be6ee9a2234a4de9781cdfbb597299d6a06ff36eb43.
3. Извлеките ipatool-cpp-1.3.4-windows-amd64.exe под именем build/res/ipatool-cpp.exe.
   SHA-256 EXE: 3ab8167cbe3a36f3e12bf20ba4e7b9bd06a7b3165566973de3758786894edb0f.
4. Из корня репозитория (или распакованного архива исходников) запустите Python 3.12:
   python rebuild_portable.py PATH_TO_ORIGINAL_EXE . RestoreAppStore-cpp-only-1.3.4.exe

Результат этой команды собирает тот же код приложения и движок. Контрольная сумма
может отличаться от опубликованного EXE из-за параметров упаковки PyInstaller.
Исходный код движка: https://github.com/Sorvigolova/ipatool/tree/1.3.4.

Примечания LOCAL_CHANGES.txt описывают предыдущую сборку с двумя движками.

Лицензии сторонних компонентов, которые в архиве исходников лежали в `build/res/`, в репозитории находятся в каталоге `licenses/`.
