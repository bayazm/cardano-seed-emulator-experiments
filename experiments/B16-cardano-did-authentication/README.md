# B16-cardano-did-authentication · DID-based relay identity and authorization

## Overview

Evaluate possession of an enrolled relay identity alongside ledger eligibility and network admission.

## Research Objective

Evaluate possession of an enrolled relay identity alongside ledger eligibility and network admission.

## Background

The prototype derives a did:key identifier from an Ed25519 public key. A trusted authority signs enrollment. The gateway verifies the presented identity and signed challenge before consulting the on-chain authorization record.

## Architecture

AS180–AS182 are producers, AS183 is an incumbent relay and AS184 is the candidate. Each uses `10.<ASN>.0.71` and TCP 3001. The candidate peers with AS183; AS183 is the enforcement point for admission and revocation. AS185 (`10.185.0.71`) is a separate test host and has no Cardano node. Network magic is 5556.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4. Aiken v1.1.24 with standard library v4.0.0 is required for contract checks. Python cryptography is required for the DID code.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B16-cardano-did-authentication/network/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `private-testnet-conway-v2`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B16-cardano-did-authentication --minutes 30
cd experiments/B16-cardano-did-authentication/network
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

Open a shell at the repository root after startup. Follow the [registry and admission procedure](../../docs/reproducibility/registry-procedure.md) for the ordered funding, deployment, admission and revocation steps. The [runtime verification plan](../../docs/reproducibility/runtime-verification.md) records the live inputs and the required evidence.

## Verification

Verify legitimate challenge signing, enrollment-to-DID matching, freshness, active ledger revision and recorded firewall admission. Compare controller dry run, ledger agreement, rules and connectivity before and after revocation. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

Archived records show rejection of impersonation, DID substitution and same/fresh-challenge replay, with a successful legitimate replay-test control. The historical N17 controller also recorded revision-2 agreement and restoration of candidate denial. Publication preparation ran 23 Aiken checks and local policy and enrollment checks. The new namespace and registry helpers await live validation. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

Trust covers the authority keys, gateway, registry query path, observed endpoint mapping and host firewall. Key possession and a DID do not provide hardware attestation. Process-local challenge state leaves restart and distributed gateway behavior unverified.

## Limitations

Role staging and registry deployment tooling passed offline checks. Namespace startup and the integrated live workflow remain untested. Separate wire-level and local crypto evidence should be interpreted within each test scope. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
- [Aiken v1.1.24](https://github.com/aiken-lang/aiken/releases/tag/v1.1.24)
- [W3C DID Core](https://www.w3.org/TR/did-core/)
