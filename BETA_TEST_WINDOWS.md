# Transcribbler — Beta Test Protocol (Windows)

**Version:** v0.1.0  
**Platform:** Windows 10/11  
**Repo:** https://github.com/JonasBaath/transcribbler  

Du är Claude och kör detta testprotokoll på en Windows-dator. Utför varje steg i ordning, rapportera resultatet (OK / FAIL + felbeskrivning) och fortsätt till nästa steg även om ett steg misslyckas, om inte annat anges.

---

## Förberedelser

### Kontrollera förutsättningar

```powershell
python --version
# Förväntat: Python 3.9, 3.10 eller 3.11
# Om saknas: installera från https://python.org (kryssa i "Add to PATH")

node --version
# Förväntat: v20 eller senare
# Om saknas: installera från https://nodejs.org

ffmpeg -version
# Förväntat: ffmpeg version 6.x eller senare
# Om saknas: winget install Gyan.FFmpeg
#   eller: choco install ffmpeg  (om Chocolatey finns)
#   eller: ladda ner manuellt från https://ffmpeg.org/download.html och lägg i PATH

git --version
# Om saknas: winget install Git.Git
```

---

## DEL 1 — Installation

### 1.1 Klona repo

```powershell
git clone https://github.com/JonasBaath/transcribbler.git
cd transcribbler
```

### 1.2 Skapa virtualenv och installera beroenden

```powershell
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

**Förväntat:** inga fel. Rapportera eventuella pip-fel med fullständig output.

### 1.3 Installera ML-beroenden (valfritt för grundtest)

ML-beroenden behövs för Whisper och OCR. Hoppa över detta steg om disken är begränsad (kräver ~3 GB).

```powershell
pip install -r requirements-ml.txt
```

**OBS:** `easyocr` (med torch-backend) installeras via `requirements-ml.txt`. Rapportera eventuella CUDA-varningar.

---

## DEL 2 — Flask-server (core)

### 2.1 Starta servern

```powershell
python main.py
```

**Förväntat:**
- Utskrift: `Running on http://127.0.0.1:5050`
- Webbläsaren öppnas automatiskt på `http://127.0.0.1:5050`

**Rapportera:** starttid, eventuella felmeddelanden i terminalen.

### 2.2 Skapa nytt projekt

I webbgränssnittet:
1. Klicka "Nytt projekt" / "New project"
2. Ange projektnamn, välj en mapp
3. Klicka OK / Skapa

**Förväntat:** projekt laddas, tomt kodbok, tom transkriptlista.

### 2.3 Importera textfil

Skapa en testfil:

```powershell
echo "Intervju med testperson. Fraga: Vad tycker du om verktyget? Svar: Det verkar bra men jag behover testa mer." > test_intervju.txt
```

Importera i UI: Importknapp → välj `test_intervju.txt`.

**Förväntat:** transkriptet visas i listan och kan öppnas.

### 2.4 Importera .docx

Skapa en minimal docx-fil via Python:

```powershell
python -c "from docx import Document; d=Document(); d.add_paragraph('Testtext fran docx-fil.'); d.save('test.docx')"
```

Importera `test.docx` i UI.

**Förväntat:** transkript importeras korrekt.

### 2.4b Importera .nsenc (krypterad Notescribbler-fil)

Skapa en testfil med CLI:n:

