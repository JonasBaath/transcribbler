# Transcribbler — Beta Test Protocol (Linux)

**Version:** v0.1.0  
**Platform:** Ubuntu 24.04 LTS (eller motsvarande)  
**Repo:** https://github.com/JonasBaath/transcribbler  

Du är Claude och kör detta testprotokoll på en Linux-dator. Utför varje steg i ordning, rapportera resultatet (OK / FAIL + felbeskrivning) och fortsätt till nästa steg även om ett steg misslyckas, om inte annat anges.

---

## Förberedelser

### Kontrollera och installera förutsättningar

```bash
python3 --version
# Förväntat: Python 3.9, 3.10 eller 3.11
# Om saknas: sudo apt install python3 python3-venv python3-pip

node --version
# Förväntat: v20 eller senare
# Om saknas:
#   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
#   sudo apt install nodejs

ffmpeg -version
# Om saknas: sudo apt install ffmpeg

git --version
# Om saknas: sudo apt install git
```

---

## DEL 1 — Installation

### 1.1 Klona repo

```bash
git clone https://github.com/JonasBaath/transcribbler.git
cd transcribbler
```

### 1.2 Skapa virtualenv och installera beroenden

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

**Förväntat:** inga fel. Rapportera eventuella pip-fel med fullständig output.

### 1.3 Installera ML-beroenden (valfritt för grundtest)

ML-beroenden behövs för Whisper och OCR. Hoppa över om disken är begränsad (~3 GB).

```bash
pip install -r requirements-ml.txt
```

**OBS:** `python-doctr[torch]` installeras automatiskt på Linux. Rapportera eventuella CUDA/ROCm-varningar.

---

## DEL 2 — Flask-server (core)

### 2.1 Starta servern

```bash
source venv/bin/activate
python3 main.py
```

**Förväntat:**
- Utskrift: `Running on http://127.0.0.1:5050`
- Webbläsaren öppnas automatiskt på `http://127.0.0.1:5050`
- Om webbläsaren inte öppnas automatiskt: öppna manuellt

**Rapportera:** starttid, eventuella felmeddelanden i terminalen.

### 2.2 Skapa nytt projekt

I webbgränssnittet:
1. Klicka "Nytt projekt" / "New project"
2. Ange projektnamn, välj en mapp
3. Klicka OK / Skapa

**Förväntat:** projekt laddas, tomt kodbok, tom transkriptlista.

### 2.3 Importera textfil

```bash
echo "Intervju med testperson. Fraga: Vad tycker du om verktyget? Svar: Det verkar bra men jag behover testa mer." > test_intervju.txt
```

Importera i UI: Importknapp → välj `test_intervju.txt`.

**Förväntat:** transkriptet visas i listan och kan öppnas.

### 2.4 Importera .docx

```bash
python3 -c "from docx import Document; d=Document(); d.add_paragraph('Testtext fran docx-fil.'); d.save('test.docx')"
```

Importera `test.docx` i UI.

**Förväntat:** transkript importeras korrekt.

### 2.4b Importera .nsenc (krypterad Notescribbler-fil)

```bash
python3 -m core.nsenc --encrypt test.nsenc
# Ange lösenord när det frågas, t.ex. "test1234"
# Ange innehåll "Testanteckning fran nsenc" när det frågas
```

Importera i UI, ange samma lösenord.

**Förväntat:** lösenordsfält dyker upp när `.nsenc` väljs; efter rätt lösenord importeras anteckningen.

### 2.4c Importera .scribbler

Om testfil finns, importera via UI — annars hoppa över och rapportera "ingen testfil".

### 2.5 Kodbok — skapa koder

1. Öppna "Kodbok" / "Codebook"
2. Skapa en toppnivåkod, t.ex. "Tema A"
3. Skapa en underkod till "Tema A", t.ex. "Positiv"
4. Skapa ytterligare en toppnivåkod "Tema B"

**Förväntat:** trädstruktur visas korrekt.

### 2.6 Annotering — markera och koda text

1. Öppna transkriptet från 2.3
2. Markera "Det verkar bra"
3. Koppla till koden "Positiv"

**Förväntat:** markeringen visas med kodfärg, koden visas i sidofältet.

### 2.7 Export

1. Öppna Export-dialog
2. Välj format: CSV
3. Välj exportmapp (t.ex. hemkatalog)
4. Exportera

**Förväntat:** CSV-fil skapas i vald mapp. Öppna och verifiera att annoteringen syns.

Upprepa för **Markdown**- och **QDPX**-format.

**QDPX-specifikt:** filen ska gå att öppna i ATLAS.ti eller NVivo (verifiering endast om programvara finns tillgänglig — annars verifiera bara att `.qdpx`-filen skapas och är en giltig ZIP: `unzip -l <fil>.qdpx`).

### 2.8 Flera kodare + IRR

1. Skapa en ny kodare via UI (kodar-badge uppe till höger)
2. Med den nya kodaren aktiv: markera "verkar bra" i samma transkript och koppla till "Positiv"
3. Öppna Verktyg → IRR, välj båda kodarna

**Förväntat:** Cohen's Kappa beräknas och visas.

### 2.9 Port-kollision

Starta en andra instans medan första körs:

```bash
python3 main.py
```

**Förväntat:** antingen (a) felmeddelande, eller (b) annan port väljs automatiskt. Rapportera vilket.

### 2.10 Stäng servern

Tryck `Ctrl+C` i terminalen på första instansen.

**Förväntat:** servern avslutas. Rapportera om Ctrl+C hänger sig (känd bugg — rapportera hur länge det tar).

---

## DEL 3 — Electron-skalet

