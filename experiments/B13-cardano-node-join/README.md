# B13 · Staged relay joining

Start AS171 with an empty database after AS170 has begun producing blocks. Verify that the late relay synchronizes on A's ledger. AS170 and AS171 use the same A genesis. AS172 produces independently on B with its own genesis. Both networks use magic 5555 and the same configured start. The three systems route through IX200 and Cardano listens on TCP 3001.

## Installation and deployment

Use Linux x86-64, Cardano Node 11.1.3, CLI 11.2.3.0, and the pinned SEED Emulator and host tools in the [B13 runbook](../../docs/reproducibility/b13.md#install-and-prepare-a-fresh-run). From the repository root in Bash, set:

```bash
scenario="B13-cardano-node-join"
```

Use the runbook to create the private experiment copy, install the binaries, explicitly generate fresh genesis and credentials, and verify the two Shelley starts and hashes.

Keep AS172's delivered topology for the staged test so it remains an independent control. The [AS172 → AS170 template](../../docs/reproducibility/b13.md#select-the-peer-topology) is available for a separate cross-network run. Follow [compile and build](../../docs/reproducibility/b13.md#compile-and-build), then run these commands from `output/`:

```bash
docker-compose up -d --scale hnode_171_host_0=0
docker-compose ps
a="$(docker-compose ps -q hnode_170_host_0)"
b_magic=5555
docker exec "$a" cardano-cli query tip --socket-path /cardano/node.socket --testnet-magic 5555
```

Check that AS171 is absent from the running services. AS170 must produce blocks with the relay still stopped before you can evaluate late-join synchronization. Wait until after A's configured genesis time and repeat the AS170 tip query until you record an increasing block number. If AS170 fails to advance:

- Compare the container's `docker exec "$a" date -u` with A's generated Shelley `systemStart`. Allow time for the single producer to forge.
- Check `docker-compose ps`, the node socket with `docker exec "$a" test -S /cardano/node.socket`, and AS170 startup and forging messages using `node_log "$a"` from the [runbook](../../docs/reproducibility/b13.md#check-tcp-and-the-cardano-handshake).
- Check that the AS170 image contains A's matching genesis files and readable producer credentials at `/cardano/producer/`. Check the log for genesis hash mismatches, credential or KES errors, and database startup failures. Confirm that this run uses its fresh database bind mount and that the CLI query uses magic 5555.

If blocks still fail to advance, record an unmet producer prerequisite and leave the synchronization and compatibility outcome inconclusive. Once AS170 is advancing, start AS171:

```bash
date -u
docker-compose up -d hnode_171_host_0
docker-compose ps
```

## Verify and clean up

Load the service IDs and `probe` function from [TCP and Cardano handshake checks](../../docs/reproducibility/b13.md#check-tcp-and-the-cardano-handshake) and run the probe toward AS170 from the relay.

```bash
probe "$relay" 10.170.0.71 5555
```

Use the [tip queries](../../docs/reproducibility/b13.md#check-block-production-and-synchronization) for all three nodes. Record a later AS171 tip matching a previously observed AS170 block, slot and hash. Track AS172 as a separate control. Use [cleanup and troubleshooting](../../docs/reproducibility/b13.md#troubleshoot-and-clean-up) from the same Compose project.
