"""
main.py — Transcribbler Flask app.
Run: python3 main.py
Opens automatically in the default browser.
"""
import json
import logging
import os
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

from flask import (Flask, jsonify, render_template, request,
                   send_from_directory)

from core import project as proj_mod
from core import codebook as cb_mod
from core import annotation as ann_mod
from core import export as exp_mod
from core import merge as merge_mod

# Apply PyTorch 2.6+ compatibility patch for pyannote/lightning_fabric
import core.transcribe as _tr_mod  # noqa — triggers _patch_torch_load() at import time

# Root logger: WARNING — quiet by default, real errors and warnings still surface.
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("transcribbler")
# Our own loggers: INFO — we want to see timing/diagnostic output from
# core/transcribe.py in the terminal.
logging.getLogger("transcribbler").setLevel(logging.INFO)
logging.getLogger("transcribbler.timing").setLevel(logging.INFO)
# Silence werkzeug's per-request HTTP log spam (GET /api/jobs/... every 2s).
# WARNING level still surfaces real errors (4xx/5xx) if Flask hits them.
logging.getLogger("werkzeug").setLevel(logging.WARNING)

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # disable static file caching

# ---------------------------------------------------------------------------
# State (single-session, in-memory)
# ---------------------------------------------------------------------------
STATE = {
    "folder": None,   # active project folder (str)
    "project": None,  # project dict
    "coder": None,    # active coder name
}

# ---------------------------------------------------------------------------
# Background job store
# Each job: {status, stage, progress, result, error, _audio_tmp, _finished_at}
# status: "pending" | "running" | "done" | "error"
# ---------------------------------------------------------------------------
JOBS = {}
JOB_EXPIRY_SECONDS = 600  # auto-clean finished jobs after 10 minutes


def _cleanup_expired_jobs():
    """Remove finished/errored jobs older than JOB_EXPIRY_SECONDS and their temp files."""
    now = time.monotonic()
    expired = [
        jid for jid, job in JOBS.items()
        if job.get("_finished_at") and now - job["_finished_at"] > JOB_EXPIRY_SECONDS
    ]
    for jid in expired:
        job = JOBS.pop(jid, {})
        # Clean up any leftover temp audio file
        audio_path = (job.get("result") or {}).get("audio_path")
        if audio_path:
            try:
                Path(audio_path).unlink(missing_ok=True)
            except Exception:
                pass
        logger.info("Expired job %s cleaned up", jid)


# Lock som serialiserar alla skrivoperationer mot project.json
# Skyddar mot race condition när flera OCR/audio-jobb körs parallellt.
_PROJECT_LOCK = threading.Lock()

RECENT_FILE = Path.home() / ".transcribbler_recent.json"
CONFIG_FILE = Path.home() / ".transcribbler_config.json"
MAX_RECENT = 8


# ---------------------------------------------------------------------------
# Config helpers (HF token, etc.)
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_FILE, 0o600)


def _load_recent() -> list:
    if not RECENT_FILE.exists():
        return []
    try:
        with open(RECENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_recent(folder: str, project_name: str):
    recent = [r for r in _load_recent() if r["folder"] != folder]
    recent.insert(0, {"folder": folder, "name": project_name})
    recent = recent[:MAX_RECENT]
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(recent, f, ensure_ascii=False, indent=2)


def _require_project():
    if not STATE["folder"] or not STATE["project"]:
        return jsonify({"error": "Inget projekt öppnat."}), 400
    return None


def _heic_to_jpeg_bytes(img_path: Path):
    """Convert a HEIC/HEIF file to JPEG bytes.

    Tries sips (macOS built-in) first, then ImageMagick (magick/convert),
    then Pillow+pillow-heif.  Returns None if no converter is available so
    callers can fall back to serving the raw file.
    """
    import subprocess, tempfile, platform
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        if platform.system() == "Darwin":
            subprocess.run(
                ["sips", "-s", "format", "jpeg", str(img_path), "--out", tmp_path],
                check=True, capture_output=True,
            )
        else:
            # Try ImageMagick (magick ≥7) then legacy convert
            for cmd in (["magick", str(img_path), tmp_path],
                        ["convert", str(img_path), tmp_path]):
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    break
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            else:
                # Last resort: pillow-heif
                from PIL import Image
                import pillow_heif  # noqa — registers HEIF opener
                Image.open(img_path).convert("RGB").save(tmp_path, "JPEG")
        return Path(tmp_path).read_bytes()
    except Exception:
        logger.exception("HEIC→JPEG conversion failed for %s", img_path)
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _safe_transcript_path(filename: str) -> Path:
    """Resolve a transcript-relative filename and verify it stays inside the
    project's transcripts/ directory.  Raises ValueError on traversal."""
    base = Path(STATE["folder"]).resolve() / "transcripts"
    resolved = (base / filename).resolve()
    resolved.relative_to(base)   # raises ValueError if outside
    return resolved


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static/img", "logo.svg", mimetype="image/svg+xml")


# ---------------------------------------------------------------------------
# Project routes
# ---------------------------------------------------------------------------

@app.route("/api/project/recent", methods=["GET"])
def get_recent():
    return jsonify({"recent": _load_recent()})


@app.route("/api/pick-folder", methods=["GET"])
def pick_folder():
    """Open a native OS folder picker and return the chosen path."""
    import subprocess, platform
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["osascript", "-e",
                 'POSIX path of (choose folder with prompt "Välj projektmapp")'],
                capture_output=True, text=True, timeout=60,
            )
            folder = result.stdout.strip().rstrip("/")
        elif system == "Windows":
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
                "$d.Description = 'Välj projektmapp';"
                "if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath }"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps],
                capture_output=True, text=True, timeout=60,
            )
            folder = result.stdout.strip()
        else:
            # Linux: try zenity, fall back to kdialog
            try:
                result = subprocess.run(
                    ["zenity", "--file-selection", "--directory",
                     "--title=Välj projektmapp"],
                    capture_output=True, text=True, timeout=60,
                )
                folder = result.stdout.strip()
            except FileNotFoundError:
                result = subprocess.run(
                    ["kdialog", "--getexistingdirectory", os.path.expanduser("~")],
                    capture_output=True, text=True, timeout=60,
                )
                folder = result.stdout.strip()
        return jsonify({"folder": folder or ""})
    except Exception:
        logger.exception("pick_folder failed")
        return jsonify({"error": "Kunde inte öppna mappväljaren.", "folder": ""}), 500


@app.route("/api/project/new", methods=["POST"])
def new_project():
    data = request.json
    folder = data.get("folder", "").strip()
    name = data.get("name", "").strip()
    coder = data.get("coder", "").strip()
    if not folder or not name or not coder:
        return jsonify({"error": "folder, name och coder krävs."}), 400
    project = proj_mod.create_project(folder, name, coder)
    STATE["folder"] = folder
    STATE["project"] = project
    STATE["coder"] = coder
    _save_recent(folder, name)
    return jsonify({"ok": True, "project": project})


@app.route("/api/project/open", methods=["POST"])
def open_project():
    data = request.json
    folder = data.get("folder", "").strip()
    coder = data.get("coder", "").strip()
    if not folder or not coder:
        return jsonify({"error": "folder och coder krävs."}), 400
    try:
        project = proj_mod.open_project(folder)
    except FileNotFoundError:
        return jsonify({"error": "Ingen giltig projektmapp."}), 404
    STATE["folder"] = folder
    STATE["project"] = project
    STATE["coder"] = coder
    _save_recent(folder, project["name"])
    return jsonify({"ok": True, "project": project})


@app.route("/api/project", methods=["GET"])
def get_project():
    err = _require_project()
    if err:
        return err
    return jsonify({
        "project": STATE["project"],
        "folder": STATE["folder"],
        "coder": STATE["coder"],
    })


@app.route("/api/project/settings", methods=["PATCH"])
def update_project_settings():
    err = _require_project()
    if err:
        return err
    data = request.json
    allowed = {"numbering", "name", "auto_identify", "trans_order",
               "use_weight", "use_waveform"}
    for k, v in data.items():
        if k in allowed:
            STATE["project"][k] = v
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True, "project": STATE["project"]})


