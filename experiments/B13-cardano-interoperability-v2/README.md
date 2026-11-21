# B13 · Distinct-magic interoperability

Test how different network magic values affect node-to-node negotiation across two independently generated private chains with the same genesis start time.

AS170 produces blocks and AS171 relays on network A. AS172 produces on network B. The three systems route through the SEED IX200 network. Cardano listens on TCP 3001.

## Installation and deployment

Use Linux x86-64, Cardano Node 11.1.3, CLI 11.2.3.0, and the pinned SEED Emulator and host tools in the [B13 runbook](../../docs/reproducibility/b13.md#install-and-prepare-a-fresh-run). From the repository root in Bash, set:

```bash
scenario="B13-cardano-interoperability-v2"
```

Use the runbook to create the private experiment copy, install the binaries, explicitly generate fresh genesis and credentials, and verify the two Shelley starts and hashes.

For the cross-network treatment, [apply the AS172 → AS170 topology template](../../docs/reproducibility/b13.md#select-the-peer-topology) before compiling. The delivered topology provides the optional baseline with AS172 external peers disabled. Then [compile and build](../../docs/reproducibility/b13.md#compile-and-build) and start from `output/`:

```bash
docker-compose up -d
docker-compose ps
b_magic=6666
```

## Verify and clean up

Use the runbook's [TCP and Cardano handshake commands](../../docs/reproducibility/b13.md#check-tcp-and-the-cardano-handshake) and [synchronization checks](../../docs/reproducibility/b13.md#check-block-production-and-synchronization). Compare the AS172-to-AS170 probe using B's magic 6666 with the control using A's magic 5555. Check the configured peer attempt separately and compare advancing A and B ledger points.

Use the runbook's [cleanup and troubleshooting](../../docs/reproducibility/b13.md#troubleshoot-and-clean-up) from the same Compose project.
