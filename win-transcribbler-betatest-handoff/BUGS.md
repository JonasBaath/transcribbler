# Buggrapporter — Transcribbler v0.1.0-beta (Windows-runda 2026-04-25)

Klara att klistra in i issue-tracker eller åtgärda direkt.

---

## BUGG #1 — IRR krasha på alla krypterade projekt [KRITISK]

**Symptom**: GET `/api/transcripts/<tid>/irr?coder_a=A&coder_b=B` returnerar
500 "Kunde inte beräkna IRR." för varje krypterat projekt. Plain projekt
fungerar troligen (ej testat — alla testprojekt råkade vara krypterade).

**Stack**:
```
File "main.py", line 1613, in get_irr
    result = cohens_kappa(STATE["folder"], STATE["project"], tid, coder_a, coder_b)
File "core/irr.py", line 25, in cohens_kappa
    text = get_transcript_text(folder, t, key=key)
File "core/project.py", line 384, in get_transcript_text
    return path.read_text(encoding="utf-8")
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 4: invalid start byte
```

**Rotorsak**: `cohens_kappa()` accepterar `key=` som kwarg och skickar vidare
till både `get_transcript_text()` och `load_annotations()`. Men anroparen i
`main.py:1613` glömmer `key=_key()`. När projektet är krypterat har
transcript-text-filen "TENC"-header-bytes; utan `key` faller läsningen
igenom till plain UTF-8-decode → fel på första non-ASCII-byte.

**Fix** (1 rad i `main.py:1613`):
```python
result = cohens_kappa(STATE["folder"], STATE["project"], tid,
                      coder_a, coder_b, key=_key())
```

**Test som hade fångat**: `tests/test_irr.py` har sannolikt bara
okrypterade fixtures. Lägg till en testfall som öppnar krypterat projekt
och kör IRR.

**Reproduce**:
1. Skapa krypterat projekt med lösenord
2. Lägg till annoteringar från två kodare på samma transkript
3. Kör IRR från UI eller curl GET `/api/transcripts/<tid>/irr`

---

## BUGG #2 — Whisper svensk-path saknar `transformers` [KRITISK]

**Symptom**: Audio upload med default language → bakgrundsjobb fail i
"loading_model"-stadiet:
```
NameError: name 'transformers' is not defined
File "core/transcribe.py", line 171, in _convert_kb_whisper_to_ct2
    converter.convert(str(output_dir), quantization="int8", force=False)
File ".../ctranslate2/converters/transformers.py", line 108, in _load
    config = transformers.AutoConfig.from_pretrained(...)
```

**Rotorsak**: KBLab/kb-whisper-large konverteras med
`ctranslate2.converters.TransformersConverter` som kräver Python-paketet
`transformers`. ctranslate2:s import är skyddad av `try/except ImportError: pass`
(se `ctranslate2/converters/transformers.py:12-15`). Om `transformers` inte
finns definieras `TransformersConverter` ändå, men dess `_load()` exploderar
i NameError vid första användning.

`requirements-ml.txt` deklarerar inte `transformers`. Verifierat med:
```
$ python -c "import transformers"
ModuleNotFoundError: No module named 'transformers'
```

**Fix** — lägg till i `requirements-ml.txt`:
```
transformers>=4.40
```

(Versionsval: matcha vad faster-whisper/ctranslate2 stödjer; 4.40 är
modern och stabil. Kontrollera att den inte krockar med pyannote.audio.)

**Påverkan**: Whisper för svenska (default `language=sv` eller `autodetect`
→ KBLab-path) helt blockerat på alla beta-installationer som kör
fresh `pip install -r requirements-ml.txt`. Engelska-pathen påverkas
troligen ej eftersom faster-whisper hämtar pre-konverterad modell direkt
från `Systran/faster-whisper-medium`.

**Bonus-bugg i ctranslate2**: importskyddet är försvagat — borde antingen
låta NameError bli ImportError vid TransformersConverter-konstruktion, eller
skippa hela klassen om transformers saknas. Kan rapporteras uppströms.

---

## BUGG #3 — Port-kollision tyst på Windows [HÖG]

**Symptom**: Två `python main.py`-instanser (default PORT=5050) kan startas
parallellt. Ingen EADDRINUSE; båda lyssnar samtidigt:
```
TCP    127.0.0.1:5050    0.0.0.0:0    LISTENING    9364
TCP    127.0.0.1:5050    0.0.0.0:0    LISTENING    11100
```

**Rotorsak**: Werkzeug-dev-servern sätter `SO_REUSEADDR=1` per default. På
Windows tillåter detta multibind, varefter senast bundna socket typiskt
får inkommande SYN — men routning är ej deterministisk.