# ---------------------------------------------------------------------------
# Transcript routes
# ---------------------------------------------------------------------------

def _transcription_job(job_id: str, audio_path: str, folder: str,
                        project: dict, name: str, settings: dict):
    """
    Worker thread: diarize (optional) + transcribe, then store result in JOBS.
    audio_path is a temp file owned by this job; cleaned up on commit or error.
    """
    import tempfile
    from core.transcribe import (transcribe_with_diarization, transcribe_with_gaps,
                                  transcribe, is_audio, get_model_label,
                                  extract_speaker_embeddings, match_voice_profile,
                                  load_voice_profile, get_diarization_device)

    def _progress(stage, fraction):
        JOBS[job_id]["stage"] = stage
        JOBS[job_id]["progress"] = fraction

    JOBS[job_id]["status"] = "running"
    try:
        use_diarization = settings.get("diarization", False)

        if use_diarization:
            hf_token = _load_config().get("hf_token", "")
            if not hf_token:
                raise ValueError("Inget Hugging Face-token sparat. Ange token i inställningarna.")
            result = transcribe_with_diarization(
                audio_path, hf_token, settings, progress_cb=_progress
            )
        else:
            _progress("loading_model", 0.05)
            gaps_result = transcribe_with_gaps(
                audio_path,
                language=settings.get("language", "sv"),
                model_size=settings.get("model_size", "medium"),
                language_choice=settings.get("language_choice", "sv"),
                progress_cb=_progress,
            )
            _progress("done", 1.0)
            # Keep segments empty for non-diarized transcripts — downstream
            # rendering treats non-empty segments as speaker-labelled.
            result = {"text": gaps_result["text"], "segments": [], "speakers_found": []}

        # Voice profile matching (only when diarization found speakers)
        voice_matches = {}
        if use_diarization and result.get("speakers_found") and settings.get("auto_identify"):
            coder = STATE.get("coder", "")
            profile = load_voice_profile(coder)
            if profile and profile.get("embedding"):
                try:
                    _progress("voice_matching", 0.95)
                    import time as _t_vm, logging as _logvm
                    _vmlog = _logvm.getLogger("transcribbler.timing")
                    _vm_start = _t_vm.monotonic()
                    spk_embs = extract_speaker_embeddings(audio_path, result["segments"])
                    voice_matches = match_voice_profile(spk_embs, profile["embedding"])
                    _vmlog.info("voice_matching: %.1fs (%d speakers)",
                                _t_vm.monotonic() - _vm_start, len(spk_embs))
                except Exception as ve:
                    # Non-fatal — log but don't fail the job
                    print(f"[voice matching] {ve}")

        JOBS[job_id]["result"] = {
            "text":           result["text"],
            "segments":       result["segments"],
            "speakers_found": result["speakers_found"],
            "voice_matches":  voice_matches,
            "diar_device":    get_diarization_device() if use_diarization else None,
            "name":           name,
            "settings":       settings,
            "audio_path":     audio_path,   # kept for commit step
        }
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["progress"] = 1.0
        JOBS[job_id]["stage"] = "done"

    except Exception as _exc:
        # Wrap logger.exception() — speechbrain's lazy k2 import can crash
        # the logging call itself, which would leave the job stuck forever.
        try:
            logger.exception("Transcription job %s failed", job_id)
        except Exception:
            # logger crashed; also protect print_exc since traceback.py
            # walks module attributes and triggers the same k2 import error.
            print(f"[transcription_job] {job_id} failed: {type(_exc).__name__}: {_exc}")
            try:
                import traceback as _tb
                _tb.print_exc()
            except Exception:
                pass  # print_exc also crashed — give up on detailed logging
        # Always mark the job as failed, even if all logging crashed.
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = "Transkriptionen misslyckades. Se serverloggen för detaljer."
        # Clean up temp audio on failure
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass


def _ocr_job(job_id: str, image_path: str, folder: str, project: dict, name: str):
    """
    Worker thread: OCR på en bildfil → spara transkript automatiskt.
    image_path är en tempfil som ägs av detta jobb och städas upp vid klart/fel.
    """
    from core.ocr import ocr_image

    def _progress(stage, fraction):
        JOBS[job_id]["stage"] = stage
        JOBS[job_id]["progress"] = fraction

    JOBS[job_id]["status"] = "running"
    try:
        result = ocr_image(image_path, progress_cb=_progress)
        text  = result["text"]
        boxes = result.get("boxes", [])

        _progress("saving", 0.92)
        tid = str(uuid.uuid4())[:8]

        # Spara OCR-rutor innan locken (ingen conflict-risk här)
        boxes_path = Path(folder) / "transcripts" / f"{tid}_ocr_boxes.json"
        boxes_path.write_text(json.dumps(boxes, ensure_ascii=False), encoding="utf-8")

        # Läs om project från disk under lock för att undvika race condition
        # när flera bilder importeras parallellt.
        with _PROJECT_LOCK:
            current = proj_mod.open_project(folder)
            updated = proj_mod.add_image_transcript(
                folder, current, tid, name, image_path, text
            )
            STATE["project"] = updated

        JOBS[job_id]["result"] = {
            "source":  "image",
            "tid":     tid,
            "project": updated,
        }
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["stage"]  = "done"
        JOBS[job_id]["progress"] = 1.0

    except Exception:
        logger.exception("OCR job %s failed", job_id)
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = "OCR misslyckades. Se serverloggen för detaljer."
    finally:
        try:
            Path(image_path).unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/api/transcripts/upload", methods=["POST"])
