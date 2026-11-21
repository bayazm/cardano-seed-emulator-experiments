# Minimal B12-P9 smart-contract demonstration

**Prepared for execution after approval.** Use one clean Ubuntu VM and one fresh four-node B12-P9 network. The demo consists of a 5 ADA funding transaction and one valid spend. Evaluate a third, mismatched candidate locally.

The funding output’s **inline datum** stores the ASCII sensor ID `AGRI-002`. The spending input’s **redeemer** supplies the sensor ID for the validator to compare with the datum. The original validator compares bytes. The new fixture encodes the hyphen as `2d`; the historical fixtures with underscores retain their original encodings.

## 1. Start the network, verify synchronization and compile

Follow sections 1–4 of the [single-VM runbook](B12_fresh_host_rehearsal.md) in one Bash session. Those sections provide the install, fresh-genesis, Compose startup and validator compilation commands, and establish the shell variables and functions used below. Stop at the deployment gate until authorization is granted. Use the fresh VM's local Docker daemon and new B12-P9 directories.

After startup, AS150–AS152 should run as producers and AS153 as relay. Require all four live node sockets, peer connections, advancing heights and a shared numbered block hash. The effective ledger parameters must show **Conway 9.0**, a 251-entry Plutus V3 cost model, and the genesis manifest must match the live configuration for magic **4343**. Compile the original validator with Aiken 1.1.24 and stdlib v4.0.0. Expect all three original tests to pass and the original script hash `16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83`.

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
test "$script_address" = addr_test1wqt0dwxvl6u3w09cch70un8m5jxxshkjx93kayknz6ljeqctlj32q
remote 150 query utxo --address "$payout" > "$evidence/p9-funding-utxos.json"
remote 150 query utxo --address "$collateral_address" > "$evidence/p9-collateral-utxos.json"
funding_input=$(jq -er 'to_entries | map(select((.value.value|keys)==["lovelace"] and .value.value.lovelace>6000000)) |
  max_by(.value.value.lovelace).key' "$evidence/p9-funding-utxos.json")
collateral=$(jq -er 'to_entries | map(select((.value.value|keys)==["lovelace"] and .value.value.lovelace>1010000
  and .value.datum==null and .value.inlineDatum==null)) | min_by(.value.value.lovelace).key' "$evidence/p9-collateral-utxos.json")
collateral_lovelace=$(jq -er --arg ref "$collateral" '.[$ref].value.lovelace' "$evidence/p9-collateral-utxos.json")
datum_fixture=agri-002-demo.json
funding_out="$root/p9-funding"
spend_out="$root/p9-spend"
step p9-funding-build 'Unsigned, balanced 5 ADA script output with original inline datum' python "$helper" funding \
  --project "$project" --cli "$cli" --script "$script" --input "$funding_input" \
  --datum "$datum_fixture" --payout "$payout" --output "$funding_out"
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
        --slurpfile datum "$repo/experiments/B12-P9/fixtures/$datum_fixture" \
        'has($prev)|not' <<< "$response" >/dev/null ||
        ! jq -e --arg ref "$script_input" --arg addr "$script_address" \
        --slurpfile datum "$repo/experiments/B12-P9/fixtures/$datum_fixture" \
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
    --collateral-lovelace "$collateral_lovelace" --payout "$payout" --output "$1" --datum "$datum_fixture" --redeemer "$2"
}
step p9-positive 'AGRI-002 validates with live execution units and fees' \
  build_spend "$spend_out" "$datum_fixture"

reject_wrong_id() {
  local log="$evidence/p9-wrong-sensor-evaluation.txt" rc=0
  build_spend "$root/p9-wrong-sensor" agri-001.json > "$log" 2>&1 || rc=$?
  cat "$log"
  test "$rc" -ne 0 || return 1
  grep -Eiq 'Plutus script at:|ScriptWitnessIndexTxIn|script evaluation failed' "$log" || return 1
  grep -Fq '16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83' "$log"
}
step p9-wrong-id 'Original validator rejects the distinct sensor ID during local evaluation' reject_wrong_id
```

The positive build writes `$spend_out/view.json` and `$spend_out/execution-cost.json`. Expect one payout, a balanced fee, explicit collateral and a cost result for the original script with positive memory and CPU units. The negative uses the existing `AGRI_001` fixture as the unequal byte string while keeping the script input and collateral the same. Review its log for a Plutus execution failure from the original script. A missing input, invalid collateral or Docker error is an inconclusive negative test. The negative body stays local and unsigned.

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


## Expected evidence and limits

- Funding proof shows the same transaction ID, block height, slot and block hash on all four sampled chains. Before spending, all four nodes report the 5,000,000-lovelace script UTXO with the exact AGRI-002 datum.
- Spend proof shows the same valid transaction body and block hash on all four chains. The original script UTXO is consumed, the expected payout exists and the collateral UTXO remains unspent. Keep the payout and collateral unspent until verification finishes. If peers are still catching up, repeat the read-only proof with a new acceptance ID. Resolve an ambiguous submission before trying to send again.
- The test demonstrates an equality check on publicly supplied bytes. A matching sensor ID does not authenticate a physical device, establish measurement accuracy, or verify a measurement hash. Wallet signatures authorize use of their respective funding inputs or collateral.
- CIP-20 is auxiliary transaction metadata. The existing script-spend helper has no metadata argument, so this demo uses only the datum and redeemer. A future CIP-20 attachment would require separate inclusion verification and would leave the validator's equality check unchanged.

Record the network checks, Aiken output, funding and spend proofs, live evaluation, negative trace and fee evidence under the fresh rehearsal evidence root. Keep keys, signed envelopes and database files private.
