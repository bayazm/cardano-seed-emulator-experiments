# Runtime verification plans

These plans are for a later authorized run on a dedicated Linux VM. Use a fresh experiment copy and empty runtime root for each case. Use the setup, genesis and exact start commands from the linked experiment README. First verify Docker, Compose, SEED, CLI and node versions against the [installation guide](install.md). Record resolved Python packages and Docker image IDs or digests. Save compiler output, `docker-compose config -q` status and `docker-compose ps`. Record UTC times, magic, era hashes and phase names. Use a ten-minute observation window after the configured genesis time and a three-minute minimum after each phase change. Record actual durations and any startup delays.

Run observations from the generated `output/` directory. For each experiment use the container names listed below, or confirm them in the generated Compose file. Store evidence under the compiler's ignored runtime directory. A reusable set of read-only queries is:

```bash
tip() {
  docker exec "$1" cardano-cli query tip --testnet-magic "$2" --socket-path /cardano/node.socket
}
docker logs --timestamps "$container"
docker exec "$container" ss -tn
```

Use the [packet-capture commands](operations.md#packet-capture) with a unique filename per host and phase. Capture both endpoints for disputed results. For a host with `/captures` mounted record the host-side mount path from generated Compose. Save capture metadata and raw traffic locally. Avoid recording secrets or exporting raw gateway transcripts.

## B11 · Genesis and relay synchronization

Use the [B11 startup](../../experiments/B11-cardano/README.md). Query `tip as150h-Cardano-Node-1-10.150.0.71 4242` and `tip as153h-Cardano-Node-4-10.153.0.71 4242` repeatedly. Save producer and relay logs. Pass if at least one new block is observed on the producer and the relay reaches a matching chain point. Record era and sync progress if reported. Failure to open the socket, no progress during the window, or a conflicting block at a verified common height fails this test.

## B12 · Transfer and sensor metadata

Use the [B12 startup and funding checks](../../experiments/B12-cardano/README.md). Verify all four advancing tips with magic 4242. From the compiler directory run the README's build-only transfer and then repeat with `--execute` on the dedicated test network. Repeat with the sensor metadata fixture and run the included digest verifier. Collect transaction IDs, node query evidence, transfer CSV and verifier output. Run `python3 benchmark_cardano.py --pairs 1` only after confirming genesis funding and a successful transfer. Preserve its CSV. Pass when expected transaction outputs are confirmed on the four queried nodes, the fixture digest matches, an altered copy fails verification, and both benchmark rows report confirmation. Missing funds, timeout, a divergent ledger result or unexpected verifier status fails the applicable check.

## B13 · Interoperability and staged joining

Use [distinct magic](../../experiments/B13-cardano-interoperability-v2/README.md), [matching magic and start time](../../experiments/B13-cardano-same-time/README.md), or [staged node join](../../experiments/B13-cardano-node-join/README.md). The [B13 runbook](b13.md) covers private run directories, the AS172 → AS170 topology, TCP and Cardano handshake probes, and comparing chain points. For staged joining, verify that AS170 advances before starting AS171 and that AS171 reaches a matching A block point afterward.

## B14 · Network admission and revocation

Use the [B14 runbook](b14.md#verify-denial-admission-and-revocation) for the controller, per-phase probes, packet captures, and chain-tip checks. Fresh connections should fail during startup denial, succeed at AS153 during admission, and fail again after revocation. Track existing flows separately.

## B15 v2 · Registry-backed admission and revocation

Use [B15 startup](../../experiments/B15-cardano-smart-authorization-v2/README.md) and the [registry procedure](registry-procedure.md). Run the registry helper for wallet discovery, collateral split, parameter application, mint and transitions. Check revision 0 first and use live funding and collateral references for each step. Use the procedure's controller dry runs and apply commands only after the corresponding ledger transition. Collect registry references and datums on four incumbent nodes, controller output, AS183 firewall snapshots and paired AS183/AS184 TCP/3001 captures. Confirm candidate connectivity changes with revision 1 admission and revision 2 revocation, and that legitimate peers continue. Any registry disagreement, controller error or observed mismatch between expected firewall and connectivity fails the corresponding phase.

## B16 · Identity, ledger and revocation

Use [B16 startup](../../experiments/B16-cardano-did-authentication/README.md) and the [registry procedure](registry-procedure.md). Collect local identity and policy test output first. Stage the AS183 and AS184 role directories with the B16 helper after verifying the live registry. Enter the two namespaces in separate terminals and collect the gateway ready line and candidate response. Check the AS185 TCP/3001 denial before and after admission with `docker exec b16-as185h-DID-Attacker-10.185.0.71 nc -z -w 3 10.183.0.71 3001`. Record AS183 rule counters and continue with the legitimate candidate separately. Test the enrolled candidate and compare authentication, current registry eligibility, firewall state and reachability. Collect private TCP/4040 endpoint metadata separately from TCP/3001 admission and revocation captures. Pass the integrated run only if the legitimate candidate passes the expected gates, the firewall follows the verified registry transition, new connections fail after revocation and legitimate peers remain connected. Missing root namespace access, Docker access, cryptography under the selected interpreter or the live deployment inputs blocks the corresponding phase. The historical impersonation, replay and substitution observations do not satisfy fresh validation.

## Cleanup for every experiment

Stop foreground observers and gateway processes. For B14 use the [runbook cleanup procedure](b14.md#restore-and-clean-up). For B16 use `python3 scripts/b16_n15_firewall_controller.py revoke` from `network/` if the authorized test gateway applied candidate ACCEPT rules and the run needs rollback. From the experiment's `output/` directory, run `docker-compose stop` and record `docker-compose ps`. Keep the database, evidence and local credentials protected. Stopping the isolated experiment preserves its state for audit.
