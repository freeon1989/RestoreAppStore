#!/bin/bash
# Сборка портативного RestoreAppStore-win-x64.exe (Wine + Python 3.12 + PyInstaller).
# Запускать из Linux. Нужны: wine, xvfb-run, python-3.12 windows в префиксе.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
for d in "$HOME/wine/wine-10.17-amd64-wow64/bin" "$HOME/wine/wine-10.17-amd64/bin"; do
  if [ -x "$d/wine" ]; then export PATH="$d:$PATH"; break; fi
done
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-owntube}" WINEARCH=win64 WINEDEBUG="${WINEDEBUG:--all}"
PY_WIN="${PY_WIN:-C:\\Python312\\python.exe}"
VENV="${VENV:-C:\\restore-venv}"
if [ ! -f "$WINEPREFIX/drive_c/restore-venv/Scripts/python.exe" ]; then
  xvfb-run -a wine "$PY_WIN" -m venv C:\\restore-venv
fi
xvfb-run -a wine "$VENV\\Scripts\\python.exe" -m pip install --disable-pip-version-check -r requirements-build.txt
bash scripts/bundle_icu.sh
mkdir -p build/res
cp licenses/IPATOOL_CPP_LICENSE.txt licenses/IPA_DOWNLOADER_LICENSE.txt build/res/
# ipatool-cpp 1.3.4: положите exe в build/res/ipatool-cpp.exe (суммы в BUILD-CPP-ONLY.md)
if [ ! -f build/res/ipatool-cpp.exe ]; then
  echo "нет build/res/ipatool-cpp.exe" >&2
  exit 1
fi
python3 tools/write_version_info.py build/version_info.txt
xvfb-run -a wine "$VENV\\Scripts\\python.exe" -m PyInstaller --noconfirm --clean --workpath build/pyi --distpath dist RestoreAppStore.spec
cp -f dist/RestoreAppStore.exe RestoreAppStore-win-x64.exe
sha256sum RestoreAppStore-win-x64.exe | tee RestoreAppStore-win-x64.exe.sha256
echo "готово: $ROOT/RestoreAppStore-win-x64.exe"
