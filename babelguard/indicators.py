"""Indicators: the details a scam needs the victim to use, whatever language it is written in.

A scam can be translated into any language, but it still has to send the victim somewhere: a link,
a phone number, a UPI ID, a wallet. Those details are language-independent, so they link the same
campaign across languages. Extracted from the normalized text (look-alikes folded, native digits
made ASCII), refanged ("hxxp", "[.]", " dot "), canonicalized and, where a checksum exists,
validated.

Victims' own details (OTPs, card, Aadhaar and PAN numbers) are never indicators: redact() masks
them before a message is stored or shared.
"""
import hashlib
import re
from dataclasses import dataclass

from .normalize import ascii_digits, normalize

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "shorturl.at",
              "tiny.cc", "ow.ly", "s.id", "rebrand.ly", "t.ly", "v.gd", "shorturl.asia"}
MESSAGING = {"t.me", "wa.me", "telegram.me", "chat.whatsapp.com"}
TLD = r"(?:[a-z]{2,24}|xn--[a-z0-9-]{1,59})"


@dataclass(frozen=True)
class Indicator:
    kind: str     # url | domain | phone | upi | email | btc | eth | tron
    value: str    # canonical form


def refang(s):
    s = re.sub(r"h(?:xx|\*\*|tt)p(s?)", r"http\1", s, flags=re.I)
    s = re.sub(r"\s*[\[\(\{]\s*(?:\.|dot)\s*[\]\)\}]\s*", ".", s, flags=re.I)
    s = re.sub(r"(?<=[a-z0-9])\s+dot\s+(?=[a-z0-9])", ".", s, flags=re.I)
    return s


# ---- checksums --------------------------------------------------------------------------------

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode_check(s):
    n = 0
    for c in s:
        if c not in B58:
            return None
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\0" * (len(s) - len(s.lstrip("1"))) + raw
    if len(raw) < 5:
        return None
    body, check = raw[:-4], raw[-4:]
    return body if hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4] == check else None


def b58encode_check(body):
    raw = body + hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4]
    n, out = int.from_bytes(raw, "big"), ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + out


BECH = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (top >> i) & 1 else 0
    return chk


def _hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_ok(addr):
    """BIP-173 (bech32) or BIP-350 (bech32m) checksum."""
    a = addr.lower()
    if a != addr and addr.upper() != addr or "1" not in a:
        return False
    hrp, data = a.rsplit("1", 1)
    if not hrp or len(data) < 6 or any(c not in BECH for c in data):
        return False
    return _polymod(_hrp_expand(hrp) + [BECH.index(c) for c in data]) in (1, 0x2BC830A3)


def bech32_encode(hrp, data, m=False):
    const = 0x2BC830A3 if m else 1
    pm = _polymod(_hrp_expand(hrp) + data + [0] * 6) ^ const
    return hrp + "1" + "".join(BECH[d] for d in data + [(pm >> 5 * (5 - i)) & 31 for i in range(6)])


def luhn_ok(digits):
    total = 0
    for i, c in enumerate(reversed(digits)):
        d = int(c)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


