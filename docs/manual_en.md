# Transcribbler — User Manual

## What is Transcribbler?

Transcribbler is a tool for qualitative data analysis (QDA). You import transcripts, code passages of text, build a codebook and analyse your material — all in one application. It runs locally on your computer, and project data is not sent anywhere. (Exception: PNG export downloads a helper library from the internet, but no project data is sent.)

Automatic audio transcription is available as an option but is switched off by default (see section 2.3).

### Language

The application starts in Swedish if your computer's language is Swedish, and in English otherwise. You can switch language at any time with the **EN**/**SV** button at the top right (also on the start screen). Your choice is remembered. The language also determines error messages, headings in exported documents and file names.

---

## Installation

Download the latest version from GitHub:

https://github.com/JonasBaath/transcribbler/releases

Choose the file for your operating system under **Assets**. Everything you need is included in the app; you do not need to install Python or anything else. Once installed, the app takes up about 2.5 GB on Windows and 1.7 GB on macOS.

| System | File |
|--------|------|
| macOS with Apple silicon (M1–M4) | `Transcribbler-<version>-arm64.dmg` |
| macOS with an Intel processor | `Transcribbler-<version>.dmg` (without `arm64`) |
| Windows 10/11 | `Transcribbler.Setup.<version>.exe` |
| Linux | `Transcribbler-<version>.AppImage` |

Not sure which Mac you have? Choose  → **About This Mac**. If it says "Chip: Apple M…", you have Apple silicon.

The app is not signed by Apple or Microsoft, so your system will warn you the first time you open it. This is expected; follow the steps below.

### macOS

1. Double-click the .dmg file and drag **Transcribbler** into the **Applications** folder.
2. Open Transcribbler from **Applications**. A message says that Apple cannot check the app. Click **Done** (or **Cancel**).
3. Open **System Settings → Privacy & Security**, scroll down and click **Open Anyway** next to Transcribbler. Confirm with your password.
4. From then on, the app opens as normal.

On macOS 14 and earlier, it is enough to right-click the app, choose **Open** and click **Open** in the dialogue.

If macOS says the app is "damaged", open Terminal and run `xattr -cr /Applications/Transcribbler.app`. Then open the app again.

### Windows

1. If your browser warns that the file is not commonly downloaded, keep it. In Edge: choose **…** next to the file, then **Keep**, **Show more** and **Keep anyway**.
2. Double-click the .exe file.
3. If "Windows protected your PC" appears, click **More info** and then **Run anyway**.
4. The installation runs automatically and the app starts when it has finished. You will then find it in the Start menu.

### Linux

1. Make the file executable: right-click → **Properties** → allow executing as a program, or run `chmod +x Transcribbler-*.AppImage` in a terminal.
2. Start it by double-clicking or with `./Transcribbler-<version>.AppImage`.

If it does not start on Ubuntu 22.04 or later, FUSE is needed: `sudo apt install libfuse2` (on Ubuntu 24.04: `libfuse2t64`).

### First start

It may take a few seconds before the start screen appears. The app uses your computer's language if it is Swedish, and English otherwise; switch with **EN**/**SV** at the top right.

On Windows, the very first start can take several minutes while the computer checks the app's files. If "Could not start the Flask server" appears, click **OK** and start Transcribbler again; the next start is faster.

---

## 1. Getting started

### 1.1 Create a project

1. Start Transcribbler and choose the **New project** tab.
2. Choose a folder in which to save the project.
3. Give the project a name under **Project name**.
4. Enter your name in **Your name (coder)**. The name identifies your annotations and may only contain letters, digits, spaces, hyphens and underscores (no full stops).
5. Optionally, tick **Encrypt project** and choose **Standard password** (at least 8 characters) or **Strong passphrase** (a generated phrase; **New phrase** generates another, **Copy** copies it). Save the password — it cannot be recovered.
6. Click **Create project**.

### 1.2 Open an existing project

1. Choose the **Open project** tab.
2. Choose the project folder, or click a project under **Recent projects**.
3. Enter your coder name and click **Open**. If the project is encrypted, enter the **Project password**.