**Konsekvens för användare**: Dubbelstart från CLI ger två tysta instanser
med olika in-memory STATE. Användaren öppnar ett projekt → request kan
hamna hos den andra instansen som INTE har det öppet → "Inget projekt
öppnat"-fel utan förklaring. Mycket svårt att felsöka för slutanvändaren.

**Fix-alternativ**:

**(a)** Använd `make_server` direkt med `allow_reuse_address=False`:
```python
from werkzeug.serving import make_server
srv = make_server("127.0.0.1", port, app)
srv.serve_forever()  # ersätter app.run(...)
```
(`make_server` har inte ett direkt allow_reuse_address-arg — får göras via
en custom subclass av BaseWSGIServer eller pidfile.)

**(b)** Pidfile / lockfil-mönster:
```python
import os, sys
LOCK = Path.home() / ".transcribbler.lock"
if LOCK.exists():
    pid = int(LOCK.read_text())
    if psutil.pid_exists(pid):
        sys.exit(f"Transcribbler kör redan (PID {pid}).")
LOCK.write_text(str(os.getpid()))
```

**(c)** Manuell socket-test innan `app.run`:
```python
with socket.socket() as s:
    try: s.bind(("127.0.0.1", port))
    except OSError: sys.exit("Port redan upptagen.")
```

(c) är enklast. Electron-flödet är inte påverkat (det väljer dynamisk port
via JS-sidan med `reservePort` och kraschar inte tyst).

---

## BUGG #4 — project.modified bumpas inte vid annotering [MEDEL]

**Symptom**: Lägg till annotering → `project.json::modified` står still.

**Repro**:
- `project.json` `modified=2026-04-24T22:18:58`
- Lägg till annotering kl 22:21:08 (annotation `created=22:21:08`)
- `project.modified` är fortfarande `22:18:58`.

**Rotorsak**: `core/annotation.py::add_annotation` skriver bara
`annotations/{tid}.{coder}.json` men kallar inte `proj_mod.save_project()`
eller bumpar `project["modified"]`. Kodbok-ändringar i `core/codebook.py`
gör det troligen — men annoteringar inte.

**Fix**: I `add_annotation()` (och `update_annotation`, `delete_annotation`)
bumpa `project["modified"]` och spara projektet:
```python
project["modified"] = datetime.now().isoformat(timespec="seconds")
proj_mod.save_project(folder, project, key=key)
```

**Påverkan**: dirty-check, recent-sortering, "ändrad sedan senaste backup"-
indikatorer; alla blir felaktiga om de förlitar sig på `modified`.

---

## Lågprioriterade fynd

### 5. `core.nsenc` saknar argparser
.nsenc-CLI-läget tolkar `--help` som filväg → FileNotFoundError. Lägg
till argparse/click. (Funnet 2026-04-24, fortfarande oöppnat.)

### 6. electron/package-lock.json drift vid `npm install`
Lockfilen muteras vid varje `npm install`. Återställs manuellt i protokollet.
Värt att lösa via package.json-version pinning eller `.npmrc save-exact=true`.

### 7. tests/fixtures/project.json skapas av pytest
Pytest skapar sidoeffekter i `tests/fixtures/` som inte gitignorerats.
Använd `tmp_path`-fixture eller cleanup i teardown.

### 8. system-info `ram_gb=null`
GET `/api/system-info` returnerar `ram_gb: null` på Windows 11. Troligen
saknat fallback i `psutil`/`platform`-läsning (denna maskin kör Windows
11 Education 10.0.26200).

### 9. Flask Electron-spawn på dynamisk port
Electron väljer dynamisk port (53917 eller annan) → protokoll-dokument
som hänvisar till "5050-polling" är vilseledande. Uppdatera README/
beta-protokoll.

### 10. FAS 5.1 cache-rensningssteg redundant
`core/transcribe.py:155-158` auto-rensar partiell KB-Whisper-cache vid varje
körning. Steg "Rensa partiell KB-Whisper-cache (~1.4 GB) — kräver OK" i
beta-protokoll kan strykas.

### 11. UX: kodbok hoppar till kodningsvy efter "lägg till kod"
Användaren förväntar sig att stanna i kodträdet efter att ha lagt till en
kod (för att lägga till flera). Funnet 2026-04-24, oöppnat. Bekräfta med
utvecklaren om detta är bugg eller avsikt.

---

## Inte bugg — bekräftade vid kodgenomgång + runtime

- **Folder-picker IPC-bridge**: korrekt konfigurerad, körts via CDP, dialog
  ägdes av electron.exe (inte powershell.exe), modal-attachad. ✓
- **QDPX-export**: skickar bara `text_file` som källa per transkript —
  matchar REFI-QDA-spec. (Tidigare flaggat som möjlig bug; retracted.)
- **Clean shutdown**: alla Electron+Flask-PIDs dör vid normal close
  (verifierat 2026-04-25 efter gårdagens session). ✓
