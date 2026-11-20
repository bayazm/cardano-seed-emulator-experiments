# B12-cardano · Conway transactions, metadata and sensor integrity

## Reproduction guides

- [Sensor-hash validator result and demo walkthrough](../../docs/reproducibility/B12_sensor_hash_final_report.md)
- [Single-network sensor-hash reproduction commands](../../docs/reproducibility/B12_sensor_hash_smart_contract_demo.md)
- [B12-4242 protocol-2 workflows and benchmark](../../docs/reproducibility/B12_portable_workflow.md)
- [Sanitized experimental evidence and checksums](../../docs/results/b12/README.md)

## Overview

Measure confirmation and size for transfers with and without metadata, and demonstrate off-chain hash verification and a Plutus sensor validator.

## Research Objective

Compare the historical confirmation and transaction-size measurements and test the independent integrity controls.

## Background

CIP-20 uses label 674. The sensor prototype uses label 1000 to carry the SHA-256 of the exact off-chain file bytes. The Aiken validator evaluates its own datum and sensor-ID condition.

## Architecture

AS150–AS152 are producers and AS153 is a relay. Each uses `10.<ASN>.0.71` on net0 and TCP 3001. The default topologies connect each of the four peers to the other three over SEED-routed links. Network magic is 4242.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4. Aiken v1.1.24 with standard library v4.0.0 is required for contract checks.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. From the repository root run `bash scripts/setup-cardano.sh B12` to install the checksum-verified archive.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `private-testnet-conway-v2`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B12-cardano --minutes 30
cd experiments/B12-cardano
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

Return to the B12 compiler directory with `cd ..` after startup, generate each local base address and use the actual AS150 container name. Start with build-only mode, then repeat with `--execute` on the authorized VM to sign and submit.

```bash
cli=resources/cardano-static/bin/cardano-cli
mkdir -p data/transaction-test-v2
for i in 1 2 3; do
  keys="config/generated/testnet-conway-v2/stake-delegators/delegator$i"
  "$cli" address build --payment-verification-key-file "$keys/payment.vkey" \
    --stake-verification-key-file "$keys/staking.vkey" --testnet-magic 4242 \
    --out-file "data/transaction-test-v2/delegator$i-base.addr"
done
python3 cardano_transaction.py --node as150h-Cardano-Node-1-10.150.0.71 \
  --from 1 --to 2 --amount 2 --metadata examples/cip20-metadata.json
python3 sensor-prototype/verification/verify_sensor.py examples/measurement.json examples/sensor-metadata.json
(cd smart-contract/sensor-validation && aiken check && aiken build)
```

Use `--metadata examples/sensor-metadata.json` for the structured sensor transfer. A separately retained helper builds CIP-20 messages from text with `bash send-metadata.sh -f 1 -t "$(cat data/transaction-test-v2/delegator2-base.addr)" -m 'message'`. Confirm funding before using it. For the benchmark, prepare its configured metadata filename and run the following. The benchmark submits real transactions on the selected test chain.

```bash
mkdir -p data/metadata-test
cp examples/sensor-metadata.json data/metadata-test/sensor_hash_002.json
python3 benchmark_cardano.py --pairs 10
python3 analyze_benchmark.py
```

`python3 monitor_blocks.py` logs periodic tip queries to the local data tree until interrupted.

## Verification

Follow the [runtime verification plan](../../docs/reproducibility/runtime-verification.md) for expected observations, evidence and cleanup.

Check initial funding, signed/submitted transaction ID, outputs on all four nodes and the benchmark CSV. Compare the hash against metadata recovered from the confirmed transaction. Modify a disposable measurement copy for the local integrity negative control. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

The ten-pair historical benchmark reported 20 confirmations across all four queried nodes. The evidence summary gives sizes, fees and medians. Three Aiken checks passed during preparation. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

A consistent digest supports byte integrity when the ledger record and source binding are trusted. It provides no independent evidence of measurement correctness or sensor identity.

## Limitations

The transaction helper queries magic 4242. The unit-tested Plutus validator and off-chain metadata verifier are separate proof-of-concept layers. The local reproduction verified 33 transactions on B12-4242 and independently exercised the original Plutus V3 script on B12-P9. See the [portable workflow](../../docs/reproducibility/B12_portable_workflow.md) and [published evidence extracts](../../docs/results/b12/README.md). See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
- [CIP-20 transaction message metadata](https://cips.cardano.org/cip/CIP-0020)
- [Aiken v1.1.24](https://github.com/aiken-lang/aiken/releases/tag/v1.1.24)