### 1.3 The Recent projects list

The cross (✕) next to a project opens a dialogue with two options:

- **Remove from list** — the project is only removed from the list. No files are deleted.
- **Delete the project permanently** — deletes the project file, transcripts and annotations. You must first tick **I understand this cannot be undone**. Exported files in the folder are kept.

### 1.4 Switching projects and renaming a project

- **Switch project** in the top bar takes you back to the start screen.
- Double-click the project name in the top bar to rename the project.

---

## 2. Adding material

Click **Import** at the top of the **Transcripts** sidebar on the left. The **Add transcript** dialogue opens. Drag files into the dialogue or click to select them, then click **Add**. You can add several files at once; each becomes a separate transcript. The **Name** field is only used if you select a single file.

### 2.1 Text files

- **.txt** — plain text.
- **.md** — Markdown. Markup (headings, bold, links) is removed, leaving plain text. The YAML header is read: `title` (and `date`) becomes the transcript name, `category` becomes the category and `tags` become tags (see 3.4).
- **.docx**, **.odt** — bold and italic formatting is preserved. Text in tables is imported row by row, with cells separated by a tab, so that speaker and utterance stay on the same line.

### 2.2 Images (OCR)

Images (.jpg, .png, .heic, etc.) can be imported. With **Extract text from image (OCR)** ticked (the default), the text is recognised: with Apple Vision on macOS and EasyOCR on Windows and Linux. If you untick it, the image is imported for coding with code pins only (see 5.5).

### 2.3 Audio files

Automatic transcription is switched off by default, as the course works with ready-made transcripts. Audio files therefore cannot be added. Transcripts that already have audio (for example, ones prepared by the course leader) can be played back: click in the text to play from that point, and the spacebar plays and pauses.

*For course leaders: transcription is enabled with `"enable_whisper": true` in `~/.transcribbler_config.json` (or the environment variable `TRANSCRIBBLER_ENABLE_WHISPER=1`). The first run downloads a speech-recognition model of about 3 GB.*

### 2.4 Notescribbler

Files from Notescribbler can be imported: **.scribbler** and **.nsenc** (encrypted; you need the export password) and **.zip** (unencrypted export, imported as plain text).

---

## 3. Managing transcripts

Click a transcript in the list to open it. Cmd/Ctrl-click to select several (for categorising and tagging).

### 3.1 Renaming, memos and searching

- **Rename**: click ✎ next to the transcript title in the editor.
- **Memo**: right-click the transcript in the list and choose **📝 Memo**. The note belongs to the whole transcript.
- **Search**: right-click and choose **🔍 Search** to open the transcript with the search bar.

### 3.2 Editing text and formatting

