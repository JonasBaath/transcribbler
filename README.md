<p align="center">
  <img src="static/img/logo.svg" width="140" alt="Transcribbler logo">
</p>

# Transcribbler

A local desktop app for qualitative transcript coding. Import transcripts (text, audio, or image), build a hierarchical codebook, and code text passages — entirely offline, no cloud services required.

![Transcribbler screenshot](docs/screenshot.png)

## Features

- **Transcription** — automatic speech-to-text via Whisper (KB-Whisper for Swedish, Whisper Medium for English)
- **Diarization** — speaker separation via pyannote.audio + ECAPA-TDNN
- **Coding** — highlight text passages and link them to hierarchical codes; undo/redo support
- **Multiple coders** — inter-rater reliability support (Cohen's Kappa)
- **OCR** — import images and extract text (Apple Vision on macOS, docTR on Windows/Linux)
- **Export** — CSV, Markdown, DOCX, ODT, QDPX (ATLAS.ti/NVivo-compatible)
- **Import** — .txt, .docx, .odt, .md (incl. YAML frontmatter from Notescribbler), .nsenc, .scribbler
- **Offline-first** — no API keys required, all data stays local

## Requirements

- Python 3.9–3.11
- [ffmpeg](https://ffmpeg.org/) (required for Whisper): `brew install ffmpeg`
- HF token for diarization (optional): [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

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
