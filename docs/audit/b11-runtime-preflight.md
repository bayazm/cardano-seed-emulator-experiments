# B11 runtime preflight

The isolated run candidate and preflight evidence are under `/tmp/b11-runtime.ZdMSRhh0/`. Startup was blocked before build or launch because Docker denied access to `/var/run/docker.sock`. Both the container and network inventory queries returned `operation not permitted`. Existing names, subnets, routes, images and daemon capacity could therefore not be verified. No daemon resource was changed.

## Checks executed

| Check | Command or method | Result |
|---|---|---|
| Capacity | `df -h`, `free -h` | 45 GiB disk and 5.2 GiB RAM available before preparation. The B11 candidate occupied about 957 MiB. Build and live peak usage remain unmeasured. |
| Docker resources | `docker context ls`, `docker ps -a`, `docker network ls` | Default local daemon. Inventory blocked by socket access. Compose 1.27.4 installed. |
| SEED and Cardano versions | `git describe`, `git rev-parse HEAD`, both Cardano executables with `--version` | SEED `v1.1-2-ga8d93cd6`, B11 node 11.0.1, CLI 11.0.0.0. |
| Installation | Attempted the documented release download | GitHub DNS lookup failed. Used copies of the version-checked local B11 binaries. The archive checksum was not independently tested. |
| Fresh genesis | `python3 scripts/prepare-genesis.py /tmp/b11-runtime.ZdMSRhh0/B11-cardano --minutes 30` | Pass. Magic 4242. Fresh keys and genesis were created in the copy. The configured UTC start was 2026-11-19 01:08:10. |
| SEED compilation | `python3 blockchain.py amd` with the inspected SEED package and an explicit temporary runtime root | Pass. All four DB directories were empty before launch. |
| Compose validation | `docker-compose config -q` on raw and run-only configurations | Pass. The run-only variant keeps 38 services and 22 static subnets. |
| Live B11 | Containers, startup, genesis compatibility, height, relay sync, ledger state, TCP/3001 and PCAP | Pending. No live logs, tips, block heights or capture exist for this run. |

The raw Compose output included 37 fixed container names, two shared dummy-image tags and optional EtherView. EtherView publishes port 5000 and mounts the daemon socket. The run-only variant omits EtherView and namespaces fixed container names and dummy-image references. The Cardano address plan is unchanged, so an inventory check and overlap comparison against existing Docker networks and host routes are still required. The project prefix also names default Compose images and networks. Builds can still use shared base images and daemon build cache.

## Commands gated on preflight and explicit approval

On an authorized daemon first check `docker ps -a`, `docker network ls`, each network's IPAM subnets, host routes and image tags. Compare them against the candidate. Stop if any fixed subnet overlaps an existing network or the run-specific names already exist. If no conflict remains, review and approve these exact build and startup commands before executing them:

```bash
cd /tmp/b11-runtime.ZdMSRhh0/B11-cardano/output
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml build 39e016aa9e819f203ebc1809245a5818 98a2693c996c2294358552f48373498d
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml build
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml up -d --no-build
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml ps
```

Confirm the intended genesis window before any launch. If a new future start is needed, prepare a separate fresh copy so the current configuration and credentials remain intact. Refer to the [B11 runtime verification plan](../reproducibility/runtime-verification.md#b11--genesis-and-relay-synchronization). Use container names from the run-only file, which carry the `b11verifyzdmsrhh0-` prefix. Store startup logs, tips, connections, status and captures under the temporary run directory. Compare common producer and relay block points and record the heights and slots.

## Targeted shutdown after an approved run

From the same output directory, verify that the Compose project listing contains only this verification's containers. Then stop that project and record the resulting status:

```bash
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml ps
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml stop
docker-compose -p b11verifyzdmsrhh0 -f docker-compose.isolated.yml ps
```

No shutdown was necessary. The temporary run directory retains generated credentials, genesis files and offline evidence.