def upload_transcript():
    """
    Accept a multipart file upload.
    - Text/DOCX: processed synchronously, returns {ok, project}.
    - Audio: launches background job, returns {job_id} immediately.
    - Image: launches OCR background job, returns {job_id} immediately.
    """
    err = _require_project()
    if err:
        return err

    from core.transcribe import is_audio
    from core.ocr import is_image
    import tempfile

    f = request.files.get("file")
    name = request.form.get("name", "").strip()

    if not f:
        return jsonify({"error": "Ingen fil bifogad."}), 400

    ext = Path(f.filename).suffix.lower()
    original_stem = Path(f.filename).stem

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    f.save(tmp.name)
    tmp.close()

    if is_audio(tmp.name):
        pass  # fall through to audio handling below
    elif is_image(tmp.name):
        run_ocr = request.form.get("run_ocr", "1") == "1"
        if not run_ocr:
            # --- Sync path: store image without OCR ---
            try:
                import shutil
                tid = str(uuid.uuid4())[:8]
                img_name = name or original_stem
                dest_name = f"{tid}_source{ext}"
                dest = Path(STATE["folder"]) / "transcripts" / dest_name
                shutil.copy2(tmp.name, dest)
                updated = proj_mod.add_image_transcript(
                    STATE["folder"], STATE["project"], tid, img_name,
                    str(dest), ""
                )
                STATE["project"] = updated
                return jsonify({"ok": True, "project": updated})
            except Exception:
                logger.exception("image import (no OCR) failed")
                return jsonify({"error": "Kunde inte importera bilden."}), 500
            finally:
                Path(tmp.name).unlink(missing_ok=True)
        # --- Async path (image OCR) ---
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            "status": "pending", "stage": "pending",
            "progress": 0.0, "result": None, "error": None,
        }
        threading.Thread(
            target=_ocr_job,
            args=(job_id, tmp.name, STATE["folder"],
                  STATE["project"], name or original_stem),
            daemon=True,
        ).start()
        return jsonify({"job_id": job_id})
    elif ext == ".scribbler":
        # --- Synchronous path: decrypt .scribbler → import as .md ---
        from core.scribbler import decrypt_scribbler
        password = request.form.get("scribbler_password", "")
        if not password:
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({"error": "Lösenord krävs för .scribbler-filer."}), 400
        try:
            plaintext = decrypt_scribbler(tmp.name, password)
        except (ValueError, ImportError) as e:
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({"error": str(e)}), 400
        except Exception:
            logger.exception("scribbler decrypt failed")
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({"error": "Dekrypteringen misslyckades."}), 500

        md_tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
        md_tmp.write(plaintext)
        md_tmp.close()
        try:
            updated = proj_mod.add_transcript(
                STATE["folder"], STATE["project"],
                md_tmp.name, name or original_stem,
            )
            STATE["project"] = updated
            return jsonify({"ok": True, "project": updated})
        except Exception:
            logger.exception("add_transcript failed for scribbler import")
            return jsonify({"error": "Kunde inte importera transkriptet."}), 500
        finally:
            Path(tmp.name).unlink(missing_ok=True)
            Path(md_tmp.name).unlink(missing_ok=True)
    elif ext == ".nsenc":
        # --- Synchronous path: decrypt .nsenc bundle → import each note as .md ---
        from core.nsenc import decrypt_nsenc
        import re as _re
        password = request.form.get("scribbler_password", "")
        if not password:
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({"error": "Lösenord krävs för .nsenc-filer."}), 400
        try:
            notes, nsenc_photos = decrypt_nsenc(tmp.name, password)
        except (ValueError, ImportError) as e:
            Path(tmp.name).unlink(missing_ok=True)
            msg = str(e)
            if "Fel lösenord" in msg:
                msg += " Tips: om du använde 'Lösenfrasen från valvet' vid exporten, ange Notescribbler-applösenordet."
            return jsonify({"error": msg}), 400
        except Exception:
            logger.exception("nsenc decrypt failed")
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({"error": "Dekrypteringen misslyckades."}), 500
        finally:
            Path(tmp.name).unlink(missing_ok=True)

        # Build a lookup of photo bytes by filename for v2 bundles.
        photo_lookup = {p["filename"]: p["data"] for p in nsenc_photos}

        def _parse_nsenc_photos(md_text: str) -> list:
            """Return photos list from YAML frontmatter of an md string."""
            m = _re.match(r"\A---\n(.*?)\n---\n?", md_text, _re.DOTALL)
            if not m:
                return []
            fm = m.group(1)
            block = _re.search(r"^photos:\s*\n((?:[ \t]+-[ \t]+\S[^\n]*\n?)+)", fm, _re.MULTILINE)
            if block:
                return [i.strip() for i in _re.findall(r"[ \t]+-[ \t]+(\S[^\n]*)", block.group(1)) if i.strip()]
            inline = _re.search(r"^photos:\s*\[([^\]]*)\]", fm, _re.MULTILINE)
            if inline:
                return [i.strip() for i in inline.group(1).split(",") if i.strip()]
            return []

        updated = STATE["project"]
        imported = 0
        trans_dir = Path(STATE["folder"]) / "transcripts"
        for note_data in notes:
            note_content = note_data.get("content", "")
            note_filename = note_data.get("filename", f"note_{imported}.md")
            md_tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
            md_tmp.write(note_content.encode("utf-8"))
            md_tmp.close()
            old_tids = {t["id"] for t in updated.get("transcripts", [])}
            try:
                note_name = Path(note_filename).stem
                updated = proj_mod.add_transcript(
                    STATE["folder"], updated,
                    md_tmp.name, note_name,
                )
                imported += 1
            except Exception:
                logger.exception("add_transcript failed for nsenc note: %s", note_filename)
                continue
            finally:
                Path(md_tmp.name).unlink(missing_ok=True)
            # Save photos referenced in note frontmatter (v2 bundles only).
            new_t = next((t for t in updated["transcripts"] if t["id"] not in old_tids), None)
            if new_t and photo_lookup:
                photo_refs = _parse_nsenc_photos(note_content)
                saved = []
                for n, photo_name in enumerate(photo_refs):
                    photo_bytes = photo_lookup.get(photo_name)
                    if photo_bytes is None:
                        continue
                    photo_ext = Path(photo_name).suffix.lower()
                    dest_name = f'{new_t["id"]}_photo_{n}{photo_ext}'
                    try:
                        (trans_dir / dest_name).write_bytes(photo_bytes)
                        saved.append(dest_name)
                    except Exception:
                        logger.exception("Failed to save nsenc photo %s", photo_name)
                if saved:
                    updated = proj_mod.set_transcript_photos(
                        STATE["folder"], updated, new_t["id"], saved)
        STATE["project"] = updated
        return jsonify({"ok": True, "project": updated, "count": imported})
    elif ext == ".zip":
        # --- Synchronous path: zip bundle → import each .md + photos inside ---
        import zipfile, re as _re
        if not zipfile.is_zipfile(tmp.name):
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({"error": "Ogiltig zip-fil."}), 400

        def _parse_zip_photos(md_text: str) -> list:
            """Return photos list from YAML frontmatter of an md string."""
            m = _re.match(r"\A---\n(.*?)\n---\n?", md_text, _re.DOTALL)
            if not m:
                return []
            fm = m.group(1)
            block = _re.search(r"^photos:\s*\n((?:[ \t]+-[ \t]+\S[^\n]*\n?)+)", fm, _re.MULTILINE)
            if block:
                return [i.strip() for i in _re.findall(r"[ \t]+-[ \t]+(\S[^\n]*)", block.group(1)) if i.strip()]
            inline = _re.search(r"^photos:\s*\[([^\]]*)\]", fm, _re.MULTILINE)
            if inline:
                return [i.strip() for i in inline.group(1).split(",") if i.strip()]
            return []

        try:
            with zipfile.ZipFile(tmp.name) as zf:
                zip_entries = set(zf.namelist())
                md_names = [n for n in zip_entries
                            if n.lower().endswith(".md") and not n.startswith("__MACOSX")]
            if not md_names:
                Path(tmp.name).unlink(missing_ok=True)
                return jsonify({"error": "Zip-filen innehåller inga .md-filer."}), 400
            updated = STATE["project"]
            imported = 0
            with zipfile.ZipFile(tmp.name) as zf:
                for md_name in md_names:
                    raw_bytes = zf.read(md_name)
                    # Try UTF-8 first; fall back to Latin-1 for pre-fix Notescribbler exports.
                    try:
                        md_text = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        md_text = raw_bytes.decode("latin-1")
                    md_tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
                    md_tmp.write(md_text.encode("utf-8"))
                    md_tmp.close()
                    note_name = Path(md_name).stem
                    old_tids = {t["id"] for t in updated.get("transcripts", [])}
                    try:
                        updated = proj_mod.add_transcript(
                            STATE["folder"], updated,
                            md_tmp.name, note_name,
                        )
                        imported += 1
                    except Exception:
                        logger.exception("add_transcript failed for zip entry: %s", md_name)
                        continue
                    finally:
                        Path(md_tmp.name).unlink(missing_ok=True)
                    # Save photos referenced in frontmatter from photos/ in zip.
                    new_t = next((t for t in updated["transcripts"] if t["id"] not in old_tids), None)
                    if new_t:
                        photo_refs = _parse_zip_photos(md_text)
                        saved = []
                        trans_dir = Path(STATE["folder"]) / "transcripts"
                        for n, photo_name in enumerate(photo_refs):
                            zip_photo = f"photos/{photo_name}"
                            if zip_photo not in zip_entries:
                                continue
                            photo_ext = Path(photo_name).suffix.lower()
                            dest_name = f'{new_t["id"]}_photo_{n}{photo_ext}'
                            try:
                                (trans_dir / dest_name).write_bytes(zf.read(zip_photo))
                                saved.append(dest_name)
                            except Exception:
                                logger.exception("Failed to save photo %s", zip_photo)
                        if saved:
                            updated = proj_mod.set_transcript_photos(
                                STATE["folder"], updated, new_t["id"], saved)
            STATE["project"] = updated
            return jsonify({"ok": True, "project": updated, "count": imported})
        except zipfile.BadZipFile:
            return jsonify({"error": "Ogiltig zip-fil."}), 400
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    else:
        # --- Synchronous path (text/docx/etc.) ---
        try:
            updated = proj_mod.add_transcript(
                STATE["folder"], STATE["project"],
                tmp.name, name or original_stem,
            )
            STATE["project"] = updated
            return jsonify({"ok": True, "project": updated})
        except Exception:
            logger.exception("add_transcript (sync) failed")
            return jsonify({"error": "Kunde inte importera filen."}), 500
        finally:
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                pass

    # --- Async path (audio) ---
    settings = {
        "language_choice":        request.form.get("language_choice", "sv"),
        "language":               request.form.get("language", "sv"),
        "model_size":             request.form.get("model", "medium"),
        "diarization":            request.form.get("diarization") == "1",
        "num_speakers":           request.form.get("num_speakers") or None,
        "min_speakers":           request.form.get("min_speakers") or None,
        "max_speakers":           request.form.get("max_speakers") or None,
        "segmentation_threshold": request.form.get("segmentation_threshold") or None,
        "clustering_threshold":   request.form.get("clustering_threshold") or None,
        "auto_identify":          request.form.get("auto_identify") == "1",
        "word_timestamps":        request.form.get("word_timestamps") == "1",
    }
    # Convert numeric strings and apply bounds
    for key in ("num_speakers", "min_speakers", "max_speakers"):
        if settings[key] is not None:
            try:
                settings[key] = max(1, min(int(settings[key]), 20))
            except ValueError:
                settings[key] = None
    for key in ("segmentation_threshold", "clustering_threshold"):
        if settings[key] is not None:
            try:
                settings[key] = max(0.0, min(float(settings[key]), 1.0))
            except ValueError:
                settings[key] = None

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "pending",
        "stage": "pending",
        "progress": 0.0,
        "result": None,
        "error": None,
    }

    t = threading.Thread(
        target=_transcription_job,
        args=(job_id, tmp.name, STATE["folder"],
              STATE["project"], name or original_stem, settings),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """Poll a background transcription job."""
    _cleanup_expired_jobs()
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Jobb hittades inte."}), 404
    # Stamp finish time on first poll after completion (for expiry cleanup)
    if job["status"] in ("done", "error") and "_finished_at" not in job:
        job["_finished_at"] = time.monotonic()
    result = job["result"] or {}
    return jsonify({
        "status":   job["status"],
        "stage":    job["stage"],
        "progress": job["progress"],
        "error":    job["error"],
        # audio job fields
        "speakers_found": result.get("speakers_found", []),
        "voice_matches":  result.get("voice_matches", {}),
        "diar_device":    result.get("diar_device"),
        # image OCR job fields
        "source":  result.get("source"),
        "project": result.get("project"),
    })


@app.route("/api/transcripts/commit/<job_id>", methods=["POST"])
def commit_transcript(job_id):
    """
    Finalise a completed transcription job.
    Body: {name: str, speakers: {SPEAKER_00: "Intervjuare", ...}}
    """
    err = _require_project()
    if err:
        return err

    job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Jobbet är inte klart eller hittades inte."}), 400

    data = request.json or {}
    speaker_map = data.get("speakers", {})
    name = data.get("name") or job["result"]["name"]

    result = job["result"]
    settings = result["settings"]
    segments = result["segments"]
    text = result["text"]
    audio_path = result["audio_path"]

    # Apply speaker name mapping to text and segments
    if speaker_map:
        for seg in segments:
            seg["speaker"] = speaker_map.get(seg["speaker"], seg["speaker"])
        lines = [f"[{seg['speaker']}]: {seg['text']}" for seg in segments if seg["text"]]
        text = "\n".join(lines)

    tid = str(uuid.uuid4())[:8]
    lang_choice = settings.get("language_choice", "sv")
    meta = {
        "whisper_model":        settings.get("model_size", "medium"),
        "language_choice":      lang_choice,
        "model_label":          _tr_mod.get_model_label(lang_choice),
        "language":             settings.get("language", "sv"),
        "diarization":          settings.get("diarization", False),
        "diarization_settings": {
            k: settings[k] for k in (
                "num_speakers", "min_speakers", "max_speakers",
                "segmentation_threshold", "clustering_threshold",
            ) if settings.get(k) is not None
        },
        "speakers": speaker_map,
    }

    try:
        with _PROJECT_LOCK:
            current = proj_mod.open_project(STATE["folder"])
            updated = proj_mod.add_audio_transcript(
                STATE["folder"], current,
                tid, name, audio_path, text, segments, meta,
            )
            STATE["project"] = updated
    except Exception:
        logger.exception("commit_transcript failed for job %s", job_id)
        # NOTE: do NOT pop the job or delete audio_path on failure — leaving
        # them in place lets the frontend retry the commit without losing
        # the (expensive) transcription/diarization result.
        return jsonify({"error": "Kunde inte spara transkriptet."}), 500

    # Success — now safe to clean up the temp audio file and job entry.
    try:
        Path(audio_path).unlink(missing_ok=True)
    except Exception:
        pass
    JOBS.pop(job_id, None)

    return jsonify({"ok": True, "project": updated})


# ---------------------------------------------------------------------------
# System info — helps users understand hardware capabilities
# ---------------------------------------------------------------------------

@app.route("/api/system-info", methods=["GET"])
def system_info():
    """Return system capabilities relevant to transcription performance."""
    import platform
    import shutil

    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "ram_gb": None,
        "gpu": "none",
        "disk_free_gb": None,
    }

    # RAM
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        # psutil not installed — try os-specific fallbacks
        try:
            if platform.system() == "Darwin":
                import subprocess
                mem = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip()
                info["ram_gb"] = round(int(mem) / (1024 ** 3), 1)
            elif platform.system() == "Linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            info["ram_gb"] = round(kb / (1024 ** 2), 1)
                            break
        except Exception:
            pass

    # GPU
    try:
        import torch
        if torch.backends.mps.is_available():
            info["gpu"] = "mps"
        elif torch.cuda.is_available():
            info["gpu"] = f"cuda ({torch.cuda.get_device_name(0)})"
    except Exception:
        pass

    # Disk free
    try:
        usage = shutil.disk_usage(Path.home())
        info["disk_free_gb"] = round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass

    # Warnings
    warnings = []
    if info["ram_gb"] and info["ram_gb"] < 6:
        warnings.append("low_ram")
    if info["gpu"] == "none":
        warnings.append("no_gpu")
    if info["disk_free_gb"] and info["disk_free_gb"] < 4:
        warnings.append("low_disk")
    info["warnings"] = warnings

    return jsonify(info)


