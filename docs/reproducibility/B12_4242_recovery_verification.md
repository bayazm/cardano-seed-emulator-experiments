# B12-4242 historical blockchain recovery verification

**Runbook and execution record.** The deployments share Docker names, subnets and a published port. The procedure preserves B12-P9 before releasing those resources and starts B12-4242 from its original images and database binds. Any future cutover requires explicit approval.

## Read-only findings

| Item | Evidence |
| --- | --- |
| B12-P9 before cutover | Project `b12-p9`, 37 running containers observed. Compose at `.local-research/b12-p9-sequential-live/output/docker-compose.yml`. The four running Cardano containers are `as150h-Cardano-Node-1-10.150.0.71`, `as151h-Cardano-Node-2-10.151.0.71`, `as152h-Cardano-Node-3-10.152.0.71`, and `as153h-Cardano-Node-4-10.153.0.71`. Their `/cardano/db` binds are `.runtime/cardano-data/testnet-conway-113-v2/as150` through `as153` relative to the P9 run. All four also bind `.runtime/captures`. |
| P9 recovery material | The generated genesis and credentials are under `config/generated/testnet-conway-v2`. The producer contexts and images carry `/cardano/producer/{kes.skey,vrf.skey,opcert.cert}`. Wallet and producer material, generated contexts, images and signed transaction artifacts are private. Runtime evidence is under `.runtime/evidence`, including `phase-5d-p9/authorized-run`. |
| P9 script history | Rechecked both archived block byte sequences and their digests in all four current DBs. Funding is block 59, slot 1632, hash `a8028908af3fb3e040a74a6b03dbcc5dc320e198a796ceac8cd650e22c36d6f2`, transaction `eefca428cdb9f9a26a5cd6ba534b3dba44cada282fda91c552b3d0160cd119e8`. The valid spend is block 81, slot 2039, hash `5c07462ee283923fdcabea1e25958eb68394d3cb35ba6956b4d388e19b8e0538`, transaction `49cb569d947821b99c3d4dca8bb27b4f1cd9cf420008f4c3f5bee3ac8c88be67`. The latest live tips are to be recorded immediately before cutover. |
| Historical B12-4242 | Original project `b12-reproduction`. Compose and generated config remain in `original-b12-run/experiments/B12-cardano`. Original DBs remain in `original-b12-run/runtime/cardano-data/testnet-conway-113-v2/as150` through `as153`. All four agreed before shutdown at block 924, slot 18774, hash `c8ea3a746e9eafb138d6a8a438efe715514b3b35dbc6f8b38c5ea1fbe2656391`. The offline audit verified 33 transactions from each of those tips. |
| Historical backups | All 39 local image references match saved IDs, including shared tags. The original Compose matches the saved copy. The four host genesis hashes, both cutover checksums, and the separate public preservation manifest passed. The quiescent DB archive matched the original binds with numeric ownership checked outside the sandbox. A sandbox-only comparison had reported remapped root-owned files as UID/GID 65534. Saved contexts and producer images preserve the original credential material. Previous live checks verified the three public operational certificates matched their source and counters. |
| Resource conflicts | The two deployments share fixed names, including the four Cardano names above, static bridge allocations, and EtherView host TCP/5000. Cardano TCP/3001 is internal. The snapshot had 31 GiB available on the repository and Docker filesystem. Recheck the actual destinations and allow space for an independent P9 image archive, contexts, quiescent DB, and logs. |

