"""Campaign linking: which messages, in whatever language, belong to the same scam operation.

Two messages are linked when they share an indicator (the same UPI ID, wallet, phone number,
domain or short link) or when their text is a near copy. Linked messages form one campaign
(connected components). Indicators that appear in too many messages are not evidence of a
shared operator (a bank's real domain quoted in thousands of scams), so they are ignored: a
default allowlist of well-known legitimate domains plus a document-frequency cutoff.

Cross-language similarity plugs in through `embed`, a function from a list of texts to unit vectors
(`babelguard.embed.Encoder`, a multilingual sentence encoder). Each message is compared only with its
`neighbours` nearest messages, so linking by meaning stays fast on large collections.
"""
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from .indicators import extract, link_key
from .normalize import normalize

LEGIT_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".gov.uk", ".gob.mx", ".go.th", ".go.ke", ".gov.ng")
LEGIT_DOMAINS = {"rbi.org.in", "npci.org.in", "sbi.co.in", "onlinesbi.sbi", "hdfcbank.com",
                 "icicibank.com", "axisbank.com", "paytm.com", "phonepe.com", "google.com",
                 "youtube.com", "facebook.com", "instagram.com", "whatsapp.com", "amazon.in",
                 "amazon.com", "flipkart.com", "irctc.co.in", "cybercrime.gov.in"}


def legit(ind):
    return ind.kind == "domain" and (ind.value in LEGIT_DOMAINS or ind.value.endswith(LEGIT_SUFFIXES))


class _DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


def shingles(text, k=5):
    t = normalize(text).canonical
    return {t[i:i + k] for i in range(max(1, len(t) - k + 1))}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


@dataclass
class Campaign:
    members: list
    indicators: set = field(default_factory=set)
    links: list = field(default_factory=list)      # (i, j, reason) edges that formed it


def link(messages, max_df=0.2, text_threshold=0.6, embed=None, embed_threshold=0.85, country=None,
         neighbours=10):
    """Group messages into campaigns. Returns campaigns, largest first; singletons included."""
    n = len(messages)
    dsu, edges = _DSU(n), []
    inds = [extract(m, country) for m in messages]
    by_ind = defaultdict(list)
    for i, s in enumerate(inds):
        for ind in s:
            if not legit(ind):
                by_ind[link_key(ind)].append(i)
    limit = max(2, int(max_df * n))
    for ind, idx in by_ind.items():
        if len(idx) > limit:
            continue
        for j in idx[1:]:
            if dsu.find(idx[0]) != dsu.find(j):
                edges.append((idx[0], j, f"{ind[0]}:{ind[1]}"))
            dsu.union(idx[0], j)
    sh = [shingles(m) for m in messages]
    for i in range(n):
        for j in range(i + 1, n):
            if dsu.find(i) != dsu.find(j) and jaccard(sh[i], sh[j]) >= text_threshold:
                edges.append((i, j, "text"))
                dsu.union(i, j)
    if embed is not None and n > 1:
        from .embed import top_k
        v = np.asarray(embed(messages), dtype=np.float32)
        nn = top_k(v, v, k=min(neighbours + 1, n))
        for i in range(n):
            for j in nn[i]:
                j = int(j)
                if j != i and dsu.find(i) != dsu.find(j) and float(v[i] @ v[j]) >= embed_threshold:
                    edges.append((min(i, j), max(i, j), "meaning"))
                    dsu.union(i, j)
    groups = defaultdict(list)
    for i in range(n):
        groups[dsu.find(i)].append(i)
    out = []
    for root, members in groups.items():
        c = Campaign(members=members)
        for i in members:
            c.indicators |= {x for x in inds[i] if not legit(x)}
        c.links = [e for e in edges if dsu.find(e[0]) == root]
        out.append(c)
    return sorted(out, key=lambda c: (-len(c.members), c.members[0]))