_VD = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
       [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
       [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
       [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_VP = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
       [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
       [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]
_VINV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_ok(digits):
    """Verhoeff checksum, as used by Aadhaar numbers."""
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VD[c][_VP[i % 8][int(ch)]]
    return c == 0


def verhoeff_digit(digits):
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VD[c][_VP[(i + 1) % 8][int(ch)]]
    return str(_VINV[c])


# ---- extraction -------------------------------------------------------------------------------

URL_RE = re.compile(r"(?:(?:https?://)|(?:www\.))[^\s<>\"']+|\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                    + TLD + r"(?:/[^\s<>\"']*)?", re.I)
EMAIL_RE = re.compile(r"\b[a-z0-9._%+-]+@(?:[a-z0-9-]+\.)+[a-z]{2,24}\b", re.I)
UPI_RE = re.compile(r"\b[a-z0-9][a-z0-9._-]{1,255}@[a-z][a-z0-9]{1,63}\b(?![.@])", re.I)
PHONE_RE = re.compile(r"(?<![\w+])(\+?\d[\d \-().]{7,18}\d)(?!\w)")
ETH_RE = re.compile(r"\b0x[0-9a-fA-F]{40}\b")
BTC_B58_RE = re.compile(r"\b[13][1-9A-HJ-NP-Za-km-z]{25,34}\b")
BTC_BECH_RE = re.compile(r"\b(?:bc|BC)1[0-9A-Za-z]{11,71}\b")
TRON_RE = re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")
COMMON_FILE_TLDS = {"exe", "apk", "pdf", "jpg", "png", "zip", "doc", "docx", "txt", "html", "php"}


def _url(raw):
    u = raw.rstrip(".,;:!?)]}'\"").lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    host, _, path = u.partition("/")
    host = host.split(":")[0].rstrip(".")
    if "." not in host or host.rsplit(".", 1)[1] in COMMON_FILE_TLDS:
        return None
    path = path.rstrip("/")
    if host in SHORTENERS or host in MESSAGING:
        return Indicator("url", host + ("/" + path if path else ""))
    return Indicator("domain", host)


# Mobile numbering plans used to normalise numbers when the sender's country is known:
# country -> (calling code, national number lengths, mobile prefix). Not exhaustive; numbers from
# other countries are kept as digits and still link through link_key().
PLANS = {
    "IN": ("91", (10,), r"[6-9]"), "BD": ("880", (10,), r"1[3-9]"), "PK": ("92", (10,), r"3"),
    "LK": ("94", (9,), r"7"), "NP": ("977", (10,), r"9[78]"), "ID": ("62", (9, 10, 11, 12), r"8"),
    "PH": ("63", (10,), r"9"), "TH": ("66", (9,), r"[689]"), "VN": ("84", (9,), r"[35789]"),
    "MY": ("60", (9, 10), r"1"), "KE": ("254", (9,), r"[17]"), "NG": ("234", (10,), r"[789][01]"),
    "GH": ("233", (9,), r"[25]"), "MZ": ("258", (9,), r"8[2-7]"), "ZA": ("27", (9,), r"[6-8]"),
    "ET": ("251", (9,), r"9"), "EG": ("20", (10,), r"1"), "GB": ("44", (10,), r"7"),
    "US": ("1", (10,), r"[2-9]"), "BR": ("55", (11,), r"\d\d9"), "ES": ("34", (9,), r"[67]"),
    "FR": ("33", (9,), r"[67]"),
}
_BY_CODE = sorted(((cc, c) for c, (cc, _, _) in PLANS.items()), key=lambda x: -len(x[0]))


def _national(d, country):
    cc, lengths, mobile = PLANS[country]
    for prefix in ("00" + cc, cc, "0"):
        if d.startswith(prefix) and len(d) - len(prefix) in lengths:
            d = d[len(prefix):]
            break
    if len(d) in lengths and re.match(mobile, d):
        return "+" + cc + d
    return None


def _phone(raw, country=None):
    """Canonical phone number: +<country code><number> when the country is known (from a + or
    00 prefix, or from the `country` hint), otherwise the national digits."""
    s = raw.strip()
    d = re.sub(r"\D", "", s)
    if not 9 <= len(d) <= 15:
        return None
    international = s.startswith("+") or d.startswith("00")
    if international:
        d = d[2:] if d.startswith("00") else d
        for cc, c in _BY_CODE:
            if d.startswith(cc):
                v = _national(d, c)
                if v:
                    return Indicator("phone", v)
        return Indicator("phone", "+" + d)
    if country in PLANS:
        v = _national(d, country)
        if v:
            return Indicator("phone", v)
    return Indicator("phone", d[1:] if d.startswith("0") and len(d) > 9 else d)


def link_key(ind):
    """What two indicators must share to link: phone numbers compare on their last 9 digits, so
    the same number written with or without its country code still links."""
    if ind.kind == "phone":
        return ("phone", re.sub(r"\D", "", ind.value)[-9:])
    return (ind.kind, ind.value)


def extract(message, country=None):
    """Set of Indicators in a message (any language). `country` (ISO 3166 alpha-2) is a hint
    for numbers written without a country code."""
    canon = refang(normalize(message).canonical)
    found, spans = set(), []
    for m in EMAIL_RE.finditer(canon):
        found.add(Indicator("email", m.group().lower()))
        spans.append(m.span())
    for m in UPI_RE.finditer(canon):
        if not any(a <= m.start() < b for a, b in spans):
            found.add(Indicator("upi", m.group().lower()))
            spans.append(m.span())
    for m in URL_RE.finditer(canon):
        if any(a <= m.start() < b for a, b in spans):
            continue
        ind = _url(m.group())
        if ind:
            found.add(ind)
            spans.append(m.span())
    original = refang(normalize(message).text)        # wallets are case-sensitive
    for m in ETH_RE.finditer(original):
        found.add(Indicator("eth", m.group().lower()))
    for m in BTC_BECH_RE.finditer(original):
        if bech32_ok(m.group()):
            found.add(Indicator("btc", m.group().lower()))
    for m in BTC_B58_RE.finditer(original):
        body = b58decode_check(m.group())
        if body and body[0] in (0x00, 0x05):
            found.add(Indicator("btc", m.group()))
    for m in TRON_RE.finditer(original):
        body = b58decode_check(m.group())
        if body and body[0] == 0x41 and len(body) == 21:
            found.add(Indicator("tron", m.group()))
    for m in PHONE_RE.finditer(canon):
        if any(a <= m.start() < b for a, b in spans):
            continue
        d = re.sub(r"\D", "", m.group())
        if (13 <= len(d) <= 19 and luhn_ok(d)) or (len(d) == 12 and verhoeff_ok(d) and d[0] not in "01"):
            continue                                   # a card or Aadhaar number, not a phone
        ind = _phone(m.group(), country)
        if ind:
            found.add(ind)
    return found


# ---- privacy ----------------------------------------------------------------------------------

def redact(message):
    """Mask victims' details before a message leaves the phone: card numbers (Luhn), Aadhaar
    (Verhoeff), PAN, and one-time codes. Scammers' indicators are kept."""
    s = refang(message)

    def digits_run(m):
        d = re.sub(r"\D", "", m.group())
        if 13 <= len(d) <= 19 and luhn_ok(d):
            return "[CARD]"
        if len(d) == 12 and d[0] not in "01" and verhoeff_ok(d):
            return "[AADHAAR]"
        return m.group()

    s = re.sub(r"(?<!\d)\d(?:[ -]?\d){11,18}(?!\d)", digits_run, ascii_digits(s))
    s = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN]", s)
    s = re.sub(r"(?i)((?:otp|code|pin|कोड|ओटीपी|ଓଟିପି)\D{0,20}?)(\d{4,8})\b", r"\1[OTP]", s)
    s = re.sub(r"(?<![\d+])\d{4,8}(?=\s*(?:is your|is the)\b)", "[OTP]", s, flags=re.I)
    return s
