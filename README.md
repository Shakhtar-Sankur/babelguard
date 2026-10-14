# Babelguard

**Every language deserves the same protection from scams.**

Babelguard is an open early-warning system for scams. When a scam campaign appears in one language
or country, it recognises the same operation as it reappears, translated, somewhere else. It then
warns people in their own language before the scam reaches them.

Scam operations reuse one playbook across many languages. Most detectors are built and tested in
English, so the people writing in other languages get the least protection. Babelguard is built
for them first.

## Status

**M1 in progress: a global benchmark.** See [docs/M1_plan.md](docs/M1_plan.md). The largest open
set of reported scam SMS (IMC 2025, 33,869 messages in 49 languages) is 65% English, and only 0.8%
is in South Asian languages and 0.1% in African ones. 96 scam templates appear in two or more
languages.

### M0 (core, tested)

| Module | What it does |
|---|---|
| `babelguard/normalize.py` | **Script-aware cleaning.** Removes the invisible characters and look-alike letters scammers use to slip past filters, and keeps the same characters where a language needs them: ZWJ and ZWNJ in Hindi, Bengali, Odia, Malayalam, Persian and Urdu; ZWSP in Thai and Khmer; emoji sequences. Every removal is counted, because a disguise attempt is itself evidence. Native digits (०-९, ୦-୯, ٠-٩, ๐-๙ …) become ASCII. |
| `babelguard/indicators.py` | **What the scam needs the victim to use:** links (refanged, look-alikes folded), phone numbers in any digits, UPI IDs, emails, and BTC, ETH and TRON wallets (checksums verified). Card and Aadhaar numbers are recognised by checksum and never mistaken for phones. `redact()` masks victims' OTPs, cards, Aadhaar and PAN numbers before anything is shared. |
| `babelguard/dataset.py`, `lsh.py`, `taxonomy.py` | **Benchmark layer.** A global scam taxonomy by pretext, with Stajano-Wilson lures. Loaders re-redact every record and keep its licence. Near-copies are grouped with MinHash LSH, including matches through translations. Splits are made by template, so no scam template sits in both training and test data. |
| `babelguard/campaigns.py` | **Campaign linking.** Messages in any language join one campaign when they share an indicator or are near copies. A slot for a multilingual encoder adds linking by meaning across translations. Well-known legitimate domains and over-common indicators never link. |

```python
from babelguard.campaigns import link

msgs = [
    "Your SBI KYC expires today. Update at hxxps://sbi-kyc-update[.]com or call 98765 43210",
    "आपका SBI KYC आज समाप्त। अपडेट करें: sbi-kyc-update.com या कॉल करें ९८७६५ ४३२१०",
    "ଆପଣଙ୍କ ପାର୍ସଲ ଅଟକି ଯାଇଛି। ଶୁଳ୍କ ପଠାନ୍ତୁ: refund.help@ybl",
    "Your parcel is held at customs. Pay the fee to refund.help@ybl",
]
for c in link(msgs):
    print(c.members, c.links)
# [0, 1] [(0, 1, 'phone:+919876543210')]     English + Hindi
# [2, 3] [(2, 3, 'upi:refund.help@ybl')]     Odia + English
```

```
pip install -r requirements.txt
python -m pytest -q
```

The plan, the novelty check and the privacy rules are in [docs/M0_plan.md](docs/M0_plan.md).

## Roadmap

1. **Benchmark:** real, human-checked scam messages and look-alike legitimate ones, starting with
   Hindi, Odia, Bengali, Tamil, Hinglish and English.
2. **Cross-language linking** with a multilingual encoder; spread tracking; a per-language
   protection-gap study of current detectors.
3. **Robustness:** how disguises affect today's detectors, and the script-aware defence, measured.
4. **Warnings:** per-language alerts, a STIX 2.1 feed for CERTs and banks, and an offline checker
   for the phone.
5. **Expansion** to Southeast Asia, Africa, Arabic and Urdu.

## Principles

- **Defensive only.** We publish measurements and fixes, never evasion kits.
- **Privacy first.** Messages are only ever forwarded with consent. Redaction happens on the phone,
  and shared records hold only the scammer's details.
- **Responsible disclosure.** Each vendor hears about its detector's weaknesses before any
  per-vendor numbers are published.

## License

Apache-2.0. `babelguard/data/confusables_ascii.json` is derived from Unicode's confusables.txt
(UTS #39), © Unicode, Inc., under the Unicode License v3.
