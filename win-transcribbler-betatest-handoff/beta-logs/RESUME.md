# Betatest Windows 2026-04-25 — RESULTAT

## Status: AUTONOM RUNDA KLAR + folder-picker UI verifierat via CDP

## Nästa steg för dig (prioritetsordning)

### 1. Fixa kritiska buggar (eller lämna in mot utvecklaren)
- [ ] **IRR krash på krypterade projekt** — main.py:1613, lägg till `key=_key()` (1 rad).
- [ ] **Whisper svensk-path saknar transformers** — `requirements-ml.txt` + `transformers>=4.40`.
- [ ] **Port-kollision tyst på Windows** — `allow_reuse_address=False` på Werkzeug-servern eller pidfile-lås.

### 2. Bekräfta tre städ-frågor
- [ ] Stryka **steg 5.1 cache-rensning** ur testprotokollet (auto-cleanup gör det redundant).
- [ ] Bestämma om **steg 2.5 UX** (kodbok hoppar till kodningsvy) är ett UI-jobb eller "fungerar som tänkt".
- [ ] Lägga upp en `.scribbler`-testfil i repo eller gitignorera 2.4c-steget.

### 3. Valfritt: kör ytterligare tester
- [ ] Whisper engelska-path (`language=en` upload) — kan jag driva via API om du säger till.
- [ ] OCR på en bild med svensk text (test-bilden gav låg kvalitet).

### 4. Städ av testkörningen
Bakgrundsprocesser kvar (kan dödas när du är klar):
- Electron CDP-mode (PID 15524 + 5 children) → Flask 53917
- Bare Flask (PID 10632 + 11100) → 5050

Stäng allt: `Stop-Process -Id 15524, 10632 -Force` (cascade dödar children).


## Klart denna runda (utöver gårdagens)

| Fas/Steg | Resultat | Anteckning |
|---|---|---|
| FAS 0 restart | OK | Electron+Flask spawnar igen på 53917. HEAD = 62cd165 (oförändrat). |
| FAS 3 step 1 | OK | Verifierade att gårdagens electron+python-PIDs är döda (clean shutdown). |
| Steg 2.7 Export | OK (via API) | Alla 5 format skrivna; CSV/MD/QDPX-innehåll verifierat. UI-IPC-test ej täckt. |
| Steg 2.8 IRR | BUGG | Annoteringar skapade som `betatestare`. IRR-endpoint kraschar på krypterade projekt — saknar `key=_key()` i main.py:1613. |
| FAS 3 step 2-3 | BUGG | Två bare `python main.py` binder båda 5050 (SO_REUSEADDR på Windows). Ingen kollisionssignal. |
| FAS 5 OCR | OK | EasyOCR-pipelinen funkar end-to-end, text + bounding boxes returneras. |
| FAS 5 Whisper | BUGG | NameError 'transformers' i ctranslate2 — `transformers` saknas i requirements-ml.txt. |
| FAS 5 Diarization | SKIP | HF-token saknas (förväntat). |
| FAS 5.1 cache | INTE NÖDVÄNDIGT | Auto-cleanup av partial cache redan inbyggt. |

## Buggar att fixa (prioritet)

### Kritisk
1. **IRR krash på krypterade projekt** — main.py:1613, lägg till `key=_key()`.
2. **Whisper svensk-path saknar transformers** — lägg till `transformers>=4.40` i requirements-ml.txt.

### Hög
3. **Port-kollision tyst på Windows** — sätt `allow_reuse_address=False` på Werkzeug-servern eller använd pidfile.
4. **project.modified bumpas inte vid annotering** — påverkar dirty-check / recent-sortering.

### Låg / dokumentations-städ
5. **`core.nsenc` saknar argparser** — gårdagens fynd, fortfarande oöppnat.
6. **electron/package-lock.json drift vid npm install** — gårdagens regression.
7. **tests/fixtures/project.json skapas av pytest** — gitignore eller tmpdir.
8. **Flask Electron-spawn på dynamisk port** vs protokollets 5050-polling — uppdatera dokumentation.
9. **system-info `ram_gb=null`** — nytt fynd, RAM-detektion fungerar inte på denna maskin.
10. **FAS 5.1 cache-rensningssteg redundant** — ta bort ur testprotokoll.

## Inte täckt — kräver dig

- ~~**Steg 2.7 folder-picker UI-test**~~ — VERIFIERAT runtime via CDP. Dialog-fönstrets
  ägar-process = `electron.exe` (inte `powershell.exe`), modal-attachad till
  transcribbler-huvudfönstret. IPC-bridgen fungerar end-to-end. ✓
- **Steg 2.5 UX-uppföljning** — kontrollera om utvecklaren vill att kodbok-vyn ska stanna kvar efter "lägg till kod".
- **Whisper engelska-path** — verifiera att `language=en` route kringgår transformers-buggen (kan jag driva via API om du säger till).
- **Cache-rensning ~1.4 GB** — RESUME.md flaggade "kräver OK" men auto-cleanup gör det överflödigt; bekräfta.

## Kvarvarande processer

| PID | Process | Port |
|---|---|---|
| 14476, 9124 + 4× electron (6860, 9068, 13984, 15380) | Electron-spawnad Flask | 53917 |
| 10632, 11100 | bare python main.py (FAS 3 instans #1, kvar för FAS 5) | 5050 |

Du kan döda allt eller fortsätta direkt. Båda Flask:erna har projektet öppet
(53917: coder=betatestare; 5050: coder=betatestare).

## Filer

- `beta-logs/7_npm_start.log` — Electron-uppstart denna runda + IRR-traceback.
- `beta-logs/7_export.log` — export-API-resultat + filverifiering.
- `beta-logs/8_flask1.log` — bare Flask #1 (port 5050, även Whisper-traceback).
- `beta-logs/8_flask2_collision.log` — bare Flask #2, identisk uppstartslogg trots multibind på 5050.
- `beta-logs/observations.md` — alla observationer (uppdaterad).
- `~/Desktop/transcribbler-export/` — export-output (5 filer från betatest2404).
- `tests/fixtures/annotations/c6c5edaa.betatestare.json` — nya betatestare-annoteringar (2 st).
