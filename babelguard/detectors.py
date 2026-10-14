"""Detectors under test, behind one interface: `score(texts) -> list of floats in [0, 1]`.

- `KeywordBaseline`: the kind of English keyword filter many legacy systems still run. It is a
  floor, not a contender: it shows what a filter built for English does to everyone else.
- `HFClassifier`: any Hugging Face text-classification model (multilingual scam and phishing
  detectors, guard models), imported lazily.
- `CallableDetector`: wraps any function, such as a call to an LLM API with a fixed prompt; the
  caller supplies the key and the budget.

`normalize_first=True` runs Babelguard's script-aware cleaning before scoring, so the same detector
can be measured with and without it.
"""
import re

from .normalize import normalize

ENGLISH_SCAM_TERMS = [
    "urgent", "immediately", "verify", "verification", "kyc", "otp", "blocked", "suspended",
    "account", "click", "link", "update", "refund", "prize", "winner", "won", "lottery", "claim",
    "reward", "cashback", "parcel", "package", "delivery", "customs", "fee", "payment", "pay",
    "bank", "card", "expire", "expired", "penalty", "fine", "police", "arrest", "loan", "job",
    "earn", "investment", "crypto", "bitcoin", "password", "login", "unusual", "unauthorized",
]


class Detector:
    name = "detector"
    normalize_first = False

    def score(self, texts):
        raise NotImplementedError

    def __call__(self, texts):
        if self.normalize_first:
            texts = [normalize(t).text for t in texts]
        return self.score(list(texts))


class KeywordBaseline(Detector):
    """Flags a message when it contains at least `min_hits` English scam terms or a link."""
    def __init__(self, terms=ENGLISH_SCAM_TERMS, min_hits=2, normalize_first=False):
        self.name = f"english-keywords(min_hits={min_hits})"
        self.re = re.compile(r"\b(" + "|".join(map(re.escape, terms)) + r")\b", re.I)
        self.min_hits, self.normalize_first = min_hits, normalize_first

    def score(self, texts):
        out = []
        for t in texts:
            hits = len(set(m.lower() for m in self.re.findall(t or "")))
            link = 1 if re.search(r"https?://|www\.|<URL>", t or "", re.I) else 0
            out.append(min(1.0, (hits + link) / self.min_hits))
        return out


class HFClassifier(Detector):
    """A Hugging Face text classifier; the score is the summed probability of `positive` labels."""
    def __init__(self, model, positive=("scam", "phishing", "spam", "fraud", "LABEL_1", "unsafe"),
                 batch_size=32, max_length=256, device=-1, normalize_first=False):
        from transformers import pipeline
        self.name = model
        self.pipe = pipeline("text-classification", model=model, top_k=None, device=device,
                             truncation=True, max_length=max_length)
        self.positive = {p.lower() for p in positive}
        self.batch_size, self.normalize_first = batch_size, normalize_first

    def score(self, texts):
        out = []
        for res in self.pipe(texts, batch_size=self.batch_size):
            out.append(sum(r["score"] for r in res if r["label"].lower() in self.positive))
        return out


class CallableDetector(Detector):
    def __init__(self, fn, name="callable", normalize_first=False):
        self.fn, self.name, self.normalize_first = fn, name, normalize_first

    def score(self, texts):
        return [float(x) for x in self.fn(texts)]