# ---------------------------------------------------------------------------
# HF Token config
# ---------------------------------------------------------------------------

@app.route("/api/config/hf-token", methods=["GET"])
def get_hf_token():
    cfg = _load_config()
    return jsonify({"has_token": bool(cfg.get("hf_token"))})


@app.route("/api/config/hf-token", methods=["POST"])
def set_hf_token():
    token = (request.json or {}).get("token", "").strip()
    if not token:
        return jsonify({"error": "Token får inte vara tomt."}), 400

    # Validate by pinging HF API
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                return jsonify({"error": "Ogiltigt token (HF svarade med fel)."}), 400
    except Exception as exc:
        return jsonify({"error": f"Kunde inte validera token: {exc}"}), 400

    cfg = _load_config()
    cfg["hf_token"] = token
    _save_config(cfg)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Voice profile routes
# ---------------------------------------------------------------------------

@app.route("/api/voice-profile", methods=["GET"])
def get_voice_profile():
    """Return metadata about the current coder's voice profile (no embedding data)."""
    from core.transcribe import load_voice_profile
    coder = STATE.get("coder") or ""
    if not coder:
        return jsonify({"has_profile": False})
    profile = load_voice_profile(coder)
    if not profile:
        return jsonify({"has_profile": False})
    return jsonify({
        "has_profile": True,
        "coder":   profile.get("coder"),
        "model":   profile.get("model"),
        "dim":     profile.get("dim"),
        "created": profile.get("created"),
    })


