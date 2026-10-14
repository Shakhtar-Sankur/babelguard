"""Agreement between two annotators of the same review file (Cohen's kappa on the label).

    python tools/agreement.py labels_hi_A.jsonl labels_hi_B.jsonl

Prints kappa, raw agreement, the confusion table, and the ids to send to a third annotator.
"""
import json
import sys
from collections import Counter

LABELS = ["scam", "spam", "legit", "unsure"]


def read(path):
    return {d["id"]: d for d in map(json.loads, open(path, encoding="utf-8")) if d.get("label")}


def kappa(a, b):
    """Cohen's kappa for two equal-length label lists."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def main(p1, p2):
    x, y = read(p1), read(p2)
    ids = sorted(set(x) & set(y))
    a, b = [x[i]["label"] for i in ids], [y[i]["label"] for i in ids]
    print(f"{len(ids)} messages labelled by both; agreement {sum(u == v for u, v in zip(a, b)) / max(1, len(ids)):.3f}; "
          f"Cohen's kappa {kappa(a, b):.3f}")
    table = Counter(zip(a, b))
    print("A \\ B   " + "  ".join(f"{k:>6s}" for k in LABELS))
    for r in LABELS:
        print(f"{r:7s} " + "  ".join(f"{table[(r, c)]:6d}" for c in LABELS))
    disputed = [i for i in ids if x[i]["label"] != y[i]["label"] or "unsure" in (x[i]["label"], y[i]["label"])]
    print("for a third annotator:", " ".join(disputed) if disputed else "none")


if __name__ == "__main__":
    main(*sys.argv[1:3])
