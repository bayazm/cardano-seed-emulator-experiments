# B12-P9 Plutus V3 reproduction

**Sequential deployment verified.** After explicit same-host approval, B12-4242 was stopped and archived, and P9 was deployed and verified on the existing daemon. The separate-VM commands below remain an alternate procedure. Transaction submission requires separate authorization. [Executed cutover evidence](../results/b12/artifact-manifest.md#e007)

## Motivation and preservation

B12-4242 ran the Conway era under ledger protocol 2.0. Its cost model was present, but the CLI rejected V3 at that protocol version. Keep B12-4242 as the historical control and use B12-P9 solely for live execution of the original Aiken validator.

A new read-only sample confirmed all four original nodes at block **297**, slot **5817**, hash `3fa8da31474fa2ad1b6f28c2096552b7381130f379a29c7b96529307a4ae529d`. The local preservation archive at `.local-research/b12-4242-preservation/` holds the four public genesis files, original node configuration and peer topologies, the live queries and Docker inventory, the Phase 4B–5D evidence, and exact CBOR for the 32 blocks containing the 33 earlier transactions. All 33 transaction IDs and containing block hashes were rechecked by following the header chain from every sampled tip. Six available historical PCAP manifest checks passed. All copied artifacts are covered by `SHA256SUMS`. The archive excludes signing secrets and signed envelopes. The original databases stay live in their existing bind mounts. The copied blocks are verification artifacts and cannot restore a node database. [Local archive manifest](../results/b12/artifact-manifest.md#e008) · [Database paths and canonical anchors](../results/b12/artifact-manifest.md#e009)

| Control | B12-4242 | B12-P9 plan |
|---|---|---|
| History | Existing chain and original 33 verified transactions | Fresh chain with separate genesis and independently generated credentials |
| Magic and ledger version | 4242, Conway 2.0 | 4343, Conway 9.0, subject to live verification |
| Roles and routing | AS150–AS152 producers, AS153 relay, SEED routed P2P mesh | Same logical topology and TCP/3001 inside a different, isolated VM or Docker host |
| Tools | Cardano Node 11.1.3, CLI 11.2.3.0 | Same pinned release, plus Aiken 1.1.24 and stdlib 4.0.0 |

## File changes and genesis inputs

- [B12-P9 preparer](../../experiments/B12-P9/prepare.py) stages a whitelist of original public sources. It changes the copied Shelley **input specification** to magic 4343 and protocol 9.0. It updates the copied compiler's display text. It retains the original node configuration, topology and validator source.
- [Docker isolation guard](../../experiments/B12-P9/check-isolation.py) rejects the original daemon, existing B12 project membership, or collisions in the compiled deployment.
- [Validator fixtures](../../experiments/B12-P9/fixtures/) encode matching, mismatched and malformed redeemers. The offline-only staged tree is at `.local-research/b12-p9-prepared/`, with source digests in `b12-p9-source.json`.

The preparer uses the documented late-protocol testnet initialization. Set protocol 9.0 in the Shelley genesis input; configure `TestShelleyHardForkAtEpoch`, `TestAllegraHardForkAtEpoch`, `TestMaryHardForkAtEpoch`, `TestAlonzoHardForkAtEpoch`, `TestBabbageHardForkAtEpoch`, and `TestConwayHardForkAtEpoch` to zero. These are top-level keys for the pinned version. Keep experimental forks disabled and omit a Dijkstra override. Byron's protocol magic must equal the Shelley magic. Keep the historical `LastKnownBlockVersion` settings for Byron signaling. Effective script compatibility depends on the genesis-derived **ledger** protocol version. [Ouroboros Consensus testnet initialization](https://ouroboros-consensus.cardano.intersectmbo.org/docs/references/miscellaneous/era_transition_governance/#initializing-the-chain-with-a-later-protocol-version) · [Node 11.1.3 protocol initialization](https://github.com/IntersectMBO/cardano-node/blob/11.1.3/cardano-node/src/Cardano/Node/Protocol/Cardano.hs#L148)

For the authorized run, the preparer calls `cardano-cli conway genesis create-testnet-data --spec-shelley … --testnet-magic 4343` with three producer credential sets, three stake delegators, three additional UTXO wallets, no governance credentials, and a fresh shared start time. It verifies the **generated** Shelley 9.0 values, magic and start-time agreement, V3 vector presence, and collateral, fee and budget settings. It verifies the producer file set and regenerates node-config file references and hashes from the verified genesis bytes. The historical helper rewrites the version in generated Shelley genesis. B12-P9 instead stops before installing genesis if the pinned CLI changes the requested version. A mock test exercised 9.0 acceptance and rejection of fallback to 2.0. The real pinned CLI subsequently retained **9.0** and magic **4343** without a post-generation version rewrite. The private check also verified a distinct Byron and Shelley genesis identity, six distinct producer/payment public keys, matching configured genesis file digests, a 251-entry V3 model, 150% collateral, at most three collateral inputs, and positive execution prices and limits. Preserve the historical Alonzo and Conway controls, which can have identical bytes across networks. Use a new generation on the target VM so its keys and start time belong to the actual deployment. [Public genesis-check evidence](../results/b12/artifact-manifest.md#e010)

## Docker isolation

The live Docker inventory found the fixed AS150–AS153 container names, static `10.150.0.0/24` through `10.153.0.0/24` allocations, and the four original database mounts. The full compiler also emits router, host and IX bridge subnets and a fixed `seedemu_ether_view` container that publishes TCP **5000**. TCP **3001** is container-to-container and does not need a host port. A distinct Compose project name alone would leave fixed names, bridge IPAM and the published port in conflict.

Use another Linux VM with a dedicated Docker daemon. Keep its P2P bridges private and avoid overlaps between its own upstream routes and SEED's static subnets. Confirm the new VM has no local TCP/5000 listener and restrict external access to the EtherView endpoint at the VM/network boundary. The guard compares daemon IDs, Compose labels, names, Docker IPAM, listening host TCP ports, and database/capture mount roots. Run it **on the target VM** using the same local socket as Compose. The archive's Docker engine ID is the original daemon reference; transfer that small file for preflight. Move no original key, genesis, or runtime directory to the P9 VM.

A same-host sequential alternative requires a separately approved cutover and quiescent backup. [Sequential deployment and recovery](B12_P9_sequential_recovery.md)

### Proposed deployment commands

Use these approved deployment commands once a separate VM is available. On the new VM use a copy of the worktree checked against the source checksums, the [pinned SEED checkout and dependencies](install.md), and the checksum-verified Linux x86-64 Cardano bundle. Choose fresh absolute paths. Allow time for SEED compilation and Docker image builds when picking the genesis lead time.

```bash
set -euo pipefail
umask 077
unset DOCKER_CONTEXT
export DOCKER_HOST=unix:///var/run/docker.sock
repo=/path/to/reviewed-worktree
bundle=/path/to/cardano-11.1.3
run=/path/to/fresh-b12-p9-run
historical_engine=/path/to/copied-b12-4242-docker-engine-id.txt
cd "$repo"
python3 experiments/B12-P9/check-isolation.py --historical-engine-id "$historical_engine"
ip route
python3 experiments/B12-P9/prepare.py stage "$run"
python3 experiments/B12-P9/prepare.py genesis "$run" --bundle "$bundle" --minutes 45

export CARDANO_EXPERIMENT_RUNTIME="$run/.runtime"
cd "$run"
test ! -e output
test ! -e "$CARDANO_EXPERIMENT_RUNTIME"
python3 blockchain.py amd
cd output
docker-compose -p b12-p9 config -q
docker-compose -p b12-p9 config > "$run/compose-normalized.yml"
python3 "$repo/experiments/B12-P9/check-isolation.py" \
  --historical-engine-id "$historical_engine" --compose "$run/compose-normalized.yml" \
  --runtime "$CARDANO_EXPERIMENT_RUNTIME"
docker-compose -p b12-p9 build
docker-compose -p b12-p9 up -d
docker-compose -p b12-p9 ps
```

Only the P9 compiler may write its new output tree and runtime root. Generated contexts may contain KES/VRF credentials and stay private. Use the named P9 project and verify the daemon again if the Docker context changes. If preparation fails, review the fresh P9 run independently before choosing another empty P9 directory.

## Live compatibility gates

After genesis, check the four processes, Unix sockets and peer transport. From the P9 Compose directory, query each service:

```bash
for asn in 150 151 152 153; do
  service="hnode_${asn}_host_0"
  docker-compose -p b12-p9 exec -T "$service" cardano-cli conway query tip \
    --testnet-magic 4343 --socket-path /cardano/node.socket
  docker-compose -p b12-p9 exec -T "$service" cardano-cli conway query protocol-parameters \
    --testnet-magic 4343 --socket-path /cardano/node.socket
done
```

Save three tip rounds approximately 60 seconds apart. Verify that blocks advance and that all four agree on a numbered block hash. Verify the live genesis hashes and effective **Conway 9.0**, and compare effective protocol parameters across nodes. Confirm a nonempty `costModels.PlutusV3`, positive execution prices, `maxTxExecutionUnits` and `maxBlockExecutionUnits` above the measured budget, a nonzero collateral percentage and at least one permitted input. Record `txFeeFixed`, `txFeePerByte`, and `utxoCostPerByte`. Recompute min UTXO and fees from P9 parameters. Record node and CLI versions from the containers. A successful live cost evaluation of the exact positive spend is the execution gate. A version check alone is insufficient.

## Original validator and transaction runbook

Run Aiken 1.1.24 against the staged unchanged project and retain check/build logs, blueprint, and hashes.

```bash
cd "$run/smart-contract/sensor-validation"
aiken --version
aiken check
aiken build
aiken blueprint convert -m sensor_validator -v sensor_validator > "$run/sensor.plutus"
aiken blueprint hash -m sensor_validator -v sensor_validator
"$bundle/bin/cardano-cli" conway transaction policyid --script-file "$run/sensor.plutus"
"$bundle/bin/cardano-cli" address build --payment-script-file "$run/sensor.plutus" \
  --testnet-magic 4343 --out-file "$run/sensor.addr"
```

Expected Plutus V3 script hash is `16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83`. The expected enterprise testnet address is `addr_test1wqt0dwxvl6u3w09cch70un8m5jxxshkjx93kayknz6ljeqctlj32q`. Address encoding alone does not distinguish testnet magic. Before staging anything, verify P9's actual genesis, socket, magic, deployment project, and UTXOs. Verify the three original tests and the hash before using the address.

1. **Funding.** In P9, derive Delegator 1 and 2 base addresses from their fresh verification keys with `cardano-cli address build --payment-verification-key-file … --stake-verification-key-file … --testnet-magic 4343`. Query UTXOs by address. Choose a pure-ADA funding input from Delegator 1 and a distinct pure-ADA collateral UTXO from Delegator 2. If collateral is oversized, use explicit total collateral and return above minimum UTXO, or prepare a small split under separate transaction approval. Calculate the minimum for a 5 ADA script output with the matching `agri-001.json` inline datum. On AS150 build `conway transaction build --tx-in … --tx-out "$script_addr+5000000" --tx-out-inline-datum-file … --change-address …`. Use the P9 magic, socket and fresh inputs. Decode the body, verify input equals outputs plus fee, sign on the host with the fresh Delegator 1 payment key, and obtain approval for that signed transaction. Record the exact funding TXID and script output index. Verify funding inclusion, amount, address and inline datum on all four peers before building the spend.
2. **Positive spend.** Build against the confirmed script input with `--tx-in-script-file sensor.plutus --tx-in-inline-datum-present --tx-in-redeemer-file agri-001.json`. Include the distinct `--tx-in-collateral`, measured collateral amount and return if applicable, and the payout/change address. Use `--change-address` to return the script value minus the fee to Delegator 1. On AS150 run `conway transaction calculate-plutus-script-cost online --tx-file … --testnet-magic 4343 --socket-path /cardano/node.socket`. Save exact fees, collateral and units, check the balance, and sign locally with the fresh Delegator 2 collateral witness. The validator itself has no required signer. Obtain approval for the signed spend before staging it.
3. **Negative cases.** Evaluate `agri-002.json` against the `AGRI_001` datum and evaluate the integer fixture `malformed.json`. Exercise missing datum using an offline simulated script input. Log failure diagnoses and exit codes. Treat these as evaluations. The script compares two public byte strings and does not authenticate a physical sensor, check a signer or verify measurement hashes.
4. **Confirmation.** After approval of each exact signed envelope, stage only the envelope, record UTC and monotonic submission times, and call AS150 `cardano-cli conway transaction submit --tx-file … --testnet-magic 4343 --socket-path /cardano/node.socket`. Query the exact transaction output references and prior input on AS150–AS153. Verify that the spend consumed the script UTXO, credited the expected payout, and left collateral unspent. Record first observations and the containing block height, slot and hash. Use a read-only ChainSync source or the Phase 5B–5C block method to hash the transaction body and anchor its block to each node's observed chain. Confirm the spend index is absent from the block's invalid transaction set.
5. **Packets.** Start bounded `timeout --signal=INT … tcpdump -i net0 -nn -s 96 -U -w /captures/b12-p9-<UTC>-as<ASN>-tcp3001.pcap 'tcp port 3001'` on P9 AS150 and AS153 before the authorized spend. Stop after observation. Record start/end UTC, interface, duration, capture counters and drops. Decode the saved files offline for TCP/3001, count packets, then calculate and verify `sha256sum -c` manifests in the P9 evidence directory.

The Phase 5D offline reference was **18,728 memory units**, **6,057,476 steps**, and **1,518 lovelace** execution cost at the copied v9 pricing. It used a 2,500-lovelace draft fee and the one-witness estimate was 2,098 lovelace. Its 150% collateral setting implied 3,750 lovelace minimum at the draft fee. These are figures from the original evaluation fixture. P9 uses different input references and may have different effective prices or fee parameters. Exact funding and spend bodies, fees, collateral and transaction IDs require fresh live UTXOs and successful live evaluation. The historical signed funding envelope must stay on B12-4242.

## Remaining verification

The real genesis check passed. The authorized sequential cutover verified all four P9 nodes on Conway 9.0 with a V3 cost model and an advancing common chain. Live script execution remains pending. The original 2.0 chain and its evidence were preserved for recovery after P9.
