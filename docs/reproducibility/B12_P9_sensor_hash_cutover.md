# Resume preserved B12-P9 for the sensor hash demo

**Preparation only.** This procedure uses the existing Ubuntu VM, the saved B12-P9 ledger on magic 4343, and the new measurement validator. B12-4242 currently occupies the shared Docker names, bridges and published TCP/5000. Use the original Compose project and bind mounts for each network. The approved Phase 6B switch ran in the other direction. [Historical recovery and P9 preservation](B12_4242_recovery_verification.md) · [Original sequential deployment](B12_P9_sequential_recovery.md)

This operator-only runbook requires private backups and bind directories. Set each placeholder to the verified path from the custodian inventory. Run the following on the regular Ubuntu terminal only after cutover approval. Keep the shell and evidence directory private. Approve any later funding and spending submissions separately. A normal node restart naturally resumes writes to its own ledger. The procedure uses the original bind directories and makes no manual database changes.

## Read-only preflight

All four B12-4242 nodes reported protocol 2.0 and shared block 1884 in the preflight sample. Each sampled chain retained all 33 historical transaction IDs at their recorded block hashes. P9 has no project containers or networks on the daemon. All recorded image tags for both projects resolved to their saved IDs. The P9 backup checksums passed, and a numeric-owner comparison matched the stopped bind directories. Exact-byte verification found the previous Plutus spend on all four saved P9 chains. The measurement fixture and compiled artifacts also verified. Compose is 1.27.4 and the shared filesystem had 28 GiB available at sampling. Recheck these gates immediately before the approved switch.

## 1. Confirm identities and preserve the running history

```bash
set -euo pipefail
umask 077
repo=/path/to/b12-reproduction
cd "$repo"
old=/path/to/preserved-b12-4242
oldroot="$old/experiments/B12-cardano"
p9=/path/to/preserved-b12-p9
saved_old=/path/to/private/b12-4242-backup
saved_p9=/path/to/private/b12-p9-backup
preservation=/path/to/private/b12-4242-preservation
historic_engine="$preservation/live-inventory/docker-engine-id.txt"
old_db="$old/runtime/cardano-data/testnet-conway-113-v2"
p9_db="$p9/.runtime/cardano-data/testnet-conway-113-v2"
old_evidence="$old/runtime/evidence/phase-5d/protocol-compatibility"
auth="$p9/.runtime/evidence/phase-5d-p9/authorized-run"
out=$(mktemp -d /path/to/private/cutover.XXXXXXXX)
unset DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME
export DOCKER_HOST=unix:///var/run/docker.sock
old_dc() { docker-compose -p b12-reproduction --project-directory "$oldroot/output" -f "$oldroot/output/docker-compose.yml" "$@"; }
p9_dc() { docker-compose -p b12-p9 --project-directory "$p9/output" -f "$p9/output/docker-compose.yml" "$@"; }
peer() {
  local id
  id=$(docker ps -q --filter "label=com.docker.compose.project=$1" --filter "label=com.docker.compose.service=hnode_${2}_host_0") || return
  test "$(wc -w <<< "$id")" -eq 1 || return
  printf '%s\n' "$id"
}
query() {
  local id=$1 magic=$2
  shift 2
  timeout 25 docker exec "$id" cardano-cli conway query "$@" --testnet-magic "$magic" --socket-path /cardano/node.socket
}
check_images() {
  local tag want
  while read -r tag want; do
    test "$(docker image inspect --format '{{.Id}}' "$tag")" = "$want" || return
  done < "$1"
}
test "$(docker info --format '{{.ID}}')" = "$(cat "$historic_engine")"
df -h "$repo" "$old" /var/lib/docker
test "$(date -u +%s)" -lt "$(date -ud '2027-02-17 18:09:33Z' +%s)"
test "$(date -u +%s)" -lt "$(date -ud '2027-02-17 23:27:33Z' +%s)"
(cd "$saved_old" && sha256sum -c pre-stop.sha256 && sha256sum -c quiescent.sha256)
(cd "$saved_p9" && sha256sum -c p9.sha256)
(cd "$preservation" && sha256sum -c --quiet SHA256SUMS)
test -z "$(docker ps -aq --filter label=com.docker.compose.project=b12-p9)"
test -z "$(docker network ls -q --filter label=com.docker.compose.project=b12-p9)"
sudo tar --numeric-owner --compare -f "$saved_p9/p9-runtime-quiescent.tar" -C "$p9"
check_images "$saved_old/image-ids.txt"
check_images "$saved_p9/p9-image-ids.txt"
old_dc config > "$out/old-normalized.yml"
p9_dc config > "$out/p9-normalized.yml"
cmp "$out/old-normalized.yml" "$saved_old/compose-normalized.yml"
cmp "$out/p9-normalized.yml" "$saved_p9/p9-normalized.yml"

mkdir "$out/old-live"
for asn in 150 151 152 153; do
  id=$(peer b12-reproduction "$asn")
  query "$id" 4242 tip > "$out/old-live/as$asn-tip.json"
  query "$id" 4242 protocol-parameters | jq -e '.protocolVersion=={major:2,minor:0}'
  docker exec "$id" sh -c 'sha256sum /cardano/*-genesis.json /cardano/config.json' \
    > "$out/old-live/as$asn-genesis.sha256"
  cmp "$out/old-live/as$asn-genesis.sha256" "$saved_old/pre-stop-live/as$asn-genesis-config.sha256"
  test "$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/cardano/db"}}{{.Type}}:{{.Source}}{{end}}{{end}}' "$id")" = "bind:$old_db/as$asn"
  if [[ $asn != 153 ]]; then
    query "$id" 4242 kes-period-info --op-cert-file /cardano/producer/opcert.cert > "$out/old-live/as$asn-kes.txt" 2>&1
  fi
done
python3 experiments/B12-P9/verify-b12-history.py --db-root "$old_db" \
  --tips "$out/old-live" --anchors "$old_evidence/history-anchors.json" > "$out/old-live/history.json"
jq -e 'length==4 and all(.[]; .verified_transactions==33)' "$out/old-live/history.json"
```

