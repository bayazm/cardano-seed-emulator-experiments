# B13 · Matching-magic interoperability

Test node-to-node negotiation and ledger compatibility between independently generated chains with magic 5555 on both networks and identical genesis start times. The configured cross-network connection runs from AS172 to AS170.

AS170 produces blocks and AS171 relays on network A. AS172 produces on network B. The three systems route through the SEED IX200 network. Cardano listens on TCP 3001.

## Installation and deployment

Use Linux x86-64, Cardano Node 11.1.3, CLI 11.2.3.0, and the pinned SEED Emulator and host tools in the [B13 runbook](../../docs/reproducibility/b13.md#install-and-prepare-a-fresh-run). From the repository root in Bash, set:

```bash
scenario="B13-cardano-same-time"
```

Use the runbook to create the private experiment copy, install the binaries, explicitly generate fresh genesis and credentials, and verify the two Shelley starts and hashes.

For the cross-network treatment, [apply the AS172 → AS170 topology template](../../docs/reproducibility/b13.md#select-the-peer-topology) before compiling. The delivered topology provides the optional baseline with AS172 external peers disabled. Then [compile and build](../../docs/reproducibility/b13.md#compile-and-build) and start from `output/`:

```bash
docker-compose up -d
docker-compose ps
b_magic=5555
```

## Verify and clean up

Use the runbook's [TCP and Cardano handshake commands](../../docs/reproducibility/b13.md#check-tcp-and-the-cardano-handshake) and [synchronization checks](../../docs/reproducibility/b13.md#check-block-production-and-synchronization). Confirm equal magic and starts and different Shelley genesis hashes before launch. Check the configured peer attempt and compare advancing ledger points after genesis to determine whether the chains share history.

Use the runbook's [cleanup and troubleshooting](../../docs/reproducibility/b13.md#troubleshoot-and-clean-up) from the same Compose project.
