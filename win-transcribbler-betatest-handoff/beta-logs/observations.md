# Observationer betatest 2026-04-24

## 2.5 Kodbok — UX
Efter att man lagt till en ny kod hoppar UI tillbaka till kodningsvyn.
Förväntat: stanna i kodträdet, eftersom användaren ofta vill lägga till flera
koder i följd innan hen går tillbaka till kodning.
Typ: UX-regression / förbättringsförslag.


## 2.3b UTF-8-import — OK
test_aao.txt (147 bytes, UTF-8 utan BOM) med "blåbär på ön", "Fråga", "kött", "Öl", "Ångest".
Alla åäö visas korrekt efter import.

## 2.4b .nsenc-import — SKIP (bugg i CLI)
core.nsenc saknar argparser — kör direkt: notes, photos = decrypt_nsenc(path, pw)
Det betyder att --help, --encrypt osv. tolkas som filvägar. FileNotFoundError: '--help'.
Påverkar: icke-interaktiv test-skript-drift. Bör lägga till argparse/click.

## 2.4c .scribbler — SKIP
Ingen testfil i repo (glob tests/**/*.scribbler = tom).

## 4 Electron-port
Electron spawnar Flask på dynamisk port (53917 denna gång), inte hårdkodat 5050.
Protokollets HTTP-polling mot 5050 timeoutar därför falskt — bör dokumenteras eller
protokollet bör läsa aktuell port från [flask:NNNNN]-prefix i npm-start-loggen.

## 4 npm install
- 13 sårbarheter (2 low, 11 high) — kör "npm audit" för detaljer.
- electron/package-lock.json muteras av npm install. Regression (samma som tidigare rundor).

## Pytest-artefakt
tests/fixtures/project.json skapas vid pytest-körning och lämnas kvar (untracked).
Antingen: (a) tmp_path-fixture istället för fixtures/, eller (b) cleanup i teardown,
eller (c) lägg till i .gitignore.

## FAS 6 pytest
94 passed, 0 failed, 11.14s. Regressionsfixarna från 62cd165 håller.

## 2.7 Export — QDPX-källor: ingen avvikelse
(Tidigare flaggat som möjlig bug — RETRACTED.) Projektet har 3 transkript;
c6c5edaa har `original=docx`, `text_file=txt`. QDPX bifogar text_file för
alla 3, vilket matchar REFI-QDA-spec. ✓

## 2.7 Export — project.modified bumpas inte vid annotering
project.json `modified=2026-04-24T22:18:58`, men en annotering har
`created=22:21:08`. Annoteringen lades alltså till efter "modified".
Påverkar synk/dirty-check och recent-sortering om någon förlitar sig
på modified-fältet.

## FAS 3 step 1 — clean shutdown verifierad
Alla PIDs från RESUME.md (electron+python) döda efter normal close.
Inga kvarvarande lyssnare på 53917/5050. ✓

## 2.8 IRR — KRITISK BUGG i krypterade projekt
GET /api/transcripts/<tid>/irr → 500 "Kunde inte beräkna IRR." på alla
krypterade projekt.

**Orsak**: `main.py:1613` anropar `cohens_kappa(folder, project, tid, a, b)`
utan `key=_key()`. `cohens_kappa` skickar då `key=None` vidare till
`get_transcript_text()` och `load_annotations()` — båda hoppar över
dekrypteringsgrenen och försöker plain UTF-8-läsa bytes med "TENC"-header
→ UnicodeDecodeError.

**Stack**:
  File "main.py", line 1613, in get_irr
    result = cohens_kappa(STATE["folder"], STATE["project"], tid, coder_a, coder_b)
  File "core/irr.py", line 25, in cohens_kappa
    text = get_transcript_text(folder, t, key=key)
  File "core/project.py", line 384, in get_transcript_text
    return path.read_text(encoding="utf-8")
  UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 4

**Fix (1 rad)**: `main.py:1613`
  result = cohens_kappa(STATE["folder"], STATE["project"], tid,
                         coder_a, coder_b, key=_key())

**Reproduce**: öppna krypterat projekt → kör IRR från UI mellan två kodare.
Inte fångat av pytest eftersom test-fixtures sannolikt är okrypterade.