@app.route("/api/voice-profile", methods=["DELETE"])
def delete_voice_profile_route():
    """Delete the current coder's voice profile."""
    from core.transcribe import delete_voice_profile
    coder = STATE.get("coder") or ""
    if not coder:
        return jsonify({"error": "Ingen kodare aktiv."}), 400
    deleted = delete_voice_profile(coder)
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/voice-profile/extract", methods=["POST"])
def extract_voice_profile():
    """
    Upload a short audio clip and extract+save a voice profile for the current coder.
    Runs synchronously (audio should be short: 30–120 s).
    """
    from core.transcribe import extract_voice_embedding, save_voice_profile
    coder = STATE.get("coder") or ""
    if not coder:
        return jsonify({"error": "Ingen kodare aktiv."}), 400

    if "file" not in request.files:
        return jsonify({"error": "Ingen fil skickades."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tomt filnamn."}), 400

    import tempfile
    suffix = Path(file.filename).suffix.lower() or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        file.save(tmp_path)

    try:
        embedding = extract_voice_embedding(tmp_path)
        profile = save_voice_profile(coder, embedding)
        return jsonify({
            "ok":      True,
            "coder":   profile["coder"],
            "dim":     profile["dim"],
            "created": profile["created"],
        })
    except Exception:
        logger.exception("Voice profile extraction failed")
        return jsonify({"error": "Kunde inte skapa röstprofil."}), 500
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/api/transcripts", methods=["POST"])
def add_transcript():
    """Legacy: accept a local file path (kept for scripting use)."""
    err = _require_project()
    if err:
        return err
    data = request.json
    src = data.get("path", "").strip()
    name = data.get("name", "").strip()
    if not src:
        return jsonify({"error": "path krävs."}), 400

    src_path = Path(src).resolve()
    if not src_path.is_file():
        return jsonify({"error": "Filen hittades inte."}), 400

    from core.transcribe import is_audio, transcribe_to_file
    import tempfile

    if is_audio(str(src_path)):
        model_size = data.get("model", "medium")
        language = data.get("language", "sv")
        tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        tmp.close()
        try:
            transcribe_to_file(str(src_path), tmp.name, language=language, model_size=model_size)
            src_path = Path(tmp.name)
            if not name:
                name = Path(data["path"]).stem
        except Exception:
            logger.exception("Legacy transcription failed: %s", src_path)
            return jsonify({"error": "Transkription misslyckades."}), 500

    try:
        updated = proj_mod.add_transcript(STATE["folder"], STATE["project"], str(src_path), name)
        STATE["project"] = updated
        return jsonify({"ok": True, "project": updated})
    except Exception:
        logger.exception("Legacy add_transcript failed: %s", src_path)
        return jsonify({"error": "Kunde inte lägga till transkript."}), 500


@app.route("/api/transcripts/<tid>/text", methods=["GET"])
def get_transcript_text(tid):
    err = _require_project()
    if err:
        return err
    t = next((t for t in STATE["project"]["transcripts"] if t["id"] == tid), None)
    if not t:
        return jsonify({"error": "Transkript hittades inte."}), 404
    text = proj_mod.get_transcript_text(STATE["folder"], t)
    return jsonify({"text": text})


@app.route("/api/transcripts/<tid>/text", methods=["PATCH"])
def update_transcript_text(tid):
    """Overwrite the plain-text content of a transcript."""
    err = _require_project()
    if err:
        return err
    t = next((t for t in STATE["project"]["transcripts"] if t["id"] == tid), None)
    if not t:
        return jsonify({"error": "Transkript hittades inte."}), 404
    text = (request.json or {}).get("text")
    if text is None:
        return jsonify({"error": "text krävs."}), 400
    try:
        txt_path = _safe_transcript_path(t["text_file"])
    except (ValueError, KeyError):
        return jsonify({"error": "Ogiltig filsökväg."}), 400
    try:
        txt_path.write_text(text, encoding="utf-8")
    except Exception:
        logger.exception("update_transcript_text failed for tid=%s", tid)
        return jsonify({"error": "Kunde inte spara texten."}), 500
    return jsonify({"ok": True})


@app.route("/api/search", methods=["GET"])
def project_search():
    """Full-text search across all transcripts in the project."""
    err = _require_project()
    if err:
        return err
    q = request.args.get("q", "").strip()[:500]   # cap at 500 chars
    if len(q) < 2:
        return jsonify({"results": [], "total_matches": 0, "query": q})

    SNIPPET_CTX       = 60   # chars of context before/after match
    MAX_PER_TRANSCRIPT = 100  # hard cap to keep response size sane

    folder      = STATE["folder"]
    transcripts = STATE["project"]["transcripts"]
    results     = []
    total_matches = 0
    q_lower = q.lower()

    for t in transcripts:
        txt_path = Path(folder) / "transcripts" / f"{t['id']}.txt"
        if not txt_path.exists():
            continue
        try:
            text = txt_path.read_text(encoding="utf-8")
        except Exception:
            continue

        text_lower = text.lower()
        matches = []
        pos = 0
        while (idx := text_lower.find(q_lower, pos)) != -1:
            snip_start = max(0, idx - SNIPPET_CTX)
            snip_end   = min(len(text), idx + len(q) + SNIPPET_CTX)
            prefix = "…" if snip_start > 0 else ""
            suffix = "…" if snip_end < len(text) else ""
            snippet = prefix + text[snip_start:snip_end].replace("\n", " ") + suffix
            matches.append({
                "start":               idx,
                "snippet":             snippet,
                "snippet_match_start": (idx - snip_start) + len(prefix),
            })
            pos = idx + len(q)
            if len(matches) >= MAX_PER_TRANSCRIPT:
                break

        if matches:
            results.append({"tid": t["id"], "name": t["name"], "matches": matches})
            total_matches += len(matches)

    return jsonify({"query": q, "results": results, "total_matches": total_matches})


@app.route("/api/transcripts/<tid>/audio", methods=["GET"])
def get_audio(tid):
    """Stream the audio file for an audio-sourced transcript."""
    err = _require_project()
    if err:
        return err
    t = next((t for t in STATE["project"]["transcripts"] if t["id"] == tid), None)
    if not t or not t.get("audio_file"):
        return jsonify({"error": "Ingen ljudfil hittades."}), 404
    try:
        audio_path = _safe_transcript_path(t["audio_file"])
    except ValueError:
        return jsonify({"error": "Ogiltig filsökväg."}), 400
    if not audio_path.exists():
        return jsonify({"error": "Ljudfilen saknas på disk."}), 404
    return send_from_directory(str(audio_path.parent), audio_path.name)


@app.route("/api/transcripts/<tid>/source-image", methods=["GET"])
def get_source_image(tid):
    """Serve the original source image for an image-sourced transcript."""
    err = _require_project()
    if err:
        return err
    t = next((t for t in STATE["project"]["transcripts"] if t["id"] == tid), None)
    if not t or not t.get("source_file"):
        return jsonify({"error": "Ingen källbild hittades."}), 404
    try:
        img_path = _safe_transcript_path(t["source_file"])
    except ValueError:
        return jsonify({"error": "Ogiltig filsökväg."}), 400
    if not img_path.exists():
        return jsonify({"error": "Källbilden saknas på disk."}), 404
    # HEIC/HEIF not supported by browsers — convert to JPEG on-the-fly
    if img_path.suffix.lower() in (".heic", ".heif"):
        data = _heic_to_jpeg_bytes(img_path)
        if data:
            return app.response_class(data, mimetype="image/jpeg")
    return send_from_directory(str(img_path.parent), img_path.name)


@app.route("/api/transcripts/<tid>/photo/<int:n>", methods=["GET"])
def get_transcript_photo(tid, n):
    """Serve the nth attached photo for a transcript (imported from Notescribbler zip)."""
    err = _require_project()
    if err:
        return err
    t = next((t for t in STATE["project"]["transcripts"] if t["id"] == tid), None)
    if not t:
        return "", 404
    photos = t.get("photos", [])
    if n < 0 or n >= len(photos):
        return "", 404
    try:
        photo_path = _safe_transcript_path(photos[n])
    except ValueError:
        return "", 400
    if not photo_path.exists():
        return "", 404
    if photo_path.suffix.lower() in (".heic", ".heif"):
        data = _heic_to_jpeg_bytes(photo_path)
        if data:
            return app.response_class(data, mimetype="image/jpeg")
    ext = photo_path.suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    return send_from_directory(str(photo_path.parent), photo_path.name, mimetype=mime)


@app.route("/api/transcripts/<tid>/ocr-boxes", methods=["GET"])
def get_ocr_boxes(tid):
    """Return saved OCR bounding boxes for an image transcript."""
    err = _require_project()
    if err:
        return err
    boxes_path = Path(STATE["folder"]) / "transcripts" / f"{tid}_ocr_boxes.json"
    if not boxes_path.exists():
        return jsonify({"boxes": []})
    boxes = json.loads(boxes_path.read_text(encoding="utf-8"))
    return jsonify({"boxes": boxes})


def _ocr_photos_job(job_id: str, tid: str, folder: str, photo_paths: list):
    """Background job: OCR each attached photo and append extracted text to transcript."""
    from core.ocr import ocr_image
    JOBS[job_id]["status"] = "running"
    try:
        texts = []
        for i, photo_path in enumerate(photo_paths):
            JOBS[job_id]["stage"] = f"ocr_{i+1}_of_{len(photo_paths)}"
            JOBS[job_id]["progress"] = i / len(photo_paths)
            result = ocr_image(photo_path)
            t = result.get("text", "").strip()
            if t:
                texts.append(t)

        if not texts:
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["result"] = {"appended": 0}
            return

        # Append to transcript .txt
        txt_path = Path(folder) / "transcripts" / f"{tid}.txt"
        existing = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""
        separator = "\n\n---\n\n"
        appended = separator.join(texts)
        txt_path.write_text(
            (existing.rstrip() + separator + appended) if existing.strip() else appended,
            encoding="utf-8",
        )

        JOBS[job_id]["result"] = {"appended": len(texts), "text": txt_path.read_text(encoding="utf-8")}
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["progress"] = 1.0
    except Exception:
        logger.exception("ocr_photos job %s failed", job_id)
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = "OCR misslyckades."


@app.route("/api/transcripts/<tid>/ocr-photos", methods=["POST"])
def ocr_transcript_photos(tid):
    """Start a background OCR job on all attached photos for a transcript."""
    err = _require_project()
    if err:
        return err
    t = next((t for t in STATE["project"]["transcripts"] if t["id"] == tid), None)
    if not t:
        return jsonify({"error": "Transkriptet hittades inte."}), 404
    photos = t.get("photos", [])
    if not photos:
        return jsonify({"error": "Inga foton att OCR:a."}), 400
    photo_paths = []
    for p in photos:
        try:
            resolved = _safe_transcript_path(p)
            if resolved.exists():
                photo_paths.append(str(resolved))
        except ValueError:
            pass
    if not photo_paths:
        return jsonify({"error": "Fotofiler saknas på disk."}), 404
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "stage": "pending", "progress": 0.0, "result": None, "error": None}
    threading.Thread(
        target=_ocr_photos_job,
        args=(job_id, tid, STATE["folder"], photo_paths),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id})


