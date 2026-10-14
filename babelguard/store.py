"""Durability: a write-ahead log and snapshots, so the engine survives being killed at any moment.

Every message is appended to the log (with a CRC32 of its record) before the engine sees it. Every
`snapshot_every` messages the engine's whole state is written to a temporary file, flushed, and
renamed over the previous snapshot, so a crash leaves either the old snapshot or the new one,
never half of one. Recovery loads the snapshot and replays the log records after it. A record cut
short by the crash (a torn last line) or failing its checksum ends the log there.

The engine is deterministic (seeded MinHash, explicit timestamps), so a recovered engine holds
exactly the campaigns an uninterrupted one would.
"""
import json
import os
import pickle
import zlib

from .engine import CampaignEngine


def _encode(rec):
    body = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
    return f"{zlib.crc32(body.encode('utf-8')):08x} {body}\n"


def _decode(line):
    if not line.endswith("\n") or len(line) < 10:
        return None
    crc, body = line[:8], line[9:-1]
    if f"{zlib.crc32(body.encode('utf-8')):08x}" != crc:
        return None
    return json.loads(body)


class EventLog:
    def __init__(self, path, fsync_every=256):
        self.path, self.fsync_every = path, fsync_every
        self.records = self._read_valid()
        self.f = open(path, "a", encoding="utf-8")
        self.pending = 0

    def _read_valid(self):
        if not os.path.exists(self.path):
            return []
        out, good_bytes = [], 0
        with open(self.path, encoding="utf-8", errors="replace", newline="") as f:
            for line in f:
                rec = _decode(line)
                if rec is None:
                    break
                out.append(rec)
                good_bytes += len(line.encode("utf-8"))
        with open(self.path, "r+b") as f:          # drop a torn or corrupt tail
            f.truncate(good_bytes)
        return out

    def append(self, rec):
        self.f.write(_encode(rec))
        self.pending += 1
        if self.pending >= self.fsync_every:
            self.flush()

    def flush(self):
        self.f.flush()
        os.fsync(self.f.fileno())
        self.pending = 0

    def close(self):
        self.flush()
        self.f.close()


class DurableEngine:
    """CampaignEngine with a write-ahead log and atomic snapshots in `directory`."""

    def __init__(self, directory, snapshot_every=5000, fsync_every=256, **engine_kw):
        os.makedirs(directory, exist_ok=True)
        self.dir, self.snapshot_every = directory, snapshot_every
        self.log = EventLog(os.path.join(directory, "events.log"), fsync_every)
        snap = os.path.join(directory, "snapshot.pkl")
        applied = 0
        if os.path.exists(snap):
            with open(snap, "rb") as f:
                state = pickle.load(f)
            self.engine, applied = state["engine"], state["applied"]
        else:
            self.engine = CampaignEngine(**engine_kw)
        for rec in self.log.records[applied:]:          # replay what the snapshot does not hold
            self.engine.ingest(rec["text"], rec["lang"], rec["t"], rec.get("country"))
        self.applied = len(self.log.records)
        self.recovered = len(self.log.records) - applied
        if self.recovered >= snapshot_every:             # else repeated crashes make each recovery longer
            self.snapshot()
        if self.recovered >= snapshot_every:             # else repeated crashes make each recovery longer
            self.snapshot()

    def ingest(self, text, lang="und", t=0.0, country=None):
        self.log.append({"text": text, "lang": lang, "t": t, "country": country})
        a = self.engine.ingest(text, lang, t, country)
        self.applied += 1
        if self.applied % self.snapshot_every == 0:
            self.snapshot()
        return a

    def snapshot(self):
        self.log.flush()                                 # the snapshot never runs ahead of the log
        tmp = os.path.join(self.dir, "snapshot.pkl.tmp")
        with open(tmp, "wb") as f:
            pickle.dump({"engine": self.engine, "applied": self.applied}, f, protocol=pickle.HIGHEST_PROTOCOL)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, os.path.join(self.dir, "snapshot.pkl"))

    def close(self):
        self.log.close()

    def partition(self):
        """Campaign id of every message, in order: the engine's whole answer, for comparisons."""
        return [self.engine.find(i) for i in range(len(self.engine.parent))]
