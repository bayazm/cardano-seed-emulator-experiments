# B12 protocol-9 demonstration on one clean host

**Status: prepared, awaiting execution.** Use one fresh Ubuntu VM and one four-node B12-P9 network with magic 4343 and Conway ledger protocol 9.0. Fund the original validator with an inline datum containing `AGRI_001`, then spend that output with the matching sensor ID in the redeemer. Confirm both transactions across all four nodes.

This demonstrates sensor data passed to and checked by the original validator. CIP-20 auxiliary metadata is a separate ledger field. The [portable transaction and benchmark workflows](B12_portable_workflow.md) and [historical results](../results/b12/README.md) are separate references.

Use an approved source revision containing the P9 helpers. Obtain authorization before deployment and separately for each signed transaction. Use fresh credentials and databases.

## Environment

| Item | Required for this procedure | Planning recommendation |
| --- | --- | --- |
| VM | Ubuntu 20.04 LTS Server, amd64, one dedicated Docker daemon. Rootful Docker on the local UNIX socket and administrator access for provisioning. | 4 vCPUs, 8 GiB RAM and 100 GiB SSD. For parallel Docker builds, prefer 8 vCPUs and 16 GiB. These are sizing targets, not measured minimums. |
| Storage | Sufficient space on both the Docker data filesystem and private evidence/backup filesystem. Check them before each build and archive. | Budget 35–55 GiB used for OS, pulled and built images, toolchains, contexts, captures and private backups. Keep at least 20 GiB free before compiling. Budget increases for long captures or extra image archives. |
| Docker | Historical reference Docker 20.10.21 and standalone `docker-compose` 1.27.4. The generated Compose and isolation guard need the normalized configuration shape used by the historical run. | Use the reference versions for fidelity. If the available approved packages differ, record the deviation and gate on Compose validation and the isolation checks. |
| Language tools | Python 3.8 in a fresh venv, pinned SEED revision, repository requirements, Bash, Git, curl, jq, tcpdump, iproute2, coreutils and tar. Node 11.1.3 / CLI 11.2.3.0 for B12. Aiken 1.1.24 with stdlib v4.0.0. | Record resolved package versions and image IDs. Treat differing versions as experimental deviations. |
| Connectivity | DNS, HTTPS to Ubuntu archives, GitHub release and Git endpoints, Python package indexes, image registries and image build package mirrors. Correct UTC with a synchronized clock. | Use isolated NAT with no public inbound forwarding for TCP/5000 or 3001. Avoid VPN/VM routes overlapping the generated topology. |
| Time | Allow for downloads, cold builds and genesis lead time. | Planning estimates are 30–90 minutes for provisioning and dependency downloads and another 30–90 minutes for a cold build. Reserve a half day for the full rehearsal, including the genesis wait, confirmations and troubleshooting. Record actual durations and disk use. |

Ubuntu 20.04 is past standard support. Use an appropriately patched image and approved package sources. The current Docker Engine Ubuntu installation page does not list Focal, so the Focal archive's `docker.io` and an approved standalone Compose build are the reference path here. [Ubuntu Focal support](https://ubuntu.com/20-04) · [Docker Ubuntu requirements](https://docs.docker.com/engine/install/ubuntu/) · [Standalone Compose documentation](https://docs.docker.com/compose/install/standalone/)

## 1. Start the acceptance log and install

Use a regular Bash shell. Replace `source_url` and `source_ref` with the approved public URL and published commit ID. The current uncommitted candidate is unavailable from a public clone until an authorized integration publishes it. Stop if the selected revision lacks the portable helpers.

