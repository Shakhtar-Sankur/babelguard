# Babelguard M2: linking scams across languages, and the protection gap

M2 has two parts.

1. **Linking by meaning.** Recognise the same scam when it reappears translated, including
   across scripts, where character matching cannot help at all.
2. **The protection gap.** For each language, measure how well today's detectors catch scams
   and how often they raise false alarms.

## Part 1: linking by meaning

- **`babelguard/embed.py`:** a multilingual sentence encoder (default
  `intfloat/multilingual-e5-small`, about 100 languages, runs on a CPU), with chunked nearest-neighbour
  search.
- **`campaigns.link(..., embed=Encoder())`:** links messages whose meaning is close. Each message is
  compared only with its nearest neighbours, so it scales to large collections.

**How it is measured (`tools/eval_linking.py`).** The IMC 2025 dataset gives an English translation
for each non-English report. That provides an answer key that does not depend on us:

- Each non-English message, in its original language and script, is used as a query against the
  pool of all those English translations.
- A query counts as found when a top-ranked translation belongs to its own template group (its own
  translation or a near-copy of it).
- Reported per language:
  - recall@1 and recall@10;
  - how often plain text matching (what linking can do without an encoder) connects the message to
    its own translation at all;
  - the share of true pairs linked at a similarity threshold calibrated so that only 1% of pairs
    from different templates would be linked.

Results go in section 3 once the run finishes.

## Part 2: the protection gap (next)

- **Detectors:**
  - open multilingual classifiers (for example, an mmBERT-based scam detector);
  - guard models (Llama Guard, Qwen3Guard);
  - general LLMs (GPT, Claude, Gemini), each behind one interface.
- **Data:** for each language, the detection rate on checked scams, and the false-alarm rate on
  genuine messages, where any exist (today: Bengali, Mozambican Portuguese, Singlish, English).
  Results are reported with bootstrap confidence intervals, and languages with too few messages
  are marked rather than ranked.
- **Disguises:** the same messages again, with hidden characters, look-alike letters and
  transliteration added, before and after Babelguard's script-aware cleaning.
- **Compute:**
  - classifiers run on Kaggle's free T4s;
  - LLM runs need API keys and are sized to a fixed budget;
  - detector weaknesses go to their vendors before per-vendor numbers are published.
