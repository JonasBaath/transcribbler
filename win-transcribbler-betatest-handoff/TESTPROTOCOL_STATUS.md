# Testprotokoll-status — Transcribbler v0.1.0-beta Windows-runda

**Sista körning**: 2026-04-25 ~09:30-20:10 (offline-maskin)
**HEAD**: `62cd1655c419264e858c63c8e5f323be30f301d3`

## Klart

| Fas/steg | Resultat | Kort |
|---|---|---|
| FAS 0 env + git pull + pip | OK (igår) | Python 3.11.9, Node v24, ffmpeg 8.1 |
| FAS 1 pip ML | OK (igår) | Allt satisfied — UTOM `transformers` (BUGG #2) |
| FAS 2 testfiler | OK (igår) | test_intervju.txt, test.docx, test_aao.txt |
| FAS 2.4b nsenc CLI-probe | SKIP | argparser saknas (lågprio #5) |
| FAS 4 npm install + start | OK (igår) | 13 sårbarheter, lockfile-drift kvar |
| Steg 2.2-2.6 (UI-flöden) | OK (igår) | Nytt projekt, importer, kodbok, annoteringar |
| Steg 2.7 Export | OK (idag) | Via Flask-API; alla 5 format. Folder-picker UI verifierad via CDP. |
| Steg 2.8 IRR | BUGG (#1) | Annoteringar OK, kappa-beräkning bryter |
| FAS 3 step 1 — clean shutdown | OK (idag) | Alla gårdagens PIDs döda |
| FAS 3 step 2-3 — port-kollision | BUGG (#3) | Två instanser binder båda 5050 |
| FAS 5 OCR | OK (idag) | EasyOCR end-to-end, text + boxes |
| FAS 5 Whisper sv | BUGG (#2) | NameError i model-conversion |
| FAS 5.3 diarization | SKIP | HF-token saknas |
| FAS 5.1 cache cleanup | EJ NÖDVÄNDIG (lågprio #10) | Auto-cleanup inbyggt |
| FAS 6 pytest | OK (igår) | 94 passed, 0 failed |
| Folder-picker UI/IPC | OK (idag) | CDP-verifierat, modal-attachad Electron-dialog |

## Återstår

### Måste-tester
Inga — alla "må"-tester är gjorda eller blockerade av buggar.

### Bör-tester
- [ ] **Whisper engelska-path** — verifiera att `language=en` route kringgår
  BUGG #2 (förväntat, ej testat). Driv via API:
  ```bash
  curl -X POST http://127.0.0.1:5050/api/transcripts/upload \
    -F "file=@tests/fixtures/test_audio.wav" \
    -F "language=en" \
    -F "name=whisper_en_test"
  # poll /api/jobs/<id>
  ```
- [ ] **OCR svensk text** — testbilden gav låg kvalitet på svenska tecken.
  Testa med en bild med tydlig svensk text.
- [ ] **Steg 2.7 native vs webb-dialog visuellt** — i Electron-läge bekräfta
  att dialogen är modern Vista-stil (bekräftat via CDP att den ÄR Electron-
  IPC-vägen, men användarens visuella UX-intryck värt en notering).

### Bekräftelse-frågor till utvecklaren
- [ ] Stryk steg 5.1 ur protokollet (lågprio #10)?
- [ ] 2.5 UX (kodbok-hopp) — bugg eller feature?
- [ ] .scribbler-testfil i repo, eller stryk 2.4c?
- [ ] system-info `ram_gb=null` — accepterat eller fix?

## Test-data som finns kvar

På offline-maskinen (ej på USB):
- `~/transcribbler/tests/fixtures/` — projekt "betatest2404" (krypterat med
  `Test123!`), 3 transkript, 5 koder, 4 Jonas-annoteringar + 2 betatestare-
  annoteringar (de senare skapade idag som setup för IRR-testet).
- `~/Desktop/transcribbler-export/` — 5 exporterade filer (kopia på USB:
  `export-evidence/`).
- `~/transcribbler/beta-logs/` — alla loggar (kopia på USB: `beta-logs/`).

OBS: betatestare-annoteringarna räknas som testdata. Vill du återställa
projektet till gårdagens originaltillstånd, ta bort
`tests/fixtures/annotations/c6c5edaa.betatestare.json`.

## Bakgrundsprocesser kvar på offline-maskinen

| PID | Process | Port | Åtgärd när du är klar |
|---|---|---|---|
| 15524 + 5 children | Electron CDP-mode | 53917 | `Stop-Process -Id 15524 -Force` |
| 10632 + 11100 | Bare Flask | 5050 | `Stop-Process -Id 10632 -Force` |

Kaskaderar ned till children automatiskt på Windows.
