"use strict";

const TRANSLATIONS = {
  sv: {
    // Splash
    "tab.open":              "Öppna projekt",
    "tab.new":               "Nytt projekt",
    "recent.label":          "Senaste projekt",
    "open.folder.ph":        "Eller ange sökväg manuellt…",
    "open.folder.title":     "Välj mapp",
    "open.coder.label":      "Ditt namn (kodare)",
    "open.coder.ph":         "anna",
    "btn.open":              "Öppna",
    "new.folder.ph":         "Välj eller ange projektmapp…",
    "new.name.label":        "Projektnamn",
    "new.name.ph":           "Min intervjustudie",
    "new.coder.label":       "Ditt namn (kodare)",
    "new.coder.ph":          "anna",
    "btn.create":            "Skapa projekt",
    // Topbar
    "btn.add.transcript":    "+ Transkript",
    "btn.import":            "Import",
    "btn.export":            "Exportera",
    "export.modal.title":    "Exportera",
    "export.folder.label":   "Destinationsmapp",
    "export.browse":         "Bläddra…",
    "export.formats.label":  "Format",
    "export.btn.confirm":    "Exportera",
    "export.ok":             "Exporterade {count} fil(er) till {folder}",
    "export.err.no.folder":  "Ange en destinationsmapp.",
    "export.err.no.format":  "Välj minst ett format.",
    "btn.tools":             "Verktyg ▾",
    "exp.csv":               "CSV (alla)",
    "exp.csv.tidy":          "CSV tidy (R/Python)",
    "exp.md.codes":          "Markdown – citat per kod",
    "exp.md.codebook":       "Markdown – kodbok",
    "exp.md.transcript":     "Markdown – detta transkript",
    "btn.merge":             "Slå ihop filer",
    "btn.switch.project":    "Byt projekt",
    "btn.theme.to.dark":     "Mörkt",
    "btn.theme.to.light":    "Ljust",
    // Sidebars
    "sidebar.transcripts":   "Transkript",
    "sidebar.codebook":      "Kodbok",
    "btn.add.code.title":    "Ny kod",
    // Editor
    "editor.placeholder":    "Välj ett transkript i listan till vänster.",
    // Transcript modal
    "trans.modal.title":     "Lägg till transkript",
    "trans.file.label":      "Välj fil (.txt, .docx, .mp3, .wav …)",
    "trans.drop.text":       "Klicka för att välja fil, eller dra hit",
    "trans.name.label":      "Namn (valfritt — används om du väljer en enda fil)",
    "trans.name.ph":         "Anna, 2024-03-12",
    "trans.whisper.summary": "Ljudfil? Whisper-inställningar",
    "trans.lang.label":      "Språk",
    "trans.model.label":     "Modell",
    "btn.trans.confirm":     "Lägg till",
    "btn.cancel":            "Avbryt",
    "trans.loading":         "Transkriberar med Whisper… det kan ta en stund.",
    // Code modal
    "code.new.title":        "Ny kod",
    "code.edit.title":       "Redigera kod",
    "code.name.label":       "Namn",
    "code.parent.label":     "Överordnad kod (tema)",
    "code.parent.none":      "— ingen (toppnivå) —",
    "code.color.label":      "Färg",
    "code.desc.label":       "Beskrivning",
    "btn.save":              "Spara",
    "btn.delete.code":       "Ta bort kod",
    // Annotation popup
    "ann.memo.ph":           "Memo (valfritt)",
    "btn.code":              "Koda",
    "ann.detail.memo.ph":    "Memo",
    "btn.update":            "Uppdatera",
    "btn.remove":            "Ta bort",
    "btn.close":             "Stäng",
    // Merge modal
    "merge.title":           "Slå ihop kodningsfiler",
    "merge.desc":            "Klistra in sökvägen till en kollegas .json-kodningsfil.",
    "merge.path.label":      "Sökväg till fil",
    "merge.path.ph":         "/Users/du/Downloads/transkript1.bjorn.json",
    "btn.merge.confirm":     "Importera",
    // Context menu
    "ctx.search":             "🔍 Sök",
    "ctx.categorize":         "📁 Kategorisera",
    "ctx.code.rename":        "✏️ Byt namn",
    "ctx.code.rename.prompt": "Nytt namn:",
    // Categorize modal
    "cat.modal.title":        "Kategorisera transkript",
    "cat.input.ph":           "Kategorinamn…",
    "btn.cat.remove":         "Ta bort kategori",
    "trans.uncategorized":    "Okategoriserade",
    // Search
    "search.ph":              "Sök i transkript…",
    // Memo
    "memo.ph":                "Memo för detta transkript…",
    // Stats
    "btn.stats":              "Statistik",
    "stats.title":            "Statistik",
    "stats.scope.all":        "Hela projektet",
    "stats.scope.transcript": "Detta transkript",
    "stats.col.code":         "Kod",
    "stats.col.count":        "Kodningar",
    "stats.col.chars":        "Tecken",
    "stats.col.coders":       "Kodare",
    // IRR
    "btn.irr":                "IRR",
    "irr.title":              "Inter-rater reliability",
    "irr.coder_a":            "Kodare A",
    "irr.coder_b":            "Kodare B",
    "irr.transcript":         "Transkript",
    "irr.compute":            "Beräkna",
    "irr.col.code":           "Kod",
    "irr.col.coder_a":        "Kodare A (tecken)",
    "irr.col.coder_b":        "Kodare B (tecken)",
    "irr.col.agreement":      "Gemensamt",
    // Misc
    "confirm.del.transcript": "Ta bort \"{name}\"?",
    "confirm.del.code":       "Ta bort koden? Kodningar som använder den förlorar sin kod.",
    "confirm.del.ann":        "Ta bort kodningen?",
    "alert.pick.transcript":  "Öppna ett transkript först.",
    "alert.pick.code":        "Välj en kod.",
    "error.fill.all":         "Fyll i alla fält.",
    "error.no.file":          "Välj minst en fil.",
    "error.scribbler.no_password": "Ange lösenord för .scribbler-filen.",
    "scribbler.password.label":    "Lösenord (från Notescribbler)",
    "scribbler.password.ph":       "Exportlösenord",
    // New features
    "btn.codetree":              "Kodträd",
    "btn.codebook":              "Kodbok",
    "codebook.empty":            "Kodboken är tom.",
    "code.ann.count":            "Antal annoteringar",
    "settings.trans.order":      "Alfabetisk ordning av transkript",
    "btn.project.search":     "Projektsök",
    "proj.search.title":      "Sök i projekt",
    "proj.search.ph":         "Sökterm…",
    "proj.search.btn":        "Sök",
    "settings.numbering":     "Numrering av koder",
    "ann.search.ph":          "Sök kod…",
    "alert.no.transcript.fmt": "Öppna ett transkript för att använda formatering.",
    // Diarization / audio upload
    "diar.label":             "Diarization (talaridentifiering)",
    "diar.num.label":         "Antal talare:",
    "diar.num.ph":            "t.ex. 2",
    "diar.num.hint":          "Lämna tomt för automatisk detektering",
    "diar.advanced":          "Avancerade inställningar",
    "diar.min.label":         "Min talare:",
    "diar.max.label":         "Max talare:",
    "diar.seg.label":         "Segmenteringströskel",
    "diar.clu.label":         "Klustringsttröskel",
    "diar.voices.soon":       "Röstprofiler — kommer snart",
    "diar.auto.identify":     "Identifiera min röst automatiskt",
    "diar.word.ts.label":     "Exakt talaruppdelning (word-level)",
    "diar.word.ts.warning":   "⚠ ~3× längre tid. 10 min ljud ≈ 50 min; 1 tim ≈ 5 tim.",
    "image.ocr.label":        "Transkribera text-i-bild",
    "diar.voice.ready":       "Röstprofil sparad ✓",
    "diar.voice.none":        "Ingen röstprofil",
    "settings.auto.identify": "Identifiera mig automatiskt",
    "btn.voice.profile":      "🎤 Röstprofil",
    "voice.modal.title":      "🎤 Röstprofil",
    "voice.modal.desc":       "Ladda upp ett ljudklipp (30–120 s) där bara du pratar. Programmet lär sig din röst och kan identifiera dig automatiskt vid framtida transkriptioner.",
    "voice.status.saved":     "Röstprofil sparad",
    "voice.upload.label":     "Välj ljudfil (WAV, MP3, M4A…)",
    "voice.extracting":       "Extraherar röstprofil…",
    "btn.voice.extract":      "Spara röstprofil",
    "btn.voice.delete":       "Ta bort",
    "voice.match.auto":       "Identifierad automatiskt",
    "voice.match.suggest":    "Liknar din röst",
    "hf.modal.title":         "Hugging Face-token krävs",
    "hf.step1":               "Gå till modellsidan och acceptera licensvillkoren:",
    "hf.step2":               "Skapa ett token (Read-behörighet räcker):",
    "hf.token.label":         "Ditt token:",
    "hf.token.ph":            "hf_…",
    "hf.save":                "Spara token",
    "hf.saved":               "Token sparat ✓",
    "hf.error":               "Ogiltigt token eller nätverksfel.",
    "progress.loading":       "Laddar modell…",
    "progress.diarizing":     "Identifierar talare…",
    "progress.transcribing":  "Whisper transkriberar…",
    "progress.done":          "Klart!",
    "spk.modal.title":        "Döp om talare",
    "spk.modal.hint":         "Ange valfria namn för varje talare (lämna tomt för att behålla automatiskt ID).",
    "spk.confirm":            "Lägg till transkript",
    "batch.spk.title":        "Namnge talare för alla filer",
    "batch.spk.hint":         "Transkriberingen är klar. Fyll i namn på talare för varje fil — lämna tomt för att behålla automatiska ID:n.",
    "batch.spk.save":         "Spara alla",
    "batch.spk.skip":         "Spara med standardnamn",
    "batch.spk.none":         "Inga talare identifierade — sparas som transkript utan talarnamn.",
    // Language / model choice
    "trans.lang_choice.label": "Transkriptionsmodell",
    "lang.autodetect":        "Autodetect — KB-Whisper (rekommenderas)",
    "lang.sv":                "Svenska — KB-Whisper",
    "lang.en":                "Engelska — Whisper",
    "lang.other":             "Övrigt — Whisper (autodetect)",
    // Codebook search
    "codebook.search.ph":     "Filtrera koder…",
    // Undo / redo
    "undo.no.action":         "Inget att ångra.",
    "redo.no.action":         "Inget att göra om.",
    // License
    "license.desc":           "Fri att använda och dela — även i yrkesarbete. Vidaredistribution kräver samma licens.",
    // New features: weight, anchor, matrix, cooccurrence, waveform, qdpx
    "settings.use.weight":    "Segmentvikt (0–100)",
    "settings.use.waveform":  "Vågform (ljudfiler)",
    "ann.weight.label":       "Vikt",
    "ann.anchor.label":       "Nyckelpassage",
    "btn.code.matrix":        "Kodmatris",
    "btn.cooccurrence":       "Kodöverlapp",
    "exp.qdpx":               "QDPX (REFI-QDA)",
  },

  en: {
    // Splash
    "tab.open":              "Open project",
    "tab.new":               "New project",
    "recent.label":          "Recent projects",
    "open.folder.ph":        "Or enter path manually…",
    "open.folder.title":     "Choose folder",
    "open.coder.label":      "Your name (coder)",
    "open.coder.ph":         "anna",
    "btn.open":              "Open",
    "new.folder.ph":         "Choose or enter project folder…",
    "new.name.label":        "Project name",
    "new.name.ph":           "My interview study",
    "new.coder.label":       "Your name (coder)",
    "new.coder.ph":          "anna",
    "btn.create":            "Create project",
    // Topbar
    "btn.add.transcript":    "+ Transcript",
    "btn.import":            "Import",
    "btn.export":            "Export",
    "export.modal.title":    "Export",
    "export.folder.label":   "Destination folder",
    "export.browse":         "Browse…",
    "export.formats.label":  "Formats",
    "export.btn.confirm":    "Export",
    "export.ok":             "Exported {count} file(s) to {folder}",
    "export.err.no.folder":  "Please specify a destination folder.",
    "export.err.no.format":  "Please select at least one format.",
    "btn.tools":             "Tools ▾",
    "exp.csv":               "CSV (all)",
    "exp.csv.tidy":          "CSV tidy (R/Python)",
    "exp.md.codes":          "Markdown – quotes per code",
    "exp.md.codebook":       "Markdown – codebook",
    "exp.md.transcript":     "Markdown – this transcript",
    "btn.merge":             "Merge files",
    "btn.switch.project":    "Switch project",
    "btn.theme.to.dark":     "Dark",
    "btn.theme.to.light":    "Light",
    // Sidebars
    "sidebar.transcripts":   "Transcripts",
    "sidebar.codebook":      "Codebook",
    "btn.add.code.title":    "New code",
    // Editor
    "editor.placeholder":    "Select a transcript from the list on the left.",
    // Transcript modal
    "trans.modal.title":     "Add transcript",
    "trans.file.label":      "Choose file (.txt, .docx, .mp3, .wav …)",
    "trans.drop.text":       "Click to choose file, or drag here",
    "trans.name.label":      "Name (optional — used if you select a single file)",
    "trans.name.ph":         "Anna, 2024-03-12",
    "trans.whisper.summary": "Audio file? Whisper settings",
    "trans.lang.label":      "Language",
    "trans.model.label":     "Model",
    "btn.trans.confirm":     "Add",
    "btn.cancel":            "Cancel",
    "trans.loading":         "Transcribing with Whisper… this may take a while.",
    // Code modal
    "code.new.title":        "New code",
    "code.edit.title":       "Edit code",
    "code.name.label":       "Name",
    "code.parent.label":     "Parent code (theme)",
    "code.parent.none":      "— none (top level) —",
    "code.color.label":      "Color",
    "code.desc.label":       "Description",
    "btn.save":              "Save",
    "btn.delete.code":       "Delete code",
    // Annotation popup
    "ann.memo.ph":           "Memo (optional)",
    "btn.code":              "Code",
    "ann.detail.memo.ph":    "Memo",
    "btn.update":            "Update",
    "btn.remove":            "Remove",
    "btn.close":             "Close",
    // Merge modal
    "merge.title":           "Merge coding files",
    "merge.desc":            "Paste the path to a colleague's .json coding file.",
    "merge.path.label":      "File path",
    "merge.path.ph":         "/Users/you/Downloads/transcript1.bjorn.json",
    "btn.merge.confirm":     "Import",
    // Context menu
    "ctx.search":             "🔍 Search",
    "ctx.categorize":         "📁 Categorize",
    "ctx.code.rename":        "✏️ Rename",
    "ctx.code.rename.prompt": "New name:",
    // Categorize modal
    "cat.modal.title":        "Categorize transcripts",
    "cat.input.ph":           "Category name…",
    "btn.cat.remove":         "Remove category",
    "trans.uncategorized":    "Uncategorized",
    // Search
    "search.ph":              "Search transcript…",
    // Memo
    "memo.ph":                "Memo for this transcript…",
    // Stats
    "btn.stats":              "Statistics",
    "stats.title":            "Statistics",
    "stats.scope.all":        "Entire project",
    "stats.scope.transcript": "This transcript",
    "stats.col.code":         "Code",
    "stats.col.count":        "Annotations",
    "stats.col.chars":        "Characters",
    "stats.col.coders":       "Coders",
    // IRR
    "btn.irr":                "IRR",
    "irr.title":              "Inter-rater reliability",
    "irr.coder_a":            "Coder A",
    "irr.coder_b":            "Coder B",
    "irr.transcript":         "Transcript",
    "irr.compute":            "Compute",
    "irr.col.code":           "Code",
    "irr.col.coder_a":        "Coder A (chars)",
    "irr.col.coder_b":        "Coder B (chars)",
    "irr.col.agreement":      "Shared",
    // Misc
    "confirm.del.transcript": "Delete \"{name}\"?",
    "confirm.del.code":       "Delete this code? Annotations using it will lose their code.",
    "confirm.del.ann":        "Remove this annotation?",
    "alert.pick.transcript":  "Open a transcript first.",
    "alert.pick.code":        "Please select a code.",
    "error.fill.all":         "Please fill in all fields.",
    "error.no.file":          "Please select at least one file.",
    "error.scribbler.no_password": "Enter password for the .scribbler file.",
    "scribbler.password.label":    "Password (from Notescribbler)",
    "scribbler.password.ph":       "Export password",
    // New features
    "btn.codetree":              "Code tree",
    "btn.codebook":              "Codebook",
    "codebook.empty":            "The codebook is empty.",
    "code.ann.count":            "Annotation count",
    "settings.trans.order":      "Alphabetical transcript labels",
    "btn.project.search":     "Project search",
    "proj.search.title":      "Search in project",
    "proj.search.ph":         "Search term…",
    "proj.search.btn":        "Search",
    "settings.numbering":     "Code numbering",
    "ann.search.ph":          "Search code…",
    "alert.no.transcript.fmt": "Open a transcript to use formatting.",
    // Diarization / audio upload
    "diar.label":             "Diarization (speaker identification)",
    "diar.num.label":         "Number of speakers:",
    "diar.num.ph":            "e.g. 2",
    "diar.num.hint":          "Leave blank for automatic detection",
    "diar.advanced":          "Advanced settings",
    "diar.min.label":         "Min speakers:",
    "diar.max.label":         "Max speakers:",
    "diar.seg.label":         "Segmentation threshold",
    "diar.clu.label":         "Clustering threshold",
    "diar.voices.soon":       "Voice profiles — coming soon",
    "diar.auto.identify":     "Identify my voice automatically",
    "diar.word.ts.label":     "Precise speaker attribution (word-level)",
    "diar.word.ts.warning":   "⚠ ~3× slower. 10 min audio ≈ 50 min; 1 hr ≈ 5 hrs.",
    "image.ocr.label":        "Transcribe text-in-image",
    "diar.voice.ready":       "Voice profile saved ✓",
    "diar.voice.none":        "No voice profile",
    "settings.auto.identify": "Identify me automatically",
    "btn.voice.profile":      "🎤 Voice profile",
    "voice.modal.title":      "🎤 Voice profile",
    "voice.modal.desc":       "Upload an audio clip (30–120 s) where only you speak. The app learns your voice and can identify you automatically in future transcriptions.",
    "voice.status.saved":     "Voice profile saved",
    "voice.upload.label":     "Choose audio file (WAV, MP3, M4A…)",
    "voice.extracting":       "Extracting voice profile…",
    "btn.voice.extract":      "Save voice profile",
    "btn.voice.delete":       "Delete",
    "voice.match.auto":       "Identified automatically",
    "voice.match.suggest":    "Resembles your voice",
    "hf.modal.title":         "Hugging Face token required",
    "hf.step1":               "Go to the model page and accept the licence:",
    "hf.step2":               "Create a token (Read access is enough):",
    "hf.token.label":         "Your token:",
    "hf.token.ph":            "hf_…",
    "hf.save":                "Save token",
    "hf.saved":               "Token saved ✓",
    "hf.error":               "Invalid token or network error.",
    "progress.loading":       "Loading model…",
    "progress.diarizing":     "Identifying speakers…",
    "progress.transcribing":  "Whisper transcribing…",
    "progress.done":          "Done!",
    "spk.modal.title":        "Name speakers",
    "spk.modal.hint":         "Enter names for each speaker (leave blank to keep automatic ID).",
    "spk.confirm":            "Add transcript",
    "batch.spk.title":        "Name speakers for all files",
    "batch.spk.hint":         "Transcription complete. Enter speaker names for each file — leave blank to keep automatic IDs.",
    "batch.spk.save":         "Save all",
    "batch.spk.skip":         "Save with default names",
    "batch.spk.none":         "No speakers identified — will be saved as transcript without speaker names.",
    // Language / model choice
    "trans.lang_choice.label": "Transcription model",
    "lang.autodetect":        "Autodetect — KB-Whisper (recommended)",
    "lang.sv":                "Swedish — KB-Whisper",
    "lang.en":                "English — Whisper",
    "lang.other":             "Other — Whisper (autodetect)",
    // Codebook search
    "codebook.search.ph":     "Filter codes…",
    // Undo / redo
    "undo.no.action":         "Nothing to undo.",
    "redo.no.action":         "Nothing to redo.",
    // License
    "license.desc":           "Free to use and share — including professional use. Redistribution requires the same licence.",
    // New features: weight, anchor, matrix, cooccurrence, waveform, qdpx
    "settings.use.weight":    "Segment weight (0–100)",
    "settings.use.waveform":  "Waveform (audio files)",
    "ann.weight.label":       "Weight",
    "ann.anchor.label":       "Key passage",
    "btn.code.matrix":        "Code matrix",
    "btn.cooccurrence":       "Code overlap",
    "exp.qdpx":               "QDPX (REFI-QDA)",
  },
};

const LANG_KEY = "transcribbler_lang";
let currentLang = localStorage.getItem(LANG_KEY) || "sv";

function t(key, vars = {}) {
  let str = (TRANSLATIONS[currentLang] || TRANSLATIONS.sv)[key] || key;
  for (const [k, v] of Object.entries(vars)) {
    str = str.replace(`{${k}}`, v);
  }
  return str;
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem(LANG_KEY, lang);
  applyTranslations();
}

function applyTranslations() {
  document.documentElement.lang = currentLang;

  // text content
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  // placeholder
  document.querySelectorAll("[data-i18n-ph]").forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  // title attribute
  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });

  // Update both lang toggle buttons (topbar + splash)
  const langLabel = currentLang === "sv" ? "EN" : "SV";
  const btn = document.getElementById("btn-lang");
  if (btn) btn.textContent = langLabel;
  const btnSplash = document.getElementById("btn-lang-splash");
  if (btnSplash) btnSplash.textContent = langLabel;

  // Update theme button label
  const themeBtn = document.getElementById("btn-theme");
  if (themeBtn) {
    const isDark = !document.body.classList.contains("light");
    themeBtn.textContent = isDark ? t("btn.theme.to.light") : t("btn.theme.to.dark");
  }
}
