"""
transcribe.py — Whisper-based audio transcription + Pyannote diarization.

Transcription backend: faster-whisper (CTranslate2) for all language choices.
  - "sv" / "autodetect" → KBLab/kb-whisper-large, auto-converted to CTranslate2 INT8
                           on first use (~30 s one-time), cached at
                           ~/.cache/transcribbler/kb-whisper-ct2/. CPU-only.
  - "en" / "other"      → openai/whisper-medium (downloaded automatically by
                           faster-whisper from Systran/faster-whisper-medium).
                           Uses CUDA if available, otherwise CPU.

Models are loaded lazily on first use and cached indefinitely in-process.
"""
from __future__ import annotations  # X | Y union hints on Python 3.9
import json
from datetime import datetime
from pathlib import Path

SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac", ".webm"}

# ---------------------------------------------------------------------------
# PyTorch 2.6+ compatibility: patch torch.load to use weights_only=False
# (lightning_fabric/pyannote checkpoint loading requires this)
# ---------------------------------------------------------------------------
def _patch_torch_load():
    try:
        import torch
        import torch.serialization
        import torch.torch_version

        # Fix 1: whitelist TorchVersion in safe-globals mode (PyTorch 2.6+).
        # This allows weights_only=True loads that reference TorchVersion.
        if hasattr(torch.serialization, "add_safe_globals"):
            try:
                torch.serialization.add_safe_globals([torch.torch_version.TorchVersion])
            except Exception:
                pass

        # Fix 2: patch BOTH torch.load and torch.serialization.load so that
        # any caller — including pyannote/lightning_fabric code that does
        # `from torch.serialization import load` — gets weights_only=False.
        # Use dict assignment (not setdefault) so we override even when
        # lightning_fabric explicitly passes weights_only=True.
        _orig = torch.serialization.load
        def _safe_load(f, *args, **kwargs):
            kwargs["weights_only"] = False  # force False; pyannote checkpoints are trusted
            return _orig(f, *args, **kwargs)
        torch.load = _safe_load
        torch.serialization.load = _safe_load
    except Exception:
        pass

_patch_torch_load()

# ---------------------------------------------------------------------------
# Module-level model caches (loaded once, never evicted)
# ---------------------------------------------------------------------------
_FW_MODEL_CACHE: dict = {}  # cache_key → faster_whisper.WhisperModel instance
_ECAPA_MODEL = None         # SpeechBrain ECAPA-TDNN for speaker embeddings
_DIAR_PIPELINE = None       # pyannote SpeakerDiarization pipeline (cached, token-agnostic)

# ---------------------------------------------------------------------------
# Voice profile storage (global per-coder, in home dir)
# ---------------------------------------------------------------------------
VOICE_PROFILES_DIR = Path.home() / ".transcribbler_voice_profiles"