@app.route("/api/transcripts/<tid>/segments", methods=["GET"])
def get_segments(tid):
    """Return diarization segments for a transcript (if available)."""
    err = _require_project()
    if err:
        return err
    seg_path = Path(STATE["folder"]) / "transcripts" / f"{tid}_segments.json"
    if not seg_path.exists():
        return jsonify({"segments": []})
    with open(seg_path, encoding="utf-8") as f:
        segs = json.load(f)
    return jsonify({"segments": segs})


@app.route("/api/transcripts/<tid>", methods=["DELETE"])
def delete_transcript(tid):
    err = _require_project()
    if err:
        return err
    STATE["project"] = proj_mod.remove_transcript(STATE["folder"], STATE["project"], tid)
    return jsonify({"ok": True, "project": STATE["project"]})


@app.route("/api/transcripts/<tid>/memo", methods=["PATCH"])
def update_transcript_memo(tid):
    err = _require_project()
    if err:
        return err
    memo = request.json.get("memo", "")
    for t in STATE["project"]["transcripts"]:
        if t["id"] == tid:
            t["memo"] = memo
            break
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True})


@app.route("/api/transcripts/<tid>/rename", methods=["PATCH"])
def rename_transcript(tid):
    err = _require_project()
    if err:
        return err
    new_name = (request.json.get("name") or "").strip()
    if not new_name:
        return jsonify({"error": "Namn får inte vara tomt."}), 400
    for t in STATE["project"]["transcripts"]:
        if t["id"] == tid:
            t["name"] = new_name
            break
    else:
        return jsonify({"error": "Transkript hittades inte."}), 404
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True, "name": new_name})


@app.route("/api/transcripts/categorize", methods=["PATCH"])
def categorize_transcripts():
    err = _require_project()
    if err:
        return err
    data = request.json or {}
    tids = set(data.get("tids") or [])
    category = data.get("category")
    if isinstance(category, str):
        category = category.strip() or None
    for tr in STATE["project"]["transcripts"]:
        if tr["id"] in tids:
            if category is None:
                tr.pop("category", None)
            else:
                tr["category"] = category
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True, "project": STATE["project"]})


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@app.route("/api/stats", methods=["GET"])
def get_stats():
    err = _require_project()
    if err:
        return err
    from core.stats import compute_stats
    tid = request.args.get("tid") or None
    return jsonify(compute_stats(STATE["folder"], STATE["project"], tid))


# ---------------------------------------------------------------------------
# Inter-rater reliability
# ---------------------------------------------------------------------------

@app.route("/api/transcripts/<tid>/irr", methods=["GET"])
def get_irr(tid):
    err = _require_project()
    if err:
        return err
    coder_a = request.args.get("coder_a", "").strip()
    coder_b = request.args.get("coder_b", "").strip()
    if not coder_a or not coder_b:
        return jsonify({"error": "coder_a och coder_b krävs."}), 400
    if coder_a == coder_b:
        return jsonify({"error": "Välj två olika kodare."}), 400
    from core.irr import cohens_kappa
    try:
        result = cohens_kappa(STATE["folder"], STATE["project"], tid, coder_a, coder_b)
        return jsonify(result)
    except Exception:
        logger.exception("IRR calculation failed")
        return jsonify({"error": "Kunde inte beräkna IRR."}), 500


@app.route("/api/coders", methods=["GET"])
def get_coders():
    """List all coders who have annotation files in this project."""
    err = _require_project()
    if err:
        return err
    ann_dir = Path(STATE["folder"]) / "annotations"
    coders = set()
    if ann_dir.exists():
        for f in ann_dir.glob("*.*.json"):
            # filename: {tid}.{coder}.json
            parts = f.stem.split(".", 1)
            if len(parts) == 2:
                coders.add(parts[1])
    return jsonify({"coders": sorted(coders)})


# ---------------------------------------------------------------------------
# Codebook routes
# ---------------------------------------------------------------------------

@app.route("/api/codes", methods=["GET"])
def get_codes():
    err = _require_project()
    if err:
        return err
    return jsonify({
        "tree": cb_mod.build_tree(STATE["project"]),
        "flat": cb_mod.flat_list(STATE["project"]),
    })


@app.route("/api/codes", methods=["POST"])
def add_code():
    err = _require_project()
    if err:
        return err
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name krävs."}), 400
    STATE["project"] = cb_mod.add_code(
        STATE["project"],
        name=name,
        parent=data.get("parent") or None,
        color=data.get("color", "#4a90d9"),
        description=data.get("description", ""),
    )
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True, "project": STATE["project"]})


@app.route("/api/codes/<code_id>", methods=["PATCH"])
def update_code(code_id):
    err = _require_project()
    if err:
        return err
    data = request.json
    STATE["project"] = cb_mod.update_code(STATE["project"], code_id, **data)
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True, "project": STATE["project"]})


@app.route("/api/codes/<code_id>", methods=["DELETE"])
def delete_code(code_id):
    err = _require_project()
    if err:
        return err
    STATE["project"] = cb_mod.delete_code(STATE["project"], code_id)
    proj_mod.save_project(STATE["folder"], STATE["project"])
    return jsonify({"ok": True, "project": STATE["project"]})


