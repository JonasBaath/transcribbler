# Transcribbler — Betatest-protokoll (Windows, Claude-driven)

**Version:** v0.1.0-beta + post-release fixar (commit `62cd165` eller nyare på `main`)
**Plattform:** Windows 10/11
**Repo:** https://github.com/JonasBaath/transcribbler
**Syfte:** Detta är en variant av `BETA_TEST_WINDOWS.md` anpassad för att köras av Claude på en dedikerad **testdator**.

---

## Ändringar sedan förra rundan (2026-04-23)

Dessa buggar ska **inte längre uppträda** — om de gör det, logga det som regression:

1. **Transkription blockerad av partiell KB-Whisper-cache.** Tidigare kastade tre jobb i rad `RuntimeError: output directory … already exists, use --force to override`. Fixat i `core/transcribe.py` (idempotent konvertering + rensning av partiell dir). **OBS:** Se nytt steg **4.0 Rensa ct2-cache** nedan innan transkription — den befintliga partiella dir:en från förra rundan måste tas bort en gång för att fixen ska kunna återskapa den.
2. **Pytest: 28 failed + 8 errors (FileNotFoundError på `annotations/<tid>.<coder>.json`).** Fixat via `os.makedirs` i `core/annotation.py:save_annotations`. Förväntat resultat i steg 5: **0 failed, 94 passed**.
3. **Step-chain-tester i `test_bug_scenarios.py` (IndexError).** Fixat via `scope="class"` på fixturerna i `tests/conftest.py`.

---

## ⚠️ LÄS FÖRST — REGLER FÖR DENNA SESSION

**Du är Claude, du kör detta protokoll på en testdator som ägs av utvecklaren (Jonas).**

1. **LOGGA SVAREN — GÖR INGA ÄNDRINGAR.**
   Detta är en testmaskin, inte en utvecklingsmaskin. Alla buggar och avvikelser ska **dokumenteras** i fälten **Observation** nedan — de ska **inte** åtgärdas av dig. Utvecklaren fixar buggarna själv på sin egen maskin efteråt.

2. **Inga kodändringar i repot.**
   Du får inte editera, skapa eller ta bort filer under `transcribbler\` förutom:
   - **Detta dokument** (`BETA_TEST_WINDOWS_CLAUDE.md`) — för att logga observationer.
   - **Loggkatalog** `transcribbler\beta-logs\` — för körloggar.
   - **Tillfälliga testfiler** som protokollet uttryckligen säger ska skapas (t.ex. `test_intervju.txt`).
   Inga `git commit`, `git push`, `git checkout`, inga `pip install --upgrade` av projektets egna paket, inga patchar till `.py`/`.js`-filer.

3. **Om något är uppenbart trasigt: beskriv, föreslå i text, implementera INTE.**
   Formulera gärna hypotes om rotorsak i Observation-fältet ("trolig orsak: path-separator på rad X") men gör inte själva fixen.

4. **Destruktiva operationer kräver explicit OK från användaren.**
   Exempel: rensa HuggingFace-cache, döda kvarvarande processer, radera venv. Pausa och fråga först.

5. **Kör ALLTID med logg till fil.**
   Använd `*>&1 | Tee-Object -FilePath beta-logs\<steg>.log` (PowerShell-syntax — se `FELMEDDELANDEN_WINDOWS.txt` rad 58).

6. **Vid UT-steg: pausa och invänta användaren.**
   Klicka inte "på måfå" i GUI:t. Om ett steg kräver mänsklig interaktion (se kategorierna nedan) — skriv tydligt vad användaren ska göra och vänta på återrapportering innan du markerar steget som klart.

### Teststegens kategorier

| Kod | Betydelse | Vem utför? |
|-----|-----------|------------|
| **AC** | **Automatisk (Claude)** — körs helt via PowerShell/CLI/HTTP. Claude kan göra detta själv. | Claude ensam |
| **UT** | **Användartest** — kräver GUI-klick, native dialoger, lösenordsfält, mikrofon, eller visuell/auditiv verifikation. | Användaren; Claude väntar |
| **AC+UT** | Blandat — Claude förbereder/startar, användaren verifierar eller interagerar med GUI. | Båda |

---

## Förberedelser

### 0.1 Skapa loggkatalog (AC)

```powershell
cd transcribbler
New-Item -ItemType Directory -Force -Path beta-logs | Out-Null
```

### 0.2 Kontrollera förutsättningar (AC)

```powershell
python --version
node --version
ffmpeg -version | Select-Object -First 1
git --version
```

Logga allt till `beta-logs\env.log`.

**Observation:**
- Python: _<fyll i>_
- Node: _<fyll i>_
- ffmpeg: _<fyll i>_
- Git: _<fyll i>_
- Saknade verktyg: _<fyll i, rapportera utan att installera>_

---

## DEL 1 — Installation

### 1.1 Repo-status + hämta senaste version (AC)

Repot är redan klonat på testmaskinen. Verifiera att arbetskatalogen är ren och hämta senaste `main`:

```powershell
git status
git fetch origin main *>&1 | Tee-Object -FilePath beta-logs\1_1_fetch.log
git log -1 --oneline origin/main
git pull --ff-only origin main *>&1 | Tee-Object -FilePath beta-logs\1_1_pull.log
git log -1 --oneline
```

**Förväntan:** HEAD ska vara `62cd165` *"fix: Windows-betatest — annotation-mkdir, KB-Whisper-idempotens, test-scope"* eller senare. Om `git status` visar oincheckade ändringar — **pausa och fråga användaren** innan `git pull`, tidigare beta-loggar kan ligga ostashade.

**Observation:**
- Branch + commit efter pull: _<fyll i>_
- `62cd165` (eller senare) i historiken? _<ja/nej>_
- Ouncommitted changes före pull: _<fyll i>_
- Fast-forward OK? _<ja/nej — om konflikt: stoppa, rapportera till användaren>_

### 1.2 Venv + requirements.txt (AC)

```powershell
venv\Scripts\activate
pip install -r requirements.txt *>&1 | Tee-Object -FilePath beta-logs\1_2_pip.log
```

**Observation:**
- Exit code: _<fyll i>_
- Eventuella fel: _<fyll i, hänvisa till `beta-logs\1_2_pip.log`>_

### 1.3 requirements-ml.txt (AC, valfritt)

Hoppa över om disk < 5 GB ledig.

```powershell
Get-PSDrive C | Select-Object Used, Free
pip install -r requirements-ml.txt *>&1 | Tee-Object -FilePath beta-logs\1_3_pip_ml.log
```

**Observation:**
- Kört? _<ja/nej + motivering>_
- CUDA-varningar: _<fyll i>_
- Exit code: _<fyll i>_

---

## DEL 2 — Flask-server (core)

### 2.1 Starta servern (AC+UT)

**AC-del:** Claude startar servern i ett bakgrundsjobb:

```powershell
python main.py *>&1 | Tee-Object -FilePath beta-logs\2_1_flask.log
```

Vänta på `Running on http://127.0.0.1:5050`.

