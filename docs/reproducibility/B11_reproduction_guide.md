# B11 Cardano — GitHub Reproduction Guide

**Repository:** https://github.com/bayazm/cardano-seed-emulator-experiments  
**Experiment:** `experiments/B11-cardano` — three producers (AS150–AS152), one relay (AS153), testnet magic `4242`, TCP `3001`.  
**Platform validated:** Ubuntu 20.04 x86-64; Python 3.8.10; Docker 20.10.21; Docker Compose 1.27.4; Cardano Node 11.0.1 / CLI 11.0.0.0.  
**Scope:** A clean Git *clone* on an already configured Ubuntu VM was tested successfully; a fresh-host installation and fresh-download execution of `setup-cardano.sh` remain separate verification tasks.

> **Isolation:** Run only one SEED/Cardano experiment per dedicated Docker host or VM. Several experiments reuse fixed container names and network addresses. Commands that stop containers must be issued only from the intended project's `output/` directory, after checking the targets. Do not use `docker system prune` or remove other projects' containers.

## A. Install host prerequisites (fresh Ubuntu host)

Install Docker Engine, standalone Docker Compose or Compose v2, Python 3 and venv, git, curl, tar, sha256sum, and tcpdump according to your Ubuntu version and organization's installation policy. Ensure you have permission to use Docker. These commands inspect the environment:

```bash
python3 --version
docker --version
docker-compose --version   # or: docker compose version
git --version
curl --version | head -n 1
```

**SEED Emulator — pinned source revision** (on a fresh host, use an independent checkout):

```bash
cd ~
git clone https://github.com/seed-labs/seed-emulator.git seed-emulator
cd seed-emulator
git checkout a8d93cd65aace99a454fae44895d41d7e8cd8197
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -c 'from seedemu import Emulator, Platform; print("SEED Emulator OK:", Platform.AMD64)'
```

Keep the virtual environment active for the Python commands below, or activate it again in each new shell with `source ~/seed-emulator/.venv/bin/activate`. **Note:** The pinned checkout's fresh Python dependency resolution has not yet been independently validated. On the previously configured VM, the shorter test was:

```bash
python3 -c 'from seedemu import Emulator, Platform; print("SEED Emulator OK:", Platform.AMD64)'
```

## B. Clone the published B11 experiment

```bash
mkdir -p ~/reproducibility-test
cd ~/reproducibility-test
git clone https://github.com/bayazm/cardano-seed-emulator-experiments.git
cd cardano-seed-emulator-experiments
pwd
git status
git rev-parse HEAD
ls experiments/B11-cardano scripts docs/reproducibility
```

Record the Git commit; for a formal study, check out and report the exact commit that was tested rather than silently using whatever is on `main` later.

## C. Install B11 Cardano binaries centrally

From the repository root, run the version-specific setup script:

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments
./scripts/setup-cardano.sh B11
```

The script selects Cardano Node release **11.0.1**, installs it once in `resources/cardano/11.0.1/` if needed, and creates or verifies a relative symbolic link at `experiments/B11-cardano/resources/cardano-static`. Downloads are checked against the expected SHA-256 checksum before extraction. An existing installation is reused after executable checks; this reuse path **does not recheck the existing binaries' checksums**.

The resulting layout is:

```text
resources/cardano/11.0.1/bin/cardano-node
resources/cardano/11.0.1/bin/cardano-cli
experiments/B11-cardano/resources/cardano-static -> ../../../resources/cardano/11.0.1
```

Verify the installed binaries:

```bash
experiments/B11-cardano/resources/cardano-static/bin/cardano-node --version
experiments/B11-cardano/resources/cardano-static/bin/cardano-cli --version
readlink -f experiments/B11-cardano/resources/cardano-static
```

Expected: `cardano-node 11.0.1`, `cardano-cli 11.0.0.0`. No system-wide Cardano binary installation is needed. The central binary directory is intentionally ignored by Git; collaborators must run the setup script after cloning. The relative symlink is tracked by Git. **The script's existing-installation path and B11 Docker build were tested; its fresh-download path has not yet been independently tested.**

Do not create a physical `experiments/B11-cardano/resources/cardano-static` directory manually: it would conflict with the symlink and setup script. The setup script refuses to overwrite an existing conflicting directory or link.

## D. Generate fresh genesis and credentials

From the repository root, **before launch**, in a disposable clean experiment checkout:

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments
umask 077
python3 scripts/prepare-genesis.py experiments/B11-cardano --minutes 60
find experiments/B11-cardano/config -type f | sort | head -n 25
git status --short
```

