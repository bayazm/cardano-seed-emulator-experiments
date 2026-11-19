# B13-cardano-interoperability-v2 · Independent chains with distinct network magic

## Overview

Compare routing and Cardano communication across independently configured private chains.

## Research Objective

Compare routing and Cardano communication across independently configured private chains.

## Background

Network magic is a node-to-node compatibility parameter. Genesis and common ledger history define separate compatibility checks.

## Architecture

Network A has producer AS170 (`10.170.0.71`) and relay AS171 (`10.171.0.71`). Network B has producer AS172 (`10.172.0.71`). A peers internally over TCP 3001. B starts without external local roots. The SEED underlay routes between these autonomous systems. Network magic is 5555 (A) and 6666 (B).

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B13-cardano-interoperability-v2/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `network-A and network-B`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

The original genesis shell helper in `scripts/` is retained for provenance. The commands below use the common generator, which creates the output parent and selects each variant’s timing.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B13-cardano-interoperability-v2 --minutes 30
cd experiments/B13-cardano-interoperability-v2
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

Establish baseline production separately. In a fresh copy, add AS171 as a local root in B using the same local-root structure as node2 and keep all chain inputs unchanged. Capture the connection attempt on each side and inspect node handshake logs and both tips. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

Historical diagnostic capture filenames were identified. Protocol-level outcomes have not been independently reconstructed. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

Transport reachability alone cannot establish blockchain interoperability.

## Limitations

The default launch does not configure a cross-chain peer. The controlled topology edit and application-layer diagnostics are required. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
