# B12 portable reproduction and evidence checks

Use [installation](install.md) and the [B12 experiment launcher](../../experiments/B12-cardano/README.md) on a dedicated x86-64 Ubuntu Docker host. The historical environment used standalone Compose 1.27.4 and Python 3.8.10. Install the pinned SEED checkout, Bash, jq, tcpdump and the Python packages below in an isolated environment. Keep generated keys, signed envelopes, logs and DBs in an ignored private root. The dependency pins record the tested environment. Review them before choosing a newer execution environment.

```bash
python3 -m pip install -r experiments/B12-cardano/reproduction-requirements.txt
bash scripts/setup-cardano.sh B12
```

## B12-4242 and the benchmark

Follow the [fresh-genesis and Compose instructions](../../experiments/B12-cardano/README.md). Record the actual runtime root from the Compose mounts and set `project` to the deployed Compose label. Ensure that AS150–AS153 are running and that the live network reports Conway protocol 2.0 with magic 4242. Use the operator's runtime and public genesis file to collect consensus and TCP/3001 evidence.

```bash
python3 scripts/collect-b12-phase-4b.py --project "$project" \
  --runtime "$runtime" --genesis-file "$shelley_genesis"
runner=experiments/B12-cardano/benchmark_reproduction.py
python3 "$runner" plan
(cd docs/results/b12 && sha256sum -c SHA256SUMS)
python3 "$runner" summarize docs/results/b12/benchmark-trials.csv > /tmp/b12-recomputed-summary.json
diff -u docs/results/b12/benchmark-summary.json /tmp/b12-recomputed-summary.json
```

The benchmark plan preserves the exact ten historical rounds of A basic ADA, B CIP-20 label 674 and C synthetic industrial metadata label 1000. The previous paired tool remains available for its separate 20-trial methodology. For a single build-only transfer, use the README's `cardano_transaction.py` procedure with no metadata flag. Set it to the original [CIP-20 or synthetic AGRI-002 fixtures](../../experiments/B12-cardano/benchmark-fixtures/) for standalone metadata builds.

Only run the following after authorizing **30 new testnet submissions** on your own deployment. Set `db_root` to the parent of the four mounted AS directories, `keys_root` to the generated stake-delegators directory, `cli` to the pinned Cardano CLI and `output` to a fresh private directory. Fund the generated sender with at least 65 ADA and avoid concurrently spending from the benchmark wallets.

```bash
python3 "$runner" run --project "$project" --db-root "$db_root" \
  --keys-root "$keys_root" --cli "$cli" --output "$output" --authorize-submit B12-4242
```

The runner uses each confirmed change as the next input and stops on an unresolved or failed trial. It records submit command duration, first observed exact UTXO state on each node, delay against the earliest peer and the observation spread. Polling starts after the submission response on a three-second schedule. The deadline is 180 seconds from monotonic command start. These are observation times. Forging times and finality are outside the measurement. Every verified row requires four-node UTXO agreement and containing-block hashes linked to the sampled tips. Report mean, median, min, max, sample standard deviation and nearest-rank p95 over successful trials, along with fee and size. Ten trials per workload support descriptive comparisons. Raw observations remain private. Use the [operations guide](operations.md) for independent optional packet capture.

## B12-P9 validator

Use the [P9 deployment guide](B12_P9_plutus_v3_guide.md) with disjoint runtime, genesis, keys and Docker resources. In a fresh VM obtain the original engine ID from the operator's B12-4242 inventory when comparing against it. Use an isolated Docker daemon and verify there are no shared fixed names, ports or subnets. The deployment must be running for live inspection and transaction construction, and it must have matching protocol 9.0 parameters and a 251-entry V3 cost model.

From the repository root set `repo=$PWD` and the absolute `cli` path. Point `script` at a private writable path for the exported script.

```bash
(cd "$repo/experiments/B12-cardano/smart-contract/sensor-validation" &&
  aiken --version && aiken check && aiken build && aiken blueprint convert -m sensor_validator -v sensor_validator > "$script")
test "$("$cli" conway transaction policyid --script-file "$script")" = \
  16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83
helper="$repo/experiments/B12-P9/verify_plutus.py"
python3 "$helper" inspect --project "$p9_project"
```

Derive both generated wallet addresses as in the P9 guide. Select a pure-ADA `funding_input` from the payout wallet and a separate pure-ADA collateral output controlled by its corresponding wallet. Use fresh output directories. The commands below build unsigned bodies and the spend command evaluates the original script on the live ledger. They perform no signing or submission.

```bash
python3 "$helper" funding --project "$p9_project" --cli "$cli" --script "$script" \
  --input "$funding_input" --payout "$payout" --output "$funding_out"

# Run only once the separately authorized funding output is confirmed.
python3 "$helper" spend --project "$p9_project" --cli "$cli" --script "$script" \
  --input "$script_input" --collateral "$collateral" --collateral-address "$collateral_address" \
  --collateral-lovelace "$collateral_lovelace" --payout "$payout" --output "$spend_out"
```

The positive spend expects the exact 5 ADA script output and inline `AGRI_001` datum. Review `view.json` for validity, payout, collateral and total fee, and `execution-cost.json` for the separately measured script fee and execution units. To exercise local failures, use a fresh output directory with `--redeemer agri-002.json` or `--redeemer malformed.json`. The expected failure occurs at build or evaluation. The original validator checks sensor-ID equality. Physical sensor authenticity and measurement integrity are outside its logic.

After a separately authorized spend, supply the original signed envelope and the observed payout. The verifier checks spend input consumption, retained collateral, expected output and exact transaction-body bytes on the canonical chain sampled at each node. Run while payout and collateral remain unspent. The offline command works with a private saved block and original envelope and checks inclusion within that block, independent of Docker.

```bash
python3 "$helper" verify-spend --project "$p9_project" --db-root "$p9_db_root" \
  --signed "$signed" --input "$script_input" --collateral "$collateral" \
  --output-ref "$payout_ref" --payout "$payout" --lovelace "$payout_lovelace"
python3 "$helper" verify-block --block "$saved_block" --signed "$signed" --block-hash "$saved_hash"
```

The block reader targets the tested Conway ChainDB format. If a live chunk moves while being read, resample and retry. For another storage format obtain a compatible read-only ChainSync source. [Public evidence and limits](../results/b12/README.md) · [Historical recovery and graceful shutdown](B12_4242_recovery_verification.md)
