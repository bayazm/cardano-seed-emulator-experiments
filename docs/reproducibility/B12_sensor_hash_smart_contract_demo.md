# B12-P9 sensor measurement integrity demo

**Prepared. Live execution requires approval.** Use one clean Ubuntu VM and one fresh four-node B12-P9 network with Conway protocol 9.0 and magic 4343. This uses a separate Plutus V3 script from the original sensor-ID validator. The two scripts have different addresses.

## Byte format and commitment

The test fixture is the following UTF-8 byte sequence, with a literal ASCII hyphen, vertical-bar separators, and no trailing newline, whitespace, or byte-order mark.

```text
AGRI-002|2026-11-20T10:00:00Z|23.6|61
```

The fields are sensor ID, UTC timestamp in the displayed seconds-and-`Z` form, Celsius temperature with one fractional digit, and relative humidity as an integer percent. The demo generator uses the exact displayed formatting. `23.60` is a different byte sequence. The SHA-256 commitment is `b76cef7674424ef76659031a5cf22f1d9b38316c2fe1e71cdbd12c75fc30ac26`.

The 5 ADA funding output contains constructor 0 with the expected sensor-ID bytes and 32-byte SHA-256 hash. The spend redeemer contains constructor 0 with the claimed ID and exact measurement bytes. The validator resolves its own input, requires an inline datum on that output, decodes both records, compares IDs and computes SHA-256 on-chain over the redeemer's bytes. The funding output fixes the commitment before spending. Both comparisons must succeed. [Validator and unit tests](../../experiments/B12-cardano/smart-contract/sensor-validation/validators/sensor_hash_validation.ak) · [Fixture generator](../../experiments/B12-P9/generate_sensor_hash_fixtures.py) · [Deterministic example fixtures](../../experiments/B12-P9/fixtures/sensor-hash/)

## 1. Prepare the network, fixtures and compiled script

Use sections 1–3 of the [single-VM runbook](B12_fresh_host_rehearsal.md) in one Bash session. They establish the shell variables and functions below. Obtain deployment approval before starting the fresh network. Require AS150–AS152 producers and AS153 relay, peer connections, a shared block hash, and 251 live Plutus V3 model entries. Then compile this script locally.

```bash
fixtures="$root/hash-fixtures"
python3 "$repo/experiments/B12-P9/generate_sensor_hash_fixtures.py" "$fixtures"
python3 "$repo/experiments/B12-P9/generate_sensor_hash_fixtures.py" "$fixtures" --verify
project_source="$repo/experiments/B12-cardano/smart-contract/sensor-validation"
script="$root/sensor_hash_validation.plutus"
(
  cd "$project_source"
  aiken --version
  aiken check
  aiken build
  aiken blueprint convert -m sensor_hash_validation -v sensor_hash_validation > "$script"
)
script_hash=$("$cli" conway transaction policyid --script-file "$script")
test "$script_hash" = f7b1435250172148a3c6c2fc5eccf212062d314cd11744018af5fa29
```

The offline evaluator uses synthetic UTXOs and an unsigned body. Supply protocol parameters, era history and genesis start time from the same protocol-9 context and any valid testnet payment address for the synthetic payout.

```bash
bash "$repo/experiments/B12-P9/evaluate_sensor_hash_offline.sh" \
  "$cli" "$script" "$protocol_params" "$era_history" "$system_start_utc" "$testnet_payout" "$root/hash-offline"
```

[Offline verification report](B12_sensor_hash_offline_verification.md)

## 2. Fund with AGRI-002 and verify inclusion

Generate addresses locally from the new P9 verification keys. Review node ownership, funding balance and collateral output before using the selected values. Keep the script artifact, signed envelopes and operational evidence private. The helper builds unsigned transactions and performs evaluation. Each submission requires authorization for its exact signed transaction ID.

