"""Protection-gap metrics and the detector interface."""
import math

from babelguard.dataset import Record
from babelguard.detectors import CallableDetector, KeywordBaseline
from babelguard.protection import by_group, rates, wilson


def test_wilson_interval():
    lo, hi = wilson(8, 10)
    assert 0.49 < lo < 0.5 and 0.94 < hi < 0.95          # textbook values: 0.490, 0.943
    assert wilson(0, 0) != wilson(0, 0)                    # nan pair
    assert wilson(0, 20)[0] == 0.0 and wilson(20, 20)[1] == 1.0


def test_rates_ignore_spam_and_unknown():
    r = rates(["scam", "scam", "legit", "legit", "spam", "unknown"], [1, 0, 1, 0, 1, 1])
    assert (r.scams, r.caught, r.genuine, r.false_alarms) == (2, 1, 2, 1)
    assert r.detection == 0.5 and r.false_alarm == 0.5


def rec(lang, label):
    return Record(id="x", text="t", lang=lang, region="r", label=label)


def test_by_group_reports_gap_to_english_and_small_samples():
    recs = [rec("en", "scam")] * 40 + [rec("hi", "scam")] * 40 + [rec("sw", "scam")] * 5
    flags = [1] * 36 + [0] * 4 + [1] * 10 + [0] * 30 + [1] * 5
    t = by_group(recs, flags)
    assert t["en"]["detection"] == 0.9 and t["hi"]["detection"] == 0.25
    assert t["hi"]["gap_vs_english"] == -0.65
    assert t["sw"]["enough_data"] is False and t["en"]["enough_data"] is True
    assert math.isnan(float("nan")) and t["en"]["false_alarm"] is None


def test_keyword_baseline_and_normalization():
    kw = KeywordBaseline(min_hits=2)
    assert kw(["URGENT: verify your KYC now"])[0] == 1.0
    assert kw(["Lunch at 1?"])[0] == 0.0
    disguised = "Ur​gent: ver​ify your K​YC"          # hidden characters break words
    assert KeywordBaseline(min_hits=2)([disguised])[0] < 1.0
    assert KeywordBaseline(min_hits=2, normalize_first=True)([disguised])[0] == 1.0


def test_callable_detector():
    d = CallableDetector(lambda ts: [len(t) > 3 for t in ts], name="len")
    assert d(["hi", "hello"]) == [0.0, 1.0]