def is_audio(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO


def get_model_label(language_choice: str) -> str:
    return {
        "autodetect": "KB-Whisper (autodetect)",
        "sv":         "KB-Whisper (svenska)",
        "en":         "Whisper (engelska)",
        "other":      "Whisper (övrigt)",
    }.get(language_choice, "Whisper")


def _use_kb_whisper(language_choice: str) -> bool:
    return language_choice in ("autodetect", "sv")


def _convert_kb_whisper_to_ct2(output_dir: Path):
    """
    One-time conversion of KBLab/kb-whisper-large from HuggingFace transformers
    format to CTranslate2/INT8 format for use with faster-whisper.

    Reads from the local HF cache (model must have been downloaded previously).
    Writes to output_dir (~1.4 GB). Takes ~30 seconds on an M-series Mac.
    The result is cached; subsequent calls are instant because force=False skips
    existing conversions.
    """
    import logging
    _log = logging.getLogger("transcribbler")
    _log.info("Converting KBLab/kb-whisper-large → CTranslate2/INT8 at %s (one-time, ~30 s)",
              output_dir)
    try:
        import ctranslate2
    except ImportError:
        raise ImportError("ctranslate2 is required. Run: pip install faster-whisper")
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = ctranslate2.converters.TransformersConverter(
        "KBLab/kb-whisper-large",
        low_cpu_mem_usage=True,
    )
    converter.convert(str(output_dir), quantization="int8", force=False)
    _log.info("KB-Whisper CTranslate2 conversion complete → %s", output_dir)


def _patch_ct2_config_mel_bins(ct2_path: Path, n_mels: int = 128):
    """Ensure preprocessor_config.json exists with the correct feature_size.

    faster-whisper reads the feature extractor config from preprocessor_config.json
    (not config.json). If that file is missing, FeatureExtractor defaults to
    feature_size=80. Whisper-large models require 128 mel bins.
    """
    import json
    import logging
    log = logging.getLogger("transcribbler")
    preprocessor_path = ct2_path / "preprocessor_config.json"
    try:
        config = json.loads(preprocessor_path.read_text()) if preprocessor_path.exists() else {}
        if config.get("feature_size") != n_mels:
            config["feature_size"] = n_mels
            preprocessor_path.write_text(json.dumps(config, indent=2))
            log.info("Wrote %s: feature_size=%d", preprocessor_path, n_mels)
    except Exception as exc:
        log.warning("Could not write preprocessor config: %s", exc)


def _load_faster_whisper_model(language_choice: str, model_size: str = "medium"):
    """
    Load and cache a faster-whisper (CTranslate2) model.

    Backends:
      "sv" / "autodetect" → KBLab/kb-whisper-large, INT8, CPU-only
        The model is auto-converted from the local HF cache on first use
        and stored in ~/.cache/transcribbler/kb-whisper-ct2/.
        CPU is enforced because CTranslate2's MPS backend for Whisper
        is untested; we already know the transformers MPS backend produces
        garbage output for long audio. CPU on M-series chips is fast enough
        (~4–6× realtime with CTranslate2/INT8 vs ~1.7× with transformers).

      "en" / "other" → openai/whisper-{model_size}, INT8, CUDA or CPU
        faster-whisper downloads pre-converted models automatically from
        Systran/faster-whisper-{model_size} on HuggingFace. CUDA is used
        when available; CPU otherwise. MPS skipped (no CTranslate2 MPS
        support confirmed as of 2026).
    """
    import logging
    _log = logging.getLogger("transcribbler")

    cache_key = language_choice if language_choice in ("sv", "autodetect") else model_size
    if cache_key in _FW_MODEL_CACHE:
        return _FW_MODEL_CACHE[cache_key]

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("faster-whisper is not installed. Run: pip install faster-whisper")

    if language_choice in ("sv", "autodetect"):
        ct2_path = Path.home() / ".cache" / "transcribbler" / "kb-whisper-ct2"
        if not (ct2_path / "model.bin").exists():
            _convert_kb_whisper_to_ct2(ct2_path)
        # faster-whisper reads num_mel_bins from config.json to init the feature
        # extractor. The CT2 converter doesn't always copy this field, causing it
        # to default to 80 instead of 128 (whisper-large uses 128 mel bins).
        _patch_ct2_config_mel_bins(ct2_path, n_mels=128)
        model = WhisperModel(str(ct2_path), device="cpu", compute_type="int8")
        _log.info("KB-Whisper (faster-whisper/CTranslate2 INT8) loaded on CPU")
    else:
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
        compute_type = "int8_float16" if device == "cuda" else "int8"
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        _log.info("Whisper-%s (faster-whisper/CTranslate2 %s) loaded on %s",
                  model_size, compute_type, device)

    _FW_MODEL_CACHE[cache_key] = model
    return model


# ---------------------------------------------------------------------------
# Plain transcription (no diarization)
# ---------------------------------------------------------------------------

def transcribe(audio_path: str, language: str = "sv",
               model_size: str = "medium",
               language_choice: str = "sv") -> str:
    """
    Transcribe audio and return plain text (no diarization).
    language_choice drives which backend is used:
      "autodetect" / "sv"   → KBLab/kb-whisper-large (faster-whisper/CTranslate2 INT8)
      "en"                  → faster-whisper "medium", language forced to "en"
      "other"               → faster-whisper "medium", task="transcribe", no forced language
    """
    model = _load_faster_whisper_model(language_choice, model_size)
    # Determine forced language (None = auto-detect for "autodetect" and "other")
    if language_choice == "sv":
        lang = "sv"
    elif language_choice == "en":
        lang = language  # caller-supplied language code, default "en"
    else:
        lang = None
    fw_segments, _ = model.transcribe(
        audio_path,
        language=lang,
        task="transcribe",
        vad_filter=True,
    )
    # fw_segments is a generator — iterate once to collect all text
    return " ".join(seg.text.strip() for seg in fw_segments).strip()


def transcribe_to_file(audio_path: str, out_path: str,
                       language: str = "sv", model_size: str = "medium",
                       language_choice: str = "sv") -> str:
    """Transcribe and write result to out_path. Returns the text."""
    text = transcribe(audio_path, language=language, model_size=model_size,
                      language_choice=language_choice)
    Path(out_path).write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# Pyannote diarization helpers
# ---------------------------------------------------------------------------

def _load_diarization_pipeline(hf_token: str, settings: dict):
    """
    Load and configure the pyannote SpeakerDiarization 3.1 pipeline.
    The base model is cached after first load; threshold overrides are applied
    each call (they mutate pipeline state in-place and must be re-applied).
    Raises ImportError if pyannote.audio is not installed.
    """
    global _DIAR_PIPELINE
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        raise ImportError(
            "pyannote.audio is not installed. "
            "Run: pip install pyannote.audio"
        )

    if _DIAR_PIPELINE is None:
        _DIAR_PIPELINE = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )
        # Move pipeline to GPU if available. Without this, pyannote silently
        # runs on CPU and is 20–30× slower for long files. We try MPS first
        # (Apple Silicon), then CUDA, then fall back to CPU.
        try:
            import torch
            if torch.backends.mps.is_available():
                _DIAR_PIPELINE.to(torch.device("mps"))
                import logging
                logging.getLogger("transcribbler").info("pyannote pipeline moved to MPS")
            elif torch.cuda.is_available():
                _DIAR_PIPELINE.to(torch.device("cuda"))
                import logging
                logging.getLogger("transcribbler").info("pyannote pipeline moved to CUDA")
            else:
                import logging
                logging.getLogger("transcribbler").warning(
                    "pyannote pipeline running on CPU — diarization will be very slow"
                )
        except Exception as _e:
            # If MPS .to() fails (some pyannote ops are not implemented on MPS),
            # fall back to CPU silently. Log the reason so we can debug later.
            import logging
            logging.getLogger("transcribbler").warning(
                "pyannote .to(device) failed, falling back to CPU: %s", _e
            )

    # Apply threshold overrides (only if explicitly set; always re-apply so
    # a previous run's custom thresholds don't bleed into the next call).
    #
    # Note on pyannote/speaker-diarization-3.1: it uses a *powerset*
    # segmentation model (pyannote/segmentation-3.0), which has no
    # `threshold` hyperparameter — only the clustering stage does. We try
    # to apply both thresholds and silently drop segmentation if pyannote
    # rejects it, so older client code that still sends the field keeps
    # working.
    seg_thr = settings.get("segmentation_threshold")
    clu_thr = settings.get("clustering_threshold")
    if seg_thr is not None or clu_thr is not None:
        params = {}
        if seg_thr is not None:
            params["segmentation"] = {"threshold": float(seg_thr)}
        if clu_thr is not None:
            params["clustering"] = {"threshold": float(clu_thr)}
        try:
            _DIAR_PIPELINE.instantiate(params)
        except ValueError as ve:
            # Powerset segmentation has no threshold — drop it and retry.
            if "segmentation" in params and "threshold" in str(ve):
                params.pop("segmentation", None)
                if params:
                    _DIAR_PIPELINE.instantiate(params)
            else:
                raise

    return _DIAR_PIPELINE


