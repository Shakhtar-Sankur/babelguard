"""Build the native-speaker review sample from every source (private: data/private/review/).

    python -m babelguard.sources fetch
    python tools/make_review_sample.py

Writes one JSONL file per language for annotators (text only; imported labels are kept in a
separate key file so annotators are not anchored by them) and prints the coverage table.
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babelguard.dataset import (group_templates, load_bengali_smishing, load_imc25,  # noqa: E402
                                load_moz_smishing, load_singlish, review_sample)

ROOT = "data/private"


def main(per_label=100):
    recs = (load_imc25(f"{ROOT}/imc25.csv") + load_bengali_smishing(f"{ROOT}/bengali")
            + load_moz_smishing(f"{ROOT}/moz/test.csv") + load_singlish(f"{ROOT}/singlish/Translations.xlsx"))
    group_templates(recs)
    sample = review_sample(recs, per_label)
    out = f"{ROOT}/review"
    os.makedirs(out, exist_ok=True)
    by_lang = defaultdict(list)
    for r in sample:
        by_lang[r.lang].append(r)
    with open(f"{out}/imported_labels.jsonl", "w", encoding="utf-8") as key:
        for lang, rs in sorted(by_lang.items()):
            with open(f"{out}/review_{lang}.jsonl", "w", encoding="utf-8") as f:
                for r in rs:
                    f.write(json.dumps({"id": r.id, "lang": r.lang, "variety": r.variety, "text": r.text,
                                        "source": r.source}, ensure_ascii=False) + "\n")
                    key.write(json.dumps({"id": r.id, "label": r.label, "scam_type": r.scam_type,
                                          "group": r.group}, ensure_ascii=False) + "\n")
    table = defaultdict(Counter)
    for r in sample:
        table[(r.lang, r.region)][r.label] += 1
    print(f"{len(sample)} records, {len(by_lang)} languages")
    for (lang, region), c in sorted(table.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"{lang:4s} {region:20s} scam {c['scam']:4d}  spam {c['spam']:4d}  legit {c['legit']:4d}")


if __name__ == "__main__":
    main(*(int(a) for a in sys.argv[1:2]))