# ---------------------------------------------------------------------------
# Annotation routes
# ---------------------------------------------------------------------------

@app.route("/api/transcripts/<tid>/annotations", methods=["GET"])
def get_annotations(tid):
    err = _require_project()
    if err:
        return err
    coder = request.args.get("coder", STATE["coder"])
    anns = ann_mod.load_annotations(STATE["folder"], tid, coder)
    return jsonify({"annotations": anns})


@app.route("/api/transcripts/<tid>/annotations/all", methods=["GET"])
def get_all_annotations(tid):
    err = _require_project()
    if err:
        return err
    all_coders = ann_mod.load_all_coders(STATE["folder"], tid)
    return jsonify({"by_coder": all_coders})


@app.route("/api/transcripts/<tid>/annotations", methods=["POST"])
def add_annotation(tid):
    err = _require_project()
    if err:
        return err
    data = request.json
    kind = data.get("kind", "text")
    if kind == "point":
        required = {"code_id", "x", "y"}
        if not required.issubset(data):
            return jsonify({"error": f"Fält saknas: {required - data.keys()}"}), 400
        ann = ann_mod.add_annotation(
            STATE["folder"], tid, STATE["coder"],
            code_id=data["code_id"],
            kind="point",
            x=data["x"], y=data["y"],
            memo=data.get("memo", ""),
            weight=int(data.get("weight", 50)),
            anchor=bool(data.get("anchor", False)),
        )
    else:
        required = {"code_id", "start", "end", "text"}
        if not required.issubset(data):
            return jsonify({"error": f"Fält saknas: {required - data.keys()}"}), 400
        ann = ann_mod.add_annotation(
            STATE["folder"], tid, STATE["coder"],
            code_id=data["code_id"],
            start=data["start"],
            end=data["end"],
            text=data["text"],
            memo=data.get("memo", ""),
            weight=int(data.get("weight", 50)),
            anchor=bool(data.get("anchor", False)),
        )
    return jsonify({"ok": True, "annotation": ann})


@app.route("/api/transcripts/<tid>/annotations/<ann_id>", methods=["PATCH"])
def update_annotation(tid, ann_id):
    err = _require_project()
    if err:
        return err
    data = request.json
    ok = ann_mod.update_annotation(STATE["folder"], tid, STATE["coder"], ann_id, **data)
    return jsonify({"ok": ok})


@app.route("/api/transcripts/<tid>/annotations/<ann_id>", methods=["DELETE"])
def delete_annotation(tid, ann_id):
    err = _require_project()
    if err:
        return err
    ok = ann_mod.delete_annotation(STATE["folder"], tid, STATE["coder"], ann_id)
    return jsonify({"ok": ok})


# ---------------------------------------------------------------------------
# Merge / collaboration routes
# ---------------------------------------------------------------------------

