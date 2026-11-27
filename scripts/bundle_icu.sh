#!/bin/bash
# Скачивает ICU 72.1 (неверсионные символы, Unicode License) в build/res/icu
# для Windows-сборки PySide6 6.10+. Запускать из корня репозитория.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/build/res/icu"
TAG="72.1-custom+4"
SHA="2813ea1205fcf9d9a7930339dae181dc3e299b2391f2f4879c5e542be43f3a7f"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
curl -fsSL -L -o icu-win.tar.gz \
  "https://github.com/FaithLife-Community/icu/releases/download/${TAG}/icu-win.tar.gz"
got="$(sha256sum icu-win.tar.gz | awk '{print $1}')"
if [ "$got" != "$SHA" ]; then
  echo "SHA-256 не совпала: $got" >&2
  exit 1
fi
tar xzf icu-win.tar.gz
mkdir -p "$DEST"
cp windows/system32/icu.dll windows/system32/icuuc.dll windows/system32/icuin.dll "$DEST/"
echo "ICU в $DEST"