# ---------------------------------------------------------------------------
# Voice embedding (SpeechBrain ECAPA-TDNN, 192-dim, no extra HF gate needed)
# ---------------------------------------------------------------------------

def _load_ecapa_model():
    """Load/cache SpeechBrain ECAPA-TDNN speaker embedding model.
    Tries MPS (Apple Silicon) first, then CUDA, then CPU."""
    global _ECAPA_MODEL
    if _ECAPA_MODEL is not None:
        return _ECAPA_MODEL
    try:
        from speechbrain.inference.speaker import EncoderClassifier
    except ImportError:
        raise ImportError("speechbrain is not installed. Run: pip install speechbrain")

    # Pick best available device — CPU was the previous hardcoded default and
    # made voice matching very slow on long files.
    try:
        import torch
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    except Exception:
        device = "cpu"

    cache_dir = str(Path.home() / ".cache" / "transcribbler" / "ecapa-tdnn")
    try:
        _ECAPA_MODEL = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=cache_dir,
            run_opts={"device": device},
        )
    except Exception as _e:
        # If MPS load fails, fall back to CPU silently.
        if device != "cpu":
            import logging
            logging.getLogger("transcribbler").warning(
                "ECAPA model failed to load on %s, falling back to CPU: %s", device, _e
            )
            _ECAPA_MODEL = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=cache_dir,
                run_opts={"device": "cpu"},
            )
        else:
            raise
    return _ECAPA_MODEL


