"""Tests for core/i18n.py and localised core output."""
from core.i18n import tr, set_lang, EN
from core.irr import _interpret


def teardown_function(_):
    set_lang("sv")


def test_tr_swedish_is_identity():
    set_lang("sv")
    assert tr("Inget projekt öppnat.") == "Inget projekt öppnat."


def test_tr_english_and_placeholders():
    set_lang("en")
    assert tr("Inget projekt öppnat.") == "No project is open."
    assert tr("[borttagen: {id}]", id="c1") == "[deleted: c1]"


def test_tr_unknown_key_passes_through():
    set_lang("en")
    assert tr("Okänd text") == "Okänd text"


def test_english_placeholders_match_swedish():
    import re
    ph = lambda s: sorted(re.findall(r"\{(\w+)\}", s))
    for sv, en in EN.items():
        assert ph(sv) == ph(en), sv


def test_kappa_bands_landis_koch():
    set_lang("en")
    assert _interpret(-0.1).startswith("Poor")
    assert _interpret(0.20).startswith("Slight")
    assert _interpret(0.21).startswith("Fair")
    assert _interpret(0.60).startswith("Moderate")
    assert _interpret(0.80).startswith("Substantial")
    assert _interpret(0.81).startswith("Almost perfect")
