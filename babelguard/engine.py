"""Streaming campaign engine: link each message to a campaign the moment it arrives.

`campaigns.link` groups a fixed batch. The engine does the same work incrementally, so it can run
for months on a stream:

- an indicator index: each scammer detail (link key) points at the messages that used it; details
  that turn out to be everywhere (a bank's real domain quoted in thousands of scams) stop linking;
- a streaming MinHash LSH index for near-copy text, with a bounded number of representatives per
  bucket, so a template sent a million times costs a few comparisons, not a million;
- optionally, a nearest-neighbour index over multilingual embeddings for linking by meaning;
- union-find over message ids, with per-campaign state: size, languages, first and last seen,
  indicators.

`ingest` returns the campaign a message joined and why, which is what an analyst or an alert needs.
"""
import gc
import time
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from .campaigns import legit
from .indicators import extract, link_key
from .lsh import MinHash, hashes, jaccard_hashes
from .normalize import normalize


@dataclass
class Campaign:
    id: int
    size: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    languages: set = field(default_factory=set)
    indicators: set = field(default_factory=set)


@dataclass
class Assignment:
    message: int
    campaign: int
    new: bool
    reasons: list


@dataclass(frozen=True)
class Features:
    """What `apply` needs from a message: (link key, label) of each scammer detail, in a fixed
    order, and the message's shingle hashes and LSH band keys (None for an empty message)."""
    indicators: tuple
    shingles: object
    band_keys: tuple


def message_features(text, country, mh, bands, rows):
    """Pure per-message work: the same input always gives the same Features, in any process."""
    norm = normalize(text)
    inds = sorted(((link_key(ind), f"{ind.kind}:{ind.value}") for ind in extract(text, country, norm=norm)
                   if not legit(ind)), key=lambda x: (x[0], x[1]))
    canon = norm.canonical
    if not canon:
        return Features(tuple(inds), None, ())
    sh = hashes({canon[k:k + 5] for k in range(max(1, len(canon) - 4))})
    sig = mh.signature_of_hashes(sh)
    return Features(tuple(inds), sh, tuple(sig[b * rows:(b + 1) * rows].tobytes() for b in range(bands)))


class CampaignEngine:
    def __init__(self, text_threshold=0.6, bands=21, rows=3, reps=4, max_indicator_campaigns=50,
                 embed=None, embed_threshold=0.85, ann_k=5, seed=1, gc_freeze_every=20000):
        self.mh = MinHash(bands * rows, seed)
        self.bands, self.rows, self.reps = bands, rows, reps
        self.text_threshold = text_threshold
        self.max_indicator_campaigns = max_indicator_campaigns
        self.embed, self.embed_threshold, self.ann_k = embed, embed_threshold, ann_k
        self.parent = []                     # union-find over message ids
        self.shingles = []                   # shingle hashes per message (only representatives keep theirs)
        self.buckets = [dict() for _ in range(bands)]
        self.by_indicator = defaultdict(list)        # link key -> message ids (bounded)
        self.indicator_campaigns = defaultdict(set)  # link key -> campaign roots seen with it
        self.blocked = set()                         # link keys that stopped linking
        self.campaigns = {}
        self.vectors = []                            # embeddings, if any
        self.stats = defaultdict(int)
        # The engine's state is millions of long-lived objects; Python's full garbage collection
        # rescans all of them and stalls ingest for seconds. Freezing them moves them out of its scans.
        self.gc_freeze_every = gc_freeze_every

    # ---- union-find -------------------------------------------------------------------------
    def find(self, x):
        p = self.parent
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def _union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        if rb < ra:                          # the oldest message keeps the campaign id, so ids are stable
            ra, rb = rb, ra
        self.parent[rb] = ra
        ca, cb = self.campaigns[ra], self.campaigns.pop(rb)
        ca.size += cb.size
        ca.first_seen = min(ca.first_seen, cb.first_seen)
        ca.last_seen = max(ca.last_seen, cb.last_seen)
        ca.languages |= cb.languages
        ca.indicators |= cb.indicators
        return ra

    # ---- ingest -----------------------------------------------------------------------------
    # Ingest is split in two. `features` is a pure function of the message (cleaning, scammer
    # details, shingle hashes, LSH band keys): about 90% of the work, and it can run on any core
    # or machine. `apply` links the message into the campaigns and must run in arrival order.
    def features(self, text, country=None):
        return message_features(text, country, self.mh, self.bands, self.rows)

    def ingest(self, text, lang="und", t=None, country=None):
        return self.apply(self.features(text, country), lang, t, text=text)

    def apply(self, feats, lang="und", t=None, text=None):
        t = time.time() if t is None else t
        i = len(self.parent)
        self.parent.append(i)
        self.campaigns[i] = Campaign(id=i, size=1, first_seen=t, last_seen=t, languages={lang})
        reasons, linked = [], set()

        # 1. indicators
        for key, label in feats.indicators:
            self.campaigns[self.find(i)].indicators.add(label)
            if key in self.blocked:
                continue
            for j in self.by_indicator[key][:8]:
                if self.find(j) != self.find(i):
                    self._union(i, j)
                    reasons.append(f"{key[0]}:{key[1]}")
                    linked.add(self.find(j))
            if len(self.by_indicator[key]) < 8:
                self.by_indicator[key].append(i)
            roots = self.indicator_campaigns[key]
            roots.add(self.find(i))
            if len(roots) > self.max_indicator_campaigns:
                roots = {self.find(r) for r in roots}        # merged campaigns count once
                self.indicator_campaigns[key] = roots
                if len(roots) > self.max_indicator_campaigns:
                    self.blocked.add(key)
                    self.stats["indicators_blocked"] += 1

        # 2. near-copy text, through the streaming LSH index
        sh = feats.shingles
        keep = False
        if sh is not None:
            for b, key in enumerate(feats.band_keys):
                reps = self.buckets[b].setdefault(key, [])
                for j in reps:
                    if self.find(j) == self.find(i):
                        continue
                    if jaccard_hashes(sh, self.shingles[j]) >= self.text_threshold:
                        self._union(i, j)
                        reasons.append("text")
                        break
                if len(reps) < self.reps:
                    reps.append(i)
                    keep = True
        self.shingles.append(sh if keep else None)

        # 3. meaning, through the nearest-neighbour index
        if self.embed is not None:
            if text is None:
                raise ValueError("linking by meaning needs the message text")
            v = np.asarray(self.embed([text])[0], dtype=np.float32)
            if self.vectors:
                m = np.stack(self.vectors)
                sims = m @ v
                for j in np.argsort(-sims)[:self.ann_k]:
                    if sims[j] >= self.embed_threshold and self.find(int(j)) != self.find(i):
                        self._union(i, int(j))
                        reasons.append("meaning")
            self.vectors.append(v)

        root = self.find(i)
        c = self.campaigns[root]
        c.last_seen = max(c.last_seen, t)
        c.languages.add(lang)
        self.stats["messages"] += 1
        if self.gc_freeze_every and self.stats["messages"] % self.gc_freeze_every == 0:
            gc.freeze()
        return Assignment(message=i, campaign=root, new=(c.size == 1), reasons=sorted(set(reasons)))

    def campaign_of(self, i):
        return self.campaigns[self.find(i)]

    def top(self, n=10):
        return sorted(self.campaigns.values(), key=lambda c: -c.size)[:n]
