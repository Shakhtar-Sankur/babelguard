"""Benchmark records, loaders for open datasets, and campaign-aware splits.

Every record is re-redacted on load (victims' OTPs, cards, Aadhaar, PAN), keeps its source and
licence, and starts unverified: imported labels are noisy (a genuine vaccination reminder labelled
as a scam, for instance), so only records a person has checked count as benchmark ground truth.

Splits are made by template, not by message. Scam operations send thousands of near-copies; if
copies of one template sit in both training and test data, a detector is rewarded for memorising
it. Near-copies (and messages whose translations are near-copies) are grouped first, and whole
groups are assigned to a split.
"""
import csv
import hashlib
import json
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from .campaigns import _DSU, shingles
from .indicators import redact
from .lsh import near_copies
from .taxonomy import IMC25_TYPES, language

IMC25_URL = ("https://raw.githubusercontent.com/reportsmishing/Smishing-Dataset-IMC25/main/"
             "dataset/final_dataset_output.csv")
IMC25_SHA256 = "1bbd1e9e82c3ea023112207b80da268a5c4a07d2353c2b0898360ab037fa9a64"   # main branch, fetched 2026-10-14
IMC25_CITATION = ("Agarwal, Papasavva, Suarez-Tangil, Vasek. Fishing for Smishing: Understanding SMS "
                  "Phishing Infrastructure and Strategies by Mining Public User Reports. IMC 2025. "
                  "doi:10.1145/3730567.3764431. CC BY 4.0.")


@dataclass
class Record:
    id: str
    text: str
    lang: str
    region: str
    label: str                       # scam | spam | legit | unknown
    scam_type: str = None
    lures: list = field(default_factory=list)
    translation: str = ""           # English, when the source provides one
    source: str = ""
    license: str = ""
    verified: bool = False
    group: int = -1                  # template group, for splits

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_imc25(path):
    """Records from the IMC 2025 smishing dataset (CC BY 4.0). Every report in it is a message
    users reported as smishing; its 'spam' type marks plain marketing and becomes label 'spam'."""
    csv.field_size_limit(1 << 30)
    out = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        for n, r in enumerate(csv.DictReader(f)):
            text = (r.get("text") or "").strip()
            if not text:
                continue
            code, region = language(r.get("language"))
            t = IMC25_TYPES.get((r.get("scam_type") or "").strip().lower())
            label = "spam" if t == "spam" else "scam"
            lures = [x.strip() for x in (r.get("lure_principles") or "").strip("[]").replace("'", "").split(",")
                     if x.strip()]
            out.append(Record(id=f"imc25-{n}", text=redact(text), lang=code, region=region, label=label,
                              scam_type=None if t == "spam" else t, lures=lures,
                              translation=redact((r.get("translation") or "").strip()),
                              source="imc25", license="CC-BY-4.0"))
    return out


TAG = re.compile(r"<[A-Z_]+>|\[(?:OTP|CARD|AADHAAR|PAN)\]")
MIN_CONTENT = 20     # characters of real text needed to compare a message with others


def content(text):
    """Text without anonymisation placeholders; '' when too little real text is left to compare
    (messages that are mostly placeholders would otherwise chain unrelated scams together)."""
    t = " ".join(TAG.sub(" ", text or "").split())
    return t if len(t) >= MIN_CONTENT else ""


def english_view(rec):
    return rec.translation or (rec.text if rec.lang == "en" else "")


def group_templates(records, threshold=0.6):
    """Assign rec.group: near-copies in the original text, or in the English translation, share a
    group. Returns the number of groups."""
    n = len(records)
    dsu = _DSU(n)
    for view in (lambda r: content(r.text), lambda r: content(english_view(r))):
        sets = [shingles(v) if (v := view(r)) else set() for r in records]
        for i, j, _ in near_copies(sets, threshold):
            dsu.union(i, j)
    roots = {}
    for i, r in enumerate(records):
        r.group = roots.setdefault(dsu.find(i), len(roots))
    return len(roots)


def split(records, fractions=(("train", 0.7), ("dev", 0.1), ("test", 0.2)), seed=13):
    """{split name: [records]} with every template group wholly inside one split."""
    groups = defaultdict(list)
    for r in records:
        groups[r.group].append(r)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    total, out, acc = len(records), {name: [] for name, _ in fractions}, 0
    bounds, run = [], 0.0
    for name, frac in fractions:
        run += frac
        bounds.append((name, run * total))
    for k in keys:
        name = next((nm for nm, b in bounds if acc < b), bounds[-1][0])
        out[name].extend(groups[k])
        acc += len(groups[k])
    return out
