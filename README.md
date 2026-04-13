# Transcribbler

Lokal skrivbordsapp för kvalitativ transkript-kodning. Ladda in transkript (text, ljud eller bild), bygg en hierarkisk kodbok och koda textpassager — allt offline, utan molntjänster.

![Transcribbler screenshot](docs/screenshot.png)

## Funktioner

- **Transkription** — automatisk tal-till-text via Whisper (KB-Whisper för svenska, Whisper Medium för engelska)
- **Diarisering** — talaruppdelning via pyannote.audio + ECAPA-TDNN
- **Kodning** — markera textpassager och koppla till hierarkiska koder; ångra/gör om
- **Flera kodare** — stöd för inter-rater reliability (Cohen's Kappa)
- **OCR** — importera bilder och extrahera text (Apple Vision på macOS, docTR på Windows/Linux)
- **Export** — CSV, Markdown, DOCX, ODT, QDPX (ATLAS.ti/NVivo-kompatibelt)
- **Import** — .txt, .docx, .odt, .md (inkl. YAML-frontmatter från Notescribbler), .nsenc, .scribbler
- **Offline-first** — inga API-nycklar krävs, all data stannar lokalt

## Krav

- Python 3.9–3.11
- [ffmpeg](https://ffmpeg.org/) (krävs för Whisper): `brew install ffmpeg`
- HF-token för diarisering (valfritt): [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

## Installation

```bash
git clone https://github.com/jonasbaath/transcribbler.git
cd transcribbler
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # grundinstallation (Flask + krypto)
pip install -r requirements-ml.txt  # ML-beroenden (Whisper, pyannote, OCR)
```

## Köra

```bash
source venv/bin/activate
python3 main.py
```

Öppnar automatiskt `http://127.0.0.1:5050` i webbläsaren.

### Electron-app (skrivbord)

```bash
cd electron
npm install
npm start
```

Kräver [Node.js](https://nodejs.org/) ≥ 20.

## Projektstruktur

```
main.py              Flask-app — alla routes
core/
  project.py         Projekthantering (skapa, öppna, import)
  annotation.py      Annoteringar per kodare (char-offset)
  codebook.py        CRUD för koder (hierarkiskt träd)
  transcribe.py      Whisper + pyannote (transkription + diarisering)
  export.py          CSV, Markdown, DOCX, ODT, QDPX
  irr.py             Cohen's Kappa (inter-rater reliability)
  nsenc.py           Kryptering (.nsenc — Notescribbler-format)
  scribbler.py       Kryptering (.scribbler — Notescribbler-format)
static/js/app.js     All frontend-logik (~2400 rader)
electron/            Electron-skal (main.js, preload.js)
tests/               Pytest-testsvit
```

## Tester

```bash
pip install pytest
pytest tests/ -v
```

## Licens

© Jonas Bååth — [GNU Affero General Public License v3.0](LICENSE)

Källkoden är fri att använda, modifiera och distribuera under villkoren i AGPL-3.0. Modifierade versioner som tillhandahålls som nätverkstjänst måste distribuera sin källkod.