```bash
set -euo pipefail
umask 077
source_url='REPLACE_WITH_APPROVED_PUBLIC_URL'
source_ref='REPLACE_WITH_PUBLISHED_COMMIT_SHA'
root=$(mktemp -d "$HOME/b12-p9-demo.XXXXXXXX")
evidence="$root/evidence"
mkdir -p "$evidence" "$root/downloads" "$root/bin"
printf 'id\tcommand\texit\texpected\tactual_output\tevidence\tresult\n' > "$evidence/acceptance.tsv"

# Wrap commands whose exit status enforces the stated acceptance predicate.
step() {
  local id=$1 expected=$2 rc=0 result command
  shift 2
  test ! -e "$evidence/$id.stdout" || return 2
  printf -v command '%q ' "$@"
  ( "$@" ) > "$evidence/$id.stdout" 2> "$evidence/$id.stderr" || rc=$?
  if (( rc == 0 )); then result=PASS; else result=FAIL; fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$command" "$rc" "$expected" \
    "$id.stdout; $id.stderr" "$evidence" "$result" >> "$evidence/acceptance.tsv"
  printf '%s %s\n' "$id" "$result"
  return "$rc"
}
step apt-update 'Package indexes fetched' sudo apt-get update
step apt-install 'Host dependency installation exits zero' sudo apt-get install -y \
  git curl ca-certificates python3 python3-venv python3-dev build-essential \
  libffi-dev libssl-dev docker.io docker-compose jq tcpdump iproute2
sudo systemctl enable --now docker
# If needed, have the VM administrator grant Docker access and start a new login shell.
# Reopen this same private acceptance root and re-establish the shell variables.
unset DOCKER_CONTEXT
export DOCKER_HOST=unix:///var/run/docker.sock
step engine 'Local Docker daemon reachable' docker info
step host 'Host version inventory saved' bash -c 'uname -a; cat /etc/os-release; lscpu; free -h; df -h; timedatectl status; ip route'
step compose 'Standalone Compose version recorded for review' docker-compose version
docker info --format '{{.ID}}' > "$evidence/docker-engine-id.txt"
step clone 'Public source checkout created' git clone "$source_url" "$root/repo"
repo="$root/repo"
step checkout 'Requested immutable source selected' git -C "$repo" checkout --detach "$source_ref"
git -C "$repo" rev-parse HEAD > "$evidence/source-commit.txt"
test "$(cat "$evidence/source-commit.txt")" = "$source_ref"
test -f "$repo/experiments/B12-P9/verify_plutus.py"

step seed-clone 'Upstream SEED source obtained' git clone https://github.com/seed-labs/seed-emulator.git "$root/seed-emulator"
step seed-pin 'Pinned SEED source selected' git -C "$root/seed-emulator" checkout a8d93cd65aace99a454fae44895d41d7e8cd8197
step venv 'Fresh Python venv created' python3 -m venv "$root/venv"
source "$root/venv/bin/activate"
step seed-install 'SEED pins installed' python -m pip install -r "$root/seed-emulator/requirements.txt"
step seed-package 'Pinned source installed in venv' python -m pip install -e "$root/seed-emulator"
step b12-python 'B12 pins installed' python -m pip install -r "$repo/experiments/B12-cardano/reproduction-requirements.txt"
step dependencies 'Dependency compatibility and versions recorded' python -m pip check
python -m pip freeze > "$evidence/pip-freeze.txt"
dpkg-query -W > "$evidence/dpkg-versions.txt"
cd "$repo"
step static 'Clean source passes syntax and link validation' python scripts/validate-static.py
step cardano 'B12 archive checksum and 11.1.3/11.2.3.0 versions pass' bash scripts/setup-cardano.sh B12
cli="$repo/resources/cardano/11.1.3/bin/cardano-cli"
```

If Focal's `docker-compose` package differs from the reference, obtain the approved Linux x86-64 release artifact from the [Compose 1.27.4 release](https://github.com/docker/compose/releases/tag/1.27.4), verify its upstream checksum or approved distribution digest, install it into `$root/bin`, and record its version and checksum. Resolve access issues via the VM administrator or the docker group and a new login. Docker-group membership grants root-equivalent privileges. Keep the local socket selected, and use a dedicated VM with no unrelated workloads. [Docker Linux post-installation](https://docs.docker.com/engine/install/linux-postinstall/)

## 2. Fresh-network checks

