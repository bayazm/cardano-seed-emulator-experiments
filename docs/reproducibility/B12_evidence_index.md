# B12 evidence index

This index covers the fresh B12 reproduction on 2026-11-19 and 2026-11-20 UTC. It separates **B12-4242** (magic 4242, Conway ledger protocol 2.0) and **B12-P9** (magic 4343, Conway ledger protocol 9.0). The Phase 6A audit counts 33 included transactions on B12-4242 and two on P9. The links below lead to reviewed public extracts or to the archive manifest. Manifest entries describe the source and its access limitations. See the [final reproduction report](B12_final_reproduction_report.md) for claims, discrepancies, and reproducibility gaps.

The later sensor-hash experiment adds one funding transaction and one valid spend on P9. Its evidence is indexed separately from the Phase 6A counts. [Final sensor-hash report](B12_sensor_hash_final_report.md) · [Sanitized sensor-hash verification](../results/b12/sensor-hash-verification.json)

## Source, installation and build

| Evidence | Location |
|---|---|
| Source, workload definitions and historical summary | [B12 sources and instructions](../../experiments/B12-cardano/) · [Published historical results](../results/historical-results.md) |
| Environment and versions | [Installation guide](install.md) · [Setup helper](../../scripts/setup-cardano.sh) · [B12-4242 live node version](../results/b12/artifact-manifest.md#e013) · [Live CLI version](../results/b12/artifact-manifest.md#e014) |
| Early setup and compile artifacts | [Phase 2 setup diff](../results/b12/artifact-manifest.md#e015) · [Early SEED compile log](../results/b12/artifact-manifest.md#e016) · [Early normalized Compose](../results/b12/artifact-manifest.md#e017) |
| B12-4242 deployment | [Compiled Compose](../results/b12/artifact-manifest.md#e018) · [Normalized deployed Compose](../results/b12/artifact-manifest.md#e019) · [Build log](../results/b12/artifact-manifest.md#e020) · [Startup log](../results/b12/artifact-manifest.md#e021) |
| B12-4242 genesis | [Preflight identity, funding and pool IDs](../results/b12/artifact-manifest.md#e022) · [Public era genesis, topologies and node config](../results/b12/artifact-manifest.md#e023) · [Genesis SHA-256](../results/b12/artifact-manifest.md#e024) |
| P9 genesis and deployment | [Genesis manifest and hashes](../results/b12/artifact-manifest.md#e001) · [Node configuration and era genesis](../results/b12/artifact-manifest.md#e025) · [Normalized Compose](../results/b12/artifact-manifest.md#e026) |
| P9 procedures and source | [P9 guide](B12_P9_plutus_v3_guide.md) · [Sequential recovery plan](B12_P9_sequential_recovery.md) · [P9 preparer, isolation check and fixtures](../../experiments/B12-P9/) |

No standalone Phase 1 or Phase 3 report was located. The installation instructions, early staging and compile outputs, and active deployment chain of evidence provide the available pre-runtime record. Preparing this index did not reconstruct missing records.

## B12-4242, protocol 2.0

| Phase | Report and primary evidence |
|---|---|
| 4A–4B preflight and consensus | [Verification report](../results/b12/artifact-manifest.md#e027) · [Earlier failed collection A](../results/b12/artifact-manifest.md#e028) · [Earlier failed collection B](../results/b12/artifact-manifest.md#e029) · [Post-genesis tips, process status, logs, captures and manifests](../results/b12/artifact-manifest.md#e030) |
| 5A basic transfer | [Report](../results/b12/artifact-manifest.md#e031) · [Funding wallets and balances](../results/b12/artifact-manifest.md#e032) · [Transaction validation](../results/b12/artifact-manifest.md#e033) · [Four-node observations](../results/b12/artifact-manifest.md#e034) |
| 5B CIP-20 and industrial sensor metadata | [Report](../results/b12/artifact-manifest.md#e035) · [Block 135 CBOR](../results/b12/artifact-manifest.md#e036) · [Per-node metadata and block proof](../results/b12/artifact-manifest.md#e037) · [Measurement and positive/negative integrity evidence](../results/b12/artifact-manifest.md#e038) |
| 5C confirmation benchmark | [Report](../results/b12/artifact-manifest.md#e039) · [Trial schedule](../results/b12/artifact-manifest.md#e040) · [Raw trial CSV](../results/b12/benchmark-trials.csv) · [Full statistics](../results/b12/benchmark-summary.json) · [Per-trial CBOR, tips, timed observations and metadata](../results/b12/artifact-manifest.md#e043) · [Run manifest and runner](../results/b12/artifact-manifest.md#e044) |
| 5D offline-only contract on this network | [Offline report](../results/b12/artifact-manifest.md#e045) · [CLI error under live protocol-2 parameters](../results/b12/artifact-manifest.md#e046) · [Hypothetical version-9 offline result](../results/b12/artifact-manifest.md#e047) · [Compatibility and governance investigation](../results/b12/artifact-manifest.md#e048) |
| Preservation at cutover | [Pre-stop history check](../results/b12/artifact-manifest.md#e049) · [Quiescent database digest](../results/b12/artifact-manifest.md#e050) · [Historical evidence checksum manifest](../results/b12/artifact-manifest.md#e008) · [Copies of the 32 blocks containing the 33 confirmed transactions](../results/b12/artifact-manifest.md#e051) |

The cutover archives containing raw databases, generated contexts and producer images are private. Producer images can embed credentials. Retain them outside Git and share only reviewed evidence exports.

## B12-P9, protocol 9.0

| Evidence | Location |
|---|---|
| Cutover, health, epoch and consensus | [Cutover verification](../results/b12/artifact-manifest.md#e007) · [Six tip rounds and common hash](../results/b12/artifact-manifest.md#e052) · [Live P9 protocol parameters](../results/b12/artifact-manifest.md#e053) |
| Unchanged validator and compiler results | [Original source, manifest and lockfile](../../experiments/B12-cardano/smart-contract/sensor-validation/) · [Source checksums](../results/b12/artifact-manifest.md#e054) · [Aiken version](../results/b12/artifact-manifest.md#e055) · [Tests](../results/b12/artifact-manifest.md#e056) · [Compilation](../results/b12/artifact-manifest.md#e057) · [Blueprint](../results/b12/artifact-manifest.md#e058) |
| Script funding and execution | [Final Phase 5D-P9 verification](../results/b12/artifact-manifest.md#e059) · [Funding input, outputs and fee](../results/b12/artifact-manifest.md#e060) · [Funding block 59 and node observations](../results/b12/p9-inclusion-summary.json) |
| Live costs and positive execution | [CLI online evaluator output](../results/b12/artifact-manifest.md#e062) · [Signed spend validation](../results/b12/artifact-manifest.md#e063) · [Spend block 81 proof](../results/b12/p9-inclusion-summary.json) · [On-chain script, redeemer and budget](../results/b12/artifact-manifest.md#e065) |
| Negative checks | [Offline evaluation outcomes](../results/b12/artifact-manifest.md#e066) · [Inputs for original validator fixtures](../../experiments/B12-P9/fixtures/) |

## Capture inventory

All packet counts below are offline counts for TCP/3001, in AS150 / AS153 order. The 10 packet-bearing files account for all passing capture windows in this index. Capture directories can also contain byte-identical copies of files retained with the phase evidence.

| Network / window | Packets | Files and checksums |
|---|---:|---|
| B12-4242 pre-genesis A and B | 0 / 0 each | [Original capture files](../results/b12/artifact-manifest.md#e067) · [Run B's header-only SHA-256 manifests](../results/b12/artifact-manifest.md#e029) |
| B12-4242 post-genesis 4B | 577 / 557 | [Producer manifest](../results/b12/artifact-manifest.md#e068) · [Relay manifest](../results/b12/artifact-manifest.md#e069) |
| B12-4242 benchmark round 1 | 411 / 369 | [PCAPs and capture logs](../results/b12/artifact-manifest.md#e070) · [Manifest](../results/b12/artifact-manifest.md#e071) |
| P9 ambient preflight | 97 / 100 | [Capture summary](../results/b12/artifact-manifest.md#e072) · [Manifest](../results/b12/artifact-manifest.md#e073) |
| P9 funding | 376 / 381 | [Capture summary](../results/b12/artifact-manifest.md#e074) · [Manifest](../results/b12/artifact-manifest.md#e075) |
| P9 spend | 293 / 284 | [Capture summary](../results/b12/artifact-manifest.md#e076) · [Manifest](../results/b12/artifact-manifest.md#e077) |

## Phase 6A audit outputs

- [Exact 35-transaction inventory](../results/b12/transaction-anchors.csv) includes network, phase, trial, ID, block, slot, hash, and encoded fee.
- [Machine-readable audit results](../results/b12/audit-summary.json) includes verified genesis hashes, benchmark metrics, measurement digest, script fee and execution units, and PCAP checks. [Read-only audit script](../results/b12/artifact-manifest.md#e080)
- [B12-4242 retained DB anchor recheck](../results/b12/artifact-manifest.md#e002) and [P9 block-store recheck](../results/b12/artifact-manifest.md#e081).
- [Archived Phase 6A worktree diff](../results/b12/artifact-manifest.md#e082) includes tracked changes and non-ignored new files, without staging files. The private data trees are excluded.