def extract_voice_embedding(audio_path: str) -> list:
    """
    Extract a 192-dim ECAPA-TDNN speaker embedding from an audio file.
    Returns a plain Python list of floats (JSON-serialisable).
    """
    import numpy as np
    model = _load_ecapa_model()
    signal = model.load_audio(audio_path)
    emb = model.encode_batch(signal)          # shape (1, 1, 192)
    return emb.squeeze().cpu().numpy().tolist()


def save_voice_profile(coder: str, embedding: list) -> dict:
    """Save voice profile globally for a coder. Returns the saved profile dict."""
    VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile = {
        "coder":     coder,
        "embedding": embedding,
        "model":     "speechbrain/spkrec-ecapa-voxceleb",
        "dim":       len(embedding),
        "created":   datetime.now().isoformat(timespec="seconds"),
    }
    path = VOICE_PROFILES_DIR / f"{coder}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh)
    return profile


def load_voice_profile(coder: str) -> dict | None:
    """Load voice profile for a coder, or None if not saved."""
    path = VOICE_PROFILES_DIR / f"{coder}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def delete_voice_profile(coder: str) -> bool:
    """Delete voice profile for a coder. Returns True if file existed."""
    path = VOICE_PROFILES_DIR / f"{coder}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def _cosine_similarity(a: list, b: list) -> float:
    """Cosine similarity between two float lists (returns -1 to 1)."""
    import numpy as np
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def extract_speaker_embeddings(audio_path: str, diar_segments: list) -> dict:
    """
    Extract a mean ECAPA embedding per speaker from diarization segments.
    Only segments >= 1 second are used. The "—" placeholder speaker (used for
    inaudible/noise gaps inserted by transcribe_with_diarization) is skipped
    entirely — running ECAPA on noise wastes CPU time and produces useless
    embeddings.
    Returns: {speaker_id: [192 floats]}
    """
    import numpy as np
    import torch
    try:
        import torchaudio
    except ImportError:
        raise ImportError("torchaudio is required. Run: pip install torchaudio")

    # Filter out placeholder gap segments before doing any work
    diar_segments = [s for s in diar_segments if s["speaker"] != "—"]
    if not diar_segments:
        return {}

    model = _load_ecapa_model()

    # Load full audio once
    waveform, sr = torchaudio.load(audio_path)
    if waveform.shape[0] > 1:          # mix down to mono
        waveform = waveform.mean(dim=0, keepdim=True)
    if sr != 16000:
        waveform = torchaudio.functional.resample(waveform, sr, 16000)
    waveform = waveform.squeeze(0)     # shape (samples,)

    # Group segments by speaker
    by_speaker: dict = {}
    for seg in diar_segments:
        by_speaker.setdefault(seg["speaker"], []).append(seg)

    speaker_embeddings: dict = {}
    for spk, segs in by_speaker.items():
        embs = []
        for seg in segs:
            start_s = int(seg["start"] * 16000)
            end_s   = int(seg["end"]   * 16000)
            if (end_s - start_s) < 16000:   # skip segments < 1 second
                continue
            chunk = waveform[start_s:end_s].unsqueeze(0)   # (1, samples)
            emb = model.encode_batch(chunk)                 # (1, 1, 192)
            embs.append(emb.squeeze().cpu().numpy())
        if embs:
            speaker_embeddings[spk] = np.mean(embs, axis=0).tolist()

    return speaker_embeddings


def match_voice_profile(
    speaker_embeddings: dict,
    profile_embedding: list,
    threshold_auto: float    = 0.85,
    threshold_suggest: float = 0.70,
) -> dict:
    """
    Compare each speaker's embedding to the saved voice profile.

    Returns:
      {
        speaker_id: {
          "similarity": float (0–1),
          "action":     "auto" | "suggest" | "none",
        }
      }
    action="auto"    → similarity >= threshold_auto   (pre-fill name automatically)
    action="suggest" → similarity >= threshold_suggest (show hint, ask to confirm)
    action="none"    → below threshold_suggest
    """
    results = {}
    for spk, emb in speaker_embeddings.items():
        sim = _cosine_similarity(emb, profile_embedding)
        if sim >= threshold_auto:
            action = "auto"
        elif sim >= threshold_suggest:
            action = "suggest"
        else:
            action = "none"
        results[spk] = {"similarity": round(sim, 3), "action": action}
    return results


