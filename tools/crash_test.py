"""Kill the durable engine at random moments, many times, and check every recovery (out/).

    python tools/crash_test.py 20000 50

Feeds N synthetic messages (from real IMC 2025 templates) to a DurableEngine in a child process
and SIGKILLs it K times at random moments. After each kill a new process recovers from the
snapshot and the log and the client resends from the last durable message. At the end, every
message's campaign must equal an uninterrupted run's.
"""
import json
import multiprocessing as mp
import os
import random
import shutil
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babelguard.dataset import group_templates, load_imc25  # noqa: E402
from babelguard.engine import CampaignEngine  # noqa: E402
from babelguard.loadgen import stream  # noqa: E402
from babelguard.store import DurableEngine  # noqa: E402


def worker(d, msgs, q):
    e = DurableEngine(d, snapshot_every=2000, fsync_every=100)
    q.put(("start", e.applied, e.recovered))
    for text, lang, t in msgs[e.applied:]:
        e.ingest(text, lang, t)
    e.close()
    q.put(("done", e.applied, 0))


def main(n=20000, kills=50, out="out", seed=11):
    n, kills = int(n), int(kills)
    recs = load_imc25("data/private/imc25.csv")
    group_templates(recs)
    msgs = [(a, b, t) for a, b, _, t in stream(recs, n_messages=n, n_campaigns=500, seed=seed)]
    ref = CampaignEngine()
    t0 = time.time()
    for text, lang, t in msgs:
        ref.ingest(text, lang, t)
    full_run = time.time() - t0
    expected = [ref.find(i) for i in range(len(ref.parent))]
    d = os.path.join(out, "crash_state")
    shutil.rmtree(d, ignore_errors=True)
    ctx, rng, q = mp.get_context("fork"), random.Random(seed), None
    done, killed, restarts = False, 0, []
    while not done:
        q = ctx.Queue()
        p = ctx.Process(target=worker, args=(d, msgs, q))
        p.start()
        start = q.get()
        restarts.append({"resumed_at": start[1], "replayed_from_log": start[2]})
        if killed < kills:
            time.sleep(rng.uniform(0.0, full_run / kills * 2))
            if p.is_alive():
                os.kill(p.pid, signal.SIGKILL)
                killed += 1
        p.join()
        done = p.exitcode == 0
    e = DurableEngine(d)
    got = e.partition()
    rep = {"messages": n, "kills": killed, "restarts": len(restarts), "identical": got == expected,
           "campaigns": len(set(expected)), "messages_lost": n - len(got),
           "max_replayed_from_log": max(r["replayed_from_log"] for r in restarts)}
    os.makedirs(out, exist_ok=True)
    json.dump(rep, open(os.path.join(out, "crash_test.json"), "w"), indent=1)
    shutil.rmtree(d, ignore_errors=True)
    return rep


if __name__ == "__main__":
    print(json.dumps(main(*sys.argv[1:3]), indent=1))
