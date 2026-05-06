# Transcribbler — Betatest-protokoll (Windows, parallellt)

**Version:** v0.1.0-beta + post-release fixar (commit `62cd165` eller nyare på `main`)  
**Plattform:** Windows 10/11  
**Repo:** https://github.com/JonasBaath/transcribbler  
**Syfte:** Parallellprotokoll — Claude kör CLI/bakgrundsjobb, testaren hanterar GUI. Båda arbetar samtidigt där möjligt och möts vid tydliga synkroniseringspunkter.

---

## Ändringar sedan förra rundan (2026-04-23)

Dessa buggar ska **inte längre uppträda** — om de gör det, logga som regression:

1. **Transkription blockerad av partiell KB-Whisper-cache.** `RuntimeError: output directory … already exists`. Fixat i `core/transcribe.py` (idempotent konvertering). Se steg **4.0** — partiell cache måste rensas en gång för hand.
2. **Pytest: 28 failed + 8 errors (FileNotFoundError på `annotations/<tid>.<coder>.json`).** Fixat via `os.makedirs` i `core/annotation.py`. Förväntat: **0 failed, 94 passed**.
3. **IndexError i `test_bug_scenarios.py`.** Fixat via `scope="class"` i `tests/conftest.py`.

---

## Regler

**Claude:**
1. **Logga, fixa inte.** Alla avvikelser dokumenteras i Observation-fälten — inga kodändringar.
2. **Inga git-operationer utöver pull.** Inga commits, checkouts eller force-push.
3. **Destruktiva operationer** (radera cache, döda processer, ta bort venv) kräver explicit OK av testaren — pausa och fråga.
4. **Logga alltid till fil:** `*>&1 | Tee-Object -FilePath beta-logs\<steg>.log`
5. **Synkpunkter:** vänta på testaren vid varje ⏸-markering.

**Testaren:**
1. Du behöver inte vänta på Claude — arbeta på din spår direkt.
2. Vid ⏸-markeringar: meddela Claude vad du observerat, vänta på Claudes bekräftelse.
3. Rapportera allt du ser i GUI (fel, oväntad layout, krasch).

---

## Symboler

| Symbol | Betydelse |
|--------|-----------|
| 🤖 | Claude kör detta i PowerShell |
| 👤 | Testaren gör detta i GUI |
| ⏸ | Synkroniseringspunkt — båda ska vara klara innan nästa fas |
| ⚠️ | Kräver Claudes bekräftelse eller testarens OK |

---

## FAS 0 — Parallell uppstart

*Båda startar omedelbart — ingen behöver vänta på den andre.*

### 🤖 Claude: Förberedelser (kör direkt)

```powershell
cd transcribbler
New-Item -ItemType Directory -Force -Path beta-logs | Out-Null

# Miljökontroll
python --version *>&1 | Tee-Object -FilePath beta-logs\0_env.log
node --version *>&1 | Tee-Object -Append -FilePath beta-logs\0_env.log
ffmpeg -version 2>&1 | Select-Object -First 1 | Tee-Object -Append -FilePath beta-logs\0_env.log
git --version *>&1 | Tee-Object -Append -FilePath beta-logs\0_env.log

# Hämta senaste kod
git status *>&1 | Tee-Object -FilePath beta-logs\0_git_status.log
git fetch origin main *>&1 | Tee-Object -FilePath beta-logs\0_fetch.log
git log -1 --oneline origin/main
```

Om `git status` visar oincheckade ändringar — **pausa och fråga testaren** innan pull.

```powershell
git pull --ff-only origin main *>&1 | Tee-Object -FilePath beta-logs\0_pull.log
git log -1 --oneline
```

Förväntat: HEAD = `62cd165` eller senare.

```powershell
# Aktivera venv och installera beroenden (kan ta flera minuter)
venv\Scripts\activate
pip install -r requirements.txt *>&1 | Tee-Object -FilePath beta-logs\0_pip.log
```

