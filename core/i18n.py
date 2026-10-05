"""
Minimal backend localisation (sv/en).

The Swedish text is the message key (gettext style), so call sites stay
readable: ``tr("Inget projekt öppnat.")``. Placeholders use str.format:
``tr("Fält saknas: {fields}", fields=...)``.

The language comes from the ``transcribbler_lang`` cookie the frontend sets
(see setLang() in static/js/translations.js); main.py stores it per request
via ``set_lang()``. Background threads start with the default (sv), so job
errors are stored as Swedish keys and translated when polled.
"""
from __future__ import annotations

import contextvars

LANGS = ("sv", "en")
_lang: contextvars.ContextVar[str] = contextvars.ContextVar("lang", default="sv")

EN: dict[str, str] = {
    # --- Project / general ------------------------------------------------
    "Inget projekt öppnat.": "No project is open.",
    "Kunde inte öppna mappväljaren.": "Could not open the folder picker.",
    "folder, name och coder krävs.": "Folder, name and coder are required.",
    "folder krävs.": "Folder is required.",
    "Projektfil saknas.": "Project file is missing.",
    "folder och coder krävs.": "Folder and coder are required.",
    "Ingen giltig projektmapp.": "Not a valid project folder.",
    "Kodarnamnet får bara innehålla bokstäver, siffror, mellanslag, bindestreck och understreck (inga punkter).":
        "The coder name may only contain letters, digits, spaces, hyphens and underscores (no full stops).",
    "Välj projektmapp": "Choose project folder",
    # --- Import ------------------------------------------------------------
    "Ingen fil bifogad.": "No file attached.",
    "Ljudtranskribering är inte tillgänglig i den här versionen. "
    "Importera ett färdigt transkript (.txt, .docx, .md) i stället.":
        "Audio transcription is not available in this version. "
        "Import a ready-made transcript (.txt, .docx, .md) instead.",
    "Kunde inte importera bilden.": "Could not import the image.",
    "Lösenord krävs för .scribbler-filer.": "A password is required for .scribbler files.",
    "Lösenord krävs för .nsenc-filer.": "A password is required for .nsenc files.",
    "Dekrypteringen misslyckades.": "Decryption failed.",
    "Kunde inte importera transkriptet.": "Could not import the transcript.",
    "Ogiltig zip-fil.": "Invalid zip file.",
    "Zip-filen innehåller inga .md-filer.": "The zip file contains no .md files.",
    "Kunde inte importera filen.": "Could not import the file.",
    " Tips: om du använde 'Lösenfrasen från valvet' vid exporten, ange Notescribbler-applösenordet.":
        " Tip: if you used the vault passphrase when exporting, enter the Notescribbler app password.",
    # core/scribbler.py and core/nsenc.py (exception texts passed through)
    "Filen är för kort — troligen inte en giltig .scribbler-fil.":
        "The file is too short — probably not a valid .scribbler file.",
    "Ogiltig .scribbler-fil (felaktig signatur).": "Invalid .scribbler file (bad signature).",
    "Filen är för kort — troligen inte en giltig .nsenc-fil.":
        "The file is too short — probably not a valid .nsenc file.",
    "Ogiltig .nsenc-fil (felaktig signatur).": "Invalid .nsenc file (bad signature).",
    "Fel lösenord eller skadad fil.": "Wrong password or damaged file.",
    "argon2-cffi är inte installerat. Kör: pip install argon2-cffi":
        "argon2-cffi is not installed. Run: pip install argon2-cffi",
    "cryptography är inte installerat. Kör: pip install cryptography":
        "cryptography is not installed. Run: pip install cryptography",
    # --- Jobs (OCR / transcription) ---------------------------------------
    "Jobb hittades inte.": "Job not found.",
    "Jobbet är inte klart eller hittades inte.": "The job is not finished or was not found.",
    "Transkriptionen misslyckades. Se serverloggen för detaljer.":
        "Transcription failed. See the server log for details.",
    "OCR misslyckades. Se serverloggen för detaljer.": "OCR failed. See the server log for details.",
    "OCR misslyckades.": "OCR failed.",
    "Kunde inte spara transkriptet.": "Could not save the transcript.",
    "Token får inte vara tomt.": "The token cannot be empty.",
    "Ogiltigt token (HF svarade med fel).": "Invalid token (Hugging Face returned an error).",
    "Kunde inte validera token: {error}": "Could not validate the token: {error}",
    "Ingen kodare aktiv.": "No active coder.",
    "Ingen fil skickades.": "No file was sent.",
    "Tomt filnamn.": "Empty file name.",
    "Kunde inte skapa röstprofil.": "Could not create the voice profile.",
    "path krävs.": "Path is required.",
    "Filen hittades inte.": "File not found.",
    "Transkription misslyckades.": "Transcription failed.",
    "Kunde inte lägga till transkript.": "Could not add the transcript.",
    # --- Transcripts -------------------------------------------------------
    "Transkript hittades inte.": "Transcript not found.",
    "Transkriptet hittades inte.": "Transcript not found.",
    "text krävs.": "Text is required.",
    "Ogiltig filsökväg.": "Invalid file path.",
    "Kunde inte spara texten.": "Could not save the text.",
    "Ingen ljudfil hittades.": "No audio file found.",
    "Ljudfilen saknas på disk.": "The audio file is missing on disk.",
    "Ingen källbild hittades.": "No source image found.",
    "Källbilden saknas på disk.": "The source image is missing on disk.",
    "Inga foton att OCR:a.": "No photos to run OCR on.",
    "Fotofiler saknas på disk.": "Photo files are missing on disk.",
    "Namn får inte vara tomt.": "Name cannot be empty.",
    # --- Codes / annotations / IRR ------------------------------------------
    "coder_a och coder_b krävs.": "Both coders are required.",
    "Välj två olika kodare.": "Choose two different coders.",
    "Kunde inte beräkna IRR.": "Could not calculate inter-rater reliability.",
    "Ingen av kodarna har kodat transkriptet.": "Neither coder has coded this transcript.",
    "Transkriptet är tomt.": "The transcript is empty.",
    "name krävs.": "Name is required.",
    "Kunde inte slå ihop koderna.": "Could not merge the codes.",
    "Fält saknas: {fields}": "Missing fields: {fields}",
    "Filen måste vara en JSON-fil (.json).": "The file must be a JSON file (.json).",
    "Importen misslyckades.": "Import failed.",
    "Filen är inte en kodningsfil från Transcribbler.": "The file is not a Transcribbler codings file.",
    "Filen saknar ett giltigt kodarnamn.": "The file does not contain a valid coder name.",
    "Inget transkript i filen finns i det här projektet. "
    "Kodningsfiler måste komma från en kopia av samma projekt "
    "eller från transkript med identisk text.":
        "None of the transcripts in the file exist in this project. "
        "Codings files must come from a copy of the same project "
        "or from transcripts with identical text.",
    "Kunde inte lägga till formatering.": "Could not add formatting.",
    "[borttagen: {id}]": "[deleted: {id}]",
    # Kappa bands after Landis & Koch (1977)
    "Sämre än slumpen (Landis & Koch)": "Poor — less than chance (Landis & Koch)",
    "Obetydlig överensstämmelse (Landis & Koch)": "Slight agreement (Landis & Koch)",
    "Viss överensstämmelse (Landis & Koch)": "Fair agreement (Landis & Koch)",
    "Måttlig överensstämmelse (Landis & Koch)": "Moderate agreement (Landis & Koch)",
    "Betydande överensstämmelse (Landis & Koch)": "Substantial agreement (Landis & Koch)",
    "Nästan perfekt överensstämmelse (Landis & Koch)": "Almost perfect agreement (Landis & Koch)",
    # --- Export ------------------------------------------------------------
    "Ingen mapp angiven.": "No folder specified.",
    "Kunde inte skapa exportmappen.": "Could not create the export folder.",
    # Document content
    "Analys — {name}": "Analysis — {name}",
    "kodare: {coder}": "coder: {coder}",
    "Kodare: {coder}": "Coder: {coder}",
    "_Inga kodningar hittades._": "_No annotations found._",
    "{name} — Kodade citat": "{name} — Coded excerpts",
    "Okända koder": "Unknown codes",
    "Kodbok — {name}": "Codebook — {name}",
    "_Kodboken är tom._": "_The codebook is empty._",
    "_Transkript hittades inte._": "_Transcript not found._",
    "Kodsammanfattning": "Code summary",
    "{name} — Kodade transkript": "{name} — Coded transcripts",
    "Exporterad {date}": "Exported {date}",
    "{n} kodningar": "{n} annotations",
    "nyckelpassage": "key passage",
    "Transkript": "Transcript",
    "TOTALT": "TOTAL",
    # File name stems (ASCII only)
    "annoteringar_tidy": "annotations_tidy",
    "annoteringar": "annotations",
    "citat_per_kod": "excerpts_by_code",
    "kodbok": "codebook",
    "kodtrad": "code_tree",
    "transkript": "transcript",
    "kodade_transkript": "coded_transcripts",
    "kodmatris": "code_matrix",
    "kodoverlapp": "code_overlap",
    "projekt": "project",
    "analys": "analysis",
    "kodningar": "codings",
}

_TABLES = {"en": EN}


def set_lang(lang: str | None) -> None:
    _lang.set(lang if lang in LANGS else "sv")


def get_lang() -> str:
    return _lang.get()


def tr(text: str, **kwargs) -> str:
    """Translate a Swedish message key into the current language."""
    out = _TABLES.get(_lang.get(), {}).get(text, text)
    return out.format(**kwargs) if kwargs else out
