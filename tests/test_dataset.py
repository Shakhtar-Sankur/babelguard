"""Loader, template grouping and leak-free splits."""
import csv

import numpy as np

from babelguard.dataset import group_templates, load_imc25, split
from babelguard.lsh import MinHash, near_copies

FIELDS = ["time", "sender_id", "telephone_number_type", "original_network_name", "original_network_country",
          "text", "translation", "language", "url_shortener", "named_entity", "scam_type", "lure_principles"]


def write_imc(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for text, translation, lang, stype in rows:
            w.writerow({"text": text, "translation": translation, "language": lang, "scam_type": stype,
                        "lure_principles": "['time/urgency', 'authority']"})


def test_minhash_estimates_jaccard():
    a = {f"s{i}" for i in range(200)}
    b = {f"s{i}" for i in range(50, 250)}                 # Jaccard 150/250 = 0.6
    mh = MinHash(256, seed=3)
    est = float(np.mean(mh.signature(a) == mh.signature(b)))
    assert abs(est - 0.6) < 0.08


def test_near_copies_finds_copies_only():
    base = {f"w{i}" for i in range(100)}
    sets = [base, base | {"x1", "x2"}, {f"z{i}" for i in range(100)}, set()]
    pairs = {(i, j) for i, j, _ in near_copies(sets, 0.6)}
    assert pairs == {(0, 1)}


def test_load_imc25_redacts_maps_and_keeps_licence(tmp_path):
    p = tmp_path / "imc.csv"
    write_imc(p, [
        ("Your OTP 482913 ... account blocked, visit <URL>", "", "English", "banking"),
        ("आपका खाता बंद, ओटीपी ५५५१२३ भेजें", "Your account is closed, send OTP", "Hindi", "banking"),
        ("SALE 50% off everything", "", "English", "spam"),
        ("", "", "English", "others"),
    ])
    recs = load_imc25(p)
    assert len(recs) == 3
    assert "482913" not in recs[0].text and "[OTP]" in recs[0].text
    assert "५५५१२३" not in recs[1].text
    assert (recs[1].lang, recs[1].region, recs[1].scam_type) == ("hi", "south_asia", "bank_payment")
    assert recs[2].label == "spam" and recs[2].scam_type is None
    assert all(r.license == "CC-BY-4.0" and not r.verified for r in recs)
    assert recs[0].lures == ["time/urgency", "authority"]


def test_templates_group_across_languages_and_splits_do_not_leak(tmp_path):
    p = tmp_path / "imc.csv"
    rows = []
    for i in range(30):    # one template in three languages, many copies
        rows.append((f"Your parcel is held at customs, pay the fee now ref {i}", "", "English", "delivery"))
        rows.append((f"Tu paquete está retenido en aduanas, paga la tasa ahora ref {i}",
                     f"Your parcel is held at customs, pay the fee now ref {i}", "Spanish", "delivery"))
        rows.append((f"Paket Anda tertahan di bea cukai, bayar biayanya sekarang ref {i}",
                     f"Your parcel is held at customs, pay the fee now ref {i}", "Indonesian", "delivery"))
    for i in range(40):    # distinct messages
        rows.append((f"Unique message number {i} " + "abcdefghij"[i % 10] * (i + 5), "", "English", "others"))
    write_imc(p, rows)
    recs = load_imc25(p)
    group_templates(recs)
    parcel = {r.group for r in recs if "customs" in (r.translation or r.text)}
    assert len(parcel) == 1
    assert {r.lang for r in recs if r.group in parcel} == {"en", "es", "id"}
    parts = split(recs)
    seen = {}
    for name, rs in parts.items():
        for r in rs:
            assert seen.setdefault(r.group, name) == name     # no template in two splits
    assert sum(len(v) for v in parts.values()) == len(recs)


def test_placeholder_only_messages_do_not_chain(tmp_path):
    p = tmp_path / "imc.csv"
    write_imc(p, [("<NAMED_ENTITY><URL>", "", "English", "others"),
                  ("<NAMED_ENTITY> <URL>", "", "Spanish", "others"),
                  ("【<NAMED_ENTITY>", "", "Japanese", "delivery")])
    recs = load_imc25(p)
    assert group_templates(recs) == 3


def test_review_sample_spreads_over_templates_first():
    from babelguard.dataset import Record, review_sample
    recs = []
    for i in range(50):                       # one big campaign
        recs.append(Record(id=f"big{i}", text="x", lang="hi", region="south_asia", label="scam", group=0))
    for g in range(1, 8):                     # seven small ones
        recs.append(Record(id=f"s{g}", text="y", lang="hi", region="south_asia", label="scam", group=g))
    picked = review_sample(recs, per_label=10)
    assert len(picked) == 10
    assert {r.group for r in picked} == set(range(8))       # every template before any second copy
    assert sum(r.group == 0 for r in picked) == 3


def test_kappa():
    import importlib.util
    spec = importlib.util.spec_from_file_location("agreement", "tools/agreement.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.kappa(["scam"] * 4, ["scam"] * 4) == 1.0
    assert abs(m.kappa(["scam", "legit", "scam", "legit"], ["scam", "legit", "legit", "scam"])) < 1e-9
