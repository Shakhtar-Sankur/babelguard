"""Near-copy detection at scale: MinHash signatures with LSH banding, then an exact Jaccard check.

Comparing every pair is quadratic; MinHash LSH only compares messages that collide in at least one
band. With 63 hash functions in 21 bands of 3 rows, two messages whose shingle sets have Jaccard
similarity 0.6 collide with probability 1 - (1 - 0.6^3)^21 = 0.994. Every candidate is confirmed
with the exact Jaccard similarity, so LSH can only miss links, never invent them. Large buckets
(thousands of copies of one template) are checked against a few representatives, not pairwise.
"""
import hashlib

import numpy as np

_P = (1 << 31) - 1                 # Mersenne prime: a * x < 2^62 fits in uint64


def _h64(s):
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "little")


class MinHash:
    def __init__(self, num_perm=63, seed=1):
        rng = np.random.default_rng(seed)
        self.a = rng.integers(1, _P, size=num_perm, dtype=np.uint64)
        self.b = rng.integers(0, _P, size=num_perm, dtype=np.uint64)
        self.num_perm = num_perm

    def signature(self, shingles):
        if not shingles:
            return np.full(self.num_perm, np.iinfo(np.uint64).max, dtype=np.uint64)
        return self.signature_of_hashes(hashes(shingles))

    def signature_of_hashes(self, h):
        """Signature from `hashes(shingles)`, so a caller that keeps the hashes hashes only once."""
        if not len(h):
            return np.full(self.num_perm, np.iinfo(np.uint64).max, dtype=np.uint64)
        x = h % np.uint64(_P)
        v = (self.a[:, None] * x[None, :] + self.b[:, None]) % np.uint64(_P)
        return v.min(axis=1)


def hashes(shingles):
    """Sorted, distinct 64-bit hashes of a shingle set: a compact stand-in for the set (8 bytes per
    shingle instead of a Python string), deterministic across processes, so it survives a restart."""
    return np.unique(np.fromiter((_h64(s) for s in shingles), dtype=np.uint64, count=len(shingles)))


def jaccard_hashes(a, b):
    inter = np.intersect1d(a, b, assume_unique=True).size
    return inter / (len(a) + len(b) - inter)


def near_copies(sets, threshold=0.6, bands=21, rows=3, reps=8, seed=1):
    """Pairs (i, j, jaccard) with jaccard >= threshold among shingle sets, found via LSH."""
    mh = MinHash(bands * rows, seed)
    sigs = np.stack([mh.signature(s) for s in sets]) if sets else np.zeros((0, bands * rows), np.uint64)
    found = {}
    for b in range(bands):
        buckets = {}
        for i, row in enumerate(sigs[:, b * rows:(b + 1) * rows]):
            if sets[i]:
                buckets.setdefault(row.tobytes(), []).append(i)
        for members in buckets.values():
            if len(members) < 2:
                continue
            anchors = []
            for i in members:
                for a in anchors:
                    key = (a, i)
                    if key in found:
                        break
                    inter = len(sets[a] & sets[i])
                    jac = inter / (len(sets[a]) + len(sets[i]) - inter)
                    if jac >= threshold:
                        found[key] = jac
                        break
                else:
                    if len(anchors) < reps:
                        anchors.append(i)
    return [(i, j, v) for (i, j), v in found.items()]
