# Babelguard M1: a global scam benchmark (started 14 Oct 2026)

**Goal:** Babelguard-Bench v0. Real scam messages and look-alike legitimate ones, with every label
checked by a native speaker. It covers every world region, and its splits keep each scam template
on one side only.

## 1. What the largest open dataset already shows

The seed is the IMC 2025 smishing dataset (Agarwal, Papasavva, Suarez-Tangil, Vasek; ACM IMC 2025;
CC BY 4.0). It holds 33,869 SMS that users reported as scams, in 49 identified languages. We
re-redacted it and grouped near-copies, including copies matched through its English translations
(`tools/coverage.py`). Only aggregate figures are shown below, and no message is reproduced.

**Where the reports come from: almost all from Europe, the Americas and English.**

| Region (by message language) | Messages | Share |
|---|---|---|
| English (all countries) | 22,078 | 65.2% |
| Europe and the Americas (other European languages) | 10,137 | 29.9% |
| Southeast Asia | 644 | 1.9% |
| East Asia | 332 | 1.0% |
| **South Asia** (about 1 in 4 people on Earth) | **282** | **0.8%** |
| Middle East | 169 | 0.5% |
| **Africa** (nearly 1 in 5 people on Earth) | **48** | **0.1%** |

French is counted with Europe. Russian (10) and unidentified languages (169) are left out of the table.

Hindi has 175 messages, Bengali 6, Kannada 10, and Tamil, Telugu, Odia and Marathi none. Swahili
has 30, and Hausa, Yoruba and Amharic none. These languages are where the open data runs out, and
a detector trained or tested on open data has not seen them.

**The same lures travel between languages.** Messages fall into 15,340 template groups, and 96 of
them appear in two or more languages. One parcel-tracking lure appears in six (French, Dutch,
Spanish, Italian, German, Norwegian). One "account deactivated for security reasons" lure appears
in Spanish, English and Greek written in Latin letters. A shared template is evidence of a shared
**lure**, not proof of a shared **operator**. Linking operators needs indicators (links, numbers,
wallets), which this dataset has anonymised.

**Disguises are rare in today's reported SMS.** Invisible characters appear in under 0.4% of
messages in every language with more than 50 messages, and look-alike letters in about 1–2% of
Turkish and Chinese ones. The robustness study (M3) is therefore about **resilience**: what would
happen to detectors if scammers adopted these tricks, which are common in other channels. It is
not a claim that they are widespread in SMS today.

**The labels need checking.** A spot check found a genuine vaccination reminder among the reported
scams, and a real person's name that the anonymisation missed. Imported labels therefore start as
`verified=False`, and no raw message is redistributed.

## 2. Sources

| Source | Languages | Size | Licence | Use |
|---|---|---|---|---|
| IMC 2025 smishing (UCL, IMDEA) | 49 | 33,869 | CC BY 4.0 | Seed and coverage baseline; sample for verification |
| Bengali SMS smishing (SmishDetect-LLM) | Bengali, Banglish, code-mixed | 7,005 | MIT | South Asia |
| MOZ-Smishing (AfricaNLP 2025) | Mozambican Portuguese (mobile money) | — | open (to confirm) | Africa |
| Translated Singlish SMS (Data, 2026) | Singlish | 2,788 | CC BY | Southeast Asia |
| AZ-SC | Azerbaijani | 4,538 | to confirm | Caucasus and Central Asia |
| **New collection** | the gaps above | — | ours, consented | Partners and volunteers: South Asia, Africa, Southeast Asia, Arabic |

## 3. Benchmark v0 design

- **Languages:** 24 across all regions. At least 4 each from South Asia, Southeast Asia and
  Africa; the rest from Europe, the Americas, the Middle East and East Asia.
- **Per language:** about 100 checked scams and 100 hard negatives (real OTPs, bank alerts,
  delivery notices, government messages), so roughly 4,800 records.
- **Sampling:** one message per template group first, then more from large groups, so no single
  campaign dominates.
- **Checking:** two native speakers per language, following `docs/labelling_guide.md`. Agreement
  is measured with Cohen's kappa, and disagreements are settled by a third speaker.
- **Splits:** by template group (`dataset.split`). No template appears in two splits.
- **Release:** a dataset card, the licence of each source, and a DOI. Only records that pass the
  privacy check are released.

## 4. Partners to approach (global)

| Who | Why |
|---|---|
| The IMC 2025 authors at UCL and IMDEA | Their dataset is our seed. Tell them about the PII the anonymisation missed. A natural UK collaboration. |
| GASA / Global Signal Exchange | Open complement to their closed signals |
| Masakhane (African NLP community) | Native speakers for African languages |
| AI4Bharat, IndicNLP community | Native speakers for Indian languages |
| SEA-LION / AI Singapore and Southeast Asian NLP groups | Southeast Asian languages |
| National CERTs (CERT-In, ThaiCERT, KE-CIRT, …) | Real advisories; later, the alert feed |

## 5. Next steps

1. Loaders for the Bengali (MIT) and Singlish (CC BY) sets; confirm the MOZ-Smishing and AZ-SC
   licences.
2. Draw the stratified sample for checking (24 languages).
3. Labelling tool: a small local web page that shows one message and records the label, type,
   lures and a privacy flag.
4. The professor and the university: ethics approval for new collection, and help recruiting
   annotators.