Use a start-time margin appropriate for the anticipated image-build duration; `--minutes 60` is an example. If the configured start time has passed **before the first launch**, regenerate in a fresh disposable run directory and recompile. **Never regenerate genesis against an existing blockchain database.** Genesis generation writes signing keys and can modify the tracked `config/private-testnet-d0/config.json`; do not commit these changes casually. Keep the generated genesis, credentials and associated runtime database together.

## E. Compile and validate the emulation

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments/experiments/B11-cardano
python3 blockchain.py amd
cd output
docker-compose config -q
# Inspect what would be launched and check for conflicts:
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker-compose ps
```

Expected compiler output: successful SEED Emulator rendering, Docker infrastructure generated, AS150–AS152 configured with producer credentials, AS153 configured as a relay. `config -q` exits 0 with no output on success. Inspect the generated Compose mounts and Dockerfiles before building; producer credentials are embedded in build contexts/images.

## F. Build and start — dedicated VM only

Do this only if no conflicting experiment is running and the genesis/start-time configuration is appropriate:

```bash
# Still inside experiments/B11-cardano/output
docker-compose build
docker-compose up -d
docker-compose ps
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

The auxiliary EtherView service may fail separately; investigate it without assuming the Cardano nodes failed. If a startup socket is initially absent, recheck after the node initializes. Use these **actual** service container names only if they match `docker ps` on your host.

## G. Verify all four Cardano processes

```bash
for AS in 150 151 152 153; do
  CONTAINER=$(docker ps --format '{{.Names}}' | grep "^as${AS}h-Cardano-Node-" | head -n 1)
  echo "=== AS${AS}: ${CONTAINER:-NOT FOUND} ==="
  if [ -n "$CONTAINER" ]; then
    docker exec "$CONTAINER" pgrep -af cardano-node
    docker exec "$CONTAINER" ls -l /cardano/node.socket
  fi
done
```

Expected: AS150–AS152 run with KES, VRF, operational-certificate flags; AS153 runs without producer credentials. `/cardano/node.socket` must exist for CLI queries; wait for node initialization if necessary.

## H. Query blockchain tips and prove ongoing activity

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments
mkdir -p evidence/B11
printf 'git_commit=' > evidence/B11/git-commit.txt
git rev-parse HEAD >> evidence/B11/git-commit.txt

tip_all() {
  for AS in 150 151 152 153; do
    CONTAINER=$(docker ps --format '{{.Names}}' | grep "^as${AS}h-Cardano-Node-" | head -n 1)
    echo "========== AS${AS} =========="
    if [ -z "$CONTAINER" ]; then echo "Container not found"; continue; fi
    docker exec "$CONTAINER" cardano-cli query tip \
      --socket-path /cardano/node.socket --testnet-magic 4242
    echo
  done
}
tip_all
```

Capture a timestamped first measurement:

```bash
stamp=$(date -u +%Y%m%dT%H%M%SZ)
for AS in 150 151 152 153; do
  CONTAINER=$(docker ps --format '{{.Names}}' | grep "^as${AS}h-Cardano-Node-" | head -n 1)
  docker exec "$CONTAINER" cardano-cli query tip \
    --socket-path /cardano/node.socket --testnet-magic 4242 \
    > "evidence/B11/AS${AS}-tip-${stamp}.json"
done
```

Run `tip_all` again later. Blocks and slots should advance, and the four nodes should converge to matching tip hashes (compare at a common height if sampled during propagation). **Validated observation on Nov 19, 2026:** all four nodes agreed at block 13/slot 351 and later block 18/slot 436, with reported sync 100%. This shows continuing network block production; it does **not** identify which individual producer forged each block.

## I. Test IP and TCP reachability

```bash
docker exec as150h-Cardano-Node-1-10.150.0.71 ping -c 4 10.153.0.71
docker exec as150h-Cardano-Node-1-10.150.0.71 \
  sh -c 'nc -zvw 3 10.153.0.71 3001; echo "Exit code: $?"'
