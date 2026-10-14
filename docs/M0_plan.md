# Babelguard — M0 plan (14 Oct 2026)

**One line:** an open early-warning system for scams. It spots a scam campaign in one language or
country, recognises the same operation when it reappears translated elsewhere, and warns people in
their own language before it reaches them.

## 1. What exists, and what is missing (checked 14 Oct 2026)

| Exists | Missing |
|---|---|
| **Global Signal Exchange** (Google, GASA, Oxford Information Labs): 70M+ scam signals. It is closed to accredited members and shares URLs, domains and phone numbers. | An **open** system that works on the **content** of scam messages and links campaigns **across languages**. |
| Studies showing that campaigns cross languages: 53 of 280 SMS spam campaigns used more than one language (arXiv 2204.01233); 310 coordinated investment-scam campaigns in 15+ languages shared one playbook (Bitdefender). | Ongoing, public tracking of that spread. Today it is done case by case, by hand. |
| Campaign clustering research for English: SmishViz (message clusters plus shared infrastructure); PhishCluster (URL embeddings). | Clustering that **crosses languages and scripts**. |
| Multilingual scam classifiers: Horizon-Labs mmBERT (synthetic data, about 70 languages); small student projects in 2–6 Indian languages; a synthetic 14-language Indian set. | A **human-checked** benchmark of real messages in underserved languages, and measured protection **per language**. |
| Evidence that detectors degrade outside English: one LLM's false-positive rate rose from 2.4% to 24.1% on Bangla, Chinese and Hindi email (arXiv 2512.10104). IndicSafe (12 Indic languages) covers caste, religion, gender, health and politics, but **not fraud**. | The same measurement for scams. |
| Unicode evasion studies (zero-width characters, look-alikes, bidi controls). Their standard advice is to strip invisible characters and fold look-alikes. | **Script-aware** defence. ZWJ and ZWNJ are part of correct spelling in Indic scripts, Persian and Urdu, and ZWSP marks word breaks in Thai, Lao, Khmer and Burmese, so stripping them corrupts real text. No source addresses this. |
| India's Chakshu / Sanchar Saathi and the Financial Fraud Risk Indicator (closed, government and bank use). | An open component that such systems, NGOs and researchers can all use. |

**The claim we can defend:** *"the first open system that tracks scam campaigns across languages
and gives early warning"*. We never say "the first scam-intelligence system".

## 2. Architecture

```
 sensors ──► normalize ──► indicators ──► link ──► spread ──► warn
 (forwards,   (script-aware   (links, UPI,   (shared     (where/when  (per-language alerts,
  advisories,  cleaning,       phones,        indicators, it moved)    STIX feed, phone
  public       look-alikes,    wallets;       near copies,             shield)
  posts)       native digits)  checksums)     meaning)
```

| Module | M0 status |
|---|---|
| `normalize.py`: script-aware cleaning. Keeps legitimate ZWJ, ZWNJ and ZWSP; removes and counts disguises; folds UTS #39 look-alikes in mixed-script words; turns native digits into ASCII | **done, tested** |
| `indicators.py`: links (refanged; short links keep their path), phones (Indian and international; native digits), UPI IDs, emails, BTC (base58check, bech32/bech32m), ETH, TRON (base58check). Card numbers (Luhn) and Aadhaar numbers (Verhoeff) are never treated as phones. `redact()` masks victims' OTPs, cards, Aadhaar and PAN numbers | **done, tested** |
| `campaigns.py`: links messages by shared indicators (ignoring well-known legitimate domains and over-common indicators) and by near-copy text; a slot for a multilingual encoder | **done, tested** (encoder comes in M2) |
| Benchmark, per-language protection-gap study, spread tracking, warnings, phone app | M1–M5 |

## 3. Privacy and data rights: the rules

1. **Consent:** volunteers forward messages knowingly. Nothing is collected passively.
2. **Redact on the device:** `redact()` runs before anything leaves the phone. Shared records hold
   only the scammer's indicators and a redacted template.
3. **No personal names or victim numbers** in any published dataset. Every release gets a manual
   check.
4. **Public sources:** advisories from CERT-In, I4C, RBI and banks are used for facts and indicators.
   Their text is quoted only as far as Indian copyright law allows for government works (to be
   verified before any reuse).
5. **Disclosure:** detector weaknesses are reported privately to each vendor before per-vendor
   numbers are published.
6. **Defensive only:** we publish measurements and fixes, never an evasion kit or attack tooling.

## 4. Milestones

| | What | Output | Time |
|---|---|---|---|
| M0 | Novelty check, architecture, privacy rules; normalize, indicators and campaign-linking core | This plan; tested core | **done** |
| M1 | Benchmark v0: 5 languages (Hindi, Odia, Bengali, Tamil, Hinglish) + English, ~2,000 checked messages and hard negatives | Dataset card; labelling guide | 3 weeks |
| M2 | Multilingual encoder for cross-language linking; spread tracking; the per-language protection-gap study (LLMs, guard models, open classifiers) | Linking accuracy; per-language gap table | 3–4 weeks |
| M3 | Robustness study (disguises against current detectors) plus the script-aware defence, measured | Paper section; vendor disclosure | 3 weeks |
| M4 | Warnings: per-language alerts, STIX 2.1 feed; offline phone checker | Public feed; app | 4 weeks |
| M5 | Expand to Southeast Asia (Thai, Khmer, Burmese, Tagalog), Africa (Swahili, Hausa, Amharic), Arabic and Urdu; paper; dataset DOI; outreach to CERTs and GASA | Paper; partners | months 4–6 |

## Sources

- Global Signal Exchange: https://www.globalsignalexchange.org/docs/an-introduction-to-the-global-signal-exchange
- GASA update: https://www.gasa.org/post/update-on-the-global-signal-exchange-global-anti-scam-summit-london-2025
- Twitter-guided SMS spam: https://arxiv.org/pdf/2204.01233
- Bitdefender investment-scam network: https://www.bitdefender.com/en-us/blog/labs/global-investment-scam-network-using-meta-ads
- SMS phishing review (2026): https://arxiv.org/pdf/2604.11429
- Phishing detection with LLMs (cross-lingual false positives): https://arxiv.org/pdf/2512.10104
- IndicSafe: https://arxiv.org/html/2603.17915
- Guardrail evasion with Unicode: https://arxiv.org/html/2504.11168v1
- PhishCluster: https://doi.org/10.3390/info17010064
- Horizon-Labs multilingual detector: https://huggingface.co/Horizon-Labs/phishing-scam-detector-base
- Chakshu explainer: https://factly.in/explainer-government-launches-chakshu-to-report-sms-call-or-whatsapp-messages-attempting-to-commit-fraud/amp
- Unicode UTS #39: https://www.unicode.org/reports/tr39/