**Observation:**
- Python: _
- Node: _
- ffmpeg: _
- Git: _
- HEAD-commit: _
- `62cd165` i historik? _
- pip exit code: _
- pip-fel (se `beta-logs\0_pip.log`): _

### 👤 Testaren: Läs och förbered (gör direkt)

Medan Claude installerar — gå igenom följande:

1. Läs igenom hela detta protokoll en gång.
2. Bestäm: ska ML-tester (Del 4) köras? Kräver ~5 GB disk och tar lång tid. **Svara Claude** med ja/nej.
3. Har du en Hugging Face-token för diarization? **Svara Claude** med ja/nej.
4. Notera var du vill spara exportfiler (t.ex. skrivbordet) — du behöver detta i steg 2.7.

### ⏸ SYNC 0 — Båda klara med fas 0

*Claude:* pip-installationen klar, git är på rätt commit.  
*Testaren:* har svarat på ML-frågan och HF-token-frågan.

---

## FAS 1 — ML-beroenden (valfritt)

*Kör bara om testaren svarat "ja" på ML-frågan i Sync 0. Annars hoppa till Fas 2.*

### 🤖 Claude: Installera ML-beroenden (kör direkt)

```powershell
# Kontrollera diskutrymme först
Get-PSDrive C | Select-Object Used, Free

pip install -r requirements-ml.txt *>&1 | Tee-Object -FilePath beta-logs\1_pip_ml.log
```

Kräver ~3–5 GB. Rapportera CUDA-varningar.

### 👤 Testaren: (kan vila eller läsa dokumentation)

Inget att göra under installationen.

### ⏸ SYNC 1 — ML-installation klar

*Claude:* rapporterar exit code och eventuella CUDA-varningar.

**Observation:**
- ML-test valt? _
- Diskutrymme innan install: _
- pip exit code: _
- CUDA-varningar: _

---

## FAS 2 — Flask-server och testdata

*Claude startar servern och skapar testfiler. Testaren väntar på Sync 2A innan GUI-arbete börjar.*

### 🤖 Claude: Starta server + skapa testfiler (kör direkt, parallellt)

**Starta server i bakgrundsjobb:**

```powershell
$flaskJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    venv\Scripts\activate
    python main.py
}
```

**Medan servern startar — skapa testfiler:**

```powershell
# Textfil
"Intervju med testperson. Fraga: Vad tycker du om verktyget? Svar: Det verkar bra men jag behover testa mer." |
    Out-File -Encoding UTF8 test_intervju.txt

# .docx
python -c "from docx import Document; d=Document(); d.add_paragraph('Testtext fran docx-fil.'); d.save('test.docx')"

# Kontrollera om nsenc CLI stöder icke-interaktiv drift
python -m core.nsenc --help *>&1 | Tee-Object -FilePath beta-logs\2_nsenc_help.log
```

**Vänta på att servern svarar:**

```powershell
$tries = 0
do {
    Start-Sleep -Seconds 2
    $tries++
    $r = try { Invoke-WebRequest -Uri http://127.0.0.1:5050/ -UseBasicParsing -ErrorAction Stop } catch { $null }
} while (-not $r -and $tries -lt 30)
if ($r) { "Server UP efter $($tries*2) sek, HTTP $($r.StatusCode)" } else { "TIMEOUT — server svarar inte" }
```

**Observation:**
- Starttid (sekunder): _
- HTTP 200? _
- Fel i serverlogg (Receive-Job $flaskJob): _
- test_intervju.txt skapad? _
- test.docx skapad? _
- nsenc CLI-läge möjligt? _

### ⏸ SYNC 2A — Server uppe + testfiler redo

*Claude:* bekräftar HTTP 200 och att testfiler skapats.  
*Testaren:* kan nu börja GUI-arbetet nedan.

### 👤 Testaren: GUI-arbete (Flask core)

Gör stegen i ordning. Meddela Claude när du är klar med varje block.

**2.2 Nytt projekt**
1. Klicka "Nytt projekt" i UI
2. Ange namn, välj mapp, klicka OK
- Observation: _

**2.3 Importera textfil**
1. Klicka Importera → välj `test_intervju.txt` (finns i transcribbler-mappen)
- Observation: _