Review exact image IDs and mounts, agreement of all 33 historical anchors, KES counters and remaining validity on all three producers, and P9's archived expiry. The VM also hosts unrelated stopped containers. Keep their project labels, images and networks intact. For both projects, archive or verify any required writable-layer changes before container recreation, particularly credentials and logs. Use the saved image/context archives as the starting recovery material and preserve changed required files privately. Resolve a missing or inconsistent image, archive, config, certificate or database before stopping anything. An old saved tip is a reference point. Sample fresh tips just before shutdown.

## 2. Controlled B12-4242 shutdown and scoped Docker release

Pause submissions and captures. Reuse the shutdown pattern from the [recovery runbook](B12_4242_recovery_verification.md#2-preserve-p9-then-release-its-resources) below with the historical project labels. The node processes need SIGTERM before their wrappers stop.

```bash
mkdir "$out/old-shutdown"
ids=()
for asn in 150 151 152 153; do
  id=$(peer b12-reproduction "$asn")
  query "$id" 4242 tip > "$out/old-shutdown/as$asn-final-tip.json"
  docker exec "$id" sh -ec 'set -- $(pgrep -x cardano-node); test "$#" -eq 1'
  ids+=("$id")
done
mapfile -t old_ids < <(docker ps -aq --no-trunc --filter label=com.docker.compose.project=b12-reproduction)
docker inspect "${old_ids[@]}" > "$out/old-containers.json"
old_dc config --services | sort > "$out/old-expected-services"
jq -r '.[].Config.Labels["com.docker.compose.service"]' "$out/old-containers.json" | sort > "$out/old-actual-services"
cmp "$out/old-expected-services" "$out/old-actual-services"
for id in "${ids[@]}"; do
  docker exec "$id" sh -ec 'set -- $(pgrep -x cardano-node); test "$#" -eq 1; kill -TERM "$1"'
done
for index in "${!ids[@]}"; do
  id=${ids[index]}
  asn=$((150 + index))
  timeout 120 docker exec "$id" sh -ec 'while pgrep -x cardano-node >/dev/null; do sleep 1; done; test -f /cardano/db/clean'
  docker cp "$id:/var/log/cardano-node.log" "$out/old-shutdown/as$asn-node.log"
  docker logs "$id" > "$out/old-shutdown/as$asn-docker.log" 2>&1
  grep -aF 'Closed db' "$out/old-shutdown/as$asn-node.log" >/dev/null
done
old_dc stop -t 120
test -z "$(docker ps -q --filter label=com.docker.compose.project=b12-reproduction)"
sudo tar --numeric-owner --acls --xattrs -C "$old/runtime" -cpf - cardano-data captures evidence > "$out/b12-4242-runtime.tar"
sudo tar --numeric-owner --compare -C "$old/runtime" -f "$out/b12-4242-runtime.tar"
(cd "$out" && sha256sum b12-4242-runtime.tar > b12-4242-runtime.sha256 && sha256sum -c b12-4242-runtime.sha256)
```

Require all four clean closes and the new quiescent archive comparison and digest before removing any wrappers. Archive any needed mutable container-layer artifacts separately. The previous backups of original images and generated contexts remain private. Verify Compose-owned networks and foreign endpoints before releasing the shared names.

```bash
mapfile -t old_nets < <(docker network ls -q --filter label=com.docker.compose.project=b12-reproduction)
test "${#old_nets[@]}" -gt 0
docker network inspect "${old_nets[@]}" > "$out/old-networks.json"
jq -e --slurpfile owners "$out/old-containers.json" '
  ($owners[0] | map(.Id)) as $ids |
  all(.[]; .Labels["com.docker.compose.project"]=="b12-reproduction" and
    all((.Containers // {} | keys[]); . as $id | ($ids | index($id)) != null))
' "$out/old-networks.json"
test "$(docker ps -aq --no-trunc --filter label=com.docker.compose.project=b12-reproduction | sort)" = "$(jq -r '.[].Id' "$out/old-containers.json" | sort)"
old_dc down -t 120
test -z "$(docker ps -aq --filter label=com.docker.compose.project=b12-reproduction)"
test -z "$(docker network ls -q --filter label=com.docker.compose.project=b12-reproduction)"
python3 experiments/B12-P9/check-isolation.py --sequential --historical-engine-id "$historic_engine" \
  --historical-runtime "$old/runtime" --compose "$out/p9-normalized.yml" --runtime "$p9/.runtime"
```

Use only this named Compose project for teardown. The guard checks remaining fixed names, bridge allocations, ports and planned binds. Abort on a conflict. No volume or image removal flags, orphan cleanup, or prune.

## 3. Resume preserved B12-P9 and prove continuity

```bash
check_images "$saved_p9/p9-image-ids.txt"
for asn in 150 151 152 153; do
  test -s "$p9_db/as$asn/protocolMagicId"
  test -d "$p9_db/as$asn/volatile"
done
p9_dc up -d --no-build
p9_dc ps
# After startup, verify the four sockets and give the preserved chain time to advance.
helper="$repo/experiments/B12-P9/verify_plutus.py"
python3 "$helper" inspect --project b12-p9 > "$out/p9-live.json"
jq -e '.parameters.protocolVersion=={major:9,minor:0} and (.parameters.costModels.PlutusV3|length)==251' "$out/p9-live.json"
for asn in 150 151 152 153; do
  id=$(peer b12-p9 "$asn")
  test "$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/cardano/db"}}{{.Type}}:{{.Source}}{{end}}{{end}}' "$id")" = "bind:$p9_db/as$asn"
  docker exec "$id" sh -c 'sha256sum /cardano/*-genesis.json /cardano/config.json' > "$out/p9-as$asn-genesis.sha256"
  cmp "$out/p9-as$asn-genesis.sha256" "$saved_p9/p9-final/as$asn-genesis-config.sha256"
  docker exec "$id" ss -Hlnt 'sport = :3001' | grep .
  docker exec "$id" ss -Hnt state established '( sport = :3001 or dport = :3001 )' | grep .
  if [[ $asn != 153 ]]; then
    query "$id" 4343 kes-period-info --op-cert-file /cardano/producer/opcert.cert > "$out/p9-as$asn-kes.txt" 2>&1
  fi
done
for round in 1 2 3; do
  for asn in 150 151 152 153; do
    query "$(peer b12-p9 "$asn")" 4343 tip > "$out/p9-round-$round-as$asn.json"
  done
  if [[ $round != 3 ]]; then sleep 60; fi
done
PYTHONPATH="$repo/experiments/B12-cardano" python3 - "$p9_db" "$auth" "$out" <<'PY'
import json
import sys
from pathlib import Path

from block_proof import canonical_transaction, envelope_body

database, archive, out = map(Path, sys.argv[1:])
anchor = "49cb569d947821b99c3d4dca8bb27b4f1cd9cf420008f4c3f5bee3ac8c88be67"
expected_hash = "5c07462ee283923fdcabea1e25958eb68394d3cb35ba6956b4d388e19b8e0538"
expected_body = envelope_body(archive / "spend.signed")
proofs = {}
for asn in range(150, 154):
    points = [json.loads((out / f"p9-round-{r}-as{asn}.json").read_text()) for r in (1, 2, 3)]
    assert all(t["era"] == "Conway" for t in points)
    assert points[-1]["block"] > max(1572, points[0]["block"]), (asn, points)
    _, body, _, block, proof = canonical_transaction(database / f"as{asn}", points[-1], anchor, 81)
    assert proof["block"] == 81 and proof["slot"] == 2039 and proof["block_hash"] == expected_hash
    assert body == expected_body and block == (archive / "spend-containing-block.cbor").read_bytes()
    proofs[asn] = proof
assert all(proof == proofs[150] for proof in proofs.values())
(out / "p9-archived-spend-recheck.json").write_text(json.dumps(proofs, indent=2) + "\n")
PY
```

Require at least one agreed post-resume numbered block across all four peers. Compare sampled hashes at the same height. If rounds catch different tip heights, sample again or verify a common post-resume ancestor by ChainDB or ChainSync. Matching the archived spend block establishes retained history. It is a separate check from current synchronization. Review producer KES counters, Node 11.1.3, CLI 11.2.3.0, and startup logs. The predeploy isolation guard is for the stopped state. The running checks above are deliberately scoped to P9 so the unrelated stopped projects may remain.

If P9 fails before starting, retain its binds and bring B12-4242 back with `old_dc up -d --no-build` only after confirming shared resources are free. If P9 partially starts, preserve diagnostics, gracefully stop its nodes and confirm ownership before project-scoped release, then verify the newly archived B12-4242 binds and image IDs before restoring. If shutdown failed before `down`, the old wrappers are still available. Diagnose the partial shutdown and use the recovery runbook's retained-container path. Never replace an original DB with an empty bind or manually restore over a live DB.

## 4. Prepare the unsigned measurement funding body

Use the commands below to compile and build against the preserved P9 network. They replace the fresh-deployment setup in the [measurement runbook](B12_sensor_hash_smart_contract_demo.md). The original Aiken source and script identity remain unchanged.

```bash
root="$out"
evidence="$out"
project=b12-p9
magic=4343
db_root="$p9_db"
keys="$p9/config/generated/testnet-conway-v2/stake-delegators"
cli="$repo/resources/cardano/11.1.3/bin/cardano-cli"
export PYTHONPATH="$repo/experiments/B12-cardano"
# Shared runbook uses a peer function taking only ASN and remote for CLI queries.
# Use distinct names for the two-argument cutover peer lookup and the demo wrapper.
p9_peer() { peer b12-p9 "$1"; }
remote() {
  local id
  id=$(p9_peer "$1") || return
  shift
  timeout 90 docker exec "$id" cardano-cli conway "$@" --testnet-magic 4343 --socket-path /cardano/node.socket
}
fixtures="$out/hash-fixtures"
python3 experiments/B12-P9/generate_sensor_hash_fixtures.py "$fixtures"
python3 experiments/B12-P9/generate_sensor_hash_fixtures.py "$fixtures" --verify
script="$out/sensor_hash_validation.plutus"
(
 cd "$repo/experiments/B12-cardano/smart-contract/sensor-validation"
 aiken --version
 aiken check
 aiken build
 aiken blueprint convert -m sensor_hash_validation -v sensor_hash_validation > "$script"
)
script_hash=$("$cli" conway transaction policyid --script-file "$script")
test "$script_hash" = f7b1435250172148a3c6c2fc5eccf212062d314cd11744018af5fa29
payout=$("$cli" address build --payment-verification-key-file "$keys/delegator1/payment.vkey" \
  --stake-verification-key-file "$keys/delegator1/staking.vkey" --testnet-magic 4343)
remote 150 query utxo --address "$payout" > "$out/p9-current-funding-utxos.json"
funding_input=$(jq -er 'to_entries | map(select((.value.value|keys)==["lovelace"] and .value.value.lovelace>6000000)) |
  max_by(.value.value.lovelace).key' "$out/p9-current-funding-utxos.json")
python3 "$helper" funding --project "$project" --cli "$cli" --script "$script" \
  --input "$funding_input" --payout "$payout" --script-hash "$script_hash" \
  --datum-file "$fixtures/datum.json" --output "$out/hash-funding"
"$cli" conway transaction txid --tx-body-file "$out/hash-funding/tx.body" > "$out/hash-funding/txid.json"
```

**Stop at the unsigned funding body.** Review the 5 ADA output, exact inline datum, change, fee, validity and transaction ID. Request separate authorization for funding submission. Build the live spend and local negative evaluations after the new 5 ADA script output is confirmed. The [measurement runbook](B12_sensor_hash_smart_contract_demo.md) gives the valid redeemer, wrong-ID, temperature and humidity cases and the four-node exact-body verification. In that runbook, use `p9_peer 150` for the AS150 lookup inside `submit_exact`. The prebuilt offline fixtures establish the expected behavior without touching either ledger. Keep the new spend unsigned until it has been reviewed and obtain separate approval before submitting it.

## Approved execution on 2026-11-20

- **B12-4242 preserved.** The last shared sample was block 1920, slot 71736, hash `caad1671e3961fc5a038c222083c423d52e8b03ed38b840863feb8a1eb6f4944`. All 33 historical transactions verified on each chain before shutdown and in the quiescent stores. The new runtime archive matched the stopped bind directories and passed SHA-256 verification. The shutdown script initially paused on the wording of the AS150 log. All four nodes had exited with fresh clean markers and immutable-store close logs before wrapper stop. Only the verified B12-4242 Compose containers and networks were released.
- **P9 restored.** All four nodes resumed the original magic-4343 genesis, bind mounts, and images, with protocol 9.0 and 251 Plutus V3 cost-model entries. All four agreed in three consecutive samples at blocks 1574, 1576 and 1578. The final shared block was slot 53439, hash `f45ed4f82420542721460b0ae1b3603d1fe8f61f4e81b16d50c93a52503bc025`. Exact-byte replay found the previous Plutus V3 spend in block 81 on all four resumed chains.
- **Validator and fixture verified.** The new script hash is `f7b1435250172148a3c6c2fc5eccf212062d314cd11744018af5fa29`. Recompilation reproduced the original sensor-ID script hash. The inline datum contains `AGRI-002` and commitment `b76cef7674424ef76659031a5cf22f1d9b38316c2fe1e71cdbd12c75fc30ac26`.
- **Unsigned funding body prepared.** Transaction ID `cec962433d2049aa7ab1fd16493dc498a1116ef480d4aab7fa424441ac0f7510` funds exactly 5 ADA and pays a fee of 428 lovelace. The sole input is Delegator 3's `ecbc3290431a531e0c283b18d461864867b24522eff4a5a550c0c1d5d42fd153#0`. Delegator 3 was selected to preserve outputs from the previous demo. Its change is 89,994,999,572 lovelace. Delegator 2's `ba3d3b873fe788f38fd995f83ddbf4dd5c3ba7bbab9dd5bdff369057f73373ab#0` is planned collateral for a later spend. All four nodes still showed the previous demo's unspent outputs. A helper-path error stopped the initial build before it created a body. The corrected unsigned-only run passed.
- The body has lower validity slot 53519 and exclusive upper slot 60719. Before any authorized signing, recheck the current slot and funding input. An expired body requires a new build and approval of its new transaction ID. No signing, submission, or live spending preparation was performed.

[Sanitized evidence](../results/b12/sensor-hash-verification.json) · Unsigned body (private archive) · Funding details (private archive)

## Separately approved funding submission

The exact previously reviewed body was revalidated, signed with Delegator 3, and submitted once on magic 4343. Transaction `cec962433d2049aa7ab1fd16493dc498a1116ef480d4aab7fa424441ac0f7510` was verified on the canonical chain of all four nodes at block 1593, slot 53852, hash `0d87e06082269ae47f00e9be00850c3d340a60f6a3aad07bd5e0f860ea8bae57`. All four observed the consumed wallet input, the 5 ADA script output at index 0 with the expected inline datum, the expected change, and the unchanged planned collateral. Verification used the exact signed transaction body and identical containing block bytes. The signed envelope remains private. No new spending transaction was prepared, signed or submitted. [Sanitized evidence](../results/b12/sensor-hash-verification.json)

## Separately approved unsigned spend and local evaluation

On 2026-11-20 at 14:42:48 UTC, all four nodes still reported the 5 ADA input with the exact funded datum and the planned, unspent collateral. The original validator source and script hash verified. The matching canonical AGRI-002 measurement passed the live-parameter calculation with 41,108 memory units and 15,289,580 CPU steps. Script execution cost was 3,475 lovelace. The balanced unsigned body pays 4,417 lovelace total and returns 4,995,583 lovelace to Delegator 3, with no separate change output. Its ID is `b944855580f84b08a03bda144bac657fc263658d07fa4ff090c0ea4d7f374181`, valid from slot 54901 until the exclusive upper bound 62101. Revalidate validity and both inputs before any separately approved signing.

The offline CLI evaluated unsigned controls against the real funded datum and the saved live UTXOs, protocol parameters and era history. The matching control reproduced the live budget. Changed temperature, changed humidity, wrong sensor ID and malformed redeemer all failed inside the original sensor-hash script witness. The first two changed only the measurement bytes and its digest, the third retained the committed measurement and changed the claimed ID, and the fourth failed decoding the constructor. The funded script UTXO and collateral were identical before and after evaluation on all four nodes. Nothing was signed or submitted. Unsigned body (private archive) · Evaluation checksums (private archive)

## Separately approved sensor-hash spend

The exact reviewed spend `b944855580f84b08a03bda144bac657fc263658d07fa4ff090c0ea4d7f374181` was signed with Delegator 2's collateral witness and submitted once. All four nodes verified its valid inclusion in block 1661, slot 55199, hash `5463a2ca3de45ad228faa92ebab92f23472e472f6b65f776e1c73b53eaea4115`. They observed consumption of the 5 ADA script input, the expected 4,995,583 lovelace payout, and the unchanged collateral UTXO. The on-chain Plutus V3 witness matched the new validator hash, exact AGRI-002 measurement and committed SHA-256. It recorded 41,108 memory units and 15,289,580 CPU steps, with a total fee of 4,417 lovelace. The negative cases remained local. [Sanitized inclusion and witness evidence](../results/b12/sensor-hash-verification.json)
