"""Can Babelguard recognise the same scam across a language barrier? (private: writes to out/)

    python -m babelguard.sources fetch imc25
    python tools/eval_linking.py data/private/imc25.csv [model]

Ground truth comes from the IMC 2025 dataset itself: each non-English report carries an English
translation. Every non-English message (in its original language and script) is used as a query
against the pool of all those English translations; it counts as found when a top-ranked
translation belongs to its own template group (its own translation or a near-copy of it).

Reported per language: recall@1 and @10 with the multilingual encoder; how often plain text
matching (character 5-gram Jaccard >= 0.3, what linking can do without an encoder) connects the
message to its own translation at all; and a similarity threshold calibrated so that only 1% of
pairs from different templates would be linked.
"""
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babelguard.campaigns import jaccard, shingles  # noqa: E402
from babelguard.dataset import content, group_templates, load_imc25  # noqa: E402
from babelguard.embed import DEFAULT_MODEL, Encoder, top_k  # noqa: E402


def main(path, model=DEFAULT_MODEL, out="out"):
    t0 = time.time()
    recs = load_imc25(path)
    group_templates(recs)
    q = [r for r in recs if r.lang not in ("en", "und") and content(r.text) and content(r.translation)]
    src = [content(r.text) for r in q]
    tgt = [content(r.translation) for r in q]
    groups = np.array([r.group for r in q])
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(out, f"emb_{model.replace('/', '_')}_{len(q)}.npz")
    if os.path.exists(cache):
        z = np.load(cache)
        es, et = z["src"], z["tgt"]
    else:
        enc = Encoder(model)
        es, et = enc(src), enc(tgt)
        np.savez_compressed(cache, src=es, tgt=et)
    t_embed = time.time() - t0

    nn = top_k(es, et, k=10)
    hit = groups[nn] == groups[:, None]
    r1, r10 = hit[:, 0], hit.any(axis=1)
    text_ok = np.array([jaccard(shingles(a), shingles(b)) >= 0.3 for a, b in zip(src, tgt)])

    # calibration: own-pair similarity vs pairs from different template groups
    own = np.einsum("ij,ij->i", es, et)
    rng = np.random.default_rng(0)
    j = rng.integers(0, len(q), size=len(q) * 5)
    i = np.repeat(np.arange(len(q)), 5)
    diff = groups[i] != groups[j]
    neg = np.einsum("ij,ij->i", es[i[diff]], et[j[diff]])
    thr = float(np.quantile(neg, 0.99))

    by = defaultdict(list)
    for k, r in enumerate(q):
        by[r.lang].append(k)
    langs = {}
    for lang, ks in sorted(by.items(), key=lambda kv: -len(kv[1])):
        ks = np.array(ks)
        langs[lang] = {"region": q[ks[0]].region, "messages": int(len(ks)),
                       "recall@1": round(float(r1[ks].mean()), 3), "recall@10": round(float(r10[ks].mean()), 3),
                       "text_match": round(float(text_ok[ks].mean()), 3),
                       "linked_at_1pct_fpr": round(float((own[ks] >= thr).mean()), 3)}
    report = {"model": model, "queries": len(q), "pool": len(q),
              "recall@1": round(float(r1.mean()), 3), "recall@10": round(float(r10.mean()), 3),
              "text_match": round(float(text_ok.mean()), 3),
              "threshold_1pct_fpr": round(thr, 4),
              "linked_at_1pct_fpr": round(float((own >= thr).mean()), 3),
              "own_pair_similarity_median": round(float(np.median(own)), 4),
              "other_pair_similarity_median": round(float(np.median(neg)), 4),
              "seconds_embedding": round(t_embed, 1), "languages": langs}
    json.dump(report, open(os.path.join(out, "linking_eval.json"), "w"), indent=1)
    return report


if __name__ == "__main__":
    rep = main(*sys.argv[1:3])
    print(json.dumps({k: v for k, v in rep.items() if k != "languages"}, indent=1))
    print(f"{'lang':5s} {'region':20s} {'n':>5s} {'R@1':>6s} {'R@10':>6s} {'text':>6s} {'link@1%':>8s}")
    for lang, v in rep["languages"].items():
        print(f"{lang:5s} {v['region']:20s} {v['messages']:5d} {v['recall@1']:6.3f} {v['recall@10']:6.3f} "
              f"{v['text_match']:6.3f} {v['linked_at_1pct_fpr']:8.3f}")
