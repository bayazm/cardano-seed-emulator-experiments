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

## B13 interoperability v2, same magic and same time · Independent networks

Use the respective [distinct-magic](../../experiments/B13-cardano-interoperability-v2/README.md), [same-magic](../../experiments/B13-cardano-same-magic/README.md) or [same-time](../../experiments/B13-cardano-same-time/README.md) startup. For the independent-chain baseline keep the delivered B topology. For the paired test use a separate fresh compiler copy. In `config/network-B/topology-node3.json`, replace the empty `localRoots` list with the following group, then compile from that copy. Keep other inputs and topology settings controlled.

```json
[{"accessPoints":[{"address":"10.171.0.71","port":3001}],"advertise":false,"trustable":true,"valency":1}]
```

Query `tip as170h-Cardano-A-Node-1-10.170.0.71 5555` and `tip as172h-Cardano-B-Node-3-10.172.0.71 6666` for distinct magic. Substitute 5555 on B for the matching-magic variants. To establish TCP reachability from B, use:

```bash
docker exec as172h-Cardano-B-Node-3-10.172.0.71 nc -z -w 3 10.171.0.71 3001
```

Compare paired AS171/AS172 TCP/3001 captures, handshake logs, tip history and common chain points. Evaluate each scenario separately:

| Scenario | Expected control | Pass or failure condition |
|---|---|---|
| Distinct magic | Magic 5555/6666, equal configured start | Record transport reachability and evidence of the protocol outcome for distinct magic. Capture or logs that establish neither handshake result nor ledger behavior leave the result inconclusive. |
| Same magic | Magic 5555/5555, B starts 20 minutes after A | Confirm both distinct genesis identities and the configured start difference before comparing handshake and ledger evidence. Wait for B genesis before interpreting an absent connection. A mismatched control or absent usable evidence fails the run. |
| Same time | Magic 5555/5555, equal configured start, independent genesis | Verify equality of magic and time and distinct era hashes, then record handshake outcome separately from ledger behavior. A shared tip claim requires a verified common block point. A mislabeled configuration or missing diagnostics fails the run. |

The hypotheses are that magic affects negotiation and that matching magic/time can still leave separate ledgers. Report observations, including unexpected results, rather than treating the hypotheses as measured outcomes.

## B13 node join · Same-ledger convergence

Use the [staged startup](../../experiments/B13-cardano-node-join/README.md). Verify AS170 starts advancing before starting `hnode_171_host_0`. Collect timestamps, its startup logs, AS170 and AS171 tips using magic 5555, and a TCP/3001 capture between them. Check AS172 separately. Pass when the late AS171 relay advances to a common A chain point after startup. If AS171 was already started, shares a dirty database, or fails to converge, the staged result is invalid or failed.

## B14 · Network admission and revocation

Use the [B14 phase commands](../../experiments/B14-cardano-relay-admission/README.md). At each phase collect AS153 `iptables -w -nvL INPUT` and `OUTPUT` via `docker exec`, plus candidate/relay logs, `ss -tn` and TCP/3001 captures. To test a new candidate connection during each window:

```bash
docker exec as154h-Cardano-Node-5-10.154.0.71 nc -z -w 3 10.153.0.71 3001
```

Pass when the fresh candidate connection fails in baseline, succeeds in the admitted phase and fails again after rule restoration, with evidence of expected rule order and continued legitimate connectivity. Track existing flows separately from new probes. Capture ambiguity or unchanged candidate connectivity requires investigation.

## B15 v2 · Registry-backed admission and revocation

Use [B15 startup](../../experiments/B15-cardano-smart-authorization-v2/README.md) and the [registry procedure](registry-procedure.md). Run the registry helper for wallet discovery, collateral split, parameter application, mint and transitions. Check revision 0 first and use live funding and collateral references for each step. Use the procedure's controller dry runs and apply commands only after the corresponding ledger transition. Collect registry references and datums on four incumbent nodes, controller output, AS183 firewall snapshots and paired AS183/AS184 TCP/3001 captures. Confirm candidate connectivity changes with revision 1 admission and revision 2 revocation, and that legitimate peers continue. Any registry disagreement, controller error or observed mismatch between expected firewall and connectivity fails the corresponding phase.

## B16 · Identity, ledger and revocation

Use [B16 startup](../../experiments/B16-cardano-did-authentication/README.md) and the [registry procedure](registry-procedure.md). Collect local identity and policy test output first. Stage the AS183 and AS184 role directories with the B16 helper after verifying the live registry. Enter the two namespaces in separate terminals and collect the gateway ready line and candidate response. Check the AS185 TCP/3001 denial before and after admission with `docker exec b16-as185h-DID-Attacker-10.185.0.71 nc -z -w 3 10.183.0.71 3001`. Record AS183 rule counters and continue with the legitimate candidate separately. Test the enrolled candidate and compare authentication, current registry eligibility, firewall state and reachability. Collect private TCP/4040 endpoint metadata separately from TCP/3001 admission and revocation captures. Pass the integrated run only if the legitimate candidate passes the expected gates, the firewall follows the verified registry transition, new connections fail after revocation and legitimate peers remain connected. Missing root namespace access, Docker access, cryptography under the selected interpreter or the live deployment inputs blocks the corresponding phase. The historical impersonation, replay and substitution observations do not satisfy fresh validation.

## Cleanup for every experiment

Stop foreground observers and gateway processes. For B14 restore the phase rules using the exact inverse commands in its README if the admitted phase was left active. For B16 use `python3 scripts/b16_n15_firewall_controller.py revoke` from `network/` if the authorized test gateway applied candidate ACCEPT rules and the run needs rollback. From the experiment's `output/` directory, run `docker-compose stop` and record `docker-compose ps`. Keep the database, evidence and local credentials protected. Stopping the isolated experiment preserves its state for audit.
