<p align="center">
  <img src="static/img/logo.svg" width="140" alt="Transcribbler logo">
</p>

# Transcribbler

A local desktop app for qualitative transcript coding. Import transcripts (text, audio, or image), build a hierarchical codebook, and code text passages — entirely offline, no cloud services required.

> [!NOTE]
> **Beta.** Installation and launch verified on macOS (arm64 + Intel), Windows 10/11, and Linux (AppImage). Functional testing beyond startup is still light — please file issues for anything that breaks.

![Transcribbler screenshot](docs/screenshot.png)

## Features

- **Transcription** — automatic speech-to-text via Whisper (KB-Whisper for Swedish, Whisper Medium for English)
- **Diarization** — speaker separation via pyannote.audio + ECAPA-TDNN
- **Coding** — highlight text passages and link them to hierarchical codes; undo/redo support
- **Multiple coders** — inter-rater reliability support (Cohen's Kappa)
- **OCR** — import images and extract text (Apple Vision on macOS, EasyOCR on Windows/Linux)
- **Export** — CSV, Markdown, DOCX, ODT, QDPX (ATLAS.ti/NVivo-compatible)
- **Import** — .txt, .docx, .odt, .md (incl. YAML frontmatter from Notescribbler), .nsenc, .scribbler
- **Offline-first** — no API keys required, all data stays local

## Requirements

- Python 3.9–3.11
- [ffmpeg](https://ffmpeg.org/) (required for Whisper): `brew install ffmpeg`
- HF token for diarization (optional): [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### Recommended system specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 4 GB | 8 GB+ |
| **Disk** | 3 GB free (models + app) | 5 GB+ free |
| **GPU** | Not required | Apple Silicon (MPS) or NVIDIA (CUDA) for fast diarization |
| **OS** | macOS 12+, Windows 10+, Ubuntu 20.04+ | Latest stable |

Without a GPU, speaker diarization runs on CPU and is significantly slower (20-30x). Transcription (Whisper) runs well on CPU.

## Installation

```bash
git clone https://github.com/jonasbaath/transcribbler.git
cd transcribbler
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # core installation (Flask + crypto)
pip install -r requirements-ml.txt  # ML dependencies (Whisper, pyannote, OCR)
```

## Running

```bash
source venv/bin/activate
python3 main.py
```

Opens `http://127.0.0.1:5050` automatically in the browser.

### Electron app (desktop)

```bash
cd electron
npm install
npm start
```

Requires [Node.js](https://nodejs.org/) ≥ 20.

### Building installers (DMG / NSIS / AppImage)

The bundled Python runtime lives in `electron/python-runtime/` and is copied as-is into the installer. Before building, ML-deps (Whisper, pyannote, torch, EasyOCR/Vision) must be installed into that runtime so end users don't need to `pip install` anything:

```bash
cd electron
npm install
npm run prepare:runtime     # installs requirements-ml.txt into python-runtime/ (~1 GB)
npm run build:mac           # or build:win / build:linux
```

`prepare:runtime` runs automatically as a `prebuild:*` hook, so `npm run build:mac` alone also works. Re-run with `FORCE=1 npm run prepare:runtime` to reinstall.

The `electron/python-runtime/` directory itself is **not checked into git** — each platform needs a matching [python-build-standalone](https://github.com/astral-sh/python-build-standalone) unpacked there before building.

## GPU acceleration on Linux (optional)

The Linux AppImage ships with **CPU-only PyTorch** to keep the download to ~600 MB. For most users (interview audio in the 10-minute range) CPU transcription is fast enough — KB-Whisper-medium runs at ~2× realtime on a modern laptop.

If you have an **NVIDIA GPU** with a working CUDA-capable driver installed on your host system, you can swap in the CUDA build of PyTorch to accelerate Whisper transcription by 5–10×:

```bash
# From inside the AppImage's bundled python (one-time):
./Transcribbler-0.1.0.AppImage --appimage-extract
cd squashfs-root/resources/python-runtime
./bin/python -m pip install --upgrade \
    torch torchaudio \
    --index-url https://download.pytorch.org/whl/cu121
# Re-pack or just run from squashfs-root/AppRun
```

Or, if running from a dev clone instead of the AppImage:

```bash
source venv/bin/activate
pip install --upgrade torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

CUDA 12.1 is recommended; adjust the index URL (`cu118`, `cu124`, etc.) to match your driver. Verify with `python -c "import torch; print(torch.cuda.is_available())"` — should print `True`.

**Note:** the bundled CPU build will not use AMD ROCm or Intel GPUs. macOS uses Apple's MPS backend automatically when available; Windows currently bundles the standard PyPI wheel (CPU + CUDA when present on system).

## Project structure

```
main.py              Flask app — all routes
core/
  project.py         Project management (create, open, import)
  annotation.py      Annotations per coder (char-offset)
  codebook.py        CRUD for codes (hierarchical tree)
  transcribe.py      Whisper + pyannote (transcription + diarization)
  export.py          CSV, Markdown, DOCX, ODT, QDPX
  irr.py             Cohen's Kappa (inter-rater reliability)
  nsenc.py           Encryption (.nsenc — Notescribbler format)
  scribbler.py       Encryption (.scribbler — Notescribbler format)
static/js/app.js     All frontend logic (~2400 lines)
electron/            Electron shell (main.js, preload.js)
tests/               Pytest test suite
```

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## License

© Jonas Bååth — [GNU Affero General Public License v3.0](LICENSE)

The source code is free to use, modify, and distribute under the terms of AGPL-3.0. Modified versions provided as a network service must distribute their source code.