**2.4 Importera .docx**
1. Importera → välj `test.docx`
- Observation: _

**2.4b Importera .nsenc**
*(Hoppa till 2.4c om Claude rapporterat att nsenc inte stöder icke-interaktiv drift.)*
1. Claude skapar filen om möjligt. Annars: kör `python -m core.nsenc --encrypt test.nsenc` i terminalen, ange lösenord "test1234"
2. Importera `test.nsenc` via UI, ange lösenord "test1234"
- Lösenordsfält dyker upp? _
- Import lyckas? _

**2.4c Importera .scribbler**
- Finns testfil i repo? Om ja, importera. Om nej: SKIP
- Observation: _

**2.5 Kodbok**
1. Öppna Kodbok
2. Skapa toppnivåkod "Tema A"
3. Skapa underkod "Positiv" under Tema A
4. Skapa toppnivåkod "Tema B"
- Trädstruktur korrekt? _

**2.6 Annotering**
1. Öppna transkriptet från 2.3
2. Markera "Det verkar bra"
3. Koppla till koden "Positiv"
- Markering visas med kodfärg? _

**2.7 Export**
1. Öppna Export-dialog
2. Exportera som CSV → välj exportmapp (notera sökvägen, ge den till Claude)
3. Exportera som Markdown
4. Exportera som QDPX
- Exportmapp: _

### 🤖 Claude: Verifiera exporter (när testaren rapporterat exportmapp)

```powershell
$exportmapp = "FYLL_I_TESTARENS_EXPORTMAPP"
Get-ChildItem $exportmapp | Select-Object Name, Length, LastWriteTime |
    Tee-Object -FilePath beta-logs\2_7_export_files.log

# CSV-innehåll
$csv = Get-ChildItem $exportmapp -Filter *.csv | Select-Object -First 1
if ($csv) { Get-Content $csv.FullName -First 20 | Tee-Object -FilePath beta-logs\2_7_csv.log }

# QDPX = giltig ZIP?
$qdpx = Get-ChildItem $exportmapp -Filter *.qdpx | Select-Object -First 1
if ($qdpx) {
    Expand-Archive $qdpx.FullName -DestinationPath beta-logs\qdpx-check -Force
    Get-ChildItem beta-logs\qdpx-check -Recurse | Select-Object FullName |
        Tee-Object -FilePath beta-logs\2_7_qdpx.log
}
```

**Observation:**
- CSV skapad + innehåll rimligt? _
- MD skapad? _
- QDPX giltig ZIP? _

**Fortsättning GUI (testaren):**

**2.8 IRR**
1. Skapa ny kodare via UI (kodar-badge → byt/skapa)
2. Med ny kodare aktiv: markera "verkar bra" → koda som "Positiv"
3. Verktyg → IRR → välj båda kodarna → kör
- Cohen's Kappa-värde: _

### ⏸ SYNC 2B — Flask-GUI-arbete klart

*Testaren:* klar med 2.2–2.8, rapporterat alla observationer.  
*Claude:* exporter verifierade.

---

## FAS 3 — Port-kollision och pytest (parallellt)

*Claude kör båda dessa utan att testaren behöver göra något.*

### 🤖 Claude: Port-kollision + pytest i parallell

```powershell
# Port-kollision: starta en andra instans
$second = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    venv\Scripts\activate
    python main.py
}
Start-Sleep -Seconds 5
Receive-Job $second *>&1 | Tee-Object -FilePath beta-logs\2_9_port.log
Stop-Job $second; Remove-Job $second

# Starta pytest som bakgrundsjobb
$pytestJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    venv\Scripts\activate
    pip install pytest -q
    pytest tests/ -v
}
```

Pytest körs nu i bakgrunden. Claude rapporterar port-kollisionsresultatet direkt.

**Observation port-kollision:**
- Beteende: (a) felmeddelande / (b) annan port / (c) tyst krasch: _
- Felmeddelande: _

### 👤 Testaren: Stäng Flask-servern

