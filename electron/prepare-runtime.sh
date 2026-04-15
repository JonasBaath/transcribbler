#!/usr/bin/env bash
# Installerar ML-deps (Whisper, pyannote, torch, docTR/Vision) i
# electron/python-runtime/ så electron-builder kan baka in allt i DMG/NSIS/AppImage.
# Körs automatiskt via `npm run build:*` (prebuild-hook i package.json).
#
# Idempotent: hoppar över om pyannote redan finns i runtime och FORCE inte satts.
set -euo pipefail

cd "$(dirname "$0")"
RUNTIME_DIR="python-runtime"

PBS_RELEASE="20250317"
PBS_PY_VERSION="3.11.11"

detect_pbs_triple() {
  local arch
  arch="$(uname -m)"
  case "$OSTYPE" in
    darwin*)
      case "$arch" in
        arm64|aarch64) echo "aarch64-apple-darwin" ;;
        x86_64)        echo "x86_64-apple-darwin" ;;
        *) echo "unsupported-darwin-arch:$arch" >&2; return 1 ;;
      esac
      ;;
    linux*)
      case "$arch" in
        x86_64)        echo "x86_64-unknown-linux-gnu" ;;
        aarch64|arm64) echo "aarch64-unknown-linux-gnu" ;;
        *) echo "unsupported-linux-arch:$arch" >&2; return 1 ;;
      esac
      ;;
    msys*|cygwin*|win32*)
      echo "x86_64-pc-windows-msvc"
      ;;
    *)
      echo "unsupported-ostype:$OSTYPE" >&2
      return 1
      ;;
  esac
}

download_runtime() {
  local triple url tarball
  triple="$(detect_pbs_triple)"
  url="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/cpython-${PBS_PY_VERSION}+${PBS_RELEASE}-${triple}-install_only.tar.gz"
  tarball="python-runtime.tar.gz"

  echo "Laddar ner python-build-standalone ${PBS_PY_VERSION} (${triple})..."
  echo "  $url"
  curl -fL --retry 3 -o "$tarball" "$url"

  echo "Packar upp till $RUNTIME_DIR/ ..."
  rm -rf "$RUNTIME_DIR"
  tar -xzf "$tarball"
  # python-build-standalone install_only-tarballs packar upp till ./python/
  mv python "$RUNTIME_DIR"
  rm -f "$tarball"
}

if [[ ! -x "$RUNTIME_DIR/bin/python" && ! -x "$RUNTIME_DIR/python.exe" ]]; then
  echo "$RUNTIME_DIR saknas — laddar ner python-build-standalone."
  download_runtime
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
