"""Coverage and disguise report for an imported dataset (private: writes to out/).

    curl -o data/private/imc25.csv <IMC25_URL from babelguard/dataset.py>
    python tools/coverage.py data/private/imc25.csv

Per language and region: messages, share of the dataset, how often scammers disguise text
(invisible characters, look-alike letters), template groups, and templates seen in more than one
language (matched through the dataset's English translations).
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babelguard.dataset import IMC25_SHA256, group_templates, load_imc25, sha256  # noqa: E402
from babelguard.normalize import normalize  # noqa: E402

INVISIBLE = {"zwsp", "zwj", "zwnj", "bidi_override", "bidi_control", "tag_char", "word_joiner",
             "soft_hyphen", "hangul_filler", "grapheme_joiner", "invisible_operator", "bom",
             "mongolian_vowel_sep"}


def main(path, out="out"):
    digest = sha256(path)
    if digest != IMC25_SHA256:
        print(f"warning: sha256 {digest} differs from the pinned {IMC25_SHA256}")
    t0 = time.time()
    recs = load_imc25(path)
    n_groups = group_templates(recs)
    by_lang = defaultdict(list)
    for r in recs:
        by_lang[r.lang].append(r)
    langs = {}
    for lang, rs in sorted(by_lang.items(), key=lambda kv: -len(kv[1])):
        an = [normalize(r.text).anomalies for r in rs]
        langs[lang] = {
            "region": rs[0].region, "messages": len(rs), "share": round(len(rs) / len(recs), 5),
            "scam": sum(r.label == "scam" for r in rs),
            "invisible_chars": round(sum(any(k in INVISIBLE for k in a) for a in an) / len(rs), 4),
            "lookalike_letters": round(sum(a["confusable_folded"] > 0 for a in an) / len(rs), 4),
            "template_groups": len({r.group for r in rs}),
        }
    regions = Counter()
    for r in recs:
        regions[r.region] += 1
    group_langs = defaultdict(set)
    for r in recs:
        group_langs[r.group].add(r.lang)
    cross = {g: sorted(ls) for g, ls in group_langs.items() if len(ls - {"und"}) > 1}
    report = {
        "source": "imc25", "sha256": digest, "messages": len(recs), "template_groups": n_groups,
        "cross_language_groups": len(cross),
        "cross_language_examples": sorted(cross.values(), key=len, reverse=True)[:15],
        "regions": dict(regions.most_common()), "languages": langs,
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs(out, exist_ok=True)
    json.dump(report, open(os.path.join(out, "coverage_imc25.json"), "w"), indent=1, ensure_ascii=False)
    return report


if __name__ == "__main__":
    rep = main(sys.argv[1], *(sys.argv[2:3]))
    print(json.dumps({k: v for k, v in rep.items() if k != "languages"}, indent=1, ensure_ascii=False))
    for lang, v in list(rep["languages"].items())[:25]:
        print(lang, v)
