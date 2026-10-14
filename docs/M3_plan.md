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