1. Tryck `Ctrl+C` i Flask-terminalfönstret
2. Meddela Claude hur lång tid det tog och om det hängde

**Observation:**
- Sekunder tills prompt: _
- Antal Ctrl+C som krävdes: _

### 🤖 Claude: Verifiera att servern är borta

```powershell
Get-Process python -ErrorAction SilentlyContinue | Format-Table Id, ProcessName
```

**Observation:**
- Kvarvarande python-processer: _

---

## FAS 4 — Electron

### 🤖 Claude: npm install (kör direkt)

```powershell
cd electron
npm install *>&1 | Tee-Object -FilePath ..\beta-logs\4_npm_install.log
```

### 👤 Testaren: (vila eller notera observationer från fas 2–3)

Inget att göra under npm install.

### ⏸ SYNC 4A — npm install klar

**Observation:**
- Exit code: _

### 🤖 Claude: Starta Electron (och invänta testaren)

```powershell
npm start *>&1 | Tee-Object -FilePath ..\beta-logs\4_npm_start.log
```

### 👤 Testaren: Verifiera och interagera

1. Electron-fönster öppnas? (Meddela Claude ja/nej)
2. UI syns inuti fönstret?
3. Öppna Export-dialog → klicka mappväljare
   - Native Windows-dialog eller webb-dialog?
4. Stäng fönstret normalt

**Observation:**
- Fönster öppnas? _
- `[flask]`-rader i logg? _
- Mappväljare: native / webb-dialog / krasch: _

### 🤖 Claude: Verifiera att alla processer avslutats

```powershell
cd ..
Get-Process python, electron -ErrorAction SilentlyContinue | Format-Table Id, ProcessName |
    Tee-Object -FilePath beta-logs\4_procs.log
```

**Observation:**
- Kvarvarande processer: _

### ⏸ SYNC 4B — Electron-fas klar

---

## FAS 5 — ML: OCR + Whisper

*Körs bara om ML-beroenden installerats (Fas 1). Annars: hoppa till Fas 6.*

### 🤖 Claude: Rensa partiell KB-Whisper-cache ⚠️

*Engångssteg. Claude frågar testaren innan körning.*

> Jag behöver rensa `%USERPROFILE%\.cache\transcribbler\kb-whisper-ct2` (~1,4 GB, partiell konvertering från förra rundan). OK?

*Efter OK:*

```powershell
$ct2 = Join-Path $env:USERPROFILE ".cache\transcribbler\kb-whisper-ct2"
if (Test-Path $ct2) {
    Get-ChildItem $ct2 | Measure-Object -Sum Length | Select-Object Count, Sum
    Remove-Item -Recurse -Force $ct2
    "Rensade $ct2"
} else {
    "Ingen ct2-cache att rensa"
} *>&1 | Tee-Object -FilePath beta-logs\5_0_cache_clear.log
```

**Observation:**
- Testarens OK: _
- Cachen fanns? _
- Antal filer + storlek: _

### 👤 + 🤖 OCR och Whisper (parallellt)

*Claude startar Flask igen för ML-testen.*

```powershell
# 🤖 Starta om Flask
$flaskJob2 = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    venv\Scripts\activate
    python main.py
}
# Vänta på HTTP 200
$tries = 0
do {
    Start-Sleep -Seconds 2; $tries++
    $r = try { Invoke-WebRequest -Uri http://127.0.0.1:5050/ -UseBasicParsing -ErrorAction Stop } catch { $null }
} while (-not $r -and $tries -lt 30)
"Server: $(if($r){'UP'}else{'TIMEOUT'})"
```

**Testaren — OCR (steg 5.1):**
1. Importera `tests\fixtures\test_image.jpeg` med "Image OCR" ikryssad
2. Vänta tills transkriptet visas
3. Rapportera: modell-nedladdningstid, körtid, om "ROCKENS FOLKPARTISTER" hittades, om åäö är rätt

