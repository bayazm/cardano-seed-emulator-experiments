# B14-cardano-relay-admission · Firewall-based relay admission

## Overview

Compare the candidate’s TCP traffic under default denial, a temporary admission and revocation.

## Research Objective

Compare the candidate’s TCP traffic under default denial, a temporary admission and revocation.

## Background

Linux iptables implements source and destination filtering on the incumbent nodes. The initial rules drop targeted traffic at TCP destination port 3001.

## Architecture

AS150–AS152 are producers and AS153 is a relay. Each uses `10.<ASN>.0.71` on net0 and TCP 3001. The default topologies connect each of the four peers to the other three over SEED-routed links. The candidate AS154 (`10.154.0.71`) targets incumbent AS153. Network magic is 4242.

## Prerequisites

Linux x86-64, Python 3, Cardano Node 11.1.3 and CLI 11.2.3.0, and the pinned SEED Emulator revision in the [installation guide](../../docs/reproducibility/install.md). The audit host used Python 3.8.10, Docker 20.10.21 and Compose 1.27.4.

## Installation

1. Install SEED Emulator and the host utilities from the installation guide.
2. In `experiments/B14-cardano-relay-admission/`, extract the checksum-verified Cardano archive under `resources/cardano-static/`.
3. Return to the repository root for fresh genesis generation.

## Configuration

The compiler reads `config/` under its own directory. The active profile is `private-testnet-conway-v2`. The numbered topology files define local roots. Use the [genesis guide](../../docs/reproducibility/genesis.md) to keep era files and corresponding locally generated credentials together. Choose a dedicated empty runtime root for a fresh run.

## Running the Experiment

From the repository root, in a disposable experiment copy:

```bash
umask 077
python3 scripts/prepare-genesis.py experiments/B14-cardano-relay-admission --minutes 30
cd experiments/B14-cardano-relay-admission
python3 blockchain.py amd
cd output
docker-compose config -q
docker-compose build
docker-compose up -d
docker-compose ps
```

From `output/`, capture the default-denied state before adding a narrowly scoped rule to allow the candidate/AS153 phase. Remove those exact two phase rules to restore default denial. Keep this change confined to the dedicated test VM.

```bash
relay=as153h-Cardano-Node-4-10.153.0.71
docker exec "$relay" iptables -w -nvL INPUT
docker exec "$relay" iptables -w -I INPUT 1 -s 10.154.0.71 -p tcp --dport 3001 -j ACCEPT
docker exec "$relay" iptables -w -I OUTPUT 1 -d 10.154.0.71 -p tcp --dport 3001 -j ACCEPT
# Capture the admitted phase before restoring default deny.
docker exec "$relay" iptables -w -D INPUT -s 10.154.0.71 -p tcp --dport 3001 -j ACCEPT
docker exec "$relay" iptables -w -D OUTPUT -d 10.154.0.71 -p tcp --dport 3001 -j ACCEPT
```

Record the original rule state before starting and use matched capture windows.

## Verification

Follow the [runtime verification plan](../../docs/reproducibility/runtime-verification.md) for expected observations, evidence and cleanup.

Record INPUT and OUTPUT counters, candidate AS154 TCP state, repeated connection attempts and packet flags before admission, during admission and after revocation. Use chain-tip queries before inferring synchronization. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

## Experimental Results

Historical candidate captures show no SYN-ACK under E2 and E4 and two under E3. E4 also includes traffic from its capture window; see the evidence table. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

An address-based rule is bound to the observed network endpoint. Trust depends on routing and firewall administration.

## Limitations

Established flows, interface selection and traffic unrelated to candidate-initiated port 3001 can complicate capture interpretation. See the [validation matrix](../../docs/audit/validation-matrix.md) for the checks performed on this release.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