**Status denna runda**: betatestare-annoteringarna skapades OK
(0f7f51ec, 8bb99fa0). Själva kappa-beräkningen blockerad tills
ovan fix landar.

## FAS 3 — port-kollision detekteras inte på Windows
Två `python main.py`-instanser (default PORT=5050) startade ~10s isär
binder BÅDA framgångsrikt port 5050. Ingen EADDRINUSE, inget felmeddelande.
Båda PID:s syns LISTENING i `netstat` samtidigt (PID 11100 + PID 9364).

```
TCP    127.0.0.1:5050    0.0.0.0:0    LISTENING    9364
TCP    127.0.0.1:5050    0.0.0.0:0    LISTENING    11100
```

**Orsak**: Werkzeug-dev-servern sätter SO_REUSEADDR=1 by default.
På Windows tillåter detta multibind, varefter senast bundna socket
typiskt får inkommande SYN — men routning är ej deterministisk.

**Konsekvens**: en användare som råkar dubbelstarta från CLI får
två tysta instanser med olika in-memory STATE. Förstgångsöppna ett
projekt → räknar med att rätt STATE svarar — men nästa request kan
hamna hos den andra instansen som INTE har projektet öppet → "Inget
projekt öppnat"-fel pop-upps oförklarligt.

**Förslag**:
- Sätt allow_reuse_address=False på Werkzeug-servern (Werkzeug exposear
  detta via `make_server`), eller
- Skriv en pidfile/lockfil vid start och vägra starta om den finns och
  pekar på en levande process.

**Reproduce**:
  $ python main.py --no-browser   # term1
  $ python main.py --no-browser   # term2 — ska felfa, gör det inte

(Electron-flödet är inte påverkat — det väljer dynamisk port via
JS-sidan och kraschar ej tyst.)

## FAS 5.1 — partiell cache rensas redan automatiskt
RESUME.md flaggade "Rensa partiell KB-Whisper-cache (~1.4 GB) — kräver OK"
som ett förberedelsesteg. Inte längre nödvändigt:
`core.transcribe._convert_kb_whisper_to_ct2` (transcribe.py:155-158) gör
`shutil.rmtree(output_dir)` automatiskt om mappen finns men sentinel-filer
saknas. Loggades vid Whisper-körning:
  "Removing partial KB-Whisper CTranslate2 directory ... before re-converting"
Steg 5.1 kan strykas ur protokollet.

## FAS 5 OCR — ✓
EasyOCR-pipelinen kör end-to-end utan extra setup.
- POST /api/transcripts/upload (multipart, run_ocr=1) → job_id
- Poll /api/jobs/<id> → status="done" på ~5 min (test_image.jpeg, CPU).
- Skapar transcript med text + bounding boxes (`/ocr-boxes` returnerar
  fraction-koordinater x/y/w/h).
- Kvalitet på test-bilden låg (gröna rubriker → "TC", "MIGRF", "F@LKPARTISTER")
  — testbilden är dock kanske avsiktligt svår.

## FAS 5 Whisper — KRITISK BUGG: saknad dependency `transformers`
Whisper-jobb misslyckas i model-loading med:
  NameError: name 'transformers' is not defined
  (ctranslate2/converters/transformers.py:108)

**Orsak**: KBLab/kb-whisper-large konverteras via
`ctranslate2.converters.TransformersConverter`, som kräver `transformers`-
paketet. ctranslate2:s import är skyddad av `try/except ImportError: pass`
(transformers.py:12-15) → om paketet saknas definieras `TransformersConverter`
ändå, men `_load()` kraschar med NameError vid användning.

**Verifierat**: `python -c "import transformers"` → ModuleNotFoundError.
`requirements-ml.txt` deklarerar inte `transformers`.

**Fix**: lägg till i requirements-ml.txt
  transformers>=4.40
(matcha versionsintervallet faster-whisper/ctranslate2 stödjer.)

**Påverkan**: Whisper för svenska (sv/autodetect → KBLab-path) helt blockerat
på alla beta-installationer som kör fresh `pip install -r requirements-ml.txt`.
Engelska/`whisper-medium`-pathen påverkas troligen inte (faster-whisper
laddar pre-konverterad modell direkt från Systran/faster-whisper-medium).