[Evidence index](B12_evidence_index.md) · [Prior cutover procedure and ownership inventory](B12_P9_sequential_recovery.md) · [P9 genesis manifest](../results/b12/artifact-manifest.md#e001) · [Historical DB recheck](../results/b12/artifact-manifest.md#e002)

## KES and recovery limits

Historical genesis was **2026-11-19 18:09:33 UTC**. The preparation clock was about **2026-11-20 07:59 UTC**, roughly 13 hours 49 minutes after genesis and 8 hours 34 minutes after Compose stop. With one-second slots, 129,600 slots per KES period and certificates starting at period 0, this was still wall-clock period **0**. All three saved producer queries show counter 0 matching ledger state and an exclusive end at period 60, **2027-02-17 18:09:33 UTC**. Time spent stopped still counts. P9 uses the same period length and evolution count, with genesis **2026-11-19 23:27:33 UTC**. Query its actual certificates and counters before shutdown to establish its rollback deadline. Check both deadlines and the VM clock again immediately before the switch. If validity or counters fail, abort and leave credential remediation for separate review.

The original node binary and configuration must resume Conway protocol **2.0** on magic **4242**. P9 rollback must resume Conway **9.0** on **4343**. Expect a wall-clock slot gap after a planned outage. Define success as retained history plus new block production across four nodes. A running wrapper, socket availability or an old readable tip on its own is insufficient.

## Approved execution only

Run these sections in one Bash session on the regular Ubuntu terminal. Keep the transcript and backups owner-only. Stop at any command failure or unexpected result. Pause transaction and capture jobs and exclude other Docker operators during the window.

### 1. Pin deployment identity and record P9 state

```bash
set -euo pipefail
umask 077
repo=/path/to/b12-reproduction
old=/path/to/original-b12-run
oldroot="$old/experiments/B12-cardano"
archive=/path/to/private/research-archive
saved="$archive/b12-4242-cutover-backup"
p9=/path/to/p9-run
old_db="$old/runtime/cardano-data/testnet-conway-113-v2"
p9_db="$p9/.runtime/cardano-data/testnet-conway-113-v2"
auth="$p9/.runtime/evidence/phase-5d-p9/authorized-run"
evidence="$old/runtime/evidence/phase-5d/protocol-compatibility"
out=$(mktemp -d "$archive/b12-recovery.XXXXXXXX")
unset DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME
export DOCKER_HOST=unix:///var/run/docker.sock
test "$(docker info --format '{{.ID}}')" = "$(cat "$archive/b12-4242-preservation/live-inventory/docker-engine-id.txt")"
cd "$repo"
old_compose() { docker-compose -p b12-reproduction --project-directory "$oldroot/output" -f "$oldroot/output/docker-compose.yml" "$@"; }
p9_compose() { docker-compose -p b12-p9 --project-directory "$p9/output" -f "$p9/output/docker-compose.yml" "$@"; }
check_images() {
  while read -r tag expected; do
    test "$(docker image inspect --format '{{.Id}}' "$tag")" = "$expected" || return 1
  done < "$1"
}
node_id() {
  local id
  id=$(docker ps -q --filter "label=com.docker.compose.project=$1" --filter "label=com.docker.compose.service=hnode_${2}_host_0")
  test "$(wc -w <<< "$id")" -eq 1 || return 1
  printf '%s\n' "$id"
}
query() {
  local id=$1 magic=$2
  shift 2
  timeout 25 docker exec "$id" cardano-cli conway query "$@" --testnet-magic "$magic" --socket-path /cardano/node.socket
}
sample() {
  local project=$1 magic=$2 dir=$3 asn id
  mkdir -p "$dir"
  date -u +%FT%TZ > "$dir/sample.utc"
  for asn in 150 151 152 153; do
    id=$(node_id "$project" "$asn") || return 1
    query "$id" "$magic" tip > "$dir/as$asn-tip.json" || return 1
  done
}
(cd "$saved" && sha256sum -c pre-stop.sha256 && sha256sum -c quiescent.sha256)
(cd "$archive/b12-4242-preservation" && sha256sum -c --quiet SHA256SUMS)
# Recorded paths in this manifest refer to the original workspace.
# Use each filename within the operator-supplied genesis directory.
genesis_dir="$oldroot/config/generated/testnet-conway-v2"
while read -r expected original; do
  printf '%s  %s\n' "$expected" "$genesis_dir/${original##*/}" | sha256sum -c -
done < "$evidence/host-genesis.sha256"
cmp "$oldroot/output/docker-compose.yml" "$saved/docker-compose.yml"
sudo tar --numeric-owner --compare -f "$saved/cardano-data-quiescent.tar" -C "$old/runtime/cardano-data"
check_images "$saved/image-ids.txt"
old_compose config > "$out/old-normalized.yml"
cmp "$out/old-normalized.yml" "$saved/compose-normalized.yml"
p9_compose config > "$out/p9-normalized.yml"
test -z "$(docker ps -aq --filter label=com.docker.compose.project=b12-reproduction)"
test -z "$(docker network ls -q --filter label=com.docker.compose.project=b12-reproduction)"
mapfile -t p9_containers < <(docker ps -aq --filter label=com.docker.compose.project=b12-p9)
printf '%s\n' "${p9_containers[@]}" > "$out/p9-container-ids.txt"
docker inspect "${p9_containers[@]}" > "$out/p9-containers.json"
jq -r '.[] | [.Config.Image,.Image] | @tsv' "$out/p9-containers.json" | sort -u > "$out/p9-image-ids.txt"
check_images "$out/p9-image-ids.txt"
sample b12-p9 4343 "$out/p9-final"
for asn in 150 151 152 153; do
  id=$(node_id b12-p9 "$asn")
  docker exec "$id" sh -c 'sha256sum /cardano/*-genesis.json /cardano/config.json' > "$out/p9-final/as$asn-genesis-config.sha256"
  query "$id" 4343 protocol-parameters > "$out/p9-final/as$asn-parameters.json"
  jq -e '.protocolVersion == {major:9,minor:0}' "$out/p9-final/as$asn-parameters.json"
  docker diff "$id" > "$out/p9-final/as$asn-writable-layer.txt"
  if [[ $asn != 153 ]]; then
    docker exec "$id" test -s /cardano/producer/kes.skey
    docker exec "$id" test -s /cardano/producer/vrf.skey
    docker exec "$id" sha256sum /cardano/producer/opcert.cert > "$out/p9-final/as$asn-opcert.sha256"
    query "$id" 4343 kes-period-info --op-cert-file /cardano/producer/opcert.cert > "$out/p9-final/as$asn-kes.txt" 2>&1
  fi
done
```

Review the actual container and mount inventory against both normalized Compose files. Require the expected service labels, only known bind mounts, exact per-node DB paths (including resolved paths), and no overlap between roots. Review writable-layer changes across the entire project and preserve any required runtime-only changes before removal. Match P9 genesis and configuration against its genesis manifest and compare the live public opcert digests with the corresponding generated producer files. Review Docker storage and host listeners, including TCP/5000. Check that every non-socket bind source is covered by the planned context or runtime archive. Preserve any additional sources before continuing. Authorize no image replacement as part of this plan.

### 2. Preserve P9, then release its resources

Save a private rollback copy before stopping P9. Record the current Docker network IDs and inspect all endpoints. Archive all application bind data, original P9 config, contexts and exact images. The Docker socket is an engine endpoint and is excluded from filesystem backup.

```bash
inspect_networks() {
  local project=$1 dest=$2
  local -a ids
  mapfile -t ids < <(docker network ls -q --filter "label=com.docker.compose.project=$project")
  test "${#ids[@]}" -gt 0 || return 1
  docker network inspect "${ids[@]}" > "$dest"
}
inspect_networks b12-p9 "$out/p9-networks.json"
jq -e --slurpfile owners "$out/p9-containers.json" '
  ($owners[0] | map(.Id)) as $ids |
  all(.[]; .Labels["com.docker.compose.project"]=="b12-p9" and
    all((.Containers // {} | keys[]); . as $id | ($ids | index($id)) != null))
' "$out/p9-networks.json"
mapfile -t p9_images < <(awk '{print $1}' "$out/p9-image-ids.txt")
docker image save "${p9_images[@]}" | gzip -1 > "$out/p9-images.tar.gz"
gzip -t "$out/p9-images.tar.gz"
tar --acls --xattrs -C "$p9" -cpf "$out/p9-context.tar" config output b12-p9-genesis-manifest.json

graceful_nodes() {
  local project=$1 dest=$2 asn id worker failed=0
  local -a workers=()
  mkdir -p "$dest" || return 1
  for asn in 150 151 152 153; do
    id=$(node_id "$project" "$asn") || return 1
    docker exec "$id" sh -ec 'set -- $(pgrep -x cardano-node); test "$#" -eq 1' || return 1
    printf '%s\n' "$id" > "$dest/as$asn-container.txt"
  done
  for asn in 150 151 152 153; do
    (
      id=$(cat "$dest/as$asn-container.txt")
      docker exec "$id" sh -ec 'set -- $(pgrep -x cardano-node); test "$#" -eq 1; kill -TERM "$1"' || exit 1
      timeout 120 docker exec "$id" sh -ec '
        while pgrep -x cardano-node >/dev/null; do sleep 1; done
        test -f /cardano/db/clean
      ' || exit 1
      docker cp "$id:/var/log/cardano-node.log" "$dest/as$asn-cardano-node.log" || exit 1
      docker logs "$id" > "$dest/as$asn-docker.log" 2>&1
    ) &
    workers+=("$!")
  done
  for worker in "${workers[@]}"; do wait "$worker" || failed=1; done
  return "$failed"
}
graceful_nodes b12-p9 "$out/p9-shutdown"
```

Review all four node shutdown logs and clean markers before stopping the wrappers. A failed signal, missing log, or timeout leaves the containers in place for diagnosis. A direct node SIGTERM is necessary because the original startup wrapper backgrounds Cardano.

```bash
p9_compose stop -t 120
test -z "$(docker ps -q --filter label=com.docker.compose.project=b12-p9)"
date -u +%FT%TZ > "$out/p9-stopped.utc"
sudo tar --acls --xattrs --numeric-owner -cpf - -C "$p9" .runtime > "$out/p9-runtime-quiescent.tar"
sudo tar --numeric-owner --compare -f "$out/p9-runtime-quiescent.tar" -C "$p9"
(cd "$out" && sha256sum p9-{images.tar.gz,context.tar,runtime-quiescent.tar,image-ids.txt,normalized.yml} > p9.sha256 && sha256sum -c p9.sha256)
inspect_networks b12-p9 "$out/p9-networks-before-down.json"
jq -e --slurpfile owners "$out/p9-containers.json" '
  ($owners[0] | map(.Id)) as $ids |
  all(.[]; .Labels["com.docker.compose.project"]=="b12-p9" and
    all((.Containers // {} | keys[]); . as $id | ($ids | index($id)) != null))
' "$out/p9-networks-before-down.json"
test "$(docker ps -aq --no-trunc --filter label=com.docker.compose.project=b12-p9 | sort)" = "$(jq -r '.[].Id' "$out/p9-containers.json" | sort)"
p9_compose down -t 120
test -z "$(docker ps -aq --filter label=com.docker.compose.project=b12-p9)"
test -z "$(docker network ls -q --filter label=com.docker.compose.project=b12-p9)"
```

Reinspect the daemon's container names and network subnets, host TCP/5000, and all bind sources. Require the historical resources to be free. If other owners or overlapping subnets are found, stop. Compose `down` removes its containers, writable layers and managed networks. Use no volume or image removal flags. [Docker Compose down](https://docs.docker.com/reference/cli/docker/compose/down/)

### 3. Resume the original chain and verify it

```bash
check_images "$saved/image-ids.txt"
for asn in 150 151 152 153; do
  test -s "$old_db/as$asn/protocolMagicId"
  test -d "$old_db/as$asn/volatile"
done
old_compose up -d --no-build
old_compose ps
```

Wait for the four sockets, inspect startup logs, and check the running images, process arguments and actual binds against the saved inventory. If an image is missing or changed, abort the normal path. The verified image archive supports a separate recovery after reviewing tag ownership. If a DB is damaged, retain it and rehearse extraction only into a separate empty location. Avoid substituting an empty bind, deleting DB files, or regenerating genesis or credentials.

```bash
collector="$evidence/collect-read-only.sh"
bash "$collector" "$out/old-restored"
for asn in 150 151 152 153; do
  id=$(node_id b12-reproduction "$asn")
  test "$(cat "$out/old-restored/as$asn-tip.exit")" = 0
  jq -e '.protocolVersion == {major:2,minor:0}' "$out/old-restored/as$asn-protocol-parameters.json"
  cmp "$out/old-restored/as$asn-genesis-config.sha256" "$saved/pre-stop-live/as$asn-genesis-config.sha256"
  docker exec "$id" ss -lnt 'sport = :3001'
  docker exec "$id" ss -nt '( sport = :3001 or dport = :3001 )'
  if [[ $asn != 153 ]]; then
    query "$id" 4242 kes-period-info --op-cert-file /cardano/producer/opcert.cert > "$out/old-restored/as$asn-kes.txt" 2>&1
  fi
done
for round in 1 2 3; do
  sample b12-reproduction 4242 "$out/old-round-$round"
  if [[ $round != 3 ]]; then sleep 60; fi
done
python3 "$repo/experiments/B12-P9/verify-b12-history.py" \
  --db-root "$old_db" --tips "$out/old-round-3" \
  --anchors "$evidence/history-anchors.json" > "$out/old-restored-history.json"
```

Require original binary versions 11.1.3 and 11.2.3.0, Conway on all four nodes, TCP/3001 listeners and peer handshakes, and advancing blocks on each node. Each verifier result must show 33 included transactions and the original per-transaction block hashes. Also require block 924 and **one common post-restart block** on all four sampled chains. The following extends the existing decoder to verify ancestry when tips differ:

```bash
python3 -B - "$repo" "$old_db" "$out" > "$out/old-common-block.json" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

repo, db, out = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location(
    "history", repo / "experiments/B12-P9/verify-b12-history.py"
)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)

def sample(asn, round_num):
    return json.loads((out / f"old-round-{round_num}/as{asn}-tip.json").read_text())

common = None
for asn in history.PEERS:
    rounds = [sample(asn, number) for number in (1, 2, 3)]
    assert all(t["era"] == "Conway" for t in rounds), asn
    assert 924 <= rounds[0]["block"] <= rounds[1]["block"] <= rounds[2]["block"], asn
    assert rounds[2]["block"] > rounds[0]["block"], asn
    tip = rounds[-1]
    index = history.block_index(db / f"as{asn}", tip["block"])
    cursor = tip["hash"]
    descendants = set()
    for height in range(tip["block"], 924, -1):
        actual, slot, parent, _ = index[cursor]
        assert height == actual, (asn, height)
        descendants.add((height, slot, cursor))
        cursor = parent
    assert cursor == "c8ea3a746e9eafb138d6a8a438efe715514b3b35dbc6f8b38c5ea1fbe2656391", asn
    assert index[cursor][:2] == (924, 18774), asn
    common = descendants if common is None else common & descendants
assert common, "No common post-restart block in the sampled chains"
height, slot, digest = max(common)
print(json.dumps({"common_block": height, "slot": slot, "hash": digest}))
PY
```

The common-block result is saved beside the transaction verification JSON. If the parser rejects a DB record or a live read races a chunk move, retry with fresh tips or verify against read-only ChainSync using the original anchors. A parser failure alone is insufficient to diagnose corruption. If heights stall, first check KES and opcert counters, clock, startup arguments, filesystem access, protocol identity and peer sessions. Treat an origin reset, missing historical ancestor or different genesis as a failed recovery.

## Rollback to P9

- Before P9 removal, resume retained wrappers with `p9_compose stop -t 120` followed by `p9_compose start` once any partial shutdown is resolved and the DB binds and KES remain valid. Inspect any process that failed to exit before attempting this.
- After P9 removal, if historical services started, record diagnostics and any tips. If all four nodes are running, run `graceful_nodes b12-reproduction "$out/old-rollback-shutdown"`. For partial startup, inspect all four project-labeled services individually, gracefully signal each existing Cardano PID and verify its closure before stopping wrappers. Preserve historical binds and the original archive. Inspect historical network ownership and endpoints using the checks above with the historical project and a fresh historical container inventory. Then run `old_compose stop -t 120` and `old_compose down -t 120`. Check that its project containers and networks are gone and the shared names, subnets and port are free.
- Verify `(cd "$out" && sha256sum -c p9.sha256)`, `check_images "$out/p9-image-ids.txt"`, the current P9 KES deadline and the original P9 configuration and bind paths. If P9 stayed stopped and its binds are intact, compare them against the saved quiescent archive again. Resume with `p9_compose up -d --no-build`. Use the existing P9 DBs in place and leave the archive untouched. A missing DB or mismatched image requires separate review. The restart naturally resumes writing to its original live DB bind.
- Run `sample b12-p9 4343 "$out/p9-rollback-live"` and repeat across three timed rounds. Verify Conway 9.0, original genesis and exact mounts, TCP/3001 sessions and advancing common history. Check the preserved funding and spending block bytes in each node's immutable or volatile stores and confirm those hashes on the recovered canonical chain via ChainSync if the local parser rejects P9 encoding. As corroboration, query the spend output `49cb569d947821b99c3d4dca8bb27b4f1cd9cf420008f4c3f5bee3ac8c88be67#0` with `query "$id" 4343 utxo --tx-in` and that output reference on each node. The expected value is 4,997,793 lovelace if still unspent. A UTXO lookup alone is insufficient to prove both historical transactions.

Keep backups, logs and activation records private. The preparation itself left both networks untouched.

## Approved execution on 2026-11-20

- All four P9 nodes agreed immediately before shutdown at block **1572**, slot **32635**, hash `8a1b24ac0241bc4f4d682af4d2483368083e0682cc4fc7c14efb9ad6c3141601`. AS151 logged a later local tip during shutdown. The four quiescent binds preserve their actual final state. The three live producer certificates matched the build contexts and ledger counters and expire on **2027-02-17 at 23:27:33 UTC**.
- All four P9 databases closed cleanly. Both Plutus-related blocks were rechecked in each quiescent store. The P9 wrappers stopped by **08:34:55 UTC**. The quiescent archive matched the original binds, and the P9 archive checksums passed. Runtime-only transaction and dashboard artifacts were copied privately. Only P9 project containers and managed networks were removed, by **08:40:13 UTC**. [P9 block comparison](../results/b12/artifact-manifest.md#e003) · [Private backup checksum manifest](../results/b12/artifact-manifest.md#e004)
- After verifying availability of the fixed names, static subnets and TCP/5000, the original B12-4242 project was recreated from its saved configuration, images and existing database binds. Compose startup finished by **08:42:53 UTC**. The approved execution did not regenerate genesis, change credentials, or submit transactions.
- **Recovery passed.** AS150–AS153 used the original database binds and genesis/configuration digests. Each ran Node 11.1.3 and CLI 11.2.3.0, answered socket queries on magic 4242, reported Conway protocol 2.0, and had three established TCP/3001 peer sessions. The three producer KES counters matched.
- The timed samples agreed across all four nodes at **950 → 954 → 955** at **08:51:35, 08:52:36 and 08:53:37 UTC**. Each sampled chain traces through the original block 924 and contains all **33 historical transactions** at their recorded block hashes. The common block 955 was at slot **53032**, hash `47b723a13aaa4a1f399eb8bb7c7eeec44c95a931b7ae5f63294c117b4002a595`. [Common-block proof](../results/b12/artifact-manifest.md#e005) · [Per-node transaction verification](../results/b12/artifact-manifest.md#e006)
- B12-4242 was left running. B12-P9 remains stopped with its original binds and validated rollback archive. No rollback was needed or exercised.