**Testaren — Whisper (steg 5.2, efter OCR):**
1. Importera `tests\fixtures\test_audio.wav`
2. Välj språk: svenska (→ KB-Whisper) eller engelska (→ Whisper Medium)
3. Starta transkribering utan diarization
4. Rapportera: nedladdningstid, körtid, GPU-användning (Task Manager), kvalitet 1–5

**Testaren — Diarization (steg 5.3, om HF-token finns):**
1. Ange token i Inställningar
2. Importera ljud med flera talare
3. Kör med diarization aktiverat
- Observation: _

**Observation ML:**
- OCR modell-nedladdningstid: _
- OCR körtid: _
- "ROCKENS FOLKPARTISTER" hittat? _
- åäö korrekt? _
- Whisper nedladdningstid: _
- Whisper körtid: _
- GPU utnyttjad? _
- Whisper kvalitet (1–5): _
- Diarization: OK / FAIL / SKIP: _

### ⏸ SYNC 5 — ML-fas klar

*Testaren stänger Flask (Ctrl+C). Claude verifierar inga kvarvarande processer.*

---

## FAS 6 — Pytest-resultat

*Pytestjobbet startades redan i Fas 3. Här hämtar Claude resultatet.*

### 🤖 Claude: Hämta pytest-resultat

```powershell
# Vänta på jobbet om det fortfarande körs
Wait-Job $pytestJob -Timeout 300
Receive-Job $pytestJob *>&1 | Tee-Object -FilePath beta-logs\6_pytest.log
Remove-Job $pytestJob
```

Om jobbet av någon anledning inte längre finns (t.ex. session avbröts):

```powershell
venv\Scripts\activate
pytest tests/ -v *>&1 | Tee-Object -FilePath beta-logs\6_pytest.log
```

**Förväntat:** `0 failed, 94 passed`.

**Observation:**
- Passed / Failed / Error: _
- 0 failed? _
- Regressionsfailures (namn): _
- Se `beta-logs\6_pytest.log` för tracebacks

---

## Sammanställning

| Fas | Steg | Resultat | Kommentar |
|-----|------|----------|-----------|
| 0 | Env + git pull | OK/FAIL | Commit? |
| 0 | pip requirements.txt | OK/FAIL | |
| 1 | pip requirements-ml.txt | OK/FAIL/SKIP | |
| 2 | Flask start | OK/FAIL | Starttid |
| 2 | Nytt projekt | OK/FAIL | |
| 2 | Importera .txt | OK/FAIL | |
| 2 | Importera .docx | OK/FAIL | |
| 2 | Importera .nsenc | OK/FAIL | |
| 2 | Importera .scribbler | OK/FAIL/SKIP | |
| 2 | Kodbok | OK/FAIL | |
| 2 | Annotering | OK/FAIL | |
| 2 | Export CSV/MD/QDPX | OK/FAIL | |
| 2 | IRR (Cohen's Kappa) | OK/FAIL | Kappa-värde: |
| 3 | Port-kollision | OK/FAIL | Beteende a/b/c |
| 3 | Stäng Flask | OK/FAIL | Tid: |
| 4 | Electron npm install | OK/FAIL | |
| 4 | Electron start | OK/FAIL | |
| 4 | IPC mappväljare | OK/FAIL | |
| 4 | Stäng Electron | OK/FAIL | |
| 5 | Rensa ct2-cache | OK/SKIP | |
| 5 | OCR | OK/FAIL/SKIP | |
| 5 | Whisper | OK/FAIL/SKIP | |
| 5 | Diarization | OK/FAIL/SKIP | |
| 6 | Pytest | OK/FAIL | Passed/Failed: |

**Python-version:**  
**Node-version:**  
**Windows-version (`winver`):**  
**GPU (om tillämpligt):**  
**Övriga observationer:**

---

## Efter körning (utvecklaren)

1. Hämta detta dokument + `beta-logs\` från testmaskinen.
2. Kontrollera att `git status` **bara** visar ändringar i detta dokument, `beta-logs\` och tillfälliga testfiler (`test_intervju.txt`, `test.docx`, `test.nsenc`). Inget annat ska vara ändrat.
3. Åtgärda buggar på utvecklarmaskinen.