Define these functions in the same shell. `project`, `magic`, `major`, `runtime` and `compiler` are set by that VM's network section. For gates involving manual review, record the decision in the checklist with the relevant transcript. Mark failures as failures even if a later retry passes.

```bash
dc() { docker-compose -p "$project" --project-directory "$compiler/output" -f "$compiler/output/docker-compose.yml" "$@"; }
peer() {
  local ids
  ids=$(docker ps -q --filter "label=com.docker.compose.project=$project" \
    --filter "label=com.docker.compose.service=hnode_${1}_host_0") || return
  test "$(wc -w <<< "$ids")" -eq 1 || return 1
  printf '%s\n' "$ids"
}
remote() {
  local id
  id=$(peer "$1") || return
  shift
  timeout 90 docker exec "$id" cardano-cli conway "$@" --testnet-magic "$magic" --socket-path /cardano/node.socket
}
inventory() {
  for n in 150 151 152 153; do
    id=$(peer "$n") || return
    docker exec "$id" cardano-node --version | grep 'cardano-node 11.1.3' || return
    docker exec "$id" cardano-cli --version | grep 'cardano-cli 11.2.3.0' || return
    docker exec "$id" sh -c 'sha256sum /cardano/*-genesis.json /cardano/config.json' | sort -k2 > "$evidence/as$n-genesis.sha256" || return
    docker inspect --format '{{json .Mounts}}' "$id" | jq -e --arg path "$db_root/as$n" \
      'any(.[]; .Type=="bind" and .Source==$path and .Destination=="/cardano/db")' || return
    docker exec "$id" cat /cardano/shelley-genesis.json | jq -e --argjson magic "$magic" '.networkMagic==$magic' || return
    remote "$n" query protocol-parameters > "$evidence/as$n-parameters.json" || return
    jq -e --argjson major "$major" '.protocolVersion == {major:$major,minor:0}' "$evidence/as$n-parameters.json" || return
    docker exec "$id" test -S /cardano/node.socket || return
    docker exec "$id" ss -Hlnt 'sport = :3001' | grep . || return
    docker exec "$id" ss -Hnt state established '( sport = :3001 or dport = :3001 )' | grep . || return
    diff -u "$evidence/expected-genesis.sha256" "$evidence/as$n-genesis.sha256" || return
  done
}
```

After compilation and before `up`, inspect `dc config`, `docker ps -a`, `docker network ls`, network IPAM, `ip route`, and `ss -ltn`. Require fresh per-AS mounts beneath the specified runtime, distinct bridge allocations, free fixed names and TCP/5000, and no overlapping non-default VM route. A different network magic alone does not isolate the emulators. After start, wait until after the generated UTC start, then run the inventory and collector. The collector records three rounds approximately 60 seconds apart and TCP/3001 PCAP counts and checksums. Review the summary for both advancing chain heights and a shared numbered point with the same hash, plus nonempty captures with passing hashes. If asynchronous tips do not share an observed height, collect more samples or verify a common numbered ancestor with a compatible read-only ChainDB/ChainSync reader.

## 3. Deploy B12-P9

Use the newly installed public Cardano bundle. Use the guard’s `--fresh-host` checks before starting containers and `--verify-running` afterward. These checks read Docker state.

