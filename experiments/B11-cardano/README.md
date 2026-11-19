# B11-cardano · Initial private Cardano deployment

## Overview

Observe block production and synchronization in a routed emulated network.

## Research Objective

Determine whether a private blockchain initializes and converges across multiple autonomous systems.

## Background

The producer obtains KES and VRF signing material and an operational certificate from a consistent genesis run. The relay follows the chain over the node-to-node protocol.

## Architecture

AS150–AS152 are producers and AS153 is a relay. Each uses `10.<ASN>.0.71` on net0 and TCP 3001. The default topologies connect each of the four peers to the other three over SEED-routed links. Network magic is 4242.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.0.1 and CLI 11.0.0.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B11-cardano/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `private-testnet-d0`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B11-cardano --minutes 30
cd experiments/B11-cardano
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

Follow the verification sequence after genesis time in the dedicated emulator VM.

## Verification

Follow the [runtime verification plan](../../docs/reproducibility/runtime-verification.md) for expected observations, evidence and cleanup.

Collect increasing tips from all four hosts and compare hashes at common heights. Query the Shelley ledger and check relay logs or connections when it lags. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

The controlled publication run advanced from block 1 to block 3 with matching tips and 100.00% reported sync on all four nodes. The relay reached the producer on TCP/3001. See the [B11 runtime result](../../docs/audit/b11-runtime-result.md). The archived query and adoption CSVs provide historical baseline observations. Their exact genesis pairing remains unresolved. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

Producer credentials are staged in container builds. The experiments assume trusted administrative access to the host.

## Limitations

This setup has a small producer set, accelerated era activation and experiment-specific protocol settings. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.0.1 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.0.1)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