- **Edit text**: click ✎ **Edit text** in the toolbar. The text opens in an editing field with **Save**/**Cancel**. If the transcript already has annotations, you are warned that their positions may shift.
- **Bold/italic**: select text and click **B** or **I** in the toolbar. Click formatted text to remove the formatting.
- **Readability**: **A−**/**A+** change the font size and **Sans**/**Serif** the typeface.

### 3.3 Categorising

Right-click and choose **📁 Categorise**. Transcripts with the same category are grouped in the list. **Remove category** removes the grouping.

### 3.4 Tagging

Tags describe characteristics of the transcripts, such as "teacher", "pupil" or "school A". A transcript can have several tags.

1. Select one or more transcripts, right-click and choose **🏷️ Tag**.
2. Type a tag under **Add tag…** and click **Add** (or press Enter). Existing tags are suggested as you type.
3. Remove a tag with the ✕ on the tag. **(partial)** means that only some of the selected transcripts have the tag.
4. Click **Done**.

Tags are shown in the transcript list and are used to filter the Analysis view (see 7.3).

### 3.5 Order and deletion

- Drag the ⋮⋮ handle to change the order.
- **Letter labels for transcripts** (Settings) puts A., B., C. … in front of the names. The labels follow the order and are used in the Analysis view and in exports.
- Delete a transcript with the ✕ on its row. The transcript and all its annotations are deleted, for every coder. This cannot be undone.

---

## 4. Building a codebook

The codebook is in the right-hand sidebar.

### 4.1 Creating codes

1. Click **+** (**New code**) in the **Codebook** sidebar.
2. Give the code a name and choose a colour.
3. Optionally, choose a **Parent code (theme)** to build a hierarchy.
4. Optionally, add a **Description**. It is shown when you hover over the code.
5. Click **Save**.

You can also create a code while coding (see 5.1).

### 4.2 Hierarchy and numbering

Codes can be arranged in a tree, e.g. "Organisation" with the child codes "Results" and "Ambition". With **Code numbering** switched on in Settings, codes are numbered automatically (1, 2, 2.1, 2.2 …).

### 4.3 Editing, renaming and deleting

- Click ✎ on the code's row to open **Edit code** (name, colour, parent code, description).
- Right-click a code and choose **✏️ Rename** to change only its name.
- **Delete code** (in **Edit code**) deletes the code **and every annotation with that code, for all coders**. Child codes move up one level. This cannot be undone.

### 4.4 Merging codes

**Tools ▾ → Codebook → Merge codes**. Choose the **Source code (removed)** and the **Target code (kept)**, then click **Merge**. All annotations are moved to the target code for every coder, the source code's child codes are moved under the target, and the source code is deleted. This cannot be undone.

### 4.5 Filtering codes

Type in **Filter codes…** above the codebook to find codes in a large codebook.

### 4.6 The Codebook and Code tree tools

- **Tools ▾ → Codebook** lists all codes with their annotation counts and marks codes that have key passages (◆). The codebook can be exported as CSV, MD, DOCX and ODT.
- **Tools ▾ → Code tree** shows the hierarchy graphically and can be exported as PNG, PDF, MD, DOCX and ODT.

---

## 5. Coding text

### 5.1 Basic coding

1. Open a transcript.
2. Select a passage of text with the mouse.
3. A pop-up appears. Search for a code and choose it. If the code does not exist, type a new name and click **+ Create "…"** — the code is created and applied straight away.
4. Optionally, write a memo, tick **Key passage** or set a **Weight** (0–100; only shown if **Segment weight** is switched on in Settings).
5. Click **Code**.

Coded passages are highlighted in colour. Where several codes overlap, each code gets its own coloured underline.

### 5.2 Changing an annotation

Click a highlighted passage to open the detail view. There you can change the memo, weight, key-passage marking and code. Click **Update** to save your changes, **Remove** to delete the annotation, or **Close**.

### 5.3 Undo and redo

Cmd/Ctrl+Z undoes and Cmd/Ctrl+Shift+Z (or Ctrl+Y) redoes. This applies to adding and removing annotations in the open transcript, up to 200 steps. Changes to codes, text, memos and weights cannot be undone.

### 5.4 What you see

In the Coding view you see **only your own** annotations. The Analysis view, statistics, matrices and exports include all coders in the project.

### 5.5 Coding images (code pins)

For image transcripts: click 📍 **Place code pins** in the image panel header, then click in the image to place a code pin. Drag a pin to move it. **Show recognised text** shows where OCR found text.

---

## 6. Search

### 6.1 Searching a transcript

Press Cmd+F (macOS) or Ctrl+F (Windows/Linux). Enter goes to the next match, Shift+Enter to the previous one, and Esc closes the search bar.

### 6.2 Project search

Click **Project search** in the top bar to search all transcripts. Click a result to open the transcript at that point.

---

## 7. Analysis view

### 7.1 Opening the Analysis view

Click **Analysis view** in the top bar (next to **Coding view**).

### 7.2 Choosing codes

Tick the codes whose excerpts you want to see. Ticking a parent code also ticks its child codes. The number next to each code is the number of excerpts from all coders, after the tag filter. **All**/**None** select or deselect all codes.

### 7.3 Tag filter

The **🏷️ All transcripts** button limits the analysis to transcripts with certain tags (see 3.4).

