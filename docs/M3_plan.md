# Babelguard M3: at scale

M0 to M2 proved the method on about 45,000 messages in batch. M3 turns Babelguard into one
end-to-end system that runs continuously, at volume, and measures itself.

## Architecture

```
 sources ──► ingest ──► clean + indicators ──► campaign engine ──► store ──► feeds
 (forwards,   (stream,    (script-aware,         (indicator index,   (append-   (STIX/TAXII for CERTs,
  partners,    back-       checksummed            streaming LSH,      only log,  per-language alerts,
  feeds)       pressure)   indicators)            ANN on meaning,     snapshots) offline phone checker)
                                                  union-find)
                                   ▲
                       GPU embedding service (batched)
```

| Milestone | What | How it is proven |
|---|---|---|
| **M3.1** | **Streaming campaign engine**: each message is linked on arrival by shared indicators, near-copy text (incremental MinHash LSH) and, optionally, meaning (nearest-neighbour index); campaigns keep first and last seen times, languages, size and indicators | Throughput and per-message latency (p50/p99) on a stream of millions of messages; linking precision and recall (B-cubed) against known campaigns |
| **M3.2** | **Load generator with ground truth**: synthetic campaigns built from real reported templates, each with its own links, numbers and UPI IDs, small edits, and a translated variant taken from the dataset's real translations | Every synthetic message carries its true campaign, so accuracy is measurable at any scale. Synthetic load is labelled as synthetic in every result |
| **M3.3** | **GPU embedding service**: batched multilingual encoder on a T4, fed by the engine | Messages per second against batch size; equal to CPU output |
| **M3.4** | **Nearest-neighbour index at 10M–100M messages**: IVF-PQ and HNSW | Recall@10 against exact search; memory per message; query latency |
| **M3.5** | **Durable store and recovery**: append-only log with snapshots; the engine restarts from a crash with identical campaigns | Fault injection (kill at random points), every restart checked against an uninterrupted run |
| **M3.6** | **Feeds**: STIX 2.1 bundles for national cyber teams, per-language alerts | Validation against the STIX schema; end-to-end latency from first message to alert |

## Honesty rules for scale numbers

- Open data holds about 45,000 real messages. Volumes beyond that are synthetic load built from
  real templates, and are always reported as such.
- Every throughput number states the hardware (CPU model and cores, or the T4) and the message mix.
- Accuracy at scale is measured against the generator's known campaigns, and also on the real
  messages, where the IMC translations give an independent answer key.

## Results

### M3.1 streaming engine, 100,000 messages (14 Oct 2026)

