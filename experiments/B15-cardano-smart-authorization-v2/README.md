# B15-cardano-smart-authorization-v2 · Smart-contract-backed relay authorization

## Overview

Connect a ledger-authorized relay membership transition to an explicit TCP enforcement step.

## Research Objective

Connect a ledger-authorized relay membership transition to an explicit TCP enforcement step.

## Background

The one-shot minting policy consumes a particular UTXO and mints a singleton B15_REGISTRY token. The validator checks administrator signatures, registry token continuity and state transitions.

## Architecture

AS180–AS182 are producers, AS183 is an incumbent relay and AS184 is the candidate. Each uses `10.<ASN>.0.71` and TCP 3001. The candidate peers with AS183; AS183 is the enforcement point for admission and revocation. Network magic is 5556.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4. Aiken v1.1.24 with standard library v4.0.0 is required for contract checks.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B15-cardano-smart-authorization-v2/network/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `private-testnet-conway-v2`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B15-cardano-smart-authorization-v2 --minutes 30
cd experiments/B15-cardano-smart-authorization-v2/network
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

Open a shell at the repository root after startup. Follow the [registry and admission procedure](../../docs/reproducibility/registry-procedure.md) for the ordered funding, deployment, admission and revocation steps. The [runtime verification plan](../../docs/reproducibility/runtime-verification.md) records the live inputs and the required evidence.

## Verification

Query the script address on each incumbent node. Verify the unique token, inline datum, revision and UTXO reference. Compare rule state and TCP/capture evidence after the controller applies a decision. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

The Aiken suite passed 23 tests. Historical captures identify admission and revocation phases. Their full transaction-to-packet correspondence remains unverified. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

NFT uniqueness identifies registry state for the configured policy. Physical relay identity depends on independent binding and operator trust. The off-chain controller reads registry state and changes iptables; successful validation alone does not modify the network.

## Limitations

The deployment helper has passed offline parameter and command checks. Fresh transaction balancing and confirmation remain untested. Controllers assume one candidate, fixed revisions, known containers and a trusted local ledger query. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
- [Aiken v1.1.24](https://github.com/aiken-lang/aiken/releases/tag/v1.1.24)
