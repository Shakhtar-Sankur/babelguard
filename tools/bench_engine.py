"""Throughput, latency and accuracy of the streaming engine on synthetic campaigns (out/).

    python tools/bench_engine.py 100000 2000

Builds a stream of N messages over C campaigns from real IMC 2025 templates
(babelguard.loadgen; the load is synthetic and reported as such), feeds it to CampaignEngine one
message at a time, and reports messages per second, per-message latency (p50, p99, max) and
B-cubed precision/recall/F1 against the true campaigns.
"""
import json
import os
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babelguard.dataset import group_templates, load_imc25  # noqa: E402
from babelguard.engine import CampaignEngine  # noqa: E402
from babelguard.loadgen import bcubed, stream  # noqa: E402


def main(n=100000, c=2000, out="out"):
    n, c = int(n), int(c)
    recs = load_imc25("data/private/imc25.csv")
    group_templates(recs)
    msgs = list(stream(recs, n_messages=n, n_campaigns=c, seed=0))
    e = CampaignEngine()
    lat = np.empty(n)
    ids = np.empty(n, dtype=np.int64)
    t0 = time.perf_counter()
    for k, (text, lang, _, t) in enumerate(msgs):
        s = time.perf_counter()
        ids[k] = e.ingest(text, lang, t).message
        lat[k] = time.perf_counter() - s
    wall = time.perf_counter() - t0
    pred = [e.find(int(i)) for i in ids]
    p, r, f = bcubed(pred, [m[2] for m in msgs])
    true_campaigns = len({m[2] for m in msgs})
    rep = {"load": "synthetic, from real IMC 2025 templates", "messages": n, "campaigns_true": true_campaigns,
           "campaigns_found": len(set(pred)), "seconds": round(wall, 1),
           "messages_per_second": round(n / wall, 1), "messages_per_day_one_core": int(n / wall * 86400),
           "latency_ms": {"p50": round(float(np.percentile(lat, 50)) * 1e3, 3),
                          "p99": round(float(np.percentile(lat, 99)) * 1e3, 3),
                          "max": round(float(lat.max()) * 1e3, 1)},
           "bcubed": {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)},
           "indicators_blocked": e.stats["indicators_blocked"],
           "hardware": f"{platform.processor() or platform.machine()}, 1 core (Python)"}
    os.makedirs(out, exist_ok=True)
    json.dump(rep, open(os.path.join(out, f"bench_engine_{n}.json"), "w"), indent=1)
    return rep


if __name__ == "__main__":
    print(json.dumps(main(*sys.argv[1:3]), indent=1))