```bash
wallet() {
  "$cli" address build --payment-verification-key-file "$keys/delegator$1/payment.vkey" \
    --stake-verification-key-file "$keys/delegator$1/staking.vkey" --testnet-magic 4343
}
payout=$(wallet 1)
collateral_address=$(wallet 2)
script_address=$("$cli" address build --payment-script-file "$script" --testnet-magic 4343)
test "$script_address" = addr_test1wrmmzs6j2qtjzj9rcmp0chkv7gfqvtf3fng3w3qp3t6l52g76x36q
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
  --script-hash "$script_hash" --datum-file "$fixtures/datum.json" --payout "$payout" --output "$funding_out"
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
        --slurpfile datum "$fixtures/datum.json" \
        'has($prev)|not' <<< "$response" >/dev/null ||
        ! jq -e --arg ref "$script_input" --arg addr "$script_address" \
        --slurpfile datum "$fixtures/datum.json" \
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
```

## 3. Evaluate the matching and incorrect redeemers

```bash
build_spend() {
  python "$helper" spend --project "$project" --cli "$cli" --script "$script" \
    --input "$script_input" --collateral "$collateral" --collateral-address "$collateral_address" \
    --collateral-lovelace "$collateral_lovelace" --payout "$payout" --output "$1" --script-hash "$script_hash" --datum-file "$fixtures/datum.json" --redeemer-file "$fixtures/$2"
}
step p9-positive 'AGRI-002 validates with live execution units and fees' \
  build_spend "$spend_out" redeemer.json

reject_measurement_case() {
  local name=$1 log="$evidence/$1-evaluation.txt" rc=0
  build_spend "$root/p9-$name" "$name.json" > "$log" 2>&1 || rc=$?
  cat "$log"
  test "$rc" -ne 0 || return 1
  grep -Eiq 'Plutus script at:|ScriptWitnessIndexTxIn|script evaluation failed' "$log" || return 1
  grep -Fq "$script_hash" "$log"
}
for case in wrong-id wrong-temperature wrong-humidity; do
  step "hash-$case" 'The measurement validator rejects this candidate locally' reject_measurement_case "$case"
done
```

Expect a positive cost entry for this script hash in `$spend_out/execution-cost.json` and a balanced payout, fee and collateral in `view.json`. The negative candidates use the same confirmed input and collateral. Review their evaluation traces for the failed script. A missing UTXO, expired interval or network error is inconclusive. The negative candidates stay unsigned. Live units and total fees are determined by the live evaluation.

## 4. Submit the approved spend and verify four-node inclusion

```bash
"$cli" conway transaction sign --tx-body-file "$spend_out/tx.body" \
  --signing-key-file "$keys/delegator2/payment.skey" --testnet-magic 4343 --out-file "$spend_out/tx.signed"
spend_id=$(txid "$spend_out/tx.signed")
payout_lovelace=$(jq -er '.outputs | if length==1 then .[0].amount.lovelace else error("expected one payout") end' "$spend_out/view.json")
printf 'Spend ID %s\n' "$spend_id"
# Set approved_spend to the separately approved exact ID.
step p9-spend-send 'Exact spend command accepted; inclusion is checked separately' \
  submit_exact "$spend_out/tx.signed" "${approved_spend:?Approve the exact spending ID first}"
# After observing the payout, retain it and collateral unspent while verifying all four chains.
step p9-spend-proof 'Exact original body, shared block, consumed input, payout and retained collateral' \
  python "$helper" verify-spend --project "$project" --db-root "$db_root" --signed "$spend_out/tx.signed" \
  --input "$script_input" --collateral "$collateral" --output-ref "$spend_id#0" \
  --payout "$payout" --lovelace "$payout_lovelace"
```



## Security limits

Successful hash verification demonstrates byte equality with a previously funded commitment. It **does not prove sensor authenticity or measurement truthfulness**. The funder can commit to fabricated bytes. The validator treats the measurement as opaque bytes and leaves timestamp freshness, format validation, embedded field interpretation, and physical provenance to the application. It imposes no sensor-specific signing requirement. Anyone who obtains the matching preimage can satisfy the script if the rest of the transaction is valid, and the redeemer exposes the measurement in the ledger. Use synthetic measurements for this public demonstration. CIP-20 auxiliary metadata is separate from the datum and redeemer.

Keep the funding and spend approvals separate. Record the signed transaction IDs, script evaluations, confirmed block anchors and proof output. Keep signed envelopes, keys and databases private.
