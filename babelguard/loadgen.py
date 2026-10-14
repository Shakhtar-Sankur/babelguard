"""Synthetic scam streams with known campaigns, built from real reported templates.

Open data holds tens of thousands of real messages; testing an engine at millions needs load. Each
synthetic campaign takes one real template (a distinct one, so campaigns never share a lure by
construction) and gives it its own scammer details: phone numbers, a lookalike domain, a UPI ID.
Its messages then vary the way real ones do: victims' names, dates and amounts change, a word is
dropped, and some use the template's real English translation (the same campaign in a second
language). A share are disguised with hidden characters or look-alike letters. Message counts per
campaign follow a heavy tail, as real campaigns do.

Every message carries its true campaign id. Results on this load are labelled synthetic.
"""
import random
import re

from .dataset import content

NAMES = ["Asha", "Ravi", "Maria", "John", "Fatima", "Chen", "Amara", "Luis", "Priya", "Omar"]
WORDS = ["secure", "verify", "update", "help", "claim", "track", "refund", "portal", "pay", "info"]
TLDS = ["com", "top", "xyz", "info", "online", "in", "co", "site"]
UPI = ["ybl", "okaxis", "paytm", "upi", "oksbi", "ibl"]
TAG = re.compile(r"<([A-Z_]+)>")


def _phone(rng):
    return rng.choice("6789") + "".join(rng.choice("0123456789") for _ in range(9))


def _disguise(text, rng):
    if rng.random() < 0.5:
        words = text.split(" ")
        k = rng.randrange(len(words))
        w = words[k]
        if len(w) > 3:
            p = rng.randrange(1, len(w))
            words[k] = w[:p] + "​" + w[p:]
        return " ".join(words)
    return text.replace("a", "а", 1).replace("o", "о", 1)     # Cyrillic look-alikes


class Campaign:
    def __init__(self, cid, template, translation, lang, rng):
        self.id, self.template, self.translation, self.lang = cid, template, translation, lang
        self.domain = f"{rng.choice(WORDS)}-{rng.choice(WORDS)}{rng.randrange(10, 99)}.{rng.choice(TLDS)}"
        self.phones = [_phone(rng) for _ in range(rng.choice([1, 1, 2, 3]))]
        self.upi = f"{rng.choice(WORDS)}.{rng.choice(WORDS)}{rng.randrange(100)}@{rng.choice(UPI)}"

    def fill(self, text, rng):
        def sub(m):
            tag = m.group(1)
            if tag == "URL":
                return f"https://{self.domain}/{rng.choice(WORDS)}"
            if tag == "PHONE_NUMBER":
                return rng.choice(self.phones)
            if tag == "NAMED_ENTITY":
                return rng.choice(NAMES)
            if tag == "DATE_TIME":
                return f"{rng.randrange(1, 29)}/{rng.randrange(1, 13)}"
            if tag in ("US_BANK_NUMBER", "US_DRIVER_LICENSE"):
                return str(rng.randrange(10**5, 10**6))
            return rng.choice(NAMES)
        out = TAG.sub(sub, text)
        if self.domain not in out and rng.random() < 0.5:
            out += f" {self.upi}" if rng.random() < 0.5 else f" Call {rng.choice(self.phones)}"
        return out


def templates(records):
    """One (text, translation, lang) per template group with enough real text."""
    seen, out = set(), []
    for r in records:
        if r.group in seen or not content(r.text):
            continue
        seen.add(r.group)
        out.append((r.text, r.translation if content(r.translation) else "", r.lang))
    return out


def stream(records, n_messages, n_campaigns, seed=0, translated=0.2, disguised=0.05, alpha=1.3):
    """Yield (text, lang, campaign_id, t) for a heavy-tailed mix of synthetic campaigns."""
    rng = random.Random(seed)
    pool = templates(records)
    rng.shuffle(pool)
    n_campaigns = min(n_campaigns, len(pool))
    camps = [Campaign(c, *pool[c], rng=rng) for c in range(n_campaigns)]
    weights = [1.0 / (k + 1) ** alpha for k in range(n_campaigns)]
    t = 0.0
    for _ in range(n_messages):
        c = rng.choices(camps, weights)[0]
        if c.translation and rng.random() < translated:
            text, lang = c.fill(c.translation, rng), "en"
        else:
            text, lang = c.fill(c.template, rng), c.lang
        words = text.split(" ")
        if len(words) > 8 and rng.random() < 0.3:
            del words[rng.randrange(len(words))]
            text = " ".join(words)
        if rng.random() < disguised:
            text = _disguise(text, rng)
        t += rng.expovariate(1.0)
        yield text, lang, c.id, t


def bcubed(pred, true):
    """B-cubed precision, recall and F1 of a clustering (parallel lists of cluster ids)."""
    from collections import Counter
    n = len(pred)
    pt = Counter(zip(pred, true))
    ps, ts = Counter(pred), Counter(true)
    p = sum(c * c / ps[a] for (a, _), c in pt.items()) / n
    r = sum(c * c / ts[b] for (_, b), c in pt.items()) / n
    return p, r, 2 * p * r / (p + r)
