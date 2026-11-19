# B13-cardano-same-magic · Independent chains with matching magic and staggered starts

## Overview

Test what matching magic permits while genesis identities and start times differ.

## Research Objective

Test what matching magic permits while genesis identities and start times differ.

## Background

Identical network magic can permit protocol negotiation while chains retain separate genesis identities and history.

## Architecture

Network A has producer AS170 (`10.170.0.71`) and relay AS171 (`10.171.0.71`). Network B has producer AS172 (`10.172.0.71`). A peers internally over TCP 3001. B starts without external local roots. The SEED underlay routes between these autonomous systems. Network magic is 5555 on both networks.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B13-cardano-same-magic/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `network-A and network-B`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

The original genesis shell helper in `scripts/` is retained for provenance. The commands below use the common generator, which creates the output parent and selects each variant’s timing.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B13-cardano-same-magic --minutes 30
cd experiments/B13-cardano-same-magic
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

Use the common genesis generator. It offsets B by 20 minutes. Record the two generated starts and repeat observations after B starts.

## Verification

Follow the [runtime verification plan](../../docs/reproducibility/runtime-verification.md) for expected observations, evidence and cleanup.

After both chains start, add AS171 as a local root on B in a fresh compiler copy and preserve other variables. Compare TCP and node logs against distinct-magic B13, then query both ledgers. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

The archived source shows equal magic and different Shelley starts. The release generator uses a controlled offset; the historical waiting interval was larger. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

Separate genesis remains a confounding compatibility variable even when the magic matches.

## Limitations

The default topology leaves B without a cross-chain peer. A fresh run does not recreate the historical A database. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
