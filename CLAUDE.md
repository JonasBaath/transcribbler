# Transcribbler — CLAUDE.md

## Vad projektet gör
Lokal macOS-webbapp för kvalitativ transkript-kodning. Användaren laddar in transkript (text eller ljud), skapar en kodbok med hierarkiska koder, markerar textpassager och kopplar dem till koder. Stödjer flera kodare per projekt och beräknar inter-rater reliability (Cohen's Kappa).

## Licens
© Jonas Bååth — [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Fri att använda och dela, även i yrkesarbete. Vidaredistribution kräver samma licens.

## Teknikstack
- **Backend**: Python 3.9+, Flask 3.x — enkelprocess, ingen databas
- **Frontend**: Vanilla JS (`"use strict"`), CSS custom properties, ingen build-step
- **Ljud**: faster-whisper (CTranslate2) + KBLab/kb-whisper-large (CT2/INT8) + pyannote.audio 3.x (diarisering)
- **Dokument**: python-docx, odfpy
- **Beroenden**: `requirements.txt` — installera i venv

## Köra projektet
```bash
cd transcribbler
source venv/bin/activate
python3 main.py          # öppnar http://127.0.0.1:5050 i webbläsaren
```
`--no-browser` stänger av auto-öppning (används av `.claude/launch.json`).

## Installera beroenden
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# ffmpeg krävs för Whisper: brew install ffmpeg
```

## Mappstruktur
```
main.py                  # Flask-app, alla routes, JOBS-store
core/
  project.py             # skapa/öppna projekt, add_transcript, add_audio_transcript
  annotation.py          # load/save annoteringar per kodare (char-offset)
  formatting.py          # bold/italic-spans per kodare
  codebook.py            # CRUD för koder (hierarkiskt träd)
  transcribe.py          # Whisper/KB-Whisper + Pyannote, modell-cachning
  export.py              # CSV, Markdown, DOCX, ODT-export
  stats.py               # kodanvändningsstatistik
  irr.py                 # Cohen's Kappa (character-level)
  merge.py               # slå ihop annoteringar från flera kodare
static/js/
  app.js                 # all frontend-logik (~2300 rader)
  translations.js        # i18n (sv/en), TRANSLATIONS-objekt + t() helper
static/css/style.css     # CSS custom properties för theme/layout
templates/index.html     # enda HTML-sida (SPA)
```

## Projektformat på disk
```
MyProject/
  project.json           # metadata, codes[], transcripts[], speakers[]
  transcripts/
    {tid}.txt            # extraherad klartext
    {tid}.mp3            # original ljudfil (om audio)
    {tid}_segments.json  # diariseringssegment [{speaker,start,end,text}]
  annotations/
    {tid}.{coder}.json   # annoteringar per kodare
    {tid}.{coder}.fmt.json  # bold/italic-spans per kodare
~/.transcribbler_recent.json   # senaste projekt (global)
~/.transcribbler_config.json   # HF-token för Pyannote (global)
```

Transkript-objekt i `project.json` kan ha ett valfritt `category`-fält (sträng) för kategorisering.

## State-modell
- `STATE = {folder, project, coder}` — in-memory, en session
- `JOBS = {}` — bakgrundsjobb för ljudtranskription (polling via `GET /api/jobs/<id>`)
- Annoteringar använder **char-offset** in i `.txt`-filen — råtext ändras aldrig
- `undoStack` / `redoStack` — in-memory per öppet transkript, nollställs vid `clearEditor()`
- `segments` / `segmentCharMap` — laddas asynkront för audio-transkript, används för klick-till-seek

## Frontend state-variabler (app.js topp)
Alla state-variabler **måste** deklareras längst upp i `app.js` för att undvika TDZ-fel. Aktuella variabler:

| Variabel | Typ | Beskrivning |
|---|---|---|
| `project` | object/null | Aktivt projekt |
| `currentTid` | string/null | Öppet transkript-id |
| `currentText` | string | Råtext för öppet transkript |
| `annotations` | array | Annoteringar för öppet transkript |
| `pendingSelection` | object/null | `{start, end, text}` — väntande markering |
| `pendingAnnId` | string/null | Id för annotation i redigering |
| `formattingSpans` | array | Bold/italic-spans för öppet transkript |
| `numberingEnabled` | bool | Kodträds-numrering |
| `transOrderEnabled` | bool | Alfabetisk etikett på transkript |
| `selectedTids` | Set | Multi-valda transkript-id:n |
| `_dragSelecting` | bool | True medan vänster musknapp hålls nere i listan |
| `_dragMoved` | bool | True när drag-markering nått ett andra element |
| `_categorizeTids` | array | Id:n som kategoriseras just nu |
| `searchMatches` | array | Träffar i aktiv sökning |
| `searchIndex` | number | Aktiv träff-index |
| `undoStack` / `redoStack` | array | Ångra/gör om (max `MAX_UNDO_DEPTH = 200`) |
| `segments` / `segmentCharMap` | array | Diariseringssegment + char-mapping |
| `_audioBatch` | array | `{jobId, name, speakers_found, voice_matches}` per väntande audio-fil i multi-fil-batch |
| `_audioCommitResolve` | function/null | Promise-resolver för obsolete per-fil-dialog (kept for cleanup) |
| `_sourceImgState` | object | `{tid: {open, boxesVisible}}` — per-transkript source image state |

## Transkriptionsmodeller

Alla backends använder **faster-whisper** (CTranslate2). `language_choice` styr modellval:

| Värde | Modell | Språk | Device |
|---|---|---|---|
| `"autodetect"` | `KBLab/kb-whisper-large` (CT2/INT8) | automatisk (detektion) | **CPU (tvingad)** |
| `"sv"` | `KBLab/kb-whisper-large` (CT2/INT8) | svenska (tvingad) | **CPU (tvingad)** |
| `"en"` | `openai/whisper-medium` (CT2, auto-dl) | engelska | CUDA/CPU |
| `"other"` | `openai/whisper-medium` (CT2, auto-dl) | `task="transcribe"`, ingen tvingad | CUDA/CPU |

Modellerna cachas i `_FW_MODEL_CACHE: dict` och `_DIAR_PIPELINE` i `core/transcribe.py` — laddas en gång per server-process. Transkript-metadata lagrar `model_label` (t.ex. `"KB-Whisper (svenska)"`) för visning i UI:t.

**KB-Whisper CT2-konvertering** (`_convert_kb_whisper_to_ct2`): Sker automatiskt vid första användning — läser från lokalt HF-cache, konverterar till `~/.cache/transcribbler/kb-whisper-ct2/` (INT8, ~1.4 GB, ~30 s engångskostnad). Efterföljande anrop är omedelbart (konverterad modell finns på disk). `_load_faster_whisper_model()` kontrollerar `(ct2_path / "model.bin").exists()` och anropar konverteringen vid behov.

### ⚠️ KRITISKT: KB-Whisper-large + MPS = trasigt (kvarstår med CTranslate2)

KB-Whisper körs fortfarande på **CPU** (tvingat) — `device="cpu"` i `_load_faster_whisper_model()`. Bakgrund: transformers Whisper-pipelinen på Apple Silicon MPS producerade **garbage-output** för KB-Whisper-large på audio > 30 sekunder (devlog 2026-04-08). CTranslate2:s MPS-backend är oprövat för just denna modell. CPU-hastighet med CTranslate2/INT8 på M-serien: **~4–6× realtid** (vs ~1.7× med transformers segment-level, ~5.1× med word-level). En 10 minuters fil tar ~2 min (vs ~17–51 min tidigare). CUDA fortfarande tillåtet för `en`/`other` (Linux/Windows).

### Alignment-strategi (Whisper-driven, word-level precision)

Sedan 2026-04-10 körs faster-whisper med `word_timestamps=True` alltid för diarisering:

1. faster-whisper + VAD producerar ord-för-ord tidsstämplar via CTranslate2
2. Varje ord → `_speaker_runs()` hittar pyannote-talare som överlappar ordets tidsintervall
3. Om ett "word" (eller segment) spänner över talarbyte → text splittas **proportionellt** vid ord-gränser
4. Gap-fill: tidsluckor ≥ 3s → `[ohörbart MM:SS:HH – MM:SS:HH]`-rader infogas
5. Consecutive rader med samma talare slås ihop

Word-level är nu standard (inte ett opt-in) — faster-whisper word timestamps är ~2× snabbare än transformers word-level. Checkboxen "Exakt talaruppdelning (word-level)" i UI:t är numera obsolet men kvar i dialog-koden.

`_looks_like_garbage()` filtrerar bort spurious Whisper-output (< 2 tecken, eller bara punktuering) — fångar hallucinationer som `"!"` på brusigt ljud.

`[ohörbart]`-rader renderas utan speaker-prefix (bara `[ohörbart 01:42:57 – 02:15:33]`), till skillnad från vanliga rader (`[Jonas]: ...`). Frontend `buildSegmentCharMap` speglar detta exakt.

**ECAPA gränskorrigering (`_refine_speaker_boundaries`)**
Körs automatiskt i Stage 2b direkt efter pyannote-diariseringen, innan Whisper. Strategi: bygg referensembeddings från långa (≥ 1s) segment → för varje kort segment (< 1.5s) extrahera ECAPA-embedding → omtilldela om annan talare är ≥ 0.10 cosine-enheter närmre. Fångar gränsprecisionsfel ("Ja", "samla", "också" till fel talare). Re-mergar intilliggande segment efter omtilldelning. Loggar varje omtilldelning på INFO-nivå (`boundary_refinement`). Hoppar över om < 2 talare har långa segment.

**Pyannote** (fortsätter på MPS)
Kräver HF-token sparad i `~/.transcribbler_config.json`. Token valideras mot HF API vid inmatning. Guarded med `ImportError` om paketet saknas. Pipeline cachas globalt i `_DIAR_PIPELINE`; flyttas till MPS via `.to(torch.device("mps"))` efter `Pipeline.from_pretrained()` — diarisering går på ~0.17× realtid. Trösklar sätts om per anrop; pyannote 3.1 powerset-segmentation har ingen `threshold` så `_load_diarization_pipeline()` har try/except som droppar segmentation-threshold om den försöker sättas.

**ECAPA-TDNN (SpeechBrain)** (MPS med CPU-fallback)
`_load_ecapa_model()` försöker MPS först, faller tillbaka till CPU tyst vid fel. `extract_speaker_embeddings()` filtrerar bort segment med placeholder-talare `"—"` för att inte slösa tid på brus.

**PyTorch 2.6 compat**
`_patch_torch_load()` i `core/transcribe.py` tvingar `weights_only=False` på både `torch.load` OCH `torch.serialization.load` (lightning_fabric bypasser den första). Använder ren tilldelning (`kwargs["weights_only"] = False`), inte setdefault, eftersom lightning_fabric skickar True explicit. Plus `torch.serialization.add_safe_globals([TorchVersion])` som belt-and-suspenders.

**Python 3.9-kompatibilitet**
`core/transcribe.py` har `from __future__ import annotations` överst — krävs för `X | Y` union-syntax i type hints med Python 3.9.

## Audio-sync (klick-till-seek)
När ett audio-transkript öppnas:
1. `GET /api/transcripts/<tid>/segments` hämtar diariseringssegmenten asynkront.
2. `buildSegmentCharMap(segs)` mappar varje segment till ett tecken-intervall i `.txt`-filen (speglar serverns text-konstruktion: `"\n".join(f"[{spk}]: {txt}" ...)`).
3. Klick i transkribt-texten (utan selektion) → `charOffsetToTime()` → `audio.currentTime = t; audio.play()`.

## Ångra/gör om (undo/redo)
- `undoStack` / `redoStack` — varje post: `{type: "add"|"delete", tid, ann}`.
- Hjälpfunktioner `pushUndo(a)` / `pushRedo(a)` — cap på `MAX_UNDO_DEPTH = 200` via `.shift()`.
- Ny annotation pushes till `undoStack`, rensar `redoStack`.
- Borttagen annotation pushes till `undoStack`, rensar `redoStack`.
- `Ctrl/Cmd+Z` anropar `undo()`, `Ctrl/Cmd+Y` eller `Ctrl/Cmd+Shift+Z` anropar `redo()`.
- Stacks nollställs i `clearEditor()` och är per öppet transkript (`action.tid !== currentTid` ignoreras).

## Sökfunktioner

**In-transcript sökning**
- Aktiveras via `Cmd/Ctrl+F` eller högerklick → "Sök" i transkribt-listan.
- `#search-bar` är ett **direkt barn till `<main id="editor-pane">`** (scrollcontainern) för att `position: sticky` ska fungera.
- `top: -28px` + `margin: -28px -36px 0` motverkar editor-panelens 28px top-padding — håller sökfältet klistrat längst upp utan synlig text ovanför.
- `clearSearch()` döljer fältet; `openSearch()` visar och fokuserar det.

**Projektsökning**
- Knapp `#btn-project-search` i topbaren öppnar `#modal-project-search`.
- `GET /api/search?q=` — servern letar igenom alla transkripts `.txt`-filer.
- Svar: `{results, total_matches, query}`. Varje resultat har `snippet` och `snippet_match_start` (offset in i snippet) för frontend-highlighting.
- Auto-sökning: debounce 300ms, triggas vid ≥ 3 tecken.
- Modalen är fast positionerad vid överkanten (`align-items: flex-start`, `padding-top` = topbar-höjd + marginal).

## Transkript-kategorisering
- Cmd/Ctrl+klick i sidopanelen togglar item i `selectedTids` utan att ladda transkriptet.
- Vänster musknapp nedtryckt + flytta pekaren över fler items = drag-select (via `mouseover`-delegation på `#transcript-list`).
- Klick utanför listan rensar `selectedTids`.
- Högerklick → "Kategorisera" öppnar `#modal-categorize`: fritext-input med `<datalist>` av befintliga kategorier, "Spara" / "Ta bort kategori" / "Avbryt".
- Backend: `PATCH /api/transcripts/categorize` med `{tids: [...], category: str|null}`.
- Sidebar renderas med sorterade kategori-rubriker, okategoriserade sist under "—"-separator.
- `renderTranscriptList()` hanterar all gruppering; DOM-uppdateringar under drag görs direkt (utan full re-render) för att bevara event-lyssnare.

## Topbar-layout
```
[Logo] [Projektnamn]  [⚙] [Export] [Verktyg ▾] [Projektsök]    [EN] [☀] [Byt projekt]
                                                           ← spacer →
```
- `#coder-badge` är **absolut positionerad** i `#topbar` (`position: relative`) — visas vid vänstersidans kant.
  - `left: calc(var(--left-w, 220px) - 14px)` + `transform: translate(-100%, -50%)` + `top: 50%`
  - Dess högra kant ligger i linje med Import-knappens högra kant i sidopanelen.
  - `--left-w` sätts på **både `#workspace` och `document.documentElement`** i resize-handlern (`onMove`) — krävs eftersom `#topbar` och `#workspace` är syskon och CSS-variabler inte propagerar uppåt.
- **"Import"-knappen** (`#btn-add-transcript`, klass `btn-sidebar-import`) ligger i `.sidebar-header` i `#sidebar-left` — inte i topbaren.
- **Export** — öppnar `#modal-export` (mapp-väljare via `GET /api/pick-folder` + format-checkboxar), skriver direkt till disk via `POST /api/export/to-folder`.
- **Verktyg ▾** — Statistik, IRR, Kodträd, Slå ihop filer.
- Dropdowns använder click-to-toggle (`.open`-klass via JS, inte `:hover`) — undviker hover-gap-problemet.
- `closeAllDropdowns()` kallas från document-click-lyssnaren (stänger vid klick utanför).
- Inställnings-popover (`#settings-wrap`) ligger omedelbart efter `#btn-add-transcript` i DOM.

## Viktiga kodmönster

**JS: variabeldeklarationer**
Alla `let`/`const` som används av funktioner som anropas tidigt (t.ex. från `loadTranscript` eller `enterApp`) **måste** deklareras längst upp i `app.js` (runt rad 10–50). TDZ-fel har orsakat buggar flera gånger — lägg alltid ny state-variabel överst.

**JS: nya DOM-element**
Event-lyssnare på element som inte finns i gammal cachad HTML ska använda `?.addEventListener(...)` för att vara defensiva.

**JS: drag-select**
`e.preventDefault()` på `mousedown` i en lista **undertrycker** efterföljande `click`-event — använd det aldrig för detta. Förhindra text-selektion under drag med CSS `user-select: none` på list-items istället.

**Cache-busting**
`app.js` och `translations.js` laddas med `?v=N` i `index.html`. Öka N vid JS/translations-ändringar. Aktuella versioner: **app.js v=56**, **translations.js v=18**. Flask serverar alltid färskt innehåll (`SEND_FILE_MAX_AGE_DEFAULT=0`), men webbläsarens HTML-cache kräver **Cmd+Shift+R** efter HTML-ändringar.

**CSS-variabelpropagering (`--left-w`, `--right-w`)**
Panelbredder sätts i `initResizablePanels`. Eftersom `#topbar` och `#workspace` är syskon (inte förälder/barn) propagerar variabler satta på `#workspace` **inte** till `#topbar`. Lösning: sätt alltid på **båda** `workspace` och `document.documentElement` i `onMove` (drag) och vid initial laddning från localStorage.
```js
workspace.style.setProperty("--left-w", w + "px");
document.documentElement.style.setProperty("--left-w", w + "px");
```

**Audio-upload-flöde (multi-fil batch, sedan 2026-04-08)**
Text/DOCX → synkront svar `{ok, project}`. Ljud → asynkront `{job_id}`, frontend pollar `GET /api/jobs/<id>` var 2:a sekund. `settings.language_choice` skickas med och avgör modellval.

**Multi-fil audio:** Upload-loopen i `btn-trans-confirm` samlar varje fils resultat i `_audioBatch[]` istället för att öppna per-fil-talardialog. Efter hela loopen öppnas `#modal-batch-speakers` med alla filer synliga samtidigt (en scrollbar sektion per fil, voice-profile-matchningar förifyllda). Två knappar:
- **"Spara alla"** (`btn-batch-spk-save`) — commit:ar alla filer i sekvens via `commitBatchSpeakers()` med progress-räknare `"Sparar fil X/N"`, retry vid fel (misslyckade filer ligger kvar i `_audioBatch` för nästa försök).
- **"Spara med standardnamn"** (`btn-batch-spk-skip`) — commit:ar alla med tom speaker-map (behåller `SPEAKER_XX`-namn).

Designen stödjer obevakad körning över natten: starta batchen på kvällen, allt transkriberas i bakgrunden, batch-dialogen väntar i morgon. Efter commit kan talare döpas om via befintlig rename-funktionalitet.

**Speaker-attribution:** För varje Whisper-segment körs `_speaker_runs()` som returnerar pyannote-talare i ordning, med consecutive same-speaker-runs ihopslagna. Om ett Whisper-segment spänner över en talarbyte splittas texten proportionellt efter tidsfraktion, med splits vid ord-gränser. Detta fångar fall som "Rosa säger 'Solid base' kort innan Jonas tar över" korrekt.

**i18n — två språkväxlarknappar**
Det finns `#btn-lang` (topbar) och `#btn-lang-splash` (splash). `applyTranslations()` i `translations.js` uppdaterar båda. Glöm inte detta vid framtida tillägg av language-relaterad UI.

## Logotyp & varumärke

**SVG-logon** (`static/img/logo.svg` + inline i `index.html`) föreställer ett vågformsdiagram (horisontell baslinje + 6 vertikala staplar) som "upplöses" i pixelblock åt höger — en visuell metafor för tal→text. Färg styrs via CSS:
```css
.splash-logo-img line { stroke: var(--accent); }
.splash-logo-img rect  { fill: var(--accent); }
#topbar-logo line { stroke: var(--accent); }
#topbar-logo rect  { fill: var(--accent); }
```
`currentColor` på SVG-barn fungerar inte tillförlitligt i Firefox — använd alltid CSS-selektorer mot barn-elementen.

**Typografi** — logotexten är uppdelad med `<span>` i HTML:
```html
<h1><span class="brand-trans">tran</span><span class="brand-scrib">scribbler</span></h1>
```
- `.brand-trans` → `font-weight: 700` (fet)
- `.brand-scrib` → `font-weight: 300` (tunn)

Delningspunkten är **tran | scribbler** (inte "trans"), så att "s" hamnar på den tunna sidan.

## Designval: Ingen AI-assisterad kodning

**AI-assisterad kodning implementeras inte i Transcribbler. Detta är ett avsiktligt designbeslut, inte en teknisk begränsning.**

Motivering:
1. **Kvalitativ epistemologi** — Kvalitativ kodning bygger på forskarens tolkande process. AI-förslag riskerar att styra kodaren snarare än tvärtom (confirmation bias). Forskarens aktiva val *är* metoden.
2. **Transparens och reproducerbarhet** — AI-modeller är versionsspecifika och svårreproducerbara. Metodredovisning i akademiska texter kräver att kodningsprocessen kan beskrivas oberoende av proprietära system.
3. **Offline-first och integritet** — Externa AI-API:er kräver nätverksåtkomst och exponerar känsliga transkriptdata (personuppgifter, intervjusvar) för tredje part. Transcribbler körs helt lokalt av integritetsskäl.
4. **Pedagogisk princip** — Verktyget riktar sig till studenter och forskare som ska *lära sig* kvalitativ kodning. AI-förslag motverkar det inlärningsmålet.

Om detta designval ifrågasätts i framtiden: Beslutet togs 2026-04-10 och gäller tills vidare. Argumenten ovan ska vägas mot eventuella motargument innan något ändras.

## Kända quirks
- Bara ett projekt öppet åt gången per server-process
- `variable shadowing`: använd aldrig `t` som loop-variabel — det skuggar `t()` (i18n-funktionen)
- Firefox cachar HTML aggressivt — hard refresh (Cmd+Shift+R) krävs ofta vid utveckling
- **Använd ALDRIG `preview_start` eller andra preview-verktyg** — de fungerar inte för det här projektet (macOS TCC-sandbox saknar åtkomst till Documents-mappen) och slösar bara tokens. Kör alltid servern manuellt: `python3 main.py`
