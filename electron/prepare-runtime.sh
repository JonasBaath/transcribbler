#!/usr/bin/env bash
# Installerar ML-deps (Whisper, pyannote, torch, docTR/Vision) i
# electron/python-runtime/ så electron-builder kan baka in allt i DMG/NSIS/AppImage.
# Körs automatiskt via `npm run build:*` (prebuild-hook i package.json).
#
# Idempotent: hoppar över om pyannote redan finns i runtime och FORCE inte satts.
set -euo pipefail

cd "$(dirname "$0")"
RUNTIME_DIR="python-runtime"

if [[ ! -x "$RUNTIME_DIR/bin/python" && ! -x "$RUNTIME_DIR/python.exe" ]]; then
  echo "FEL: $RUNTIME_DIR saknas eller är trasig."
  echo "Ladda ned python-build-standalone för plattformen och packa upp till $RUNTIME_DIR/ först."
  exit 1
fi

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  PY="$RUNTIME_DIR/python.exe"
else
  PY="$RUNTIME_DIR/bin/python"
fi

if [[ -z "${FORCE:-}" ]] && "$PY" -c "import pyannote.audio" 2>/dev/null; then
  echo "ML-deps redan installerade i $RUNTIME_DIR (sätt FORCE=1 för omsintallation)."
  exit 0
fi

echo "Installerar ML-deps i $RUNTIME_DIR ..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r ../requirements-ml.txt
echo "Klar. Storlek:"
du -sh "$RUNTIME_DIR"
