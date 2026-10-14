"""Script-aware normalization: undo the disguises scammers use, without breaking real text.

Filters are evaded by hiding characters inside words (zero-width spaces, joiners, bidi controls,
tag characters) and by swapping letters for look-alikes from other scripts (Cyrillic "а" for
Latin "a"). The usual defence, deleting every invisible character, breaks the languages that need
them: the zero-width joiner and non-joiner (ZWJ, ZWNJ) are part of correct spelling in Indic
scripts, Persian and Urdu; the zero-width space marks word breaks in Thai, Lao, Khmer and Burmese;
ZWJ builds emoji sequences. This module keeps those uses and removes the rest, and reports every
removal, because a disguise attempt is itself evidence.

    n = normalize("Pa​ytm KYC ...")
    n.text        # cleaned text, still correct in its own script (NFC)
    n.canonical   # comparison form: NFKC, casefolded, ASCII digits, look-alikes folded
    n.anomalies   # Counter of what was removed or folded, e.g. {"zwsp": 1}
"""
import json
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

ZWSP, ZWNJ, ZWJ = "​", "‌", "‍"

# Removed wherever they appear: they change nothing a reader sees in a short message.
ALWAYS_STRIP = {
    "­": "soft_hyphen", "͏": "grapheme_joiner", "᠎": "mongolian_vowel_sep",
    "⁠": "word_joiner", "⁡": "invisible_operator", "⁢": "invisible_operator",
    "⁣": "invisible_operator", "⁤": "invisible_operator", "﻿": "bom",
    "ㅤ": "hangul_filler", "ﾠ": "hangul_filler", "ᅟ": "hangul_filler",
    "ᅠ": "hangul_filler",
}
BIDI = set("‎‏؜‪‫‬‭‮⁦⁧⁨⁩")
BIDI_OVERRIDE = set("‭‮")          # force display order: the classic spoofing trick

# Virama-like signs: ZWJ/ZWNJ next to one of these controls conjunct formation (Unicode Indic FAQ).
VIRAMAS = set("्্੍્୍்్್഻഼്්"
              "္်្꣄᭄꧀")
INDIC = {"DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "ORIYA", "TAMIL", "TELUGU", "KANNADA",
         "MALAYALAM", "SINHALA", "MYANMAR", "KHMER", "BALINESE", "JAVANESE", "SAURASHTRA"}
ARABIC = {"ARABIC", "SYRIAC", "NKO"}
NO_SPACE = {"THAI", "LAO", "KHMER", "MYANMAR", "TIBETAN"}   # ZWSP is a legitimate break hint
COMPATIBLE = [{"CJK", "HIRAGANA", "KATAKANA", "KATAKANA-HIRAGANA", "HANGUL"}]     # scripts that mix within words

_CONF = None


def confusables():
    global _CONF
    if _CONF is None:
        p = os.path.join(os.path.dirname(__file__), "data", "confusables_ascii.json")
        _CONF = json.load(open(p, encoding="utf-8"))["map"]
    return _CONF


def script(ch):
    """Coarse script of one character: the first word of its Unicode name for letters and marks
    (LATIN, CYRILLIC, DEVANAGARI, ORIYA, ...), EMOJI, INHERITED for generic combining marks,
    COMMON for everything else."""
    cp = ord(ch)
    if 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x1F3FB <= cp <= 0x1F3FF:
        return "EMOJI"
    cat = unicodedata.category(ch)
    if cat[0] not in "LM":
        return "COMMON"
    name = unicodedata.name(ch, "")
    if not name or name.startswith("COMBINING"):
        return "INHERITED"
    first = name.split()[0]
    if first in ("FULLWIDTH", "HALFWIDTH", "MATHEMATICAL"):
        return name.split()[1]
    return first


def _neighbours(s, i):
    j = i - 1
    while j >= 0 and s[j] in (ZWJ, ZWNJ, "️"):
        j -= 1
    k = i + 1
    while k < len(s) and s[k] in (ZWJ, ZWNJ):
        k += 1
    return (s[j] if j >= 0 else ""), (s[k] if k < len(s) else "")


def _joiner_ok(s, i):
    """Whether the ZWJ/ZWNJ at s[i] has a legitimate job where it stands."""
    prev, nxt = _neighbours(s, i)
    if i > 0 and s[i - 1] in VIRAMAS and script(s[i - 1]) in INDIC:
        return True                    # after a virama: half-forms, chillus, explicit virama
    if not prev or not nxt:
        return False
    sp, sn = script(prev), script(nxt)
    if s[i] == ZWJ and sp == "EMOJI" and sn == "EMOJI":
        return True
    if sp in INDIC and sn in (sp, "INHERITED") or sn in INDIC and sp in (sn, "INHERITED"):
        return s[i - 1] in VIRAMAS or (i + 1 < len(s) and s[i + 1] in VIRAMAS)
    if sp in ARABIC and sn in ARABIC:
        return True
    return False


def _zwsp_ok(s, i):
    prev = s[i - 1] if i > 0 else ""
    nxt = s[i + 1] if i + 1 < len(s) else ""
    return bool(prev and nxt) and script(prev) in NO_SPACE and script(nxt) in NO_SPACE


@dataclass
class Normalized:
    text: str
    canonical: str
    anomalies: Counter = field(default_factory=Counter)


def clean(s):
    """(text with illegitimate invisible characters removed, Counter of removals)."""
    s = unicodedata.normalize("NFC", s)
    out, found = [], Counter()
    for i, ch in enumerate(s):
        cp = ord(ch)
        if ch in ALWAYS_STRIP:
            found[ALWAYS_STRIP[ch]] += 1
        elif ch in BIDI:
            found["bidi_override" if ch in BIDI_OVERRIDE else "bidi_control"] += 1
        elif 0xE0000 <= cp <= 0xE007F:
            found["tag_char"] += 1
        elif ch in (ZWJ, ZWNJ):
            if _joiner_ok(s, i):
                out.append(ch)
            else:
                found["zwj" if ch == ZWJ else "zwnj"] += 1
        elif ch == ZWSP:
            if _zwsp_ok(s, i):
                out.append(ch)
            else:
                found["zwsp"] += 1
        else:
            out.append(ch)
    return "".join(out), found


def _word_scripts(word):
    return {script(c) for c in word} - {"COMMON", "INHERITED", "EMOJI"}


def _mixed(scripts):
    return len(scripts) > 1 and not any(scripts <= group for group in COMPATIBLE)


def fold_word(word, found):
    """Look-alike letters folded to ASCII in a word that mixes Latin with another script."""
    sc = _word_scripts(word)
    if not _mixed(sc):
        return word
    found["mixed_script_word"] += 1
    if "LATIN" not in sc:
        return word
    conf = confusables()
    folded = "".join(conf.get(c, c) if script(c) not in ("LATIN", "COMMON") else c for c in word)
    if _word_scripts(folded) <= {"LATIN"}:
        found["confusable_folded"] += 1
        return folded
    return word


def ascii_digits(s):
    """Every decimal digit (Devanagari ०-९, Odia ୦-୯, Arabic-Indic, Thai, fullwidth, ...) as ASCII."""
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in s)


def normalize(s):
    text, found = clean(s)
    canon = unicodedata.normalize("NFKC", text)
    canon = "".join(fold_word(w, found) if w and not w.isspace() else w
                    for w in re.split(r"(\s+)", canon))
    canon = ascii_digits(canon).casefold()
    canon = canon.replace(ZWJ, "").replace(ZWNJ, "").replace(ZWSP, "")
    return Normalized(text=text, canonical=" ".join(canon.split()), anomalies=found)
