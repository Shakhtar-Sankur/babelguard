"""Ingest on many cores: workers compute each message's Features, the engine applies them in order.

`CampaignEngine.features` is a pure function of the message and about 90% of ingest time, so it
runs in worker processes; `apply` updates the campaigns and runs in arrival order in this process.
The result is identical to feeding the same messages to `CampaignEngine.ingest` one by one.
"""
import multiprocessing as mp

from .engine import message_features
from .lsh import MinHash

_W = {}


def _init(bands, rows, seed):
    _W.update(mh=MinHash(bands * rows, seed), bands=bands, rows=rows)


def _features(item):
    text, country = item
    return message_features(text, country, _W["mh"], _W["bands"], _W["rows"])


def ingest_parallel(engine, messages, workers=3, chunksize=256, seed=1):
    """Feed (text, lang, t, country) tuples to `engine`; yields each Assignment in order.
    `seed` must be the engine's MinHash seed (the default for CampaignEngine)."""
    messages = iter(messages)
    meta = []                                   # (lang, t) of messages handed to the workers

    def texts():
        for text, lang, t, country in messages:
            meta.append((lang, t))
            yield text, country

    ctx = mp.get_context("fork")
    with ctx.Pool(workers, initializer=_init, initargs=(engine.bands, engine.rows, seed)) as pool:
        for k, feats in enumerate(pool.imap(_features, texts(), chunksize=chunksize)):
            lang, t = meta[k]
            meta[k] = None                      # do not keep every message's metadata
            yield engine.apply(feats, lang, t)