### 3.1 Installera Electron-beroenden

På Linux kan Electron kräva extra systembibliotek:

```bash
sudo apt install libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libasound2
```

### 3.2 Starta Electron

**Viktigt:** Electron startar Flask själv via `venv/bin/python3`. `venv` måste alltså existera (steg 1.2) **innan** `npm start` körs. Electron väljer en ledig port dynamiskt — inte nödvändigtvis 5050. Stäng först eventuell Flask-instans som körs (steg 2.10).

```bash
cd electron
npm install
npm start
```

**Förväntat:**
- Electron-fönster öppnas med Transcribbler-UI inuti
- Flask-servern startas i bakgrunden (`[flask]`-prefixade loggrader)

**Ubuntu 24.04-specifikt:** unprivileged user namespaces är begränsade, vilket kan blockera Electrons sandbox med `SUID sandbox helper binary`-fel. Åtgärder:

```bash
# Alternativ A (rekommenderat — endast testmiljö): kör utan sandbox
npm start -- --no-sandbox

# Alternativ B: tillåt user namespaces tillfälligt
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
```

Rapportera vilket alternativ som behövdes.

### 3.3 Verifiera IPC

Testa att mappväljaren i Export-dialogen fungerar (Electron IPC).

**Förväntat:** native Linux-mappväljare öppnas (xdg-open/portal).  
**OBS:** på minimala system (USB-boot utan skrivbordsmiljö) kan detta falla tillbaka på textinmatning — rapportera vilket.

### 3.4 Stäng Electron

Stäng fönstret normalt.

**Förväntat:** Flask-processen avslutas också. Verifiera:

```bash
pgrep -af "python.*main.py"
pgrep -af electron
```

**Förväntat:** ingen output (inga kvarvarande processer).

---

## DEL 4 — ML: OCR + Whisper (Linux-specifikt)

*Hela Del 4 kräver att ML-beroenden installerats (steg 1.3).*

### 4.1 OCR via docTR

Testbild finns i repo: `tests/fixtures/test_image.jpeg` (tidningsomslag med synlig text: "TC", "MIGRÄ[N]", "Nya rön om...", "ROCKENS FOLKPARTISTER", "ris 9:95").

Importera via UI med kryssrutan "Transkribera text i bild" / "Image OCR" ikryssad.

**Förväntat:** docTR kör OCR, text extraheras. Några ord bör kännas igen — särskilt de stora röda rubrikerna "ROCKENS FOLKPARTISTER". Mindre text och stiliserad logotyp ("TC") kan misslyckas — det är acceptabelt.

**Rapportera:** modell-nedladdningstid (första gången), CUDA/CPU-varningar, körtid, vilka ord som extraherades korrekt.

### 4.2 Whisper-transkription (ljud)

Testljudfil finns i repo: `tests/fixtures/test_audio.wav` (~30 s svenskt tal).

1. Importera `tests/fixtures/test_audio.wav` via UI
2. Välj språk (svenska → KB-Whisper, engelska → Whisper Medium)
3. Starta transkribering (utan diarization först)

**Förväntat:**
- Modell laddas ner första gången (flera GB — rapportera tid)
- Transkribering slutförs
- Text visas i transkript

**Rapportera:** körtid, GPU-användning, kvalitet.

### 4.3 Diarization (valfritt — kräver HF-token)

Kräver Hugging Face-token med godkänt licens för `pyannote/speaker-diarization-3.1`.

Om användaren har en token:
1. Ange token i Inställningar
2. Importera ljudfil med flera talare
3. Kör transkribering **med** diarization

**Förväntat:** talare separeras och markeras.

Om ingen token finns: hoppa över.

---

## DEL 5 — Pytests

```bash
source venv/bin/activate
pip install pytest
pytest tests/ -v
```

**Förväntat:** alla 47 tester gröna. Rapportera eventuella fel med fullständiga tracebacks.

---

## Sammanfattning

Fyll i efter avslutat test:

| Steg | Resultat | Kommentar |
|------|----------|-----------|
| 1.1 Klona | OK/FAIL | |
| 1.2 requirements.txt | OK/FAIL | |
| 1.3 requirements-ml.txt | OK/FAIL | |
| 2.1 Starta Flask | OK/FAIL | |
| 2.2 Nytt projekt | OK/FAIL | |
| 2.3 Importera .txt | OK/FAIL | |
| 2.4 Importera .docx | OK/FAIL | |
| 2.5 Kodbok | OK/FAIL | |
| 2.6 Annotering | OK/FAIL | |
| 2.4b .nsenc-import | OK/FAIL | |
| 2.4c .scribbler-import | OK/FAIL/SKIP | |
| 2.7 Export (CSV/MD/QDPX) | OK/FAIL | |
| 2.8 IRR | OK/FAIL | |
| 2.9 Port-kollision | OK/FAIL | Beteende (a) eller (b)? |
| 2.10 Stäng server | OK/FAIL | |
| 3.1 Electron-beroenden | OK/FAIL | |
| 3.2 Electron start | OK/FAIL | Sandbox-flagga behövd? |
| 3.3 IPC mappväljare | OK/FAIL | |
| 3.4 Stäng Electron | OK/FAIL | |
| 4.1 OCR docTR | OK/FAIL | |
| 4.2 Whisper | OK/FAIL/SKIP | |
| 4.3 Diarization | OK/FAIL/SKIP | |
| 5. Pytest | OK/FAIL | |

**Python-version:**  
**Linux-distro + version:**  
**Skrivbordsmiljö (eller "ingen"):**  
**GPU (om tillgänglig):**  
**Övriga observationer:**
