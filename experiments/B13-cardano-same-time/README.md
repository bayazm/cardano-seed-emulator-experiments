# B13-cardano-same-time · Independent chains with matching magic and start time

## Overview

Control timing in addition to matching magic and compare independently generated chains.

## Research Objective

Control timing in addition to matching magic and compare independently generated chains.

## Background

Genesis identity includes network initialization material beyond time and magic.

## Architecture

Network A has producer AS170 (`10.170.0.71`) and relay AS171 (`10.171.0.71`). Network B has producer AS172 (`10.172.0.71`). A peers internally over TCP 3001. B starts without external local roots. The SEED underlay routes between these autonomous systems. Network magic is 5555 on both networks.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B13-cardano-same-time/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `network-A and network-B`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

The original genesis shell helper in `scripts/` is retained for provenance. The commands below use the common generator, which creates the output parent and selects each variant’s timing.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B13-cardano-same-time --minutes 30
cd experiments/B13-cardano-same-time
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

Use the common genesis generator so A and B have an identical future start. Historical shell helpers use an archived timestamp.

## Verification

Follow the [runtime verification plan](../../docs/reproducibility/runtime-verification.md) for expected observations, evidence and cleanup.

Confirm equal starts and distinct era hashes before startup. In a separate compiler copy add B’s AS171 local root. Confirm or reject interoperability with Cardano handshake and common-height ledger evidence. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

The two historical Shelley genesis hashes differ even though both start times and magic values match. No fresh on-chain comparison was run. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

Matching magic and clock configuration alone leaves chain identity unestablished.

## Limitations

The historical compiler routes A database paths into a same-magic namespace. The default release runtime is isolated unless deliberately shared. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