```bash
p9="$root/p9"
compiler="$p9"
runtime="$p9/.runtime"
project=b12-p9
magic=4343
major=9
db_root="$runtime/cardano-data/testnet-conway-113-v2"
genesis="$p9/config/private-testnet-conway-v2/shelley-genesis.json"
keys="$p9/config/generated/testnet-conway-v2/stake-delegators"
guard="$repo/experiments/B12-P9/check-isolation.py"
helper="$repo/experiments/B12-P9/verify_plutus.py"
test -z "$(docker ps -aq)"
step p9-daemon 'Clean local Docker daemon' python "$guard" --fresh-host
step p9-stage 'Public P9 input staged' python "$repo/experiments/B12-P9/prepare.py" stage "$p9"
step p9-genesis 'Fresh magic 4343 genesis generated with protocol 9.0' python \
  "$repo/experiments/B12-P9/prepare.py" genesis "$p9" --bundle "$repo/resources/cardano/11.1.3" --minutes 90
step p9-genesis-manifest 'Magic 4343, protocol 9.0 and 251-entry Plutus V3 model' jq -e \
  '.magic == 4343 and .protocolVersion == {major:9,minor:0} and .plutusV3CostModelEntries == 251' \
  "$p9/b12-p9-genesis-manifest.json"
export CARDANO_EXPERIMENT_RUNTIME="$runtime"
cd "$p9"
jq -r '(.genesis | to_entries[] | "\(.value.sha256)  /cardano/\(.key)"), "\(.config_sha256)  /cardano/config.json"' \
  "$p9/b12-p9-genesis-manifest.json" | sort -k2 > "$evidence/expected-genesis.sha256"
step p9-compile 'SEED emitted independent P9 Compose' python blockchain.py amd
dc config > "$evidence/compose.normalized.yml"
step p9-isolate 'Fresh daemon, disjoint names, IPAM, ports and binds' python "$guard" \
  --fresh-host --compose "$evidence/compose.normalized.yml" --runtime "$runtime"
test "${approve_deploy_p9:-}" = YES
step p9-build 'P9 images built' dc build
step p9-start 'P9 services started' dc up -d --no-build
step p9-containers 'Running project matches the four planned Cardano containers and fresh binds' \
  python "$guard" --verify-running --compose "$evidence/compose.normalized.yml" --runtime "$runtime"
# Wait until the P9 genesis time and after peer sessions form.
step p9-inventory 'Four peers on the fresh network with protocol 9.0' inventory
step p9-inspect 'Four matching 9.0 parameter sets with 251 V3 model entries' python "$helper" inspect --project "$project"
step p9-collect 'Collector completed; review shared blocks, advancement and PCAPs' \
  python "$repo/scripts/collect-b12-phase-4b.py" --runtime "$runtime" --genesis-file "$genesis" --project "$project"
```

## 4. Compile the original validator

Install Aiken into the VM's private tools directory and use the exact release digest. The first build must resolve stdlib v4.0.0 through the published lockfile.

```bash
asset=aiken-x86_64-unknown-linux-musl.tar.gz
curl -fL --retry 3 -o "$root/downloads/$asset" "https://github.com/aiken-lang/aiken/releases/download/v1.1.24/$asset"
printf '%s  %s\n' c378acccdaf9533f3375ea623c948d3dcb21f7e8c5ecbb741162c53653470b13 "$root/downloads/$asset" | sha256sum -c -
mkdir "$root/aiken-release"
tar -xzf "$root/downloads/$asset" -C "$root/aiken-release"
mapfile -t binaries < <(find "$root/aiken-release" -type f -name aiken)
test "${#binaries[@]}" -eq 1
install -m 0755 "${binaries[0]}" "$root/bin/aiken"
export PATH="$root/bin:$PATH"
script="$root/sensor.plutus"
cd "$repo/experiments/B12-cardano/smart-contract/sensor-validation"
step aiken-version 'Aiken reports 1.1.24' bash -c 'aiken --version | grep -F "aiken v1.1.24"'
step aiken-tests 'Original and measurement validator tests pass' aiken check
step aiken-build 'Original Plutus V3 blueprint built' aiken build
aiken blueprint convert -m sensor_validator -v sensor_validator > "$script"
step aiken-hash 'Original compiled validator hash matches' bash -c '
  test "$("$1" conway transaction policyid --script-file "$2")" = 16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83
' _ "$cli" "$script"
```

