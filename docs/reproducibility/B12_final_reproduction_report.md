# B12 final reproduction report

## 1. Objective and outcome

The experiment reproduced four-node Cardano consensus, native ADA transfers, CIP-20 and industrial sensor metadata, observed confirmation timing, and the original Aiken validator's live Plutus V3 spend. **Functional reproduction passed across two private networks.** B12-4242 supplied 33 verified transactions under Conway protocol 2.0. B12-P9 supplied two verified transactions, including one valid script spend, under Conway protocol 9.0. Phase 6A audited the preserved evidence without changing either chain. [Evidence index](B12_evidence_index.md) · [Exact 35-transaction inventory](../results/b12/transaction-anchors.csv)

## 2. Architecture and topology

SEED Emulator provided the routed topology. AS150–AS152 were producers and AS153 was a relay. Each Cardano peer used its own Unix node socket and static address `10.<ASN>.0.71` on `net0`. Each connected to the other three peers on TCP/3001. The normalized Compose plan had 39 services, 22 static networks, and a managed default network for EtherView. Four separate host bind directories held the chain databases. The optional EtherView service published host TCP/5000. [B12 architecture](../../experiments/B12-cardano/README.md) · [Original normalized Compose](../results/b12/artifact-manifest.md#e019)

## 3. Software environment

The run used x86-64 Linux, Python 3.8.10, Docker 20.10.21, standalone Compose 1.27.4, and SEED Emulator at `a8d93cd65aace99a454fae44895d41d7e8cd8197`. Cardano Node **11.1.3** and CLI **11.2.3.0** both reported revision `938cba990357ae7c4b7f95c8f75dd9d31174bbeb`. The validator used Aiken **1.1.24+bacbeb3**, stdlib **4.0.0**, and Plutus V3. The local audit environment used `cbor2 5.6.5` for byte-level evidence, `cryptography 2.8` for Ed25519 checks, PyYAML 6.0.1 for Compose parsing, and tcpdump for capture and packet readback. [Installation instructions](install.md) · [Environment evidence](B12_evidence_index.md#source-installation-and-build)

## 4. Genesis and ledger protocol

Both deployments used epoch-zero test transitions through Conway, without a later-era override. The Shelley genesis seeds the effective ledger protocol version. The tests used one-second slots, 86,400-slot epochs, three producers and run-specific funding keys. The B12-4242 preflight recorded 405,000 ADA allocated across six funding outputs. Audit recomputation matched the configured Cardano genesis hashes for every era and also recorded file SHA-256 separately.

| Deployment | Magic | Initial ledger protocol | Genesis start (UTC) | Shelley genesis hash |
|---|---:|---|---|---|
| B12-4242 | 4242 | 2.0 | 2026-11-19 18:09:33 | `f4967c61c610dfcd9a777a0c7b56b49ff20dbf062fe5ece715ce26dce9f64b2e` |
| B12-P9 | 4343 | 9.0 | 2026-11-19 23:27:33 | `813c8eb1c5e6370e19d2a36385c6f5d13940637948561091c2cb67b45cf66f9b` |

Byron and Shelley differ between the deployments, while the Alonzo and Conway files have identical bytes. Equal hashes for those shared era templates are consistent with different chain identities. The P9 generator supplied version 9.0 as a CLI input and validated the generated output before hashing or installing it. [Genesis hash audit](../results/b12/audit-summary.json) · [P9 generator](../../experiments/B12-P9/prepare.py)

## 5. Consensus and network evidence

On B12-4242, the post-genesis observations moved from origin to block 3 at slot 79 and block **7** at slot **148**. All four queried nodes agreed on the numbered block hashes, including `7bc4219b56a06d914deb4e0034b3ce322ce63eb8a9d2fb22b28b0589229c1e10` at height 7. The logs recorded successful NodeToNode V15 handshakes with magic 4242 and a full peer mesh. The relay adopted blocks forged by all three producers. At cutover, the final live sample was block **924**, slot **18774**, with a shared hash and all 33 earlier transactions anchored on every node. Phase 6A independently repeated that check against the stopped database files. [Phase 4B evidence](../results/b12/artifact-manifest.md#e027) · [Historical DB recheck](../results/b12/artifact-manifest.md#e002)

The audit checked 12 capture manifest entries, including two header-only files. Two additional header-only files lack a saved manifest. Ten files contained TCP/3001 packets. They cover B12-4242 post-genesis and benchmark intervals, and P9 ambient, funding and spend intervals. Duplicate copies of captures count only once. Packet evidence shows peer traffic. Block and ledger evidence establish transaction inclusion. [Capture inventory](B12_evidence_index.md#capture-inventory)

## 6. B12-4242 transaction experiments

| Phase | Result | Block / slot | Transaction IDs |
|---|---|---|---|
| 5A | One basic 2 ADA transfer. All four nodes observed the exact recipient and change outputs. AS150 first observed inclusion after 18.31 s. | 75 / 1341 | `872f46ccf1a0272f94c8a719d90c838703bd3bcb4b46a73c26fcee22ca72447a` |
| 5B | Two 2 ADA transfers. CIP-20 label 674 and sensor label 1000 matched the submitted JSON and were independently decoded from the stored block. | 135 / 2566 | `b42897ef78ef64ad526c56d6606e9cb443afb153af243a9729287851f992e943` and `39a87d29e5ca469b1c335add42fb9ec0f9373a4a39b776e09f7519a55cd2328c` |
| 5C | 30 verified 2 ADA transfers, ten per workload. Each used a distinct input and ID. | 173–207 | [Per-trial IDs and block hashes](../results/b12/benchmark-trials.csv) |

The 33 transactions were found by hashing exact transaction-body bytes and matching complete block-header hashes. The 5B pair shares a single block. AS150 first observed those CIP-20 and sensor outputs at 9.68 and 10.39 seconds from submission start, respectively. Their shared block limits interpretation of those observed differences. [Phase 5A report](../results/b12/artifact-manifest.md#e031) · [Phase 5B report](../results/b12/artifact-manifest.md#e035) · [Audit ledger](../results/b12/transaction-anchors.csv)

## 7. Sensor metadata integrity

The shipped lab fixture's file SHA-256 matches its checked-in label-1000 metadata. The reproduction preserved that label's `sensor_id` and `data_hash` fields and used a **synthetic** AGRI-002 temperature of 21.9 °C. Its exact measurement file hashes to `48c8058f3678a57c6c5c4faf94deb540938f707d4bdd9a789600822a36149216`. That digest matched the label-1000 data recovered from Phase 5B block 135 and all ten Phase 5C sensor transactions. An altered measurement copy yielded a different digest. The original provenance and timestamp of an AGRI-002 reading were unavailable. This experiment verifies a byte-level integrity reference for the synthetic file. [Synthetic fixture and integrity evidence](../results/b12/artifact-manifest.md#e038) · [Original lab examples](../../experiments/B12-cardano/examples/)

## 8. Confirmation benchmarking

Recomputed statistics match the raw CSV and full-precision JSON for every reported metric. All 30 scheduled trials passed the exact UTXO checks and four-node block checks. The 30 benchmark rows have distinct inputs and transaction IDs. The first input was an existing change output and subsequent trials spent the preceding confirmed change. Fees and signed byte counts were verified against the transaction bodies and signed envelopes.

| Workload | Verified / failed | Mean (s) | Median (s) | Min–max (s) | Sample SD (s) | Nearest-rank p95 (s) | Mean fee (lovelace) | Signed bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Basic ADA | 10 / 0 | 12.465 | 12.752 | 0.557–25.000 | 8.635 | 25.000 | 392 | 292 |
| CIP-20 | 10 / 0 | 19.929 | 17.282 | 3.710–45.672 | 13.657 | 45.672 | 492 | 392 |
| Industrial sensor | 10 / 0 | 34.620 | 26.239 | 6.766–96.683 | 26.762 | 96.683 | 531 | 431 |

Times use AS150's first exact ledger observation after monotonic submission start. Per-node raw results, submission durations and propagation-observation spreads are also preserved. Sampling delay, block leadership, workload order, shared host and the change dependency influence the results. With ten samples the nearest-rank p95 equals the maximum. The latency comparison is descriptive.

The historical two-arm benchmark used serial polling across the peers and reported AS150 medians of 5.6132 and 18.0645 seconds for basic and metadata transfers. The current benchmark rotates three workload arms, queries peers in parallel, and checks exact change, containing blocks and metadata. The two historical CSVs cited by the release summary were unavailable in the inspected checkouts and Git history, so historical figures are attributed to that summary. These runs do not establish that metadata caused a latency difference. [Raw CSV](../results/b12/benchmark-trials.csv) · [Full metrics](../results/b12/benchmark-summary.json) · [Historical summary](../results/historical-results.md)

## 9. Plutus V3 compatibility issue

Under B12-4242, all nodes reported the Conway era and ledger protocol **2.0**, even with 251 Plutus V3 cost-model entries. The test era triggers selected Conway at epoch zero and the Shelley input retained 2.0. The CLI evaluator using those live parameters rejected V3 at the protocol-version gate, which requires major version 9 or later. An offline replay with a copied version-9 parameter file succeeded. That replay was diagnostic and did not change live parameters. A direct 2.0 → 9.0 governance jump is disallowed. The investigation classified an incremental historical upgrade as conditional, with unverified prerequisites and behavior in this forced-era 2.0 state. No upgrade was attempted. [Offline Phase 5D report](../results/b12/artifact-manifest.md#e045) · [Protocol investigation](../results/b12/artifact-manifest.md#e048)

## 10. Independent P9 deployment

A distinct VM was unavailable, so an approved sequential cutover reused the physical Docker host. The original nodes shut down cleanly. The original database bind directories remained in place, and the quiescent backup was verified in the Docker host namespace. The cutover archived exact images, configuration, logs, and research evidence before releasing the old Docker names and networks. P9 used a new root, fresh genesis and keys, new project label and independent databases. Its four nodes exhibited a shared height sequence **1, 1, 3, 7, 11, 16** over six startup observations, agreed at numbered heights, and all reported effective Conway **9.0**, magic **4343**, and 251 V3 model entries. The 33 original transaction anchors remain on B12-4242. Recovery by container recreation remains untested. [Cutover verification](../results/b12/artifact-manifest.md#e007) · [Recovery procedure](B12_P9_sequential_recovery.md)

## 11. Live Aiken and Plutus V3 execution

Aiken passed all three original unit tests and produced the expected script hash `16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83`. The unchanged validator uses one-byte-array-field datum and redeemer constructors and checks sensor-ID byte equality. The live spend used `AGRI_001` (underscore), distinct from the synthetic `AGRI-002` sensor metadata workload (hyphen). Physical sensor authentication, signer authorization and measurement-hash integrity fall outside the validator's logic.

| P9 transaction | Block / slot | Outcome |
|---|---|---|
| `eefca428cdb9f9a26a5cd6ba534b3dba44cada282fda91c552b3d0160cd119e8` | 59 / 1632 | 5 ADA script output with inline datum, separate 2 ADA collateral output, and expected change. Total fee 458 lovelace. |
| `49cb569d947821b99c3d4dca8bb27b4f1cd9cf420008f4c3f5bee3ac8c88be67` | 81 / 2039 | Original V3 script ran in a valid transaction. Script output was consumed, 4.997793 ADA paid out, and 2 ADA collateral retained. Total fee 2,207 lovelace. |

The Phase 6A audit matched original CBOR body bytes, block hashes and transaction indexes for both P9 transactions. It also verified the saved block bytes against all four local block stores. The valid spend at index 0 of block 81 (hash `5c07462ee283923fdcabea1e25958eb68394d3cb35ba6956b4d388e19b8e0538`) contains the original V3 witness, matching redeemer, **18,728 memory units** and **6,057,476 steps**, consistent with the online evaluation. At the recorded prices, rounding the combined cost gives **1,518 lovelace** for execution, included in the 2,207-lovelace total fee. Four-node spend observation times ranged from 50.85 to 51.03 seconds. Funding polling began after inclusion, so its later observed delay is unsuitable as an exact inclusion latency. Local mismatched, malformed, and missing-datum tests failed. No invalid transaction was submitted and no collateral-forfeiture behavior was measured. [Final P9 verification](../results/b12/artifact-manifest.md#e059) · [Independent P9 block byte check](../results/b12/artifact-manifest.md#e081)

## 12. Audit discrepancies and limits

| Finding | Audit disposition |
|---|---|
| Pre-genesis Phase 4B interim report says both attempts lacked rounds 2–3 and manifests. | The second collector continued after that assessment. The archive now contains rounds 2 and 3 at 17:27:25 and 17:28:26 UTC, with empty JSON and failed socket queries. It also contains two 24-byte header-only files with matching manifests. The first attempt still has only round 1 and no manifests. These are pre-genesis failures. The post-genesis pass is independently verified. |
| The generated post-genesis summary called origin a missing valid observation. | All four initial queries exited successfully and reported origin with no numbered block or hash. The later reports correctly interpret origin, then blocks 3 and 7. |
| P9 startup collector initially failed on a repeated height; the spend block checker initially failed its CBOR re-encoding assertion. | Later P9 samples verified advancement. Preserved original CBOR slices verified the spend across all four block stores. The initial observations and both limitations remain in the phase records. |
| Earlier deployment and phase reports use “pending” or “not started” in dated sections. The B12 README and broad publication audit pages still describe older validation scope. | Treat those statements as historical snapshots and use this report and the evidence index for the current reproduction status. |
| Historical raw benchmark CSVs and standalone Phase 1/3 reports were unavailable. | The historical results are attributed to the release summary. The earlier setup diff, logs and preflight are indexed individually. Fresh timing statistics were checked against the actual reproduction CSV. |

All 35 included IDs, fees, block references, and network assignments agreed with the audited data. No checksum mismatch was found in the 12 listed PCAP entries. The audited positive contract result consists of one confirmed spend. The small benchmark samples and one contract execution establish functional behavior under the documented conditions, with restricted generalization. [Audit result JSON](../results/b12/audit-summary.json)

## 13. Reproducibility assessment

**Portable workflows available. Independent live rehearsal remains pending.** Another student can use the pinned toolchain, topology templates, genesis generators, transaction helper, metadata fixtures, unchanged Aiken project, and P9 deployment guide to construct a fresh independent instance. Reproducing exact historic IDs, balances, block hashes or performance observations requires the original chain evidence. Fresh signing keys, start times and chain state produce different identifiers.

| Area | Available starting point | Remaining gap |
|---|---|---|
| Installation | Tool versions, Cardano release digest, pinned SEED revision and Aiken lockfile. | Add a tested fresh-install dependency lock and cold-cache rehearsal. Record base-image digests and apt packages. The setup script verifies archives during fresh installation and checks binary versions for an already-installed directory. |
| Deployment | B12 generator and topology, P9 stage/genesis and isolation helpers, two deployment paths and recovery runbook. | Document exact supported Compose variants and rehearse on a clean host. Phase 6B verified recovery with the original local images. Loading the backup image archive and a P9 rollback remain untested. The collector takes the runtime, genesis file and project as inputs. |
| Transactions and captures | B12 build/sign/submit helper, 5A/5B reports, benchmark schedule, P9 fixtures and step-by-step funding/build/approve guidance. | Phase 6D ports the instrumented benchmark, P9 unsigned builds and the inclusion verifier. The live commands need fresh Ubuntu rehearsal and authorization for any testnet submission. |
| Validation and expected outputs | Public script hash, datum/redeemer structures, evidence index, CSV, exact-block validation method, and success criteria per network. | Public extracts allow summary and checksum verification. The exact CBOR parser passed against the original databases and signed envelopes, which remain private. Replaying the historical ledger audit requires controlled access to those originals. |
| Troubleshooting | Existing installation and operations guidance plus the P9 protocol and sequential recovery reports. | Consolidate the missing-socket pre-genesis symptom, empty-PCAP interpretation, wrong magic/version gate, script-CBOR re-encoding, and image tag or bind conflicts into a reproducible checklist. |

Validate the [public evidence extracts](../results/b12/README.md) and follow the [portable workflow](B12_portable_workflow.md) for a fresh deployment. Historical block-body replay requires the private sources in the [artifact manifest](../results/b12/artifact-manifest.md).

## 14. Conclusions and repository review

B12-4242 provides the preserved historical control for consensus, transfers, metadata and benchmarking. B12-P9 supplies the live V3 control with an unchanged validator and separate genesis. The successful P9 transaction demonstrates a matching public sensor ID satisfying the original spending condition. Separate evaluation is required for a system intended to establish sensor identity or measurement provenance.

The Phase 6D publication candidate includes portable tools and reviewed evidence extracts. Generated signing keys, signed envelopes, Docker images, databases and raw captures remain private. [Archived Phase 6A worktree diff](../results/b12/artifact-manifest.md#e082)
