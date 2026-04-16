# Transcribbler — User Manual

## What is Transcribbler?

Transcribbler is a tool for qualitative data analysis (QDA). You can transcribe interviews, code text passages, build a codebook, and analyse your data — all in a single application. The software runs locally on your computer; no data leaves your machine.

---

## 1. Getting started

### 1.1 Create a project

1. Launch Transcribbler.
2. Select the **New project** tab.
3. Choose a folder where the project will be stored.
4. Enter a project name (e.g. "My interview study").
5. Enter your name in the **Your name (coder)** field — this identifies who is coding.
6. Click **Create project**.

### 1.2 Open an existing project

1. Select the **Open project** tab.
2. Choose the project folder or click one of the **Recent projects**.
3. Enter your coder name and click **Open**.

---

## 2. Adding material

### 2.1 Text files

Click **+ Transcript** in the top bar. Drag in or select files:
- **.txt**, **.md** — plain text
- **.docx**, **.odt** — formatted text (bold/italic preserved on import)

### 2.2 Audio files (automatic transcription)

Drag in audio files (.mp3, .wav, .m4a, .ogg, .flac etc.). Transcribbler transcribes automatically using Whisper:

- **Swedish**: KB-Whisper (recommended)
- **English**: OpenAI Whisper
- **Other languages**: Whisper with autodetect

**Speaker identification (diarization)**: Tick the checkbox if you want the app to distinguish between speakers. You can specify the number of speakers or let the app detect it automatically.

> Tip: The first time you use diarization, a Hugging Face token is required. The app will guide you.

### 2.3 Images (OCR)

Drag in images (.jpg, .png, .heic etc.). Transcribbler can extract text from images (OCR). On macOS it uses Apple Vision; on Windows/Linux it uses EasyOCR.

### 2.4 Notescribbler import

Files from Notescribbler (.scribbler, .nsenc) can be imported directly. You need the export password from Notescribbler.

### 2.5 Batch import

You can drag in multiple files at once — they are added as separate transcripts.

---

## 3. Managing transcripts

- **Rename**: Right-click the transcript in the list, select "Rename".
- **Categorize**: Right-click, select "Categorize" to group transcripts.
- **Memo**: At the bottom of the editor there is a memo field for notes about the transcript.
- **Edit text**: Click in the text and type to edit.
- **Formatting**: Select text and use Ctrl+B (bold) or Ctrl+I (italic).
- **Delete**: Right-click and confirm deletion.

---

## 4. Building a codebook

### 4.1 Create codes

1. Click the **+** button next to "Codebook" in the sidebar.
2. Enter a code name (e.g. "Collaboration").
3. Choose a colour.
4. Optional: select a parent code (theme) to create a hierarchy.
5. Optional: write a description.
6. Click **Save**.

### 4.2 Hierarchical codebook

Codes can be arranged in a tree: e.g. "Organisation" as a parent code with "Outcome" and "Ambition" as child codes. Numbering (1, 2, 2.1, 2.2) is automatic if enabled in settings.

### 4.3 Edit and delete codes

Click a code in the codebook to edit its name, colour, parent code, or description. You can also delete the code — note that annotations linked to it will lose their code.

### 4.4 Merge codes

Via the codebook menu you can merge two codes. All annotations from the source code are moved to the target code, and the source code is removed.

### 4.5 Filter codes

Use the search field above the codebook to quickly find codes in large codebooks.

---

## 5. Coding text

### 5.1 Basic coding

1. Open a transcript.
2. Highlight a text passage with the mouse.
3. A popup appears — search for or select a code.
4. Optional: write a memo, set weight (0–100), or mark as key passage.
5. Click **Code**.

Coded passages are shown with colour highlighting in the text.

### 5.2 Edit an annotation

Click a colour-highlighted passage to open the detail view. There you can:
- Edit the memo
- Change the weight
- Toggle key passage
- Change the code (click on the code name)
- Remove the annotation

### 5.3 Undo/Redo

Use Ctrl+Z / Ctrl+Shift+Z (Cmd on macOS) to undo or redo annotations. The history holds 200 steps.

### 5.4 Coding images (pins)

For image transcripts: enable "Place code pins" and click on the image to place a code pin. Drag a pin to move it.

---

## 6. Search

### 6.1 Search in transcript

Press **Cmd+F** (macOS) or **Ctrl+F** (Windows/Linux) to open the search bar. Navigate between matches with the arrow buttons.

### 6.2 Project search

Click **Project search** in the top bar to search all transcripts at once. Click a result to jump directly to the right location.

---

## 7. Analysis view

### 7.1 Open the analysis view

Click **Analysis view** in the top bar (next to Coding view) to switch views.

### 7.2 Select codes

