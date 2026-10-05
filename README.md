<p align="center">
  <img src="static/img/logo.svg" width="140" alt="Transcribbler logo">
</p>

# Transcribbler

A local desktop app for qualitative transcript coding. Import transcripts (text or image), build a hierarchical codebook, code text passages and analyse them across transcripts — locally, with no cloud services required. Audio transcription is available as an opt-in feature.

> [!NOTE]
> **Beta.** Installation and launch verified on macOS (arm64 + Intel), Windows 10/11, and Linux (AppImage). Functional testing beyond startup is still light — please file issues for anything that breaks.

## Features

- **Transcription** (off by default, see below) — automatic speech-to-text via Whisper (KB-Whisper large for Swedish, Whisper for English)
- **Diarisation** (off by default) — speaker separation via pyannote.audio + ECAPA-TDNN
- **Coding** — highlight text passages and link them to hierarchical codes; memos, key passages, optional weights; undo/redo
- **Analysis view** — excerpts per code across transcripts, filtered by transcript tags; jump from an excerpt back to its context
- **Statistics** — code counts, code matrix and code overlap (co-occurrence)
- **Multiple coders** — separate annotations per coder; export/import of codings between copies of a project (matched by transcript text and code name). Cohen's kappa is implemented in the backend but not yet exposed in the UI
- **Encryption** — optional password-protected projects
- **Bilingual UI** — Swedish and English (follows the system language; switchable)
- **OCR** — import images and extract text (Apple Vision on macOS, EasyOCR on Windows/Linux)
- **Export** — CSV, Markdown, DOCX, ODT, PDF, PNG and QDPX (REFI-QDA; compatibility with ATLAS.ti/NVivo not verified)
- **Import** — .txt, .docx (incl. tables), .odt, .md (YAML frontmatter: title, category, tags), images, Notescribbler .nsenc/.scribbler/.zip
- **Local-first** — no API keys required and project data stays local. Exceptions: PNG export loads html2canvas from a CDN, and the first transcription/diarisation run downloads models

### Audio transcription is off by default

Transcribbler is used in teaching, where students code ready-made transcripts rather than transcribe. Audio upload is therefore hidden and refused unless you opt in — set `"enable_whisper": true` in `~/.transcribbler_config.json`, or run with `TRANSCRIBBLER_ENABLE_WHISPER=1`. Existing audio-sourced transcripts (playback, segments, waveform) work regardless of the flag.

## Download

Ready-made installers for macOS, Windows and Linux are on the [Releases](https://github.com/JonasBaath/transcribbler/releases) page — no Python required. Step-by-step instructions, including how to open the unsigned app the first time, are in the user manual: [English](docs/manual_en.md#installation) · [Svenska](docs/manual_sv.md#installation).

The sections below are for running from source.

## Requirements

- Python 3.9–3.11
- [ffmpeg](https://ffmpeg.org/) (required for Whisper): `brew install ffmpeg`
- HF token for diarisation (optional): [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### Recommended system specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 4 GB | 8 GB+ |
| **Disk** | 2.5 GB free on Windows, 1.7 GB on macOS (app) | 6 GB+ free if transcription is enabled (speech model ~3 GB) |
| **GPU** | Not required | Apple Silicon (MPS) or NVIDIA (CUDA) for fast diarisation |
| **OS** | macOS 12+, Windows 10+, Ubuntu 20.04+ | Latest stable |

Without a GPU, speaker diarisation runs on CPU and is significantly slower (20-30x). Transcription (Whisper) runs well on CPU.

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

The Linux AppImage ships with **CPU-only PyTorch** to keep the download to ~600 MB. Swedish/auto-detect transcription uses KB-Whisper large (CTranslate2, INT8), which always runs on the CPU.

If you have an **NVIDIA GPU** with a working CUDA-capable driver installed on your host system, you can swap in the CUDA build of PyTorch to accelerate diarisation and the English/"Other" Whisper models (KB-Whisper stays on the CPU):

```bash
# From inside the AppImage's bundled python (one-time):
./Transcribbler-0.1.1.AppImage --appimage-extract
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

**Note:** the bundled CPU build will not use AMD ROCm or Intel GPUs. macOS uses Apple's MPS backend for diarisation when available; Windows currently bundles the standard PyPI wheel (CPU + CUDA when present on system).

## Project structure

```
main.py              Flask app — all routes
core/
  project.py         Project management (create, open, import)
  annotation.py      Annotations per coder (char-offset)
  codebook.py        CRUD for codes (hierarchical tree)
  analysis.py        Excerpts for the Analysis view (+ tag filter)
  analysis_export.py Analysis export (MD, CSV, DOCX, ODT)
  export.py          Project export (CSV, Markdown, codebook DOCX/ODT)
  qdpx.py            QDPX (REFI-QDA) export
  stats.py           Statistics; code_matrix.py, cooccurrence.py: matrices
  merge.py           Export/import of codings between coders
  irr.py             Cohen's kappa (inter-rater reliability)
  i18n.py            Backend localisation (sv/en)
  crypto.py          Project encryption
  transcribe.py      Whisper + pyannote (transcription + diarisation)
  ocr*.py            OCR (Apple Vision, EasyOCR)
  nsenc.py           Decryption (.nsenc — Notescribbler format)
  scribbler.py       Decryption (.scribbler — Notescribbler format)
static/js/app.js     Frontend logic (~6000 lines)
static/js/translations.js  UI strings (sv/en)
docs/                User manuals (manual_sv.md, manual_en.md)
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
