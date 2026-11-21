# B12-4242 to B12-P9 sequential deployment and recovery

**Conditionally feasible on the current Ubuntu VM.** The B12-4242 history resides in four host bind directories. A controlled stop followed by project-scoped `down` can release the conflicting Docker resources while retaining those directories. Proceed only after a verified, quiescent database backup and preservation of the exact original images. Restoration by container recreation has not been exercised. The investigation preceded the approved cutover. The cutover has now passed, and the original project remains stopped. [Executed cutover evidence](../results/b12/artifact-manifest.md#e007)

## Verified persistence and conflicts

| Item | Read-only finding |
|---|---|
| Project and Compose | `b12-reproduction`, 39 project-labeled containers. Original Compose file is `/path/to/original-b12-run/experiments/B12-cardano/output/docker-compose.yml`. Installed Compose is 1.27.4. |
| Chain storage | Four distinct host bind mounts under `/path/to/original-b12-run/runtime/cardano-data/testnet-conway-113-v2/as150` through `as153`, each at container `/cardano/db`. |
| Evidence | Captures are host-bound at `runtime/captures`. Reports and transaction evidence are under `runtime/evidence`. Cardano's process logs and socket are in the containers' writable layers. |
| Volumes | 41 live mount entries across the project, all type `bind`. No named or anonymous volume was observed. The normalized file declares no volume or external network. EtherView also binds the Docker socket. |
| Genesis and config | All nodes agree with the preserved SHA-256 hashes. The original runtime config, topology files and compiled contexts are still present. The expected effective state is Conway, protocol 2.0, magic 4242. |
| Credentials | The producer KES/VRF key and operational-certificate files are present. Producer images embed the node credentials. Live KES queries report period 0, matching certificate counters and expiry **2027-02-17 18:09:33 UTC**. The live public certificate bytes matched both the original generated certificates and the image build-context copies. Key contents were not opened. Preserve active images, generated contexts and the original host wallet files privately. |
| Images | All **39** live image references resolve to the exact locally available image IDs. Most application tags are Compose-project-prefixed. Two generated base image tags, `39e016aa9e819f203ebc1809245a5818` and `98a2693c996c2294358552f48373498d`, and the EtherView tag are global. |
| Topology | The normalized file has **22** static networks. Docker shows **23** project-owned networks including `b12-reproduction_default`. None has a foreign endpoint. No remaining Docker network subnet overlapped those 22 static subnets in the inspected snapshot. Recheck before each cutover. |
| Name and port conflicts | The original SEED compiler emits fixed names for routers, route servers, hosts and `seedemu_ether_view`. It publishes host TCP **5000** for EtherView. P2P TCP **3001** is internal. An offline P9 compile confirmed the same 39 services, all 37 fixed names, all 22 static subnets and the same published port. Changing only the project name leaves those conflicts in place. |
| Resources | The Docker host has 4 CPUs, 7.8 GiB RAM and 36 GiB filesystem free at inspection. All Docker images combined use 33.36 GB. The original build context is about 789 MB. Check image-archive, build and backup space on their actual target filesystems. Do not rely on Docker's reclaimable-space estimate. |

The latest sample was 2026-11-19 **20:02 UTC**. All four nodes agreed at block **345**, slot **6786**, hash `d07e7c1ea810d4f38e3d625d36f646c6185de2e3526c972c543b81c168d62269`. The [read-only checker](../../experiments/B12-P9/verify-b12-history.py) followed header links from every sampled tip and reverified all **33** confirmed Phase 5A–5C transactions with their original block hashes. The original research evidence remains in place. [Fresh inventory](../results/b12/artifact-manifest.md#e011) · [Preservation archive](../results/b12/artifact-manifest.md#e008)

### What stop and down do here

`stop` retains containers and networks. It releases running port listeners but leaves the fixed names and network allocations reserved. A project-scoped `down` without `-v` or `--rmi` removes the original service containers and Compose-managed networks. The four database and capture bind directories and the local images remain. The **container writable layers are removed**, including original log files and any runtime-only changes. Archive logs, compare the operational certificates and any other relevant writable-layer changes to their preserved source or images, and retain the exact images before removal. The certificate paths appeared in the writable-layer diff, but all three live public certificate digests match the source and build-context copies. Repeat that check before teardown. Do not proceed if a required live artifact differs from the retained copy and lacks a recovery procedure. [Docker Compose stop](https://docs.docker.com/reference/cli/docker/compose/stop/) · [Docker Compose down](https://docs.docker.com/reference/cli/docker/compose/down/) · [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)

The original `/start.sh` backgrounds `cardano-node` and blocks on `tail -f /dev/null`. Docker's stop signal goes to the container's main process, so use the node's own runtime SIGTERM handler first. Require the node processes to exit and preserve shutdown logs before asking Compose to stop the wrappers. If a node does not exit within the verification window, retain the containers and diagnose it. [Cardano Node 11.1.3 runtime signal handling](https://github.com/IntersectMBO/cardano-node/blob/11.1.3/cardano-node/src/Cardano/Node/Run.hs#L410)

## Approved cutover procedure

These steps are proposed and have not been executed. Deployment approval for a separate VM does not cover this same-daemon cutover.

### 1. Pin the original deployment and prepare private backups

Use explicit absolute paths, the verified historical Docker engine, and the exact original Compose file. Use a fresh owner-only backup directory on storage with space for all images, database data and generated contexts. Keep backups that contain operator keys or producer images on private, preferably encrypted storage. The existing public preservation archive was designed for evidence and excludes signing material.

```bash
set -euo pipefail
umask 077
repo=/path/to/b12-reproduction
old=/path/to/original-b12-run
original="$old/experiments/B12-cardano"
runtime="$old/runtime"
db="$runtime/cardano-data/testnet-conway-113-v2"
backup=/absolute/path/to/new/private/b12-4242-cutover-backup
mkdir -m 700 "$backup"
export DOCKER_HOST=unix:///var/run/docker.sock
unset DOCKER_CONTEXT
historic_engine=/path/to/private/original-docker-engine-id.txt
test "$(docker info --format '{{.ID}}')" = "$(cat "$historic_engine")"
old_compose() {
  docker-compose -p b12-reproduction --project-directory "$original/output" \
    -f "$original/output/docker-compose.yml" "$@"
}
old_compose config > "$backup/compose-normalized.yml"
cp -p "$original/output/docker-compose.yml" "$backup/docker-compose.yml"
collector="$runtime/evidence/phase-5d/protocol-compatibility/collect-read-only.sh"
bash "$collector" "$backup/pre-stop-live"
python3 "$repo/experiments/B12-P9/verify-b12-history.py" \
  --db-root "$db" --tips "$backup/pre-stop-live" \
  --anchors "$runtime/evidence/phase-5d/protocol-compatibility/history-anchors.json" \
  > "$backup/pre-stop-history.json"
```

Pause submissions and capture jobs. Recheck current KES expiry/counters, compose roles, genesis hashes, all host DB mounts, and the owners and endpoints of all original networks. Save the live image IDs and original image references. Verify each image reference resolves to its recorded ID immediately before export. Archive credentials, original config, and generated build contexts privately so a missing local image remains recoverable. Never overwrite the source paths with a different run.

```bash
mapfile -t containers < <(docker ps -aq --filter label=com.docker.compose.project=b12-reproduction)
test "${#containers[@]}" -eq 39
docker inspect --format '{{.Config.Image}} {{.Image}}' "${containers[@]}" | sort -u > "$backup/image-ids.txt"
while read -r image expected; do
  test "$(docker image inspect --format '{{.Id}}' "$image")" = "$expected"
done < "$backup/image-ids.txt"
mapfile -t images < <(awk '{print $1}' "$backup/image-ids.txt")
docker image save "${images[@]}" | gzip -1 > "$backup/images.tar.gz"
gzip -t "$backup/images.tar.gz"
tar --acls --xattrs -C "$original" -cpf "$backup/compiler-context-and-config.tar" config output
tar -C "$runtime" -cpf "$backup/research-evidence.tar" evidence captures
```

The original image archive includes embedded producer keys. Do not publish it or add it to the public evidence archive. Compare the live public `opcert.cert` digests and known key-file locations against those in the original generated producer configuration. If live artifacts differ materially, preserve the documented active copy with equivalent privacy before teardown. Preserve Docker service labels, image list and network inspect records for later reconciliation.

### 2. Graceful shutdown, quiescent database backup, and resource release

Only after approval and the pre-stop checks, send a single SIGTERM to each identified Cardano PID directly, preferably in parallel. Wait for all four node processes to exit. The following shell fragment assumes the variables and `old_compose` function above.

```bash
workers=()
for asn in 150 151 152 153; do
  (
    id=$(cat "$backup/pre-stop-live/as$asn-container.txt")
    docker exec "$id" sh -eu -c '
      set -- $(pgrep -x cardano-node)
      test "$#" -eq 1
      kill -TERM "$1"
    '
    deadline=$((SECONDS + 120))
    while docker exec "$id" pgrep -x cardano-node >/dev/null; do
      test "$SECONDS" -lt "$deadline"
      sleep 1
    done
    test "$(docker inspect --format '{{.State.Running}}' "$id")" = true
    docker cp "$id:/var/log/cardano-node.log" "$backup/as$asn-cardano-node.log"
    docker logs "$id" > "$backup/as$asn-docker.log" 2>&1
  ) &
  workers+=("$!")
done
for worker in "${workers[@]}"; do wait "$worker"; done
```

Review the shutdown logs for clean closure and ensure that no Cardano process remains in the four containers. Retain the final sampled tips and record the stop UTC. There may be blocks after the last live query and before process exit. Keep the quiescent DB as the authoritative final local state.

```bash
old_compose stop -t 120
test -z "$(docker ps -q --filter label=com.docker.compose.project=b12-reproduction)"
date -u +%FT%TZ > "$backup/stopped.utc"
for asn in 150 151 152 153; do
  test -s "$db/as$asn/protocolMagicId"
  test -d "$db/as$asn/volatile"
done
sudo tar --acls --xattrs --numeric-owner -C "$runtime/cardano-data" \
  -cpf - testnet-conway-113-v2 > "$backup/cardano-data-quiescent.tar"
tar -tf "$backup/cardano-data-quiescent.tar" > "$backup/cardano-data-members.txt"
(
  cd "$backup"
  sha256sum images.tar.gz compiler-context-and-config.tar research-evidence.tar \
    cardano-data-quiescent.tar > SHA256SUMS
  sha256sum -c SHA256SUMS
)
```

Verify the four backed-up DB trees and their ownership/modes against the originals. Compare the tar contents against the quiescent bind sources using a privileged read-only `tar --compare` or a restore rehearsal to another empty directory. At this point the original containers still exist, so a failed backup can be investigated without removing them.

After successful backup review, recheck that no non-project container is attached to the original networks. Then release only the historical project's Docker resources:

```bash
old_compose down -t 120
test -z "$(docker ps -aq --filter label=com.docker.compose.project=b12-reproduction)"
test -z "$(docker network ls -q --filter label=com.docker.compose.project=b12-reproduction)"
```

If an endpoint or network remains, stop and inspect its ownership. Keep the original DB sources, contexts, images, genesis, logs and backups in place. No `-v`, `--rmi`, orphan removal, force kill, or prune is part of this plan.

### 3. Deploy P9 sequentially

Follow the [P9 genesis and testnet guide](B12_P9_plutus_v3_guide.md) to generate fresh magic-4343 genesis, keys and contexts with a new start time. Use a new run root and disjoint `CARDANO_EXPERIMENT_RUNTIME`. Keep the P9 Compose project **`b12-p9`**. The separate-VM guard from the earlier guide intentionally rejects this engine unless explicitly run in sequential mode.

After SEED emits P9 Compose, inspect the normalized build contexts, static IPs, private routes, storage binds and shared-image references. Use the sequential gate below. It is read-only and refuses to continue while the historical containers or networks remain.

```bash
cd "$p9_run/output"
docker-compose -p b12-p9 config > "$p9_run/compose-normalized.yml"
python3 "$repo/experiments/B12-P9/check-isolation.py" --sequential \
  --historical-engine-id "$historic_engine" --historical-runtime "$runtime" \
  --runtime "$p9_run/.runtime" --compose "$p9_run/compose-normalized.yml"
```

The offline compile found that both P9 shared base Dockerfiles are byte-identical to the original Dockerfiles. Each contains only a base-image `FROM`. The three explicitly named image services match the original. Repeat those comparisons on the fresh P9 output before building. If they still match and the saved image IDs resolve locally, reuse those images and build only the services without an explicit image name. The static compile used a nonexistent Docker socket. It created files in the disposable P9 check directory without building or creating Docker resources. [Static P9 Compose inventory](../results/b12/artifact-manifest.md#e012)

```bash
python3 - "$p9_run/compose-normalized.yml" <<'PYLIST' > "$p9_run/build-services.txt"
import sys
import yaml

with open(sys.argv[1]) as source:
    services = yaml.safe_load(source)["services"]
for name, service in services.items():
    if "build" in service and "image" not in service:
        print(name)
PYLIST
mapfile -t p9_services < "$p9_run/build-services.txt"
test "${#p9_services[@]}" -eq 36
docker-compose -p b12-p9 build "${p9_services[@]}"
```

 If the base contexts differ, adapt only the P9 Compose and Dockerfiles to use P9-specific base tags and verify every dependent `FROM` before building. Keep the shared EtherView tag pinned to its saved image ID and avoid pulling into or rebuilding historical tags. Before `docker-compose -p b12-p9 up -d --no-build`, check the project and all P9 image references. Recheck the original image IDs after startup. If build space is insufficient or a port, subnet or tag conflict remains, abort P9 rather than clean unrelated Docker resources.

Once P9 genesis has passed, verify all four roles, advancing tips, common block hashes, effective Conway **9.0**, magic **4343**, V3 model, fee and collateral parameters. Preserve P9 evidence separately. Obtain approval for the exact funding transaction and, after confirmed funding and successful live cost evaluation, for the exact spend. Neither approval is implied by authorization for a cutover.

## Restore B12-4242

1. Save P9 evidence and its final tips. Use the same direct node shutdown and logging procedure against **P9's** labeled containers, then stop and run `docker-compose -p b12-p9 down -t 120` from its original generated Compose directory. Keep P9 database and evidence binds. Check the fixed names, subnets and TCP/5000 are released. Use the recorded engine ID for both phases.
2. Check that the original Compose, genesis and configuration hashes match the pre-stop evidence. Verify each original bind source exists and contains retained DB data, compare the preserved quiescent backup with the original paths, and ensure that no source points into P9. If a path is missing, damaged or linked elsewhere, stop. A normal return uses the intact original DBs in place. If restoration from backup is required, extract and verify in a separate empty recovery directory first, then obtain approval for any replacement at the original paths.
3. From the original directory, confirm every saved image reference resolves to the original ID. If an image is missing, verify the archive and use `gzip -dc "$backup/images.tar.gz" | docker image load` only after checking that loading these tags will not overwrite an unexpected conflicting image. Re-run the ID comparison afterward. Recheck certificates and KES time against current UTC.
4. Recreate services under their **original** Compose project, from their **original** file. Compose recreates the managed bridges and routes. Verify the config hash and normalized mounts before running:

   ```bash
   old_compose config -q
   old_compose up -d --no-build
   old_compose ps
   ```

   If the switch was aborted after stop and before down, `old_compose start` instead resumes the retained containers. If startup fails or KES has expired, diagnose the original deployment. Genesis regeneration and rebuilding with new credentials cannot recover the original chain.
5. Run the historical read-only collector against AS150–AS153. Verify node 11.1.3, CLI 11.2.3.0, original genesis hashes, original DB bind paths, magic 4242, Conway protocol 2.0, Unix sockets, TCP/3001 listeners and peer handshakes. Observe three rounds of tips 60 seconds apart. Verify chain advancement and a common numbered block hash. A wall-clock pause produces a slot gap and can delay first block production.
6. Run the saved verifier with the actual restored tips and the original 33 anchors. It follows links from each sampled tip, checks the exact block and transaction body hashes and fails on missing blocks. If older blocks are no longer readable through the local parser, use a compatible read-only ChainSync source and verify the same anchor list. Preserve new verification evidence separately from the originals.

   ```bash
   bash "$collector" "$backup/restored-live"
   python3 "$repo/experiments/B12-P9/verify-b12-history.py" \
     --db-root "$db" --tips "$backup/restored-live" \
     --anchors "$runtime/evidence/phase-5d/protocol-compatibility/history-anchors.json" \
     > "$backup/restored-history.json"
   ```

Verify the earlier metadata using its original containing block hashes and evidence, compare selected funded UTXOs with pre-stop balances accounting for any ordinary chain activity, and recheck the archived PCAP manifests.

## Principal threats to reproducibility

Wrong Docker context or project, global tag replacement, insufficient disk, missed shutdown, expired KES, writable-layer data lost at down, accidental volume or network deletion, host path changes, mutable source/binaries, and a different genesis identity can each invalidate the recovery. A stopped all-node testnet also accrues a real-time slot gap. The cutover plan controls these risks with exact IDs, a quiescent backup, disjoint paths, a fail-closed Docker preflight, and independent post-restore chain proofs. No quiescent backup, container removal, or restart validation has been performed in this investigation.
