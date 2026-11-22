# B14 · Firewall-based relay admission

Does a scoped firewall exception let a candidate Cardano relay connect, and does removing it block new connections while incumbent peers continue to communicate?

| Role | AS | IPv4 address |
|---|---|---|
| Block producers | AS150–AS152 | `10.150.0.71`, `10.151.0.71`, `10.152.0.71` |
| Incumbent relay | AS153 | `10.153.0.71` |
| Candidate relay | AS154 | `10.154.0.71` |

The incumbents peer with each other over SEED-routed links. AS154 dials AS153. The private network uses magic `4242` and TCP port `3001`.

## Installation and deployment

Use an isolated Linux x86-64 Docker host, standalone Docker Compose, the pinned SEED Emulator checkout, and Cardano Node 11.1.3 with CLI 11.2.3.0. Follow the [B14 runbook](../../docs/reproducibility/b14.md) to install the verified binaries, generate a fresh private chain, validate the Compose configuration, and start the experiment.

## Verify and clean up

The four incumbents start in **deny**. Use `scripts/relay-admission.sh grant` to admit the candidate at AS153 only, then `revoke` to restore denial. At each stage, use `status` to inspect rules and counters and probe AS153 from AS154. Verify that incumbent connectivity continues and keep packet captures local. Test existing connections separately because the firewall change does not explicitly close sockets. Run `restore` before teardown. The [runbook](../../docs/reproducibility/b14.md#verify-denial-admission-and-revocation) provides the commands and expected observations.
