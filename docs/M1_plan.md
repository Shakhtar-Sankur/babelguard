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
| MOZ-Smishing (AfricaNLP 2025) | Mozambican Portuguese (mobile money) | 2,561 | creativeml-openrail-m (use-restricted) | Africa; evaluated locally, never redistributed (raw text has names) |
| Translated Singlish SMS (Data, 2026) | Singlish | 2,788 | CC BY 4.0 | Southeast Asia; genuine messages (hard negatives) |
| AZ-SC | Azerbaijani | 4,538 | no public download found | Ask the author |
| **New collection** | the gaps above | — | ours, consented | Partners and volunteers: South Asia, Africa, Southeast Asia, Arabic |

### Two more gaps found while building the sample (14 Oct)

- **Genuine messages exist for only 4 of 49 languages** (Bengali, Mozambican Portuguese,
  Singlish and English). In the other 45 there is no open set of real messages, so nobody can
  measure **false alarms**, where detectors are known to break outside English. Collecting genuine
  messages (real OTPs, bank alerts, delivery and government notices) is therefore as important as
  collecting scams, and less sensitive.
- **Random splits leak templates.** In the Bengali SMS smishing dataset's own random split, 15.8%
  of test messages (22.5% of test scams) have a near-copy in its training data, so scores on that
  split are optimistic. Random splitting is common practice. Babelguard splits by template group.

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

## 5. Status and next steps

Done:
- Loaders for all four sources, each with a pinned checksum (`babelguard/sources.py`;
  `python -m babelguard.sources fetch`).
- A stratified review sample (`tools/make_review_sample.py`): 3,754 records in 49 languages.
  One record per template comes first, and imported labels are kept apart from the annotators.
- A labelling page (`tools/label.html`): offline, keyboard-driven, works on phones, handles
  right-to-left text, and saves progress in the browser. It was checked in Chromium with
  synthetic data.
- An agreement script (`tools/agreement.py`): Cohen's kappa, a confusion table, and the ids that
  go to a third annotator.

Next:
1. Recruit two native speakers per language. Start with the languages that have the most
   messages, then fill the gaps.
2. Collect genuine messages in the 45 languages that have none.
3. University ethics approval for new collection, with the professor.
4. Phone-number plans for more countries as data arrives.