@app.route("/api/merge", methods=["POST"])
def merge():
    err = _require_project()
    if err:
        return err
    data = request.json
    src = data.get("path", "").strip()
    if not src:
        return jsonify({"error": "path krävs."}), 400
    src_path = Path(src).resolve()
    if not src_path.is_file():
        return jsonify({"error": "Filen hittades inte."}), 400
    if src_path.suffix.lower() != ".json":
        return jsonify({"error": "Filen måste vara en JSON-fil (.json)."}), 400
    try:
        result = merge_mod.import_coder_file(STATE["folder"], str(src_path))
        return jsonify({"ok": True, **result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Merge failed: %s", src_path)
        return jsonify({"error": "Importen misslyckades."}), 500


@app.route("/api/transcripts/<tid>/conflicts", methods=["GET"])
def get_conflicts(tid):
    err = _require_project()
    if err:
        return err
    conflicts = merge_mod.detect_conflicts(STATE["folder"], tid)
    return jsonify({"conflicts": conflicts})


# ---------------------------------------------------------------------------
# Export routes
# ---------------------------------------------------------------------------

def _export_filename(stem: str, ext: str) -> str:
    """Build a safe filename: <stem>_<project>_<date>.<ext>"""
    from datetime import date
    import re
    proj_name = STATE.get("project", {}).get("name", "") if STATE.get("project") else ""
    safe = re.sub(r"[^\w\-]+", "_", proj_name).strip("_") if proj_name else ""
    date_str = date.today().strftime("%Y-%m-%d")
    parts = [stem]
    if safe:
        parts.append(safe)
    parts.append(date_str)
    return "_".join(parts) + "." + ext


@app.route("/api/export/csv/tidy", methods=["GET"])
def export_csv_tidy():
    err = _require_project()
    if err:
        return err
    tid = request.args.get("tid") or None
    csv_data = exp_mod.export_csv_tidy(STATE["folder"], STATE["project"], tid)
    fname = _export_filename("annoteringar_tidy", "csv")
    return app.response_class(csv_data, mimetype="text/csv",
                              headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    err = _require_project()
    if err:
        return err
    tid = request.args.get("tid") or None
    csv_data = exp_mod.export_csv(STATE["folder"], STATE["project"], tid)
    fname = _export_filename("annoteringar", "csv")
    return app.response_class(csv_data, mimetype="text/csv",
                              headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.route("/api/export/markdown/codes", methods=["GET"])
def export_md_codes():
    err = _require_project()
    if err:
        return err
    tid = request.args.get("tid") or None
    md = exp_mod.export_markdown_by_code(STATE["folder"], STATE["project"], tid)
    return app.response_class(md, mimetype="text/markdown",
                              headers={"Content-Disposition": "attachment; filename=citat_per_kod.md"})


@app.route("/api/export/markdown/codebook", methods=["GET"])
def export_md_codebook():
    err = _require_project()
    if err:
        return err
    md = exp_mod.export_markdown_codebook(STATE["project"])
    return app.response_class(md, mimetype="text/markdown",
                              headers={"Content-Disposition": "attachment; filename=kodbok.md"})


@app.route("/api/codes/stats", methods=["GET"])
def get_codes_stats():
    err = _require_project()
    if err:
        return err
    from core.stats import compute_stats
    result = compute_stats(STATE["folder"], STATE["project"])
    counts = {r["code_id"]: r["count"] for r in result["rows"]}
    return jsonify(counts)


@app.route("/api/export/codebook/csv", methods=["GET"])
def export_codebook_csv():
    err = _require_project()
    if err:
        return err
    from core.stats import compute_stats
    result = compute_stats(STATE["folder"], STATE["project"])
    counts = {r["code_id"]: r["count"] for r in result["rows"]}
    csv_data = exp_mod.export_codebook_csv(STATE["project"], counts)
    return app.response_class(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_export_filename("kodbok", "csv")}"'},
    )


@app.route("/api/export/markdown/transcript/<tid>", methods=["GET"])
def export_md_transcript(tid):
    err = _require_project()
    if err:
        return err
    coder = request.args.get("coder", STATE["coder"])
    md = exp_mod.export_markdown_transcript(STATE["folder"], STATE["project"], tid, coder)
    return app.response_class(md, mimetype="text/markdown",
                              headers={"Content-Disposition": f"attachment; filename=transkript_{tid}.md"})


# ---------------------------------------------------------------------------
# Code matrix routes (transkript × kod)
# ---------------------------------------------------------------------------

@app.route("/api/code-matrix", methods=["GET"])
def get_code_matrix():
    err = _require_project()
    if err:
        return err
    from core.code_matrix import compute_code_matrix
    return jsonify(compute_code_matrix(STATE["folder"], STATE["project"]))


@app.route("/api/export/code-matrix/csv", methods=["GET"])
def export_code_matrix_csv():
    err = _require_project()
    if err:
        return err
    import io, csv
    from core.code_matrix import compute_code_matrix
    data = compute_code_matrix(STATE["folder"], STATE["project"])
    buf = io.StringIO()
    w = csv.writer(buf)
    header = ["Transkript"] + [c["name"] for c in data["codes"]]
    w.writerow(header)
    for t in data["transcripts"]:
        row = [t["name"]] + [data["matrix"].get(t["id"], {}).get(c["id"], 0)
                              for c in data["codes"]]
        w.writerow(row)
    totals_row = ["TOTALT"] + [data["totals"].get(c["id"], 0) for c in data["codes"]]
    w.writerow(totals_row)
    return app.response_class(
        buf.getvalue().encode("utf-8-sig"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_export_filename("kodmatris", "csv")}"'},
    )


# ---------------------------------------------------------------------------
# Co-occurrence routes (kod × kod)
# ---------------------------------------------------------------------------

@app.route("/api/cooccurrence", methods=["GET"])
def get_cooccurrence():
    err = _require_project()
    if err:
        return err
    from core.cooccurrence import compute_cooccurrence
    return jsonify(compute_cooccurrence(STATE["folder"], STATE["project"]))


@app.route("/api/export/cooccurrence/csv", methods=["GET"])
def export_cooccurrence_csv():
    err = _require_project()
    if err:
        return err
    import io, csv
    from core.cooccurrence import compute_cooccurrence
    data = compute_cooccurrence(STATE["folder"], STATE["project"])
    codes = data["codes"]
    matrix = data["matrix"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([""] + [c["name"] for c in codes])
    for ca in codes:
        row = [ca["name"]] + [matrix.get(ca["id"], {}).get(cb["id"], 0) for cb in codes]
        w.writerow(row)
    return app.response_class(
        buf.getvalue().encode("utf-8-sig"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_export_filename("kodoverlapp", "csv")}"'},
    )


# ---------------------------------------------------------------------------
# QDPX export route (REFI-QDA standard)
# ---------------------------------------------------------------------------

@app.route("/api/export/qdpx", methods=["GET"])
def export_qdpx():
    err = _require_project()
    if err:
        return err
    from core.qdpx import export_qdpx as _export_qdpx
    zip_bytes = _export_qdpx(STATE["folder"], STATE["project"])
    proj_name = STATE["project"].get("name", "projekt").replace(" ", "_")
    return app.response_class(
        zip_bytes,
        mimetype="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{proj_name}.qdpx"'},
    )


# ---------------------------------------------------------------------------
# Anchor quote route — get the anchor annotation for a code
# ---------------------------------------------------------------------------

@app.route("/api/codes/<code_id>/anchor", methods=["GET"])
def get_anchor_quote(code_id):
    err = _require_project()
    if err:
        return err
    from core.annotation import load_all_coders as _load_all
    for t in STATE["project"].get("transcripts", []):
        all_coders = _load_all(STATE["folder"], t["id"])
        for coder_anns in all_coders.values():
            for ann in coder_anns:
                if ann.get("code_id") == code_id and ann.get("anchor"):
                    return jsonify({"ok": True, "annotation": ann,
                                    "transcript": t.get("name", t["id"])})
    return jsonify({"ok": True, "annotation": None})


@app.route("/api/codes/anchors", methods=["GET"])
def get_all_anchors():
    """Return {code_id: {text, tid}} for every code that has an anchor annotation."""
    err = _require_project()
    if err:
        return err
    from core.annotation import load_all_coders as _load_all
    result = {}
    for t in STATE["project"].get("transcripts", []):
        all_coders = _load_all(STATE["folder"], t["id"])
        for coder_anns in all_coders.values():
            for ann in coder_anns:
                cid = ann.get("code_id")
                if cid and ann.get("anchor") and cid not in result:
                    result[cid] = {"text": ann.get("text", ""), "tid": t["id"]}
    return jsonify(result)


# ---------------------------------------------------------------------------
# Formatting routes
# ---------------------------------------------------------------------------

@app.route("/api/transcripts/<tid>/formatting", methods=["GET"])
def get_formatting(tid):
    err = _require_project()
    if err:
        return err
    from core.formatting import load_formatting
    spans = load_formatting(STATE["folder"], tid, STATE["coder"])
    return jsonify({"spans": spans})


@app.route("/api/transcripts/<tid>/formatting", methods=["POST"])
def add_formatting(tid):
    err = _require_project()
    if err:
        return err
    from core.formatting import add_format_span
    data = request.json
    try:
        span = add_format_span(
            STATE["folder"], tid, STATE["coder"],
            start=data["start"], end=data["end"], fmt_type=data["type"]
        )
        return jsonify({"ok": True, "span": span})
    except Exception:
        logger.exception("add_format_span failed for tid=%s", tid)
        return jsonify({"error": "Kunde inte lägga till formatering."}), 500


@app.route("/api/transcripts/<tid>/formatting/<span_id>", methods=["DELETE"])
def delete_formatting(tid, span_id):
    err = _require_project()
    if err:
        return err
    from core.formatting import delete_format_span
    ok = delete_format_span(STATE["folder"], tid, STATE["coder"], span_id)
    return jsonify({"ok": ok})


# ---------------------------------------------------------------------------
# Code tree export routes
# ---------------------------------------------------------------------------

@app.route("/api/export/codetree/docx", methods=["GET"])
def export_codetree_docx():
    err = _require_project()
    if err:
        return err
    from core.export import export_codetree_docx as _docx
    data = _docx(STATE["project"])
    return app.response_class(
        data, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=kodtrad.docx"})


@app.route("/api/export/codetree/odt", methods=["GET"])
def export_codetree_odt():
    err = _require_project()
    if err:
        return err
    from core.export import export_codetree_odt as _odt
    data = _odt(STATE["project"])
    return app.response_class(
        data, mimetype="application/vnd.oasis.opendocument.text",
        headers={"Content-Disposition": "attachment; filename=kodtrad.odt"})


@app.route("/api/export/to-folder", methods=["POST"])
def export_to_folder():
    err = _require_project()
    if err:
        return err
    data = request.json or {}
    dest_str = (data.get("folder") or "").strip()
    formats = data.get("formats") or []
    tid = data.get("tid") or None

    if not dest_str:
        return jsonify({"error": "Ingen mapp angiven."}), 400

    dest = Path(dest_str)
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("export_to_folder mkdir failed: %s", dest_str)
        return jsonify({"error": "Kunde inte skapa exportmappen."}), 400

    written = []

    if "csv_tidy" in formats:
        csv_data = exp_mod.export_csv_tidy(STATE["folder"], STATE["project"], tid)
        fname = _export_filename("annoteringar_tidy", "csv")
        (dest / fname).write_text(csv_data, encoding="utf-8")
        written.append(fname)

    if "csv" in formats:
        csv_data = exp_mod.export_csv(STATE["folder"], STATE["project"], tid)
        (dest / "export.csv").write_text(csv_data, encoding="utf-8")
        written.append("export.csv")

    if "md_codes" in formats:
        md = exp_mod.export_markdown_by_code(STATE["folder"], STATE["project"], tid)
        (dest / "citat_per_kod.md").write_text(md, encoding="utf-8")
        written.append("citat_per_kod.md")

    if "md_codebook" in formats:
        md = exp_mod.export_markdown_codebook(STATE["project"])
        (dest / "kodbok.md").write_text(md, encoding="utf-8")
        written.append("kodbok.md")

    if "md_transcript" in formats:
        if not tid:
            return jsonify({"error": "Inget transkript öppet för detta exportformat."}), 400
        coder = STATE["coder"]
        md = exp_mod.export_markdown_transcript(STATE["folder"], STATE["project"], tid, coder)
        (dest / f"transkript_{tid}.md").write_text(md, encoding="utf-8")
        written.append(f"transkript_{tid}.md")

    if "qdpx" in formats:
        from core.qdpx import export_qdpx as _export_qdpx
        proj_name = STATE["project"].get("name", "projekt").replace(" ", "_")
        fname = f"{proj_name}.qdpx"
        (dest / fname).write_bytes(_export_qdpx(STATE["folder"], STATE["project"]))
        written.append(fname)

    return jsonify({"ok": True, "written": written, "folder": dest_str})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def open_browser(port):
    webbrowser.open(f"http://127.0.0.1:{port}")


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT,  lambda *_: os._exit(0))
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))

    port = int(os.environ.get("PORT", 5050))
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, open_browser, args=[port]).start()
    print(f"Transcribbler körs på http://127.0.0.1:{port}")
    app.run(port=port, debug=False, use_reloader=False)