In the codebook on the left: tick the codes whose excerpts you want to see. The number next to each code shows the annotation count. Use **All** / **None** to quickly select/deselect.

### 7.3 Display modes

- **Separate**: Excerpts are grouped by code, then by transcript, in chronological order.
- **Code-in-code**: Excerpts with overlapping codes are shown with code labels inline.

### 7.4 Filters and search

- **Search excerpts**: Filter excerpts with free text.
- **Memos**: Toggle to show/hide memos beneath excerpts.
- **Key passages**: Show only excerpts marked as key passages.

### 7.5 Export from the analysis view

1. Select codes in the codebook.
2. Click **Export** and choose a format:
   - **.docx** — Word document with colour-coded headings
   - **.odt** — OpenDocument format
   - **.md** — Markdown
   - **.csv** — For further analysis in R/Python/Excel
   - **.png** — Image

You can export all selected codes or enable **Export mode** to pick individual excerpts.

---

## 8. Statistics and matrices

### 8.1 Statistics

Click **Tools > Statistics**. Shows annotation counts and character counts per code, for the entire project or a single transcript.

### 8.2 Code matrix

**Tools > Code matrix**: a table with transcripts as rows and codes as columns. Exportable as CSV.

### 8.3 Code overlap

**Tools > Code overlap**: shows which codes overlap each other (co-occurrence). Exportable as CSV.

---

## 9. Collaboration

### 9.1 Multiple coders

Each coder works with their own coder name. Annotations are stored separately per coder and transcript.

### 9.2 Import a colleague's annotations

Click **Tools > Merge files** and paste the path to your colleague's .json annotation file.

### 9.3 Inter-rater reliability (IRR)

> *This feature is under development and not yet available in the interface.*

Computation of Cohen's kappa between two coders is planned for a future release.

---

## 10. Export the entire project

Click **Export** in the top bar. Choose a destination folder and one or more formats:

| Format | Content |
|--------|---------|
| CSV (all) | All annotations with metadata |
| CSV tidy | Format optimised for R/Python |
| Markdown — quotes per code | All coded excerpts grouped by code |
| Markdown — codebook | Codebook structure with annotation counts |
| Markdown — this transcript | Current transcript with code markings |
| QDPX (REFI-QDA) | For import into NVivo, ATLAS.ti etc. |

Exported files are automatically named with project name, date and time.

---

## 11. Settings

Click the gear icon in the top bar:

- **Code numbering**: Automatic hierarchical numbering (1, 2, 2.1 ...)
- **Alphabetical order**: Sort transcripts alphabetically
- **Segment weight**: Enable weight field (0–100) when coding
- **Waveform**: Show audio waveform for audio files
- **Language**: Swedish / English
- **Theme**: Dark / Light (can also be toggled on the start screen)

---

## Suggested workflow

### Phase 1: Preparation
1. Create a new project.
2. Build an initial codebook based on your research questions (deductive codes), or start without codes (inductive approach).

### Phase 2: Import and transcription
3. Drag in audio files — let Whisper transcribe.
4. Name speakers after transcription.
5. Review and proofread the transcripts.
6. Import any text files, images, or Notescribbler material.

### Phase 3: Coding (round 1)
7. Open the first transcript and read through it.
8. Start coding — highlight text, select or create codes.
9. Write memos for important insights.
10. Mark particularly telling passages as **key passages**.
11. Repeat for all transcripts.

### Phase 4: Codebook revision
12. Review the codebook — merge redundant codes, create hierarchies.
13. Check **Code overlap** to find codes that frequently co-occur.
14. Check **Statistics** to see the distribution of codes.

### Phase 5: Coding (round 2)
15. Go through the transcripts again with the revised codebook.
16. Fine-tune annotations and memos.

### Phase 6: Analysis
17. Switch to the **Analysis view**.
18. Select codes and study the excerpts — compare themes across transcripts.
19. Use **Code-in-code** to see overlapping annotations.
20. Filter by **Key passages** to collect the strongest quotes.
21. Export the analysis in your preferred format.

### Phase 7: Collaboration (optional)
22. Have a colleague code the same material with their own coder name.
23. Import the colleague's annotations.

### Phase 8: Final export
24. Export the entire project as CSV (for statistical analysis) or QDPX (for NVivo/ATLAS.ti).
25. Export selected analyses as .docx for the report.

---

## Keyboard shortcuts

| Shortcut | Function |
|----------|----------|
| Cmd/Ctrl + Z | Undo |
| Cmd/Ctrl + Shift + Z | Redo |
| Cmd/Ctrl + F | Search in transcript |
| Cmd/Ctrl + B | Bold |
| Cmd/Ctrl + I | Italic |
| A+ / A- | Change font size |

---

*Transcribbler — free to use and share, including professional use. Redistribution requires the same licence.*