```

Validated observation: 4/4 ping responses, 0% loss, mean RTT 0.318 ms; `nc` reported success, exit code 0. These demonstrate network/transport reachability, **not by themselves** a decoded Cardano handshake.

## J. Capture B11 producer ↔ relay TCP traffic

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments
mkdir -p evidence/B11/pcap
CONTAINER=as150h-Cardano-Node-1-10.150.0.71
docker exec "$CONTAINER" sh -c 'command -v tcpdump'
docker exec "$CONTAINER" ip -br addr
# Capture inside the container; use 'any' or the confirmed 'net0' interface.
docker exec "$CONTAINER" timeout 60 tcpdump -i any -nn \
  'tcp port 3001 and host 10.153.0.71' \
  -w /tmp/B11-AS150-AS153.pcap
docker cp "$CONTAINER":/tmp/B11-AS150-AS153.pcap evidence/B11/pcap/
ls -lh evidence/B11/pcap/
tcpdump -nn -r evidence/B11/pcap/B11-AS150-AS153.pcap -c 20
sha256sum evidence/B11/pcap/B11-AS150-AS153.pcap > evidence/B11/pcap/SHA256SUMS.txt
tcpdump -nn -r evidence/B11/pcap/B11-AS150-AS153.pcap \
  > evidence/B11/pcap/packet-summary.txt
```

A 60-second capture on Nov 19, 2026 yielded 63 packets, 0 kernel drops, 9.7 KB PCAP, with traffic in both directions. The short 13-byte payloads may be control traffic, but **their Cardano message types were not decoded**. This is evidence of bidirectional TCP application traffic on the Cardano port, not definitive proof of a protocol-specific handshake. Note that `timeout` can return status 124 when it terminates the capture at the planned duration; inspect the PCAP rather than treating this alone as failure.

## K. Save supporting metadata and protect secrets

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' \
  > evidence/B11/docker-containers.txt
python3 --version > evidence/B11/host-versions.txt
docker --version >> evidence/B11/host-versions.txt
docker-compose --version >> evidence/B11/host-versions.txt
( cd experiments/B11-cardano && resources/cardano-static/bin/cardano-node --version \
    && resources/cardano-static/bin/cardano-cli --version ) >> evidence/B11/host-versions.txt

git check-ignore -v evidence/B11/AS150-tip-*.json || true
git status --short
```

The current `.gitignore` excludes `**/evidence/`; raw captures and generated signing keys should remain private until reviewed. The genesis script may modify the tracked `config/private-testnet-d0/config.json`. **Do not push `.skey` files, unreviewed PCAP data or build contexts with private keys.** A publication-safe report can be added separately under `docs/` after review.

## L. Stop the selected B11 experiment safely

From the **B11 output directory**, first confirm the targeted project:

```bash
cd ~/reproducibility-test/cardano-seed-emulator-experiments/experiments/B11-cardano/output
pwd
docker-compose ps
# Only after confirming these are the intended B11 containers:
docker-compose stop
```

`stop` preserves Docker containers and mounted data; it is safer than indiscriminate removal. Avoid `docker-compose down -v`, `docker system prune`, or manually deleting shared containers. For a new fresh-genesis reproduction, use a new empty runtime directory and appropriate Docker isolation; do **not** reuse a prior blockchain database with newly generated genesis.

## M. Reproducibility status and qualifications

**Observed on clean Git clone within the preconfigured VM, Nov 19, 2026:** successful checksum-verified manual binary download, genesis generation, compilation, Compose validation, Docker image build, four active Cardano processes, advancing synchronized blockchain tips, ICMP and TCP reachability, and bidirectional port-3001 traffic capture. Subsequently, the centralized binary layout, setup-script reuse path, and an AS150 Docker image build were verified.

**Not established:** fresh-host installation with no preinstalled dependencies/cache; fresh-download path of the automated setup script; which of AS150–AS152 individually forged observed blocks; decoded Cardano P2P handshake; correction of the separate EtherView startup issue. A formal replication report should include the tested Git commit, Docker and dependency versions, timestamps, any Docker cache reuse, and any startup conflicts.

## Official project references

- [B11 README](https://github.com/bayazm/cardano-seed-emulator-experiments/blob/main/experiments/B11-cardano/README.md)
- [Installation](https://github.com/bayazm/cardano-seed-emulator-experiments/blob/main/docs/reproducibility/install.md)
- [Genesis](https://github.com/bayazm/cardano-seed-emulator-experiments/blob/main/docs/reproducibility/genesis.md)
- [Operations](https://github.com/bayazm/cardano-seed-emulator-experiments/blob/main/docs/reproducibility/operations.md)
- [Runtime verification](https://github.com/bayazm/cardano-seed-emulator-experiments/blob/main/docs/reproducibility/runtime-verification.md)