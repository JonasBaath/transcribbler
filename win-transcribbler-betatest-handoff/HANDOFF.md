# Transcribbler betatest — handoff

**Skriven**: 2026-04-25 av Claude (sessionsmaskin: SLU beta-test-box, offline)
**Repo HEAD vid test**: `62cd1655c419264e858c63c8e5f323be30f301d3`
**Senaste branch**: oklar (offline-maskin, ej pushat).

## Mappstruktur

```
transcribbler-betatest-handoff/
├── HANDOFF.md            ← du läser detta nu
├── BUGS.md               ← buggrapporter, klara att skicka in / fixa
├── TESTPROTOCOL_STATUS.md ← vad är gjort / vad är kvar
├── CONTINUE.md           ← hur du tar upp testet på den nya maskinen
├── beta-logs/            ← kopia av alla loggar från denna runda
│   ├── observations.md      (alla 13 observationer i kronologisk ordning)
│   ├── RESUME.md            (handoff-doc m/ åtgärdslista)
│   ├── 7_*.log              (export-runda)
│   ├── 8_*.log              (port-kollisionstest)
│   ├── 9_*.log              (CDP-runda för folder-picker)
├── probe-scripts/        ← Python-skript för att verifiera UI/IPC på ny maskin
│   ├── cdp_probe.py
│   ├── cdp_dialog_probe.py
│   ├── enum_windows.py
│   ├── dismiss_dialog.py
└── export-evidence/      ← exportresultat från steg 2.7 (5 filer)
```

## TL;DR

**4 buggar hittade. 3 kritiska, 1 hög. Detaljer i `BUGS.md`.**

| # | Bugg | Allvar | Fil:rad | Storlek |
|---|---|---|---|---|
| 1 | IRR krash på krypterade projekt | Kritisk | main.py:1613 | 1-rad-fix |
| 2 | Whisper sv-path saknar `transformers` | Kritisk | requirements-ml.txt | 1 ny rad |
| 3 | Port-kollision tyst på Windows | Hög | main.py:2360 | Werkzeug-flagga |
| 4 | project.modified bumpas inte vid annotering | Medel | core/annotation.py | Småfix |

Plus 4 mindre observationer / städ-frågor — se `BUGS.md` sektion "Lågprio".

## Hur du fortsätter på nästa maskin

Läs **`CONTINUE.md`** först. I korthet:
1. Klona repo + skapa venv + `pip install -r requirements-ml.txt`.
2. Återskapa testprojekt (eller använd "betatest2404" från offline-maskinen om du flyttar `tests/fixtures/` också — men det ingår INTE i denna USB).
3. Återstående UI-flöden: 2.5 UX-uppföljning, 5.1 cache-bekräftelse, ev. Whisper-engelska.
4. Fixa buggar lokalt → `pytest` → commit.

## Backstory

Detta är en autonom test-runda fortsatt från **2026-04-24**. Föregående runda
nådde steg 2.6, pausade vid 2.7. Denna runda (2026-04-25) körde:

- Steg 2.7 Export — via Flask-API (UI/IPC ej testad i den runda)
- Steg 2.8 IRR — annoteringar OK, IRR-endpoint kraschar (BUGG #1)
- FAS 3 port-kollision — multibind upptäckt (BUGG #3)
- FAS 5 OCR — ✓ end-to-end
- FAS 5 Whisper — kraschar i model-conversion (BUGG #2)
- Folder-picker UI verifierat via CDP — ingen bugg, bridgen funkar.

Allt arbete skedde på offline-maskinen utan internetåtkomst. Inga ändringar
i källkoden — bara observation, dokumentation, och test-data.