def diarize(audio_path: str, hf_token: str, settings: dict) -> list:
    """
    Run speaker diarization on audio_path.

    settings keys (all optional):
      num_speakers       — exact number of speakers (overrides min/max)
      min_speakers       — lower bound for speaker count
      max_speakers       — upper bound for speaker count
      segmentation_threshold — float 0–1, default 0.50
      clustering_threshold   — float 0–1, default 0.70

    Returns a list of dicts: [{speaker, start, end, text=""}]
    sorted by start time.
    """
    pipeline = _load_diarization_pipeline(hf_token, settings)

    kwargs = {}
    num = settings.get("num_speakers")
    if num:
        kwargs["num_speakers"] = int(num)
    else:
        mn = settings.get("min_speakers")
        mx = settings.get("max_speakers")
        if mn:
            kwargs["min_speakers"] = int(mn)
        if mx:
            kwargs["max_speakers"] = int(mx)

    diarization = pipeline(audio_path, **kwargs)

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "text": "",
        })

    segments.sort(key=lambda s: s["start"])
    return segments


# ---------------------------------------------------------------------------
# Combined: diarize + transcribe with word-level alignment
# ---------------------------------------------------------------------------

def _refine_speaker_boundaries(
    audio_path: str,
    diar_segments: list,
    min_dur: float = 1.5,
    margin: float = 0.10,
) -> list:
    """
    Post-process pyannote diarization by re-checking short segments using
    ECAPA speaker embeddings.

    Strategy:
    1. Build per-speaker reference embeddings from longer (≥ 1 s) segments —
       these are reliably attributed by pyannote.
    2. For each short segment (< min_dur s), extract its own ECAPA embedding
       and compare against all reference embeddings.
    3. Re-assign if another speaker is more similar by at least `margin` cosine
       units. Catches boundary errors where pyannote placed the speaker-change
       a word or two too early/late.
    4. Re-merge consecutive same-speaker segments produced by re-assignment.

    Returns the original list unchanged if prerequisites are not met (fewer
    than 2 speakers with long segments) or if any dependency fails.
    """
    import logging
    _log = logging.getLogger("transcribbler")

    if len(diar_segments) < 2:
        return diar_segments

    # Reference embeddings from longer, reliably attributed segments
    try:
        speaker_embs = extract_speaker_embeddings(audio_path, diar_segments)
    except Exception as exc:
        _log.warning("boundary_refinement: extract_speaker_embeddings failed: %s", exc)
        return diar_segments

    if len(speaker_embs) < 2:
        _log.info("boundary_refinement: skipped — fewer than 2 speakers with long segments")
        return diar_segments

    try:
        import torchaudio
        model = _load_ecapa_model()
        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != 16000:
            waveform = torchaudio.functional.resample(waveform, sr, 16000)
        waveform = waveform.squeeze(0)
    except Exception as exc:
        _log.warning("boundary_refinement: audio load failed: %s", exc)
        return diar_segments

    refined = [dict(s) for s in diar_segments]
    reassigned = 0

    for seg in refined:
        if seg["speaker"] == "—":
            continue
        dur = seg["end"] - seg["start"]
        if dur >= min_dur:
            continue  # Long segment — pyannote attribution is reliable

        start_s = int(seg["start"] * 16000)
        end_s   = int(seg["end"]   * 16000)
        if end_s - start_s < 1600:  # < 0.1 s — too short for a stable embedding
            continue

        try:
            chunk = waveform[start_s:end_s].unsqueeze(0)
            emb = model.encode_batch(chunk).squeeze().cpu().numpy().tolist()
        except Exception:
            continue

        current_spk = seg["speaker"]
        current_sim = _cosine_similarity(emb, speaker_embs.get(current_spk, []))
        best_spk    = current_spk
        best_sim    = current_sim

        for spk, ref_emb in speaker_embs.items():
            if spk == current_spk:
                continue
            sim = _cosine_similarity(emb, ref_emb)
            if sim > best_sim + margin:
                best_spk = spk
                best_sim = sim

        if best_spk != current_spk:
            _log.info(
                "boundary_refinement: [%s] %.2f–%.2fs  %s → %s  (sim %.3f → %.3f)",
                Path(audio_path).name, seg["start"], seg["end"],
                current_spk, best_spk, current_sim, best_sim,
            )
            seg["speaker"] = best_spk
            reassigned += 1

    n_short = sum(
        1 for s in refined
        if s["speaker"] != "—" and (s["end"] - s["start"]) < min_dur
    )
    _log.info(
        "boundary_refinement: [%s] %d/%d short segments re-assigned",
        Path(audio_path).name, reassigned, n_short,
    )

    if reassigned == 0:
        return refined

    # Re-merge consecutive same-speaker segments made adjacent by re-assignment
    merged = []
    for seg in refined:
        if (merged
                and merged[-1]["speaker"] == seg["speaker"]
                and seg["start"] - merged[-1]["end"] < 0.05):
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)
    return merged