**UT-del:** Användaren bekräftar att webbläsaren öppnas automatiskt (Claude kan inte verifiera om ett fönster dyker upp visuellt, bara att URL:en svarar).

Claude kan istället verifiera att servern svarar:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:5050/ -UseBasicParsing | Select-Object StatusCode
```

**Observation:**
- Starttid: _<fyll i>_
- HTTP 200? _<fyll i>_
- Webbläsare öppnades? _<användaren fyller i>_
- Fel i stderr: _<fyll i>_

### 2.2 Skapa nytt projekt (UT)

Användaren: "Nytt projekt" → ange namn → välj mapp → OK.

**Observation (användaren):**
- Projekt skapat? _<ja/nej>_
- Ev. fel i UI: _<fyll i>_

### 2.3 Importera textfil (AC+UT)

**AC-del:**
```powershell
"Intervju med testperson. Fraga: Vad tycker du om verktyget? Svar: Det verkar bra men jag behover testa mer." | Out-File -Encoding UTF8 test_intervju.txt
```

**UT-del:** användaren importerar filen via UI.

**Observation:**
- Fil skapad? _<ja/nej, AC>_
- Importeras i UI? _<ja/nej, UT>_
- Visas i transkriptlista? _<ja/nej, UT>_

### 2.4 Importera .docx (AC+UT)

**AC-del:**
```powershell
python -c "from docx import Document; d=Document(); d.add_paragraph('Testtext fran docx-fil.'); d.save('test.docx')"
```

**UT-del:** användaren importerar via UI.

**Observation:** _<fyll i>_

### 2.4b .nsenc-import (UT, primärt)

**AC-del:** Claude skapar krypterad testfil om CLI:n tillåter icke-interaktiv drift:
```powershell
python -m core.nsenc --help *>&1 | Tee-Object -FilePath beta-logs\2_4b_nsenc_help.log
```
Om `--help` avslöjar en flagga för lösenord via argument/env, använd den. **Annars:** markera som UT och be användaren skapa filen manuellt.

**UT-del:** Användaren importerar i UI och anger lösenord.

**Observation:**
- CLI-läge möjligt? _<fyll i>_
- Lösenordsfält dyker upp i UI? _<användaren>_
- Import lyckas? _<användaren>_

### 2.4c .scribbler-import (UT eller SKIP)

Om testfil saknas: SKIP och rapportera "ingen testfil i repo".

### 2.5 Kodbok (UT)

Skapa "Tema A" → "Positiv" (underkod) → "Tema B". Användaren utför.

**Observation:** _<användaren>_

### 2.6 Annotering (UT)

Markera "Det verkar bra" → koda som "Positiv".

**Observation:** _<användaren>_

### 2.7 Export (AC+UT)

**UT-del:** användaren triggar export via UI (CSV, MD, QDPX).
**AC-del:** Claude verifierar att filerna skapats och inspekterar innehåll:

```powershell
Get-ChildItem <exportmapp> | Select-Object Name, Length, LastWriteTime
Get-Content <export>.csv -First 20
# QDPX ska vara giltig ZIP:
Expand-Archive <export>.qdpx -DestinationPath beta-logs\qdpx-check -Force
Get-ChildItem beta-logs\qdpx-check -Recurse | Select-Object FullName
```

**Observation:**
- CSV skapad + innehåll rimligt? _<fyll i>_
- MD skapad + innehåll rimligt? _<fyll i>_
- QDPX giltig ZIP? _<fyll i>_

### 2.8 IRR — flera kodare (UT)

Användaren: skapa andra kodare, duplicera annotering, kör IRR-verktyget.

**Observation:** _<användaren — Cohen's Kappa-värde>_

### 2.9 Port-kollision (AC)

Andra Flask-instans medan första körs:

```powershell
Start-Process python -ArgumentList "main.py" -RedirectStandardOutput beta-logs\2_9_second_instance.log -RedirectStandardError beta-logs\2_9_second_instance.err -NoNewWindow
Start-Sleep -Seconds 5
Get-Content beta-logs\2_9_second_instance.log, beta-logs\2_9_second_instance.err
```

**Observation:**
- Beteende: (a) fel / (b) annan port / (c) tyst krasch: _<fyll i>_
- Felmeddelande: _<fyll i>_

### 2.10 Stäng servern (AC+UT)

**Känd bugg:** Ctrl+C kan hänga. Claude kan skicka Ctrl+C programmatiskt till bakgrundsjobbet — men om det hänger: pausa och fråga användaren.

**Observation:**
- Tid till prompt efter Ctrl+C: _<fyll i>_
- Antal Ctrl+C som krävdes: _<fyll i>_
- Kvarvarande processer (`Get-Process python`): _<fyll i>_

---

## DEL 3 — Electron-skalet

### 3.1 Installera + starta (AC+UT)

Stäng först Flask från 2.10.

**AC-del:**
```powershell
cd electron
npm install *>&1 | Tee-Object -FilePath ..\beta-logs\3_1_npm_install.log
npm start *>&1 | Tee-Object -FilePath ..\beta-logs\3_1_npm_start.log
```

**UT-del:** Användaren bekräftar att Electron-fönster öppnas och UI visas.

**Observation:**
- `npm install` exit code: _<fyll i>_
- `[flask]`-prefixade rader i logg? _<fyll i>_
- Electron-fönster öppnas? _<användaren>_

### 3.2 IPC-mappväljare (UT)

Användaren öppnar Export-dialog och klickar mappväljare.

**Observation:** _<användaren: native-dialog eller webb-dialog?>_

### 3.3 Stäng Electron (AC+UT)

**UT-del:** användaren stänger fönstret.
**AC-del:** Claude verifierar:
```powershell
Get-Process python, electron -ErrorAction SilentlyContinue | Format-Table Id, ProcessName
```

**Observation:**
- Kvarvarande processer: _<fyll i>_

---

## DEL 4 — ML: OCR + Whisper

*Kräver att 1.3 körts.*

### 4.1 OCR (AC+UT)

**UT-del:** Användaren importerar `tests\fixtures\test_image.jpeg` med "Image OCR" ikryssad.
**AC-del:** Claude inspekterar resultat via Flask-API eller logg.

**Observation:**
- Modell-nedladdningstid (första): _<fyll i>_
- CUDA/CPU-varningar: _<fyll i>_
- Körtid: _<fyll i>_
- Extraherad text (utdrag): _<fyll i>_
- åäö korrekt? _<fyll i>_
- Hittas "ROCKENS FOLKPARTISTER"? _<fyll i>_

### 4.0 Rensa partiell KB-Whisper-cache (AC, destruktivt — kräver OK)

**Engångssteg inför första transkriptionen efter pull av `62cd165`.** Förra rundans avbrutna konverteringar lämnade kvar en partiell `kb-whisper-ct2`-katalog som blockerade alla jobb. Den idempotenta koden skippar sentinel-filer (`model.bin` + `config.json`) om konverteringen är komplett, men en ofullständig dir måste tas bort en gång så den kan återskapas rent.

Enligt regel 4: **pausa och inhämta OK från användaren innan kommandot körs.** Fråga med exakt citatet nedan:

> "Jag behöver rensa `%USERPROFILE%\.cache\transcribbler\kb-whisper-ct2` (~1,4 GB, partiell konvertering från förra rundan). Detta är destruktivt men krävs för att den idempotenta fixen ska ha något att återskapa. OK?"

Efter OK:
```powershell
$ct2 = Join-Path $env:USERPROFILE ".cache\transcribbler\kb-whisper-ct2"
if (Test-Path $ct2) {
    Get-ChildItem $ct2 | Measure-Object -Sum Length | Select-Object Count, Sum
    Remove-Item -Recurse -Force $ct2
    "Rensade $ct2"
} else {
    "Ingen ct2-cache att rensa"
} *>&1 | Tee-Object -FilePath beta-logs\4_0_cache_clear.log
```

**Observation:**
- Fanns cachen? _<ja/nej>_
- Antal filer + storlek före rensning: _<fyll i>_
- Användarens OK: _<tidpunkt + OK/Nekat>_

### 4.2 Whisper (AC+UT)

**OBS:** Modellnedladdning kräver flera GB. Bekräfta diskutrymme.

**UT-del:** Användaren importerar `tests\fixtures\test_audio.wav`, väljer språk, startar transkribering utan diarization.
**AC-del:** Claude mäter körtid via loggar, inspekterar resultat.

**Observation:**
- Nedladdningstid: _<fyll i>_
- Körtid: _<fyll i>_
- GPU utnyttjas? _<användaren, via Task Manager>_
- Kvalitet (subjektivt 1-5): _<användaren>_

### 4.3 Diarization (UT eller SKIP)

Kräver HF-token. Om token saknas: SKIP.

**Observation:** _<fyll i>_

---

## DEL 5 — Pytest (AC)

```powershell
pip install pytest
pytest tests/ -v *>&1 | Tee-Object -FilePath beta-logs\5_pytest.log
```

**Förväntat resultat efter `62cd165`:** `0 failed, 94 passed` (macOS-referens). Förra rundans `28 failed + 8 errors` med `FileNotFoundError` på `annotations/<tid>.<coder>.json` ska vara borta.

**Observation:**
- Passed/Failed/Skipped: _<fyll i>_
- Matchar förväntat (0 failed)? _<ja/nej — om nej, logga som regression>_
- Failures (namn): _<fyll i>_
- Fullständiga tracebacks: se `beta-logs\5_pytest.log`

---

## Sammanställning

| Steg | Kategori | Resultat | Kommentar |
|------|----------|----------|-----------|
| 0.2 Env | AC | OK/FAIL | |
| 1.1 Repo-status + pull | AC | OK/FAIL | `62cd165`+ i historik? |
| 1.2 pip requirements | AC | OK/FAIL | |
| 1.3 pip ML | AC | OK/FAIL/SKIP | |
| 2.1 Starta Flask | AC+UT | OK/FAIL | |
| 2.2 Nytt projekt | UT | OK/FAIL | |
| 2.3 Importera .txt | AC+UT | OK/FAIL | |
| 2.4 Importera .docx | AC+UT | OK/FAIL | |
| 2.4b .nsenc | UT | OK/FAIL | |
| 2.4c .scribbler | UT | OK/FAIL/SKIP | |
| 2.5 Kodbok | UT | OK/FAIL | |
| 2.6 Annotering | UT | OK/FAIL | |
| 2.7 Export | AC+UT | OK/FAIL | |
| 2.8 IRR | UT | OK/FAIL | |
| 2.9 Port-kollision | AC | OK/FAIL | |
| 2.10 Stäng server | AC+UT | OK/FAIL | |
| 3.1 Electron start | AC+UT | OK/FAIL | |
| 3.2 IPC mappväljare | UT | OK/FAIL | |
| 3.3 Stäng Electron | AC+UT | OK/FAIL | |
| 4.0 Rensa ct2-cache | AC | OK/SKIP | användarens OK inhämtat? |
| 4.1 OCR | AC+UT | OK/FAIL/SKIP | |
| 4.2 Whisper | AC+UT | OK/FAIL/SKIP | blockerar tre-jobb-buggen fortfarande? |
| 4.3 Diarization | UT | OK/FAIL/SKIP | |
| 5. Pytest | AC | OK/FAIL | |

**Python-version:**
**Node-version:**
**Windows-version (`winver`):**
**GPU (om tillämpligt):**
**Övriga observationer:**

---

## Efter körning (utvecklaren)

1. Hämta detta dokument + `beta-logs\` från testmaskinen.
2. Verifiera att `git status` på testmaskinen **bara** visar ändringar i `BETA_TEST_WINDOWS_CLAUDE.md` och nya filer under `beta-logs\` + testdata (`test_intervju.txt`, `test.docx`). Om något annat är ändrat — påminn Claude på testmaskinen om regel 1.
3. Åtgärda buggar på utvecklarmaskinen.
