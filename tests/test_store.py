"""Write-ahead log, snapshots and recovery, including real SIGKILLs at random moments."""
import multiprocessing as mp
import os
import random
import signal
import time

from babelguard.dataset import Record
from babelguard.engine import CampaignEngine
from babelguard.loadgen import stream
from babelguard.store import DurableEngine, EventLog

TEXTS = ["Your parcel is held at customs, pay the fee at <URL> today",
         "Your bank account is blocked, verify now at <URL> or call <PHONE_NUMBER>",
         "You won a prize of 50000, claim it by calling <PHONE_NUMBER> now",
         "Dear <NAMED_ENTITY>, your electricity will be cut tonight, pay at <URL>",
         "Part-time job: earn 3000 a day liking videos, message <PHONE_NUMBER>",
         "Your SIM will be blocked in 2 hours, update KYC at <URL>"]


def messages(n=3000):
    recs = [Record(id=str(k), text=t, lang="en", region="global", label="scam", group=k)
            for k, t in enumerate(TEXTS)]
    return [(text, lang, t) for text, lang, _, t in stream(recs, n_messages=n, n_campaigns=6, seed=5)]


def test_torn_and_corrupt_tail_is_dropped(tmp_path):
    p = str(tmp_path / "events.log")
    log = EventLog(p)
    for k in range(5):
        log.append({"text": f"m{k}", "lang": "en", "t": k})
    log.close()
    with open(p, "a", encoding="utf-8") as f:
        f.write('deadbeef {"text": "half')                 # a crash mid-write
    assert len(EventLog(p).records) == 5
    with open(p, "r+", encoding="utf-8") as f:              # corrupt record 3 (and so 3, 4)
        lines = f.readlines()
        lines[3] = lines[3].replace("m3", "mX")
        f.seek(0); f.truncate(); f.writelines(lines)
    assert [r["text"] for r in EventLog(p).records] == ["m0", "m1", "m2"]


def test_snapshot_and_replay_equal_uninterrupted(tmp_path):
    msgs = messages(1200)
    ref = CampaignEngine()
    for text, lang, t in msgs:
        ref.ingest(text, lang, t)
    d = str(tmp_path / "s")
    e = DurableEngine(d, snapshot_every=250)
    for text, lang, t in msgs[:700]:
        e.ingest(text, lang, t)
    e.close()
    e = DurableEngine(d, snapshot_every=250)                 # snapshot at 500, replay 200
    assert e.recovered == 200
    for text, lang, t in msgs[e.applied:]:
        e.ingest(text, lang, t)
    assert e.partition() == [ref.find(i) for i in range(len(ref.parent))]


def _worker(d, msgs):
    e = DurableEngine(d, snapshot_every=400, fsync_every=40)
    for text, lang, t in msgs[e.applied:]:
        e.ingest(text, lang, t)
    e.close()


def test_survives_sigkill_at_random_moments(tmp_path):
    msgs = messages(3000)
    ref = CampaignEngine()
    for text, lang, t in msgs:
        ref.ingest(text, lang, t)
    d = str(tmp_path / "k")
    ctx = mp.get_context("fork")
    rng = random.Random(7)
    kills = 0
    for _ in range(4):
        p = ctx.Process(target=_worker, args=(d, msgs))
        p.start()
        time.sleep(rng.uniform(0.15, 0.6))
        if p.is_alive():
            os.kill(p.pid, signal.SIGKILL)
            kills += 1
        p.join()
    e = DurableEngine(d, snapshot_every=400, fsync_every=40)
    for text, lang, t in msgs[e.applied:]:
        e.ingest(text, lang, t)
    assert kills >= 1
    assert e.partition() == [ref.find(i) for i in range(len(ref.parent))]