**Inte testat denna runda**: engelska-pathen (kräver att man specificerar
language=en eller other vid upload — endpointen accepterar det men jag drev
inte UI-flaggan).

## FAS 5.3 — Diarization SKIP
HF-token saknas (`/api/config/hf-token` → has_token:false). Diarization
bygger på pyannote/speaker-diarization-3.1 från HF som kräver token.

## 2.7 / FAS 4 — Folder-picker IPC: arkitektur korrekt
Två picker-vägar finns parallellt — frontend väljer på `if (window.electronAPI)`:

**Electron-läge** (app.js:366, 2913):
  window.electronAPI.pickFolder()
   ↓ ipcRenderer.invoke('pick-folder')   (preload.js:4)
   ↓ ipcMain.handle('pick-folder')       (main.js:268-275)
   ↓ dialog.showOpenDialog(win,
       {properties:['openDirectory'], title:'Välj projektmapp'})
  → Modern Vista-style native Windows-mapdialog, modal-attachad
    till Transcribbler-fönstret.

**Browser-läge** (fallback):
  GET /api/pick-folder
   ↓ subprocess.run(['powershell', ...])  (main.py:229-240)
   ↓ System.Windows.Forms.FolderBrowserDialog (Description="Välj projektmapp")
  → Äldre WinForms tree-style-dialog, ej attachad (popp upp på godtyckligt
    skärmläge), spawnad ur ett separat PowerShell-process.

**Bedömning**:
- IPC-bridgen är korrekt konfigurerad: `contextIsolation:true`,
  `nodeIntegration:false`, preload exponerar bara whitelistad API. ✓
- Båda vägarna är "native" Win32 men UX:en skiljer sig:
  Electron-dialogen är den moderna; PowerShell-vägen är den gamla.

**Vad som inte kan verifieras utan UI-drift**:
- Om preload.js faktiskt laddas runtime (om inte → tyst fallback till
  PowerShell-vägen utan felmeddelande).
- Att dialogen visuellt renderas (men `dialog.showOpenDialog` är ett
  beprövat Electron-API).
- "Last viewed folder"-persistens i Electron-dialogen.

**Hur testaren känner igen vilken väg som används**:
- Modern Vista-stil m/ "Open"-caption  → Electron IPC ✓
- Äldre tree-stil m/ Description-text  → Flask-fallback (= Electron IPC bröt)

Ingen funktionell bugg upptäckt vid kodgenomgång.

### Runtime-verifierat via Chrome DevTools Protocol (2026-04-25)
Startade Electron med `--remote-debugging-port=9223 --remote-allow-origins=*`,
attachade Python-CDP-klient (`beta-logs/cdp_probe.py`) till renderaren och körde:

| Probe | Värde |
|---|---|
| `typeof window.electronAPI` | `'object'` ✓ |
| `Object.keys(window.electronAPI)` | `['pickFolder','onMenuClick','setMenuLang','titlebarDoubleClick','platform']` ✓ |
| `typeof window.electronAPI.pickFolder` | `'function'` ✓ |
| `window.electronAPI.platform` | `'win32'` ✓ |
| Branch `window.electronAPI ? 'electron-ipc-path' : 'flask-fallback-path'` | `'electron-ipc-path'` ✓ |

→ Preload.js laddas och bridgen exponeras helt korrekt.

Triggade sedan `window.electronAPI.pickFolder()` direkt via CDP →
modal Win32-dialog dök upp. Win32-EnumWindows-dump
(`beta-logs/enum_windows.py`):

```
HWND     PID    PROC          OWNER    CLASS                TITLE
459568   15524  electron.exe       0   Chrome_WidgetWin_1   'transcribbler'
37422094 15524  electron.exe  459568   #32770               'Välj projektmapp'
```

- Dialogfönstret ägs av **electron.exe** (PID 15524) — INTE powershell.exe → bekräftar att Electron-IPC-vägen används.
- Klass `#32770` (standard Win32-dialog; IFileOpenDialog top-level).
- Owner HWND = 459568 = transcribbler-huvudfönstret → **modal-attachad korrekt** ✓.
- Titel "Välj projektmapp" från `main.js:272`.

Stängdes via `PostMessage WM_CLOSE`. **Folder-picker UI verifierad end-to-end.**
