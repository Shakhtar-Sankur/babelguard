"""Nearest-neighbour search and meaning-based linking (no model download: a fake encoder)."""
import numpy as np

from babelguard.campaigns import link
from babelguard.embed import top_k


def unit(rows):
    v = np.asarray(rows, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_top_k_orders_by_similarity():
    corpus = unit([[1, 0, 0], [0.9, 0.1, 0], [0, 1, 0], [0, 0, 1]])
    queries = unit([[1, 0.05, 0], [0, 0, 1]])
    nn = top_k(queries, corpus, k=2)
    assert nn[0].tolist() == [0, 1]
    assert nn[1][0] == 3


def test_top_k_chunks_agree_with_one_shot():
    rng = np.random.default_rng(0)
    q, c = unit(rng.normal(size=(50, 8))), unit(rng.normal(size=(40, 8)))
    assert (top_k(q, c, k=5, chunk=7) == top_k(q, c, k=5)).all()


def test_meaning_links_only_nearest_neighbours_above_threshold():
    topics = {"parcel": [1, 0, 0], "bank": [0, 1, 0], "prize": [0, 0, 1]}

    def embed(texts):
        return unit([topics[t.split()[0]] for t in texts])

    msgs = ["parcel en", "parcel es", "parcel hi", "bank en", "bank th", "prize sw"]
    cs = link(msgs, embed=embed, embed_threshold=0.9, text_threshold=1.01, neighbours=3)
    assert sorted(sorted(c.members) for c in cs) == [[0, 1, 2], [3, 4], [5]]
