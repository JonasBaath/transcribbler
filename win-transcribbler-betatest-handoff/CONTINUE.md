# Hur du fortsätter på den nya maskinen

## Vad du behöver

- Den nya maskinen (online, kan installera paket).
- Klon-rättigheter för transcribbler-repo (eller branch där HEAD = `62cd165`).
- Python 3.11+, Node 20+, ffmpeg.
- (Valfritt) HF-token om du vill testa diarization.

## Snabbstart

```bash
git clone https://github.com/JonasBaath/transcribbler.git
cd transcribbler
git checkout 62cd1655c419264e858c63c8e5f323be30f301d3   # eller senaste main
python -m venv venv
source venv/bin/activate    # eller venv\Scripts\activate på Windows
pip install -r requirements-ml.txt
cd electron && npm install && cd ..
```

## Innan du börjar testa — fixa BUGG #2 lokalt

Annars kommer Whisper-testen att fortsätta krascha. Lägg till i
`requirements-ml.txt`:

```
transformers>=4.40
```

…och kör om `pip install -r requirements-ml.txt`.

## Två väldigt olika vägar framåt

### Väg A: Fortsätt buggtest mot HEAD som är (62cd165)

Repetera de "Bör-tester" från `TESTPROTOCOL_STATUS.md` på fräsch installation.
Buggar #1, #3, #4 ska reproduceras (förvänta dig samma symptom).

Användbart kommando — starta båda backender och Electron med CDP:
```bash
# I terminal A — bare Flask för API-driven test
python main.py --no-browser
# I terminal B — Electron med remote debug
cd electron
./node_modules/.bin/electron . --remote-debugging-port=9223 --remote-allow-origins=*
```

För att verifiera folder-picker IPC på den nya maskinen:
```bash
# Kopiera probe-scripts/cdp_probe.py till transcribbler/beta-logs/
pip install websocket-client psutil
python beta-logs/cdp_probe.py
# Förväntar 'electron-ipc-path' och en lista med 5 nycklar.
```

### Väg B: Fixa buggarna och kör pytest + manuell verifiering

1. Klistra in fix för **BUGG #1** (main.py:1613, lägg till `key=_key()`).
2. Skriv testfall för IRR mot krypterat projekt (saknas idag).
3. Klistra in fix för **BUGG #2** (lägg till `transformers>=4.40` i requirements-ml.txt).
4. Klistra in fix för **BUGG #3** (välj alternativ a/b/c från `BUGS.md`).
5. Klistra in fix för **BUGG #4** (`save_project` + bumpa `modified` i annotation.py).
6. `pytest` — alla 94 ska fortsätta passera.
7. Manuell verifiering av varje bugg-fix enligt repro-stegen i `BUGS.md`.

## Test-data du kan importera till nytt testprojekt

På offline-maskinen finns krypterat testprojekt "betatest2404"
(`tests/fixtures/`, lösenord `Test123!`). Det följer INTE med på USB:n
(för stort + krypterat). Återskapa enklast:

1. Skapa nytt projekt med samma namn + lösenord
2. Importera `tests/fixtures/test_intervju.txt`, `test.docx`, `test_aao.txt`
   (dessa följer med i repo).
3. Skapa koderna: Kos A, Positiv (under Kos A), Kod B, Kod C, Kod CC (under Kod C).
4. Annotera ngn rad i `test.docx` (nu kallad transcript "test").
5. Logga in som ny kodare ("betatestare") och annotera samma transkript igen
   — sätter scenen för IRR-test.

## Återstående bör-tester (i prioritetsordning)

Detalj i `TESTPROTOCOL_STATUS.md` § "Bör-tester". Kort:

1. Whisper engelska-path (verifierar att BUGG #2 är begränsad till sv).
2. OCR med tydlig svensk text (testbilden var svår — kvalitet kunde inte bedömas).
3. Visuell bekräftelse av Vista-stil folder-picker UX (CDP-verifierad men
   användarens UX-intryck värt en notering).

## Filer på USB du tar med dig

```
HANDOFF.md                ← entry point (du är klar med den nu)
BUGS.md                   ← klipp & klistra till issue-tracker
TESTPROTOCOL_STATUS.md    ← progress + återstår
CONTINUE.md               ← denna fil
beta-logs/                ← alla loggar + observations.md
probe-scripts/            ← Python CDP-probes (kräver venv + pip-installs)
export-evidence/          ← faktiska exportresultat från steg 2.7
```

## Frågor som kan komma upp

**"Var är Notescribbler-test (.scribbler-import)?"**
Lågprio #5/2.4c: Skipades pga ingen .scribbler-testfil i repo. Skapa en
eller hoppa.

**"Vad är `betatest2404`-projektet med Test123!?"**
Det användes i föregående runda. Lever bara på offline-maskinen. Återskapa
om du behöver — instruktioner ovan.

**"Varför CDP?"**
För att verifiera Electron IPC vs Flask-fallback för folder-picker utan
att be testaren klicka. CDP gav definitivt svar (electron.exe äger dialogen).

**"Är offline-maskinen klar att stänga?"**
Ja, efter att du städat processerna (se `TESTPROTOCOL_STATUS.md` §
"Bakgrundsprocesser"). Den behöver inte vara på.
