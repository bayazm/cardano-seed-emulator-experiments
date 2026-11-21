# B12 evidence for public review

[Trial CSV](benchmark-trials.csv) and [statistics](benchmark-summary.json) preserve the thirty recorded Phase 5C trials and their monotonic elapsed observations. The export omits wall-clock times, input and output references, wallet amounts and diagnostic text. Transaction IDs and block anchors are from the private experimental chain. The 30 verifications passed in the original run. [Checksum manifest](SHA256SUMS)

[Transaction anchors](transaction-anchors.csv) cover 33 transactions on B12-4242 and two on B12-P9. [P9 inclusion summary](p9-inclusion-summary.json) records the four saved observations for each containing block. [Audit summary](audit-summary.json) includes the genesis hashes, measurement digest and execution costs. These summaries are derived evidence. Independent byte-level replay of the historical run requires access to the original block records and sampled tips. [Artifact manifest](artifact-manifest.md)

See the [portable workflow](../../reproducibility/B12_portable_workflow.md) for the summary recalculation and exact-CBOR verifier. This directory contains no signed transactions, databases, raw packet captures, or signing keys.

[Sensor-hash verification](sensor-hash-verification.json) records the later B12-P9 funding and spend, four-node agreement, measured execution budget and local negative outcomes. It is a separate extract from the earlier 35-transaction audit. The containing-block digests identify private source records. See the [final sensor-hash report](../../reproducibility/B12_sensor_hash_final_report.md).
