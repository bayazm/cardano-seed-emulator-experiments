#!/usr/bin/env bash
# Evaluate unsigned synthetic transactions using a protocol-9 ledger snapshot.
set -euo pipefail
umask 077

if [[ $# != 7 ]]; then
  echo "Usage: bash $0 CLI SCRIPT PARAMS ERA_HISTORY SYSTEM_START TESTNET_PAYOUT NEW_OUTPUT" >&2
  exit 2
fi
cli=$1
script=$2
params=$3
era_history=$4
start=$5
payout=$6
out=$7
helpers=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
jq -e '.protocolVersion == {major:9,minor:0} and (.costModels.PlutusV3 | length)==251' "$params"
mkdir -m 700 "$out"
python3 "$helpers/generate_sensor_hash_fixtures.py" "$out/fixtures" > "$out/fixture-hash.txt"
script_hash=$("$cli" conway transaction policyid --script-file "$script")
script_address=$("$cli" address build --payment-script-file "$script" --testnet-magic 4343)
printf '%s\n' "$script_hash" > "$out/script-hash.txt"
printf '%s\n' "$script_address" > "$out/script-address.txt"

datum_hash=$("$cli" conway transaction hash-script-data --script-data-file "$out/fixtures/datum.json")

printf -v script_ref '%064x#0' 1
printf -v collateral_ref '%064x#0' 2
jq -n --arg script_ref "$script_ref" --arg collateral_ref "$collateral_ref" \
    --arg script_addr "$script_address" --arg payout "$payout" --arg datum_hash "$datum_hash" \
    --slurpfile datum "$out/fixtures/datum.json" '
    {
      ($script_ref): {address:$script_addr, value:{lovelace:5000000},
                      datum:null, datumhash:null, inlineDatum:$datum[0], inlineDatumhash:$datum_hash, referenceScript:null},
      ($collateral_ref): {address:$payout, value:{lovelace:2000000},
                          datum:null, datumhash:null, inlineDatum:null, inlineDatumhash:null, referenceScript:null}
    }' > "$out/synthetic-utxos.json"

for case in redeemer wrong-id wrong-temperature wrong-humidity wrong-serialization malformed; do
  body="$out/$case.body"
  "$cli" conway transaction build-raw --tx-in "$script_ref" --tx-in-script-file "$script" \
    --tx-in-inline-datum-present --tx-in-redeemer-file "$out/fixtures/$case.json" \
    --tx-in-execution-units '(0,0)' --tx-in-collateral "$collateral_ref" \
    --tx-out "$payout+4990000" --fee 10000 --protocol-params-file "$params" --out-file "$body"
  if "$cli" conway transaction calculate-plutus-script-cost offline \
      --start-time-utc "$start" --era-history-file "$era_history" \
      --utxo-file "$out/synthetic-utxos.json" --protocol-params-file "$params" --tx-file "$body" \
      > "$out/$case.cost.json" 2> "$out/$case.stderr"; then
    rc=0
  else
    rc=$?
  fi
  printf '%s\n' "$rc" > "$out/$case.exit"
  if [[ $case == redeemer ]]; then
    if [[ $rc != 0 ]]; then cat "$out/$case.stderr" >&2; exit "$rc"; fi
    jq -e --arg hash "$script_hash" '
      length==1 and .[0].scriptHash==$hash and
      .[0].executionUnits.memory>0 and .[0].executionUnits.steps>0' "$out/$case.cost.json"
  else
    test "$rc" -ne 0
    grep -Fq "$script_hash" "$out/$case.stderr"
    grep -Eq 'Plutus script at:|ScriptWitnessIndexTxIn' "$out/$case.stderr"
  fi
  printf '%s exit=%s\n' "$case" "$rc"
done