```powershell
python -m core.nsenc --encrypt test.nsenc
# Ange lösenord när det frågas, t.ex. "test1234"
# Anger innehåll "Testanteckning fran nsenc" när det frågas
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
3. Välj exportmapp (t.ex. skrivbordet)
4. Exportera

**Förväntat:** CSV-fil skapas i vald mapp. Öppna filen och verifiera att annoteringen syns.

Upprepa för **Markdown**- och **QDPX**-format.

**QDPX-specifikt:** filen ska gå att öppna i ATLAS.ti eller NVivo (verifiering endast om programvara finns tillgänglig — annars verifiera bara att `.qdpx`-filen skapas och är en giltig ZIP).

### 2.8 Flera kodare + IRR (inter-rater reliability)

1. Skapa en ny kodare via UI (kodar-badge uppe till höger → byt kodare / skapa ny)
2. Med den nya kodaren aktiv: markera "verkar bra" i samma transkript och koppla till "Positiv"
3. Öppna Verktyg → IRR
4. Välj de två kodarna och en kod att jämföra

**Förväntat:** Cohen's Kappa beräknas och visas.

### 2.9 Port-kollision (edge case)

Starta en andra instans medan första körs:

```powershell
python main.py
```

**Förväntat:** antingen (a) felmeddelande om porten används, eller (b) en annan port väljs automatiskt. Rapportera vilket beteende som inträffar.

### 2.10 Stäng servern

Tryck `Ctrl+C` i terminalen på första instansen.

**Förväntat:** servern avslutas. Rapportera om Ctrl+C hänger sig (känd kvarvarande bugg — rapportera ändå hur länge det tar).

---

## DEL 3 — Electron-skalet

**Viktigt:** Electron startar Flask själv via `venv\Scripts\python.exe`. `venv` måste alltså existera (från steg 1.2) **innan** `npm start` körs. Electron väljer en ledig port dynamiskt — inte nödvändigtvis 5050.

### 3.1 Installera och starta

Stäng först eventuell Flask-instans som körs (steg 2.10).

```powershell
cd electron
npm install
npm start
```

**Förväntat:**
- Electron-fönster öppnas med Transcribbler-UI inuti
- I terminalen syns `[flask]`-prefixade loggrader
- Ingen separat webbläsare behövs

### 3.2 Verifiera IPC

Testa att mappväljaren i Export-dialogen fungerar (Electron IPC, inte webbläsar-API).

**Förväntat:** native Windows-mappväljare öppnas.

### 3.3 Stäng Electron

Stäng fönstret normalt.

**Förväntat:** Flask-processen avslutas också.

Verifiera att ingen Python/Electron-process hänger kvar:

```powershell
Get-Process python, electron -ErrorAction SilentlyContinue
```

**Förväntat:** ingen output (inga kvarvarande processer).

---

## DEL 4 — ML: OCR + Whisper (Windows-specifikt)

*Hela Del 4 kräver att ML-beroenden installerats (steg 1.3).*

### 4.1 OCR via EasyOCR

Testbild finns i repo: `tests\fixtures\test_image.jpeg` (tidningsomslag med synlig text: "TC", "MIGRÄ[N]", "Nya rön om...", "ROCKENS FOLKPARTISTER", "ris 9:95").

Importera via UI med kryssrutan "Transkribera text i bild" / "Image OCR" ikryssad.

**Förväntat:** EasyOCR kör, text extraheras. Några ord bör kännas igen — särskilt de stora röda rubrikerna "ROCKENS FOLKPARTISTER". Mindre text och stiliserad logotyp ("TC") kan misslyckas — det är acceptabelt.

**Rapportera:** modell-nedladdningstid (första gången), CUDA/CPU-varningar, körtid, vilka ord som extraherades korrekt, särskilt om åäö hanteras rätt.

### 4.2 Whisper-transkription (ljud)

Testljudfil finns i repo: `tests\fixtures\test_audio.wav` (~30 s svenskt tal).

1. Importera `tests\fixtures\test_audio.wav` via UI
2. Välj språk (svenska → KB-Whisper, engelska → Whisper Medium)
3. Starta transkribering (utan diarization först)

**Förväntat:**
- Modell laddas ner första gången (flera GB — rapportera tid)
- Transkribering slutförs
- Text visas i transkript

**Rapportera:** körtid, GPU-användning (om tillgänglig), kvalitet.

### 4.3 Diarization (valfritt — kräver HF-token)

Kräver Hugging Face-token med godkänt licens för `pyannote/speaker-diarization-3.1`.

Om användaren har en token:
1. Ange token i Inställningar
2. Importera ljudfil med flera talare
3. Kör transkribering **med** diarization

**Förväntat:** talare separeras och markeras i transkriptet.

Om ingen token finns: hoppa över och rapportera.

---

## DEL 5 — Pytests

```powershell
pip install pytest
pytest tests/ -v
```

**Förväntat:** alla 47 tester gröna. Rapportera eventuella fel med fullständigt tracebacks.

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
| 3.1 Electron start | OK/FAIL | |
| 3.2 IPC mappväljare | OK/FAIL | |
| 3.3 Stäng Electron | OK/FAIL | |
| 4.1 OCR EasyOCR | OK/FAIL | |
| 4.2 Whisper | OK/FAIL/SKIP | |
| 4.3 Diarization | OK/FAIL/SKIP | |
| 5. Pytest | OK/FAIL | |

**Python-version:**  
**Windows-version:**  
**GPU (om tillgänglig):**  
**Övriga observationer:**