def transcribe_with_diarization(audio_path: str, hf_token: str,
                                settings: dict,
                                progress_cb=None) -> dict:
    """
    Run Pyannote diarization then Whisper/KB-Whisper transcription and align them.

    Alignment strategy:
      - Transcription runs on the full audio with word_timestamps=True
      - Each word is assigned to the diarization segment whose time range
        contains the word's midpoint (nearest segment wins on ties)
      - Words with no overlapping segment are appended to the nearest segment

    Returns:
      {
        "text": str,                  — plain text (speaker-labelled)
        "segments": [...],            — [{speaker, start, end, text}]
        "speakers_found": [str],      — sorted unique speaker IDs
      }
    """
    def _cb(stage, fraction):
        if progress_cb:
            progress_cb(stage, fraction)

    import time as _time
    import logging as _logging
    _log = _logging.getLogger("transcribbler.timing")
    _t_total_start = _time.monotonic()
    def _stage_log(name: str, t0: float):
        dt = _time.monotonic() - t0
        _log.info("transcribe[%s] %s: %.1fs",
                  Path(audio_path).name, name, dt)
        return _time.monotonic()

    language_choice = settings.get("language_choice", "sv")

    # Stage 1 — load transcription model (faster-whisper/CTranslate2)
    _cb("loading_model", 0.05)
    _t = _time.monotonic()
    model_size = settings.get("model_size", "medium")
    fw_model = _load_faster_whisper_model(language_choice, model_size)
    _cb("loading_model", 0.10)
    _t = _stage_log("load_model", _t)

    # Stage 2 — diarization
    _cb("diarizing", 0.15)
    diar_segments = diarize(audio_path, hf_token, settings)
    _cb("diarizing", 0.35)
    _t = _stage_log(f"diarize ({len(diar_segments)} segs)", _t)

    # Stage 2b — ECAPA boundary refinement
    # Re-checks short diarization segments (< 1.5 s) with speaker embeddings
    # to correct boundary errors where pyannote placed the speaker-change a
    # word or two too early/late. Only runs when ≥ 2 distinct speakers found.
    n_speakers = len({s["speaker"] for s in diar_segments if s["speaker"] != "—"})
    if n_speakers >= 2:
        diar_segments = _refine_speaker_boundaries(audio_path, diar_segments)
        _t = _stage_log(f"boundary_refinement ({len(diar_segments)} segs after merge)", _t)

    # Stage 3 — transcription with word-level timestamps (faster-whisper)
    _cb("transcribing", 0.40)
    _log.info("transcribe[%s] starting faster-whisper transcription (word-level timestamps)",
              Path(audio_path).name)

    # Determine forced language:
    #   "sv"         → Swedish (force; KB-Whisper tuned for Swedish)
    #   "autodetect" → None (let faster-whisper auto-detect)
    #   "en"         → English (force)
    #   "other"      → None (auto-detect, task="transcribe" = no translation)
    if language_choice == "sv":
        fw_lang = "sv"
    elif language_choice == "en":
        fw_lang = settings.get("language", "en")
    else:
        fw_lang = None  # autodetect or "other"

    # word_timestamps=True is always used for diarized transcription so the
    # proportional speaker-split has per-word precision instead of per-segment.
    # faster-whisper word timestamps are ~2× faster than transformers word-level
    # and ~4× faster than transformers segment-level (thanks to CTranslate2 INT8).
    fw_result_gen, fw_info = fw_model.transcribe(
        audio_path,
        language=fw_lang,
        task="transcribe",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    _log.info("transcribe[%s] faster-whisper detected language=%s (prob=%.2f)",
              Path(audio_path).name,
              fw_info.language, fw_info.language_probability)

    # Consume the generator and build the canonical words list.
    # Each faster-whisper Segment has a .words list of WordTiming objects
    # with .word, .start, .end attributes. If VAD filtered a segment its
    # .words may be None — fall back to segment-level timing in that case.
    words = []
    raw_seg_count = 0
    for fw_seg in fw_result_gen:
        raw_seg_count += 1
        if fw_seg.words:
            for w in fw_seg.words:
                wtext = (w.word or "").strip()
                if wtext:
                    words.append({
                        "word":  wtext,
                        "start": float(w.start),
                        "end":   float(w.end),
                    })
        else:
            # Segment-level fallback (no word timing available)
            stext = (fw_seg.text or "").strip()
            if stext:
                words.append({
                    "word":  stext,
                    "start": float(fw_seg.start),
                    "end":   float(fw_seg.end),
                })
    _log.info("transcribe[%s] faster-whisper: %d segments → %d word tokens",
              Path(audio_path).name, raw_seg_count, len(words))

    _cb("transcribing", 0.85)
    _t = _stage_log(f"transcribe ({len(words)} Whisper segments)", _t)

    # -----------------------------------------------------------------------
    # Whisper-driven alignment
    # -----------------------------------------------------------------------
    # The output is structured around Whisper's segments (one line per
    # Whisper segment). For each Whisper segment, pyannote tells us which
    # speaker has the most time overlap with it — that's the speaker prefix.
    # pyannote segments that don't receive a Whisper segment are discarded
    # (they're almost always cases where Whisper's segment boundaries don't
    # align 1:1 with pyannote's, not cases of inaudible speech). Gaps
    # between Whisper segments (or before the first / after the last) that
    # exceed GAP_THRESHOLD seconds are filled with an [ohörbart] marker —
    # so genuine silent/inaudible regions still show up.
    #
    # This structure fixes a regression introduced when we switched from
    # per-word to per-segment Whisper timestamps: with fewer Whisper items,
    # the old "assign each word to the containing pyannote segment" loop
    # left many pyannote segments empty → those showed up as spurious
    # [ohörbart] lines even when speech was clearly audible in the audio.
    # -----------------------------------------------------------------------
    inaudible_marker = "[inaudible]" if language_choice in ("en", "other") else "[ohörbart]"

    def _speaker_runs(seg_start: float, seg_end: float) -> list:
        """
        Return the sequence of (speaker, start, end) runs from pyannote that
        overlap [seg_start, seg_end], with consecutive same-speaker runs
        merged. Each run's start/end is clipped to [seg_start, seg_end].
        """
        clipped = []
        for ds in diar_segments:
            overlap_start = max(seg_start, ds["start"])
            overlap_end   = min(seg_end,   ds["end"])
            if overlap_end > overlap_start:
                clipped.append({
                    "speaker": ds["speaker"],
                    "start":   overlap_start,
                    "end":     overlap_end,
                })
        clipped.sort(key=lambda o: o["start"])
        # Merge consecutive runs of the same speaker
        merged = []
        for o in clipped:
            if merged and merged[-1]["speaker"] == o["speaker"]:
                merged[-1]["end"] = max(merged[-1]["end"], o["end"])
            else:
                merged.append(dict(o))
        return merged

    def _looks_like_garbage(text: str) -> bool:
        """Spurious Whisper output on noisy segments is often a single
        punctuation character or empty after stripping. Filter these."""
        stripped = text.strip()
        if len(stripped) < 2:
            return True
        if all(c in "!?.,;: ·-–—" for c in stripped):
            return True
        return False

    # Build the primary output from Whisper segments, splitting any segment
    # that spans a pyannote speaker change into separate pieces (text
    # distributed proportionally by time). This handles the common case of
    # a Whisper segment like "Solid base Vi skulle behöva forskning..." where
    # Rosa said "Solid base" briefly before Jonas took over — without a split
    # the whole line would be attributed to Jonas (majority overlap).
    output_segments: list = []
    for w in words:
        text = (w.get("word") or "").strip()
        if not text or _looks_like_garbage(text):
            continue
        runs = _speaker_runs(w["start"], w["end"])
        if not runs:
            # No pyannote speaker found for this Whisper segment → placeholder
            output_segments.append({
                "speaker": "—",
                "start":   round(float(w["start"]), 3),
                "end":     round(float(w["end"]), 3),
                "text":    text,
            })
            continue
        if len(runs) == 1:
            # Single speaker throughout — trivial case
            output_segments.append({
                "speaker": runs[0]["speaker"],
                "start":   round(float(w["start"]), 3),
                "end":     round(float(w["end"]), 3),
                "text":    text,
            })
            continue
        # Multi-speaker: split text proportionally by time fraction.
        # Splits happen at word boundaries (we never cut mid-word) so the
        # distribution is approximate but always readable.
        tokens = text.split()
        total_dur = sum(r["end"] - r["start"] for r in runs)
        n_tokens  = len(tokens)
        idx = 0
        for i, r in enumerate(runs):
            is_last = (i == len(runs) - 1)
            if is_last:
                piece_tokens = tokens[idx:]
            else:
                frac = (r["end"] - r["start"]) / total_dur
                take = max(1, round(n_tokens * frac))
                piece_tokens = tokens[idx:idx + take]
                idx += len(piece_tokens)
            if not piece_tokens:
                continue
            output_segments.append({
                "speaker": r["speaker"],
                "start":   round(float(r["start"]), 3),
                "end":     round(float(r["end"]), 3),
                "text":    " ".join(piece_tokens),
            })
    output_segments.sort(key=lambda s: s["start"])

    # Determine audio duration for end-of-file gap filling
    try:
        import torchaudio
        info = torchaudio.info(audio_path)
        audio_duration = float(info.num_frames) / float(info.sample_rate)
    except Exception:
        audio_duration = max(
            (s["end"] for s in output_segments),
            default=0.0,
        )

    # Insert [ohörbart] rows for time ranges Whisper didn't cover at all
    GAP_THRESHOLD = 3.0  # seconds
    filled: list = []
    prev_end = 0.0
    for seg in output_segments:
        if seg["start"] - prev_end >= GAP_THRESHOLD:
            filled.append({
                "speaker": "—",
                "start":   round(prev_end, 3),
                "end":     round(seg["start"], 3),
                "text":    inaudible_marker,
            })
        filled.append(seg)
        prev_end = max(prev_end, seg["end"])
    if audio_duration - prev_end >= GAP_THRESHOLD:
        filled.append({
            "speaker": "—",
            "start":   round(prev_end, 3),
            "end":     round(audio_duration, 3),
            "text":    inaudible_marker,
        })

    # Collapse consecutive same-speaker runs so the transcript doesn't have
    # three "[Jonas]: ..." lines in a row when Whisper happens to split a
    # long utterance into multiple segments. This also merges consecutive
    # [ohörbart] runs (speaker "—").
    collapsed: list = []
    for seg in filled:
        if collapsed and collapsed[-1]["speaker"] == seg["speaker"]:
            if seg["speaker"] == "—":
                # For inaudible runs we just extend the time range — text is
                # re-generated with the merged timestamps below
                collapsed[-1]["end"] = max(collapsed[-1]["end"], seg["end"])
            else:
                # For named speakers we concatenate the text too
                collapsed[-1]["end"]  = max(collapsed[-1]["end"], seg["end"])
                collapsed[-1]["text"] = (collapsed[-1]["text"] + " " + seg["text"]).strip()
            continue
        collapsed.append(dict(seg))
    diar_segments = collapsed

    # Attach MM:SS:HH start–end timestamps to inaudible segments so the user
    # can navigate to them in the audio and see how long they are. Format:
    # "[ohörbart 02:34:50 – 02:47:12]" / "[inaudible 02:34:50 – 02:47:12]"
    # where HH is hundredths of a second. We do this AFTER merging so the
    # timestamps reflect the span of the merged run.
    inaudible_label = "inaudible" if language_choice in ("en", "other") else "ohörbart"
    def _format_mmsshh(seconds: float) -> str:
        mm = int(seconds // 60)
        ss = int(seconds % 60)
        hh = int(round((seconds - int(seconds)) * 100))
        # Guard against rounding to 100 (e.g. 59.999 → hh=100)
        if hh == 100:
            hh = 0
            ss += 1
            if ss == 60:
                ss = 0
                mm += 1
        return f"{mm:02d}:{ss:02d}:{hh:02d}"
    for seg in diar_segments:
        if seg["speaker"] == "—":
            t_start = _format_mmsshh(seg["start"])
            t_end   = _format_mmsshh(seg["end"])
            seg["text"] = f"[{inaudible_label} {t_start} – {t_end}]"

    # Exclude the placeholder speaker from the speaker name dialog
    speakers_found = sorted({ds["speaker"] for ds in diar_segments if ds["speaker"] != "—"})
    # Rendering: inaudible lines show only "[ohörbart]" with no speaker prefix.
    # Named speakers render as "[Speaker]: text" as before. The frontend
    # buildSegmentCharMap must mirror this exactly for click-to-seek to work.
    lines = [
        ds["text"] if ds["speaker"] == "—" else f"[{ds['speaker']}]: {ds['text']}"
        for ds in diar_segments
    ]
    plain_text = "\n".join(lines)

    _cb("done", 1.0)
    _t = _stage_log(f"align+gapfill ({len(diar_segments)} final segs)", _t)
    _log.info("transcribe[%s] TOTAL: %.1fs",
              Path(audio_path).name, _time.monotonic() - _t_total_start)

    return {
        "text":           plain_text,
        "segments":       diar_segments,
        "speakers_found": speakers_found,
    }
