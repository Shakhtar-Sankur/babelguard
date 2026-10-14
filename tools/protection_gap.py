"""Run one detector over every source and report the protection gap per language (private: out/).

    python -m babelguard.sources fetch
    python tools/protection_gap.py keywords            # English keyword baseline
    python tools/protection_gap.py keywords+normalize  # the same, after script-aware cleaning
    python tools/protection_gap.py hf:<model-id>       # a Hugging Face text classifier

Labels are the sources' own and unverified (see docs/M1_plan.md): these are first estimates, to be
replaced by native-speaker-checked labels. A message is flagged when its score is at least 0.5.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babelguard.dataset import load_bengali_smishing, load_imc25, load_moz_smishing, load_singlish  # noqa: E402
from babelguard.detectors import HFClassifier, KeywordBaseline  # noqa: E402
from babelguard.protection import by_group, rates  # noqa: E402

ROOT = "data/private"


def detector(spec):
    if spec == "keywords":
        return KeywordBaseline()
    if spec == "keywords+normalize":
        return KeywordBaseline(normalize_first=True)
    if spec.startswith("hf:"):
        return HFClassifier(spec[3:])
    raise SystemExit(f"unknown detector {spec}")


def main(spec="keywords", out="out"):
    recs = (load_imc25(f"{ROOT}/imc25.csv") + load_bengali_smishing(f"{ROOT}/bengali")
            + load_moz_smishing(f"{ROOT}/moz/test.csv") + load_singlish(f"{ROOT}/singlish/Translations.xlsx"))
    recs = [r for r in recs if r.label in ("scam", "legit") and r.lang != "und"]
    det = detector(spec)
    t0 = time.time()
    flags = [s >= 0.5 for s in det([r.text for r in recs])]
    overall = rates([r.label for r in recs], flags).as_dict()
    table = by_group(recs, flags, key=lambda r: r.lang if r.variety == "native" else f"{r.lang}-{r.variety}")
    report = {"detector": det.name, "normalize_first": det.normalize_first, "messages": len(recs),
              "overall": overall, "seconds": round(time.time() - t0, 1), "languages": table}
    os.makedirs(out, exist_ok=True)
    name = spec.replace(":", "_").replace("/", "_").replace("+", "_")
    json.dump(report, open(os.path.join(out, f"protection_{name}.json"), "w"), indent=1)
    return report


if __name__ == "__main__":
    rep = main(*sys.argv[1:2])
    print(rep["detector"], "overall", rep["overall"])
    print(f"{'language':16s} {'scams':>6s} {'detect':>7s} {'95% CI':>15s} {'genuine':>8s} {'false-al':>8s} {'gap vs en':>9s}")
    for g, v in rep["languages"].items():
        if not v["scams"] and not v["genuine"]:
            continue
        ci = f"[{v['detection_ci'][0]},{v['detection_ci'][1]}]" if v["scams"] else ""
        flag = "" if v["enough_data"] else "  (too few)"
        print(f"{g:16s} {v['scams']:6d} {str(v['detection']):>7s} {ci:>15s} {v['genuine']:8d} "
              f"{str(v['false_alarm']):>8s} {str(v['gap_vs_english']):>9s}{flag}")