1. Tick one or more tags.
2. Choose **Match any** (the transcript has at least one of the tags) or **Match all** (the transcript has every tag).
3. Click **Apply**. **Clear filter** shows all transcripts again.

The button then shows, for example, "2 tag(s) · 3/8 transcripts". The filter affects the excerpts, the counts in the codebook and all exports from the Analysis view.

### 7.4 Display modes

- **Separate**: excerpts are grouped by code (with the code hierarchy as headings) and ordered by the transcript's letter label and then by order of appearance in the text.
- **Code-in-code**: excerpts are grouped by transcript, and overlapping passages are merged into one card with coloured highlights for each code.

### 7.5 Search and filters

- **Search excerpts…** searches the excerpt text, memos and transcript names. Cmd/Ctrl+F in the Analysis view moves the cursor here.
- **Memos** shows or hides memos.
- **Key passages** shows only excerpts marked as key passages.

### 7.6 Jumping to an excerpt

Click an excerpt to open the transcript in the Coding view at that passage. If you have selected text in the card, or if **Select excerpts** is switched on, the application does not jump. If the excerpt was coded by another coder, the passage is highlighted briefly and a message tells you who coded it.

### 7.7 Exporting from the Analysis view

Click **Export** in the Analysis view. In **Export analysis**, first choose the scope:

- **Export selected codes**
- **Export selected excerpts** — requires **Select excerpts** to be switched on so that you can tick individual excerpts
- **Export key passages**
- **Export all**

Then choose a format: **DOCX** (Word, with coloured code headings), **ODT**, **MD** (Markdown), **CSV** (for R, Python or a spreadsheet), **PDF** or **PNG**.

Good to know:

- The tag filter applies to every format.
- DOCX, ODT, MD and CSV are always grouped by code and always include memos, whatever the display mode and the Memos setting.
- PDF and PNG capture the view as it appears on screen.

---

## 8. Statistics and matrices

### 8.1 Statistics

**Tools ▾ → Statistics** shows the number of annotations and coded characters per code, for the **Entire project** or **This transcript**. All coders are counted, and code pins are included.

### 8.2 Code matrix

**Tools ▾ → Code matrix**: transcripts as rows and codes as columns. Codes without annotations are not shown. Can be exported as CSV.

### 8.3 Code overlap

**Tools ▾ → Code overlap**: how often two codes overlap in the text (co-occurrence). Only overlaps within the same coder's annotations are counted; code pins are not included. Can be exported as CSV.

---

## 9. Collaboration

### 9.1 Multiple coders

Each coder opens the project under their own coder name. Annotations are stored separately for each coder and transcript, so coders never overwrite each other's annotations.

### 9.2 Workflow on a course

1. **The course leader** creates a project, imports the transcripts, tags them and, if desired, builds an initial codebook.
2. The course leader gives **a copy of the project folder** to each student (or group). Do not let several people work in the same folder at the same time: the project file (which holds the codebook) may then be overwritten.
3. Each student opens their copy under **their own coder name** and codes.
4. The student chooses **Tools ▾ → Export my codings** and hands in the .json file that is created.
5. The course leader chooses **Tools ▾ → Import codings…** in their project and selects the file. Repeat for each student.

### 9.3 Importing codings

On import:

- Transcripts are matched by ID. If the ID does not exist in the project, the transcript is matched by identical text. Import therefore works even if the transcripts were imported separately, as long as the text is the same.
- Codes are matched by ID, and otherwise by name. Missing codes (for example, codes the student created) are created in their place in the hierarchy.
- Annotations that already exist are skipped, so the same file can be imported twice without creating duplicates.

After the import, a summary is shown: the number of annotations imported, new codes, transcripts that were not found, and transcripts whose text differs from the coder's version (where positions may be shifted).

*Note: the codings file is not encrypted and contains the coded excerpts, even if the project is encrypted.*

### 9.4 Inter-rater reliability (IRR)

Calculation of Cohen's kappa between two coders per transcript is implemented, but its button is not yet shown in the interface. In the desktop app, it can be reached through the menu **Tools → IRR**. Kappa is interpreted according to Landis & Koch (1977).