[Official Aiken v1.1.24 asset and checksum](https://github.com/aiken-lang/aiken/releases/expanded_assets/v1.1.24)

## 5. Fund, evaluate and verify the Plutus V3 spend

Generate addresses locally from the new P9 verification keys. Review node ownership, funding balance and collateral output before using the selected values. Keep the script artifact, signed envelopes and operational evidence private. The helper builds unsigned transactions and performs evaluation. Each submission requires authorization for its exact signed transaction ID.

```bash
wallet() {
  "$cli" address build --payment-verification-key-file "$keys/delegator$1/payment.vkey" \
    --stake-verification-key-file "$keys/delegator$1/staking.vkey" --testnet-magic 4343
}
payout=$(wallet 1)
collateral_address=$(wallet 2)
script_address=$("$cli" address build --payment-script-file "$script" --testnet-magic 4343)
test "$script_address" = addr_test1wqt0dwxvl6u3w09cch70un8m5jxxshkjx93kayknz6ljeqctlj32q
remote 150 query utxo --address "$payout" > "$evidence/p9-funding-utxos.json"
remote 150 query utxo --address "$collateral_address" > "$evidence/p9-collateral-utxos.json"
funding_input=$(jq -er 'to_entries | map(select((.value.value|keys)==["lovelace"] and .value.value.lovelace>6000000)) |
  max_by(.value.value.lovelace).key' "$evidence/p9-funding-utxos.json")
collateral=$(jq -er 'to_entries | map(select((.value.value|keys)==["lovelace"] and .value.value.lovelace>1010000
  and .value.datum==null and .value.inlineDatum==null)) | min_by(.value.value.lovelace).key' "$evidence/p9-collateral-utxos.json")
collateral_lovelace=$(jq -er --arg ref "$collateral" '.[$ref].value.lovelace' "$evidence/p9-collateral-utxos.json")
funding_out="$root/p9-funding"
spend_out="$root/p9-spend"
step p9-funding-build 'Unsigned, balanced 5 ADA script output with original inline datum' python "$helper" funding \
  --project "$project" --cli "$cli" --script "$script" --input "$funding_input" \
  --payout "$payout" --output "$funding_out"
"$cli" conway transaction sign --tx-body-file "$funding_out/tx.body" \
  --signing-key-file "$keys/delegator1/payment.skey" --testnet-magic 4343 --out-file "$funding_out/tx.signed"

txid() {
  "$cli" conway transaction txid --tx-file "$1" |
    python -c 'import sys; from cardano_transaction import parse_txhash; print(parse_txhash(sys.stdin.read()))'
}
export PYTHONPATH="$repo/experiments/B12-cardano"
funding_id=$(txid "$funding_out/tx.signed")
script_index=$(jq -er --arg addr "$script_address" '[.outputs | to_entries[] | select(.value.address==$addr)] |
  if length==1 then .[0].key else error("expected one script output") end' "$funding_out/view.json")
script_input="$funding_id#$script_index"
printf 'Funding ID %s; script output %s\n' "$funding_id" "$script_input"

submit_exact() {
  local signed=$1 approved=$2 computed id staged
  computed=$(txid "$signed") || return
  test "$computed" = "$approved" || return 1
  id=$(peer 150) || return
  staged="/tmp/b12-rehearsal-$computed.signed"
  docker cp "$signed" "$id:$staged" || return
  date -u '+%FT%TZ' >&2
  remote 150 transaction submit --tx-file "$staged" || return
  date -u '+%FT%TZ' >&2
}
# Set approved_funding to the separately approved exact ID.
step p9-funding-send 'Exact funding command accepted; inclusion is checked separately' \
  submit_exact "$funding_out/tx.signed" "${approved_funding:?Approve the exact funding ID first}"
```

Poll confirmation with a deadline. Confirm exact funding-body ancestry on the four sampled chains, alongside the expected live 5 ADA script UTXO and inline datum on all four. If an observation is incomplete, gather diagnostics and retry only the read checks under a new acceptance ID.

```bash
funding_state() {
  local deadline=$((SECONDS + 180)) n response ready
  while (( SECONDS < deadline )); do
    ready=yes
    for n in 150 151 152 153; do
      response=$(remote "$n" query utxo --tx-in "$funding_input" --tx-in "$script_input") || return
      printf '%s\n' "$response" > "$evidence/p9-as$n-funding-utxo.json" || return
      if ! jq -e --arg prev "$funding_input" --arg ref "$script_input" --arg addr "$script_address" \
        --slurpfile datum "$repo/experiments/B12-P9/fixtures/agri-001.json" \
        'has($prev)|not' <<< "$response" >/dev/null ||
        ! jq -e --arg ref "$script_input" --arg addr "$script_address" \
        --slurpfile datum "$repo/experiments/B12-P9/fixtures/agri-001.json" \
        '.[$ref]|.address==$addr and .value=={lovelace:5000000} and .inlineDatum==$datum[0]' \
        <<< "$response" >/dev/null; then
        ready=no
      fi
    done
    if [[ $ready == yes ]]; then
      for n in 150 151 152 153; do
        remote "$n" query tip > "$evidence/p9-as$n-funding-tip.json" || return
      done
      python - "$db_root" "$evidence" "$funding_out/tx.signed" <<'PY'
import json, sys
from pathlib import Path
from block_proof import canonical_transaction, digest, envelope_body

db, evidence, signed = map(Path, sys.argv[1:])
original = envelope_body(signed)
proofs = {}
for n in range(150, 154):
    tip = json.loads((evidence / f'p9-as{n}-funding-tip.json').read_text())
    _, encoded, _, _, proof = canonical_transaction(db / f'as{n}', tip, digest(original))
    assert encoded == original
    proofs[n] = proof
assert all(proof == proofs[150] for proof in proofs.values())
print(json.dumps(proofs, indent=2))
PY
      return $?
    fi
    sleep 3
  done
  return 1
}
step p9-funding-proof 'Exact funding output and containing block agree on all four nodes' funding_state

build_spend() {
  python "$helper" spend --project "$project" --cli "$cli" --script "$script" \
    --input "$script_input" --collateral "$collateral" --collateral-address "$collateral_address" \
    --collateral-lovelace "$collateral_lovelace" --payout "$payout" --output "$1" --redeemer "$2"
}
step p9-positive 'Matching redeemer builds and returns live execution units and fees' \
  build_spend "$spend_out" agri-001.json

```

The original Aiken tests cover a matching ID, a mismatched ID, and missing datum. Inspect the positive live body, validity interval, total fee, collateral and return. Record the execution-only cost separately. The validator checks sensor-ID equality. Physical sensor authentication and measurement integrity are outside its behavior.

```bash
"$cli" conway transaction sign --tx-body-file "$spend_out/tx.body" \
  --signing-key-file "$keys/delegator2/payment.skey" --testnet-magic 4343 --out-file "$spend_out/tx.signed"
spend_id=$(txid "$spend_out/tx.signed")
payout_lovelace=$(jq -er '.outputs | if length==1 then .[0].amount.lovelace else error("expected one payout") end' "$spend_out/view.json")
printf 'Spend ID %s\n' "$spend_id"
# Start the optional bounded TCP/3001 capture before authorizing submission.
# Set approved_spend to the separately approved exact ID.
step p9-spend-send 'Exact spend command accepted; inclusion is checked separately' \
  submit_exact "$spend_out/tx.signed" "${approved_spend:?Approve the exact spending ID first}"
# After observing the payout, retain it and collateral unspent while verifying all four chains.
step p9-spend-proof 'Exact original body, shared block, consumed input, payout and retained collateral' \
  python "$helper" verify-spend --project "$project" --db-root "$db_root" --signed "$spend_out/tx.signed" \
  --input "$script_input" --collateral "$collateral" --output-ref "$spend_id#0" \
  --payout "$payout" --lovelace "$payout_lovelace"
```

## 6. Acceptance and evidence checklist

Use the new run’s `acceptance.tsv`. Each automated entry has the command or shell function invoked, exit status, expected output, actual stdout and stderr file references, evidence root and result. Retain this runbook revision with the log so the bodies of shell functions remain traceable. If a predicate needs review, record a separate row containing the reviewer decision, the predicate, the evidence file and its PASS/FAIL result. A successful collector command only shows that collection completed.

| Gate | Expected output and artifacts |
| --- | --- |
| Source and host | Requested published commit, expected versions or recorded deviations, local Docker engine ID recorded, dependency versions and host/disk UTC inventory present. |
| Genesis and Compose | Fresh magic-4343 genesis. Compare live hashes to the generated configuration and verify agreement across all four peers. Check hard forks through Conway at epoch zero. Separate mounts and namespaces, configuration checks, image IDs and successful startup recorded. |
| Consensus and captures | All four Cardano sockets and TCP/3001 sessions, advancing heights and a same-height same-hash common point. Save per-node tips and protocol parameters. Record capture interval, packet counts, decode output and matching checksums. A header-only capture fails the traffic gate. |
| P9 evaluation and execution | 9.0 and 251 V3 entries, three original Aiken checks, original script hash, one successful live evaluation. Funding and spend agree across four nodes. Save script fee, total fee, execution units, UTXO checks and block proofs. |
| Final integrity | Verify the evidence manifest, all private archives remain outside Git, original networks uncontacted and no resource deletion. |

Keep `$root` private. Under `$root/evidence` retain the listed logs, proof JSONs and acceptance table. Save genesis hashes and Compose/image inventory with that evidence. The collector saves its own raw logs, tip observations and capture manifests under each `$runtime/evidence` and `$runtime/captures`. After collection stops, archive or copy new collector files into a private evidence subtree, preserving references in PCAP manifests. Save any spend capture summaries there too. Keep signed envelopes, generated keys, build contexts and backups separate from evidence intended for release. Capture SHA-256 manifests identify bytes without replacing packet inspection.

```bash
# Run after collection is complete. A rerun writes the manifest outside the hashed tree.
(cd "$evidence" && find . -type f -print0 | sort -z | xargs -0 -r sha256sum) > "$root/evidence.sha256"
(cd "$evidence" && sha256sum -c "$root/evidence.sha256")
git -C "$repo" status --short --untracked-files=all
```

## 7. Failure handling

| Symptom | Safe response |
| --- | --- |
| Missing package, DNS, TLS, registry, or checksum failure | Record the URL, expected digest and error. Diagnose clock, DNS, approved mirrors and package availability. Retry only documented sources and verify the digest before extraction. A warm cache or supplied historical container image would invalidate the cold provisioning gate. |
| Docker socket permission or unexpected engine | Correct the selected local context or request VM-admin access. Verify the daemon ID and labels before retry. Never widen socket permissions or switch to the historical host. |
| Container name, subnet, host route, or port conflict | Stop before deployment. Record Compose and daemon inventories and use another isolated clean VM or an approved network design reviewed as a deviation. Preserve the conflicting resources. |
| Genesis timing and startup | Compare synchronized UTC, start time, startup args, node logs, genesis references, process, socket and DB mounts. Before genesis, allow the planned wait. If startup missed the window, preserve the attempt and diagnose before a newly authorized run in a fresh directory. Keep existing genesis and DBs intact. |
| Missing V3 cost model or wrong protocol | Stop P9 construction. Compare live parameters on all nodes and inspect the actual mounts, genesis and hard-fork settings. Changing a JSON file after startup cannot repair effective ledger parameters. |
| Unfunded or unexpected UTXO | Confirm address derivation with generated public keys and query the correct magic from all nodes. Confirm collateral is distinct and currently unspent, and review min-UTXO and fees. Treat ambiguous submission as unresolved until chain state is verified. |
| Script evaluation failure | Verify hash, inline datum, redeemer, signer material, collateral, era, validity interval and cost model. Compare CLI diagnostics with the positive and negative gates. Preserve failed artifacts and rebuild from confirmed current ledger state only after diagnosis and any needed approval. |
| Graceful shutdown timeout | Keep the affected containers, preserve process and database diagnostic logs and inspect privately. Wait for clean closure before taking a DB archive. |

## Results

| Gate | Command / evidence | Exit and observation | Result |
| --- | --- | --- | --- |
