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

Use the [independent B15 runbook](../../docs/reproducibility/b15.md) for Cardano and Aiken installation, fresh genesis verification, disposable Compose rendering and the supervised live experiment. The installer selects the checksum-verified Cardano release with `bash scripts/setup-cardano.sh B15` from the repository root.

## Configuration

The compiler reads `network/config/private-testnet-conway-v2` and the numbered topology files. Generate genesis and producer credentials in a private run copy. Use an empty runtime root for each fresh chain.

## Running the Experiment

The [B15 runbook](../../docs/reproducibility/b15.md) covers exact-body inspection and confirmation for the mint, authorization and revocation, plus bounded packet captures and cleanup.

### Required B15 registry bootstrap checks

1. Before applying parameters, record the intended seed transaction ID and output index. Confirm the reference is an unspent pure-ADA output of the funding wallet and differs from the collateral reference. Confirm `parameters.json` records the same `mint_input`.
2. Verify that the mint script applied to that seed produces the policy ID in `policy-id.txt`. The helper compares the applied Aiken hash with Cardano CLI. Independently verify the applied spending-validator hash from its Plutus V3 envelope and confirm that it is the payment credential of the address in `membership-script.addr` on the experiment network. The validator parameters must be the intended administrator hash, that policy ID and the bytes of `B15_REGISTRY`.
3. Review the mint transaction and verify the confirmed mint uses the selected seed and mints exactly one asset under the applied policy, one unit of `B15_REGISTRY`. Verify that the minted unit goes to the expected applied script address and that its inline datum contains AS184, `10.184.0.71`, `authorized = false` and revision 0.
4. Run the deployment helper's `verify --revision 0`. Require AS180–AS183 to agree on the reference and verify the policy, name, quantity, destination and complete inline datum against the confirmed transaction before proceeding.

The mint handler requires consumption of the parameterized seed and exactly one unit of the named asset, with no additional assets under its policy. Its one-shot property relies on ledger enforcement of single UTxO consumption. The mint destination and initial datum are deployment checks. The spending validator enforces administrator authorization, successor NFT continuity and valid revision increments once the registry is initialized correctly.

## Verification

Query the script address on each incumbent node. Verify the unique token, inline datum, revision and UTXO reference. Compare rule state and TCP/capture evidence after the controller applies a decision. The [operations guide](../../docs/reproducibility/operations.md) gives common tip, packet capture and Compose commands.

The controller verifies ledger authorization independently of the AS183 firewall. With `--apply`, admission requires authorized revision 1 and revocation requires unauthorized revision 2. Each enforcer requires two agreeing rounds across all four incumbents before changing rules. Admission removes exact candidate DROP rules and attempts to restore leading DROPs in both chains on failure. Revocation requires a leading candidate DROP in both chains, retaining successful changes if one direction fails. A shadowed exact DROP can remain behind the newly inserted leading DROP until admission removes it. The commands return a nonzero status and report incomplete enforcement on failure. Re-run the applicable command after checking the ledger and resolving the failure.

Use the same `COMPOSE_PROJECT_NAME` for startup and enforcement if you set one. The documented startup from `network/output` uses `output` by default. Before changing rules, the enforcers verify that AS183 is running as Compose service `hnode_183_host_0` in the expected project, uses that project's `net_183_net0` network mode, and has `10.183.0.71` in Docker and in its network namespace. Commands use the full container ID and check it again before each rule change.

Both `--apply` commands hold the same exclusive lock at `network/.runtime/b15-firewall.lock` from the first registry query through final firewall verification or recovery. Overlapping invocations from the same checkout fail immediately. The kernel releases the lock when the process exits.

Run the offline B15 controller tests from the repository root:

```bash
python3 -B -m unittest discover -s experiments/B15-cardano-smart-authorization-v2/network/scripts -p 'test_*.py'
```

## Experimental Results

The expanded Aiken suite passed 41 tests, and the offline controller suite passed 26 mocked tests. Historical captures identify admission and revocation phases. Their full transaction-to-packet correspondence remains unverified. See the [evidence summary](../../docs/results/historical-results.md).

## Security Analysis

NFT uniqueness identifies registry state for the configured policy. Physical relay identity depends on independent binding and operator trust. The off-chain controller reads registry state and changes iptables; successful validation alone does not modify the network.

## Limitations

The deployment helper has passed offline parameter and command checks. Fresh transaction balancing and confirmation remain untested. Controllers assume trusted deployment files, host and incumbent query responses, one candidate, fixed revisions and known containers. Agreement can reflect a shared stale view or be invalidated by a later ledger change. Ledger checks, target validation and firewall commands are separate operations, and firewall changes across the two chains are non-atomic. The lock coordinates cooperating enforcers in the same checkout. Operators must coordinate manual firewall edits, container lifecycle changes and enforcement from other checkouts separately. Rule checks cover the specified IPv4 TCP/3001 path at AS183. Packet delivery, other routes and ports, and binding the IP to the operator's physical relay require independent verification.

## Troubleshooting

See the [troubleshooting guide](../../docs/troubleshooting/README.md) for missing sockets, binaries, credentials and configuration issues. If startup fails, check the generated service name, node log and start time before changing the environment.

## References

- [Cardano Node 11.1.3 release](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3)
- [SEED Emulator](https://github.com/seed-labs/seed-emulator)
- [Aiken v1.1.24](https://github.com/aiken-lang/aiken/releases/tag/v1.1.24)
