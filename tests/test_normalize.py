"""Disguises are removed and counted; legitimate uses of the same characters are kept."""
import pytest

from babelguard.normalize import ascii_digits, normalize, script

KEEP = [
    ("क्‍ष", "Devanagari half-form: ZWJ after virama"),
    ("र्‍य", "Devanagari eyelash ra"),
    ("র‍্য", "Bengali ya-phala: ZWJ before virama"),
    ("ନ୍‌ତ", "Odia: ZWNJ after virama blocks the conjunct"),
    ("ക്‍", "Malayalam: old-style chillu with ZWJ"),
    ("می‌خواهم", "Persian: ZWNJ between letters"),
    ("اردو‌زبان", "Urdu: ZWNJ between letters"),
    ("สวัสดี​ครับ", "Thai: ZWSP as a word break"),
    ("ជំរាបសួរ​លោក", "Khmer: ZWSP as a word break"),
    ("👨‍👩‍👧", "emoji family sequence"),
    ("👩🏽‍💻", "emoji with skin tone"),
]


@pytest.mark.parametrize("text,why", KEEP)
def test_legitimate_invisible_characters_are_kept(text, why):
    n = normalize(text)
    assert n.text == text, why
    assert not n.anomalies, why


STRIP = [
    ("Pa​ytm", "Paytm", "zwsp"),
    ("S‍B‍I", "SBI", "zwj"),
    ("K‌Y‌C", "KYC", "zwnj"),
    ("बैं‍क", "बैंक", "zwj"),                       # Devanagari, but no virama: no job to do
    ("ବ୍ୟା​ଙ୍କ", "ବ୍ୟାଙ୍କ", "zwsp"),                    # ZWSP inside an Odia word
    ("‮gnp.exe", "gnp.exe", "bidi_override"),
    ("ref⁠und", "refund", "word_joiner"),
    ("hi\U000E0069\U000E0067", "hi", "tag_char"),
    ("up­date", "update", "soft_hyphen"),
    ("ㅤlink", "link", "hangul_filler"),
]


@pytest.mark.parametrize("text,clean,kind", STRIP)
def test_disguises_are_removed_and_counted(text, clean, kind):
    n = normalize(text)
    assert n.text == clean
    assert n.anomalies[kind] >= 1


def test_lookalike_letters_fold_in_mixed_script_words():
    n = normalize("Login at p\u0430ytm.com and g\u043e\u043egle.com")     # Cyrillic а and оо
    assert "paytm.com" in n.canonical and "google.com" in n.canonical
    assert n.anomalies["mixed_script_word"] == 2 and n.anomalies["confusable_folded"] == 2


def test_single_script_words_are_not_folded():
    n = normalize("Привет мир and नमस्ते")
    assert n.canonical == "привет мир and नमस्ते"
    assert not n.anomalies


def test_japanese_mixing_is_not_flagged():
    assert not normalize("東京タワーへ行きます").anomalies


def test_compatibility_forms_and_case():
    assert normalize("ＰＡＹＴＭ  𝐊𝐘𝐂").canonical == "paytm kyc"


def test_native_digits_become_ascii():
    assert ascii_digits("९८७६५ ୯୮୭୬୫ ৯৮৭ ٩٨٧ ๙๘๗ ９８７") == "98765 98765 987 987 987 987"


def test_script_names():
    assert [script(c) for c in "aаαअଅاก1"] == ["LATIN", "CYRILLIC", "GREEK", "DEVANAGARI", "ORIYA",
                                               "ARABIC", "THAI", "COMMON"]
