"""Build babelguard/data/confusables_ascii.json from Unicode's confusables.txt (UTS #39).

Keeps the entries that map one non-ASCII code point to a short ASCII letter/digit prototype
(Cyrillic а -> a, Greek ο -> o, Devanagari digit-like signs -> digits, ...): the look-alikes used
to disguise Latin brand names, links and handles. Run:

    curl -o confusables.txt https://www.unicode.org/Public/security/latest/confusables.txt
    python tools/build_confusables.py confusables.txt
"""
import json
import sys

src = sys.argv[1]
out, version = {}, None
for line in open(src, encoding="utf-8-sig"):
    if line.startswith("# Version:"):
        version = line.split(":", 1)[1].strip()
    line = line.split("#", 1)[0].strip()
    if not line:
        continue
    a, b = [f.strip() for f in line.split(";")[:2]]
    if " " in a:
        continue
    cp = int(a, 16)
    target = "".join(chr(int(x, 16)) for x in b.split())
    if cp < 0x80 or not (1 <= len(target) <= 2) or not all(c.isascii() and c.isalnum() for c in target):
        continue
    out[chr(cp)] = target
json.dump({"source": "Unicode UTS #39 confusables.txt", "version": version,
           "license": "Unicode License v3 (https://www.unicode.org/license.txt)", "map": out},
          open("babelguard/data/confusables_ascii.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=0, sort_keys=True)
print(len(out), "entries, UTS #39 version", version)