---

## 10. Exporting the project

Click **Export** in the top bar. Choose a **Destination folder**, the **Scope** and one or more formats.

The **Scope** applies to the CSV formats, Markdown per code and coded transcripts:

- **Whole project** (default)
- **Open transcript only** (only available when a transcript is open)

| Format | Contents |
|--------|----------|
| CSV (all) | All annotations with metadata |
| CSV tidy (R/Python) | One row per annotation, suited to R and Python |
| Markdown – excerpts per code | Coded excerpts grouped by code |
| Markdown – codebook | Codebook structure with annotation counts (always the whole project) |
| Markdown – coded transcripts | Every transcript that has annotations, in one file: the full text with codes marked (overlaps included) and a summary with memos. Suited to reviewing the coding |
| QDPX (REFI-QDA) | Exchange format for other QDA software (always the whole project) |

If a format cannot be created, the other formats are still written and the dialogue shows what failed.

Files are named with the project name, date and time. File names and headings follow the selected language.

QDPX contains texts, codes and annotations with memos. Code pins, transcript memos, tags, weights and key passages are not included. Compatibility with NVivo and ATLAS.ti has not been verified.

---

## 11. Settings

Click ⚙ (**Settings**) in the top bar:

- **Code numbering** — automatic hierarchical numbering (1, 2, 2.1 …).
- **Letter labels for transcripts (A., B., …)** — labels in front of transcript names (see 3.5).
- **Segment weight (0–100)** — shows a weight slider when you code.

With transcription switched on, **Identify me automatically**, **Waveform (audio files)** and **🎤 Voice profile** are also available.

Language (**EN**/**SV**) and theme (**Light**/**Dark**) are changed with the buttons in the top bar and on the start screen.

---

## Suggested workflow

### Phase 1: Preparation
1. Create or open the project.
2. Build an initial codebook based on your research questions (a deductive approach), or start without codes (an inductive approach).

### Phase 2: Import
3. Import the transcripts (text, images or Notescribbler material).
4. Tag the transcripts according to the comparisons you want to make (for example, group or site).
5. Read through the transcripts and correct any errors with **Edit text** before you start coding.

### Phase 3: Coding (round 1)
6. Open the first transcript and read it through.
7. Code — select text, then choose or create codes.
8. Write memos about important observations.
9. Mark particularly telling passages as **key passages**.
10. Repeat for all transcripts.

### Phase 4: Revising the codebook
11. Review the codebook — merge redundant codes and build hierarchies.
12. Use **Code overlap** to find codes that often overlap.
13. Use **Statistics** to see how the codes are distributed.

### Phase 5: Coding (round 2)
14. Go through the transcripts again with the revised codebook.
15. Adjust annotations and memos.

### Phase 6: Analysis
16. Switch to the **Analysis view**.
17. Choose codes and read the excerpts — compare themes across transcripts.
18. Use the tag filter to compare groups.
19. Use **Code-in-code** to see overlaps.
20. Filter on **Key passages** to gather the strongest quotations.
21. Export the analysis in your chosen format.

### Phase 7: Collaboration (optional)
22. Have another coder code the same material in a copy of the project (see 9.2).
23. Import their annotations with **Import codings…**.

### Phase 8: Final export
24. Export the project as CSV (for statistical analysis) or QDPX (for other QDA software).
25. Export selected analyses as DOCX for your report.

---

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd/Ctrl + Z | Undo (adding/removing an annotation) |
| Cmd/Ctrl + Shift + Z, Ctrl + Y | Redo |
| Cmd/Ctrl + F | Search the transcript (in the Analysis view: search excerpts) |
| Enter / Shift + Enter | Next / previous search match |
| Esc | Close the search bar and pop-ups |
| Spacebar | Play/pause audio (if enabled in the audio player) |

Bold, italic and font size are controlled with the **B**, **I** and **A−**/**A+** buttons in the toolbar.

---

*Transcribbler is free software under the AGPL-3.0 licence: free to use and share, including for professional purposes. Redistributed versions must use the same licence.*