Synthetic load from real IMC 2025 templates: 1,872 campaigns with heavy-tailed sizes, 20% of
messages in a second language (the template's real translation), 5% disguised. One CPU core,
plain Python, linking by indicators and near-copy text (no embeddings in this run).

| | |
|---|---|
| Throughput | **788 messages/s** on one core (about 68 million a day, if sustained) |
| Latency per message | p50 **1.1 ms**, p99 **3.3 ms**, max 598 ms (a one-off pause, under investigation) |
| B-cubed precision / recall / F1 | **0.9995 / 0.9919 / 0.9957** |
| Campaigns found / true | 2,214 / 1,872 (some campaigns split; none of note merged) |

This load is easier than the real world, since each synthetic campaign has its own template and
its own scammer details. Real-world cross-language accuracy is measured separately in M2 (85% at
rank 1).

### M3.1 at 1,000,000 messages (14 Oct 2026)

Same generator and settings, ten times the stream: 13,116 true campaigns. One core of an Intel
Xeon at 2.80 GHz, plain Python.

| | 100,000 | 1,000,000 |
|---|---|---|
| Throughput | 788 messages/s | **803 messages/s** (about 69 million a day per core) |
| Latency p50 / p99 | 1.1 / 3.3 ms | **1.1 / 3.3 ms** |
| p99 in each tenth of the stream | | 2.9 to 3.6 ms: no slowdown as the indexes grow |
| B-cubed precision / recall / F1 | 0.9995 / 0.9919 / 0.9957 | **0.9974 / 0.9930 / 0.9952** |
| Campaigns found / true | 2,214 / 1,872 | 15,258 / 13,116 |
| Peak memory | | 5.2 GB (about 5 KB per message) |
| Longest single pause | 598 ms | 4.3 s |

Per-message cost stays flat from 100,000 to 1,000,000 messages, because the LSH buckets keep a
bounded number of representatives and indicator lists are capped. Two things must be fixed
before 100M: memory (Python objects per message; the next step is compact arrays for union-find
and signatures, and dropping shingle sets of non-representatives, which already happens) and the
rare multi-second pauses, which grow with the heap and are most likely Python's cyclic garbage
collector walking millions of objects.

### Memory and pauses fixed (14 Oct 2026)

Two changes, after measuring where memory and time went:

- Representatives kept their 5-character shingles as Python sets of strings; they now keep the
  sorted 64-bit hashes MinHash already computes (8 bytes each), which are deterministic across
  processes, so recovery from the log is unaffected.
- Every 20,000 messages the engine moves its long-lived objects out of Python's garbage collector
  (`gc.freeze()`); full collections had been rescanning millions of objects.

Same 1,000,000-message stream, same machine:

| | before | after |
|---|---|---|
| Engine memory | (not measured separately) | **203 MB, 0.21 KB per message** |
| Process peak, including the benchmark's own copy of the stream | 5.2 GB | **1.05 GB** |
| Longest single pause | 4.3 s | **96 ms** |
| p50 / p99 latency | 1.1 / 3.3 ms | 1.1 / 3.3 ms |
| Throughput | 803 messages/s | 786 messages/s |
| B-cubed precision / recall, campaigns found | 0.9974 / 0.9930, 15,258 | **identical** |

At 100,000 messages engine memory fell from 3.7 KB to 0.35 KB per message (365 MB to 34 MB).
At this rate 100 million messages need about 20 GB, within one server.

### Toward 100 million messages: parallel ingest (15 Oct 2026)

At 100M messages the limit is time, not memory: 0.21 KB per message is about 20 GB, which fits
one server, but 100M messages at 786 per second on one core take 35 hours. Profiling 20,000
messages showed where the time goes: 92% is per-message feature work (cleaning, scammer details,
shingle hashes, MinHash band keys) that depends on nothing but the message; 8% is linking it into
the campaigns, which must happen in arrival order. Two changes follow.

- **Less work per message.** Each message was cleaned three times (once for linking, twice inside
  indicator extraction), and the character-to-script lookup ran 7 million times uncached. Cleaning
  once and caching the lookup: 788 to **1,159 messages/s** on one core, with identical results.
- **Features on many cores.** `CampaignEngine.features` is now a pure function and `apply` the
  ordered step; `babelguard/parallel.py` computes features in worker processes and applies them in
  order in one process, so the campaigns are identical to the serial engine's
  (`tests/test_parallel.py` checks every message's campaign, size, languages and details).

100,000 synthetic messages (same stream and seed as above), 4-core Intel Xeon at 2.8 GHz:

| | messages/s | B-cubed precision / recall | campaigns found |
|---|---|---|---|
| one core, before | 788 | 0.9995 / 0.9919 | 2,214 |
| one core, after | 1,159 | 0.9995 / 0.9919 | 2,214 |
| 1 feature worker + apply | 1,464 | identical | identical |
| 2 feature workers + apply | 2,854 | identical | identical |
| 3 feature workers + apply | **4,057** | identical | identical |

At 4,057 messages/s one 4-core machine ingests 100M messages in about 7 hours. The apply step is
about a tenth of the work, so one apply process keeps up with roughly ten feature workers; beyond
that, the apply step is split by key (indicator keys and LSH bands hashed to shards, a shared
union-find over message ids), which is the next step, together with running the durable log in
front of the parallel path.

### M3.5 durable store and recovery (14 Oct 2026)

`babelguard/store.py`: every message goes to an append-only log (one CRC32-checked record per
line) before the engine sees it; snapshots are written to a temporary file, fsynced and renamed,
so a crash leaves the old snapshot or the new one, never half of one. A torn or corrupt log tail
is cut off on recovery, and a long replay is followed by a fresh snapshot, so recovery time stays
bounded however often the process dies.

`tools/crash_test.py` fed 20,000 synthetic messages to the engine in a child process and killed
it with SIGKILL 50 times at random moments; after each kill a new process recovered and the
client resent from the last durable message.

| | |
|---|---|
| Kills / restarts | 50 / 51 |
| Messages lost | **0** |
| Campaigns identical to an uninterrupted run | **yes** (all 20,000 messages, 2,374 campaigns) |
| Most log records replayed in one recovery | 2,000 (the snapshot interval; 12,000 before the post-recovery snapshot) |

Rerun after the memory changes below (shingles as hash arrays, frozen garbage collection): again
50 kills, nothing lost, identical campaigns.
