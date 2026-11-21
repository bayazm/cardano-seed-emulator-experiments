#!/usr/bin/env python3
"""Inspect, build without signing, or verify Conway Plutus V3 transactions."""
import argparse
from math import ceil
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "B12-cardano"))
from block_proof import canonical_transaction, digest, envelope_body, parts
from cardano_transaction import run

PEERS = range(150, 154)
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SENSOR_FIXTURES = ("agri-001.json", "agri-002.json", "agri-002-demo.json")
SCRIPT_HASH = "16f6b8ccfeb9173cb8c5fcfe4cfba48c685ed231636e92d316bf2c83"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def cli(node, *args):
    return run(["docker", "exec", node, "cardano-cli", "conway", *args,
                "--testnet-magic", "4343", "--socket-path", "/cardano/node.socket"],
               timeout=90)


def query(node, *args):
    return json.loads(cli(node, "query", *args))


def preflight(project):
    nodes, tips = {}, {}
    genesis_identity = set()
    for asn in PEERS:
        ids = run(["docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={project}",
                   "--filter", f"label=com.docker.compose.service=hnode_{asn}_host_0"]).splitlines()
        check(len(ids) == 1, f"Expected a single running AS{asn}")
        node = nodes[asn] = ids[0]
        genesis = run(["docker", "exec", node, "cat", "/cardano/shelley-genesis.json"])
        check(json.loads(genesis)["networkMagic"] == 4343, "Wrong network magic")
        genesis_identity.add(genesis)
        tip = tips[asn] = query(node, "tip")
        check(tip["era"] == "Conway" and tip.get("block") is not None, "Expected numbered Conway tip")
        parameters = query(node, "protocol-parameters")
        check(parameters["protocolVersion"] == {"major": 9, "minor": 0}, "Expected protocol 9.0")
        check(len(parameters["costModels"]["PlutusV3"]) == 251, "Unexpected Plutus V3 model size")
        check(parameters["collateralPercentage"] > 0 and parameters["maxCollateralInputs"] >= 1,
              "Collateral is unavailable")
        check(all(float(v) > 0 for v in parameters["executionUnitPrices"].values()),
              "Execution prices must be positive")
        if asn == 150:
            expected = parameters
        check(parameters == expected, "Nodes disagree on protocol parameters")
    check(len(genesis_identity) == 1, "Nodes disagree on Shelley genesis")
    return nodes, tips, expected


def utxos(node, *refs):
    return query(node, "utxo", *(flag for ref in refs for flag in ("--tx-in", ref)))


def ada(entry):
    value = entry["value"]
    check(set(value) == {"lovelace"}, "Expected an ADA-only UTXO")
    return value["lovelace"]


def build(args, nodes, tips, parameters):
    node = nodes[150]
    script_hash = run([args.cli, "conway", "transaction", "policyid", "--script-file", args.script])
    check(script_hash == args.script_hash, "Unexpected validator hash")
    script_address = run([args.cli, "address", "build", "--payment-script-file",
                          args.script, "--testnet-magic", "4343"])
    datum = args.datum_file or FIXTURES / args.datum
    output = args.output
    output.mkdir(mode=0o700)
    prefix = "/tmp/b12-p9-" + uuid.uuid4().hex
    flags = ["--tx-in", args.input, "--change-address", args.payout]
    remote_files = []

    def copy(path, extension):
        name = prefix + extension
        run(["docker", "cp", path, f"{node}:{name}"])
        remote_files.append(name)
        return name

    try:
        if args.mode == "funding":
            for peer in nodes.values():
                selected = utxos(peer, args.input)[args.input]
                check(ada(selected) > 5_000_000 and selected["address"] == args.payout,
                      "Funding input must belong to the supplied payout address")
            input_lovelace = ada(selected)
            flags += ["--tx-out", f"{script_address}+5000000",
                      "--tx-out-inline-datum-file", copy(datum, ".datum.json")]
        else:
            check(args.input != args.collateral, "Script input and collateral must differ")
            input_lovelace = 5_000_000
            expected_datum = json.loads(datum.read_text())
            for peer in nodes.values():
                entries = utxos(peer, args.input, args.collateral)
                script_entry, collateral = entries[args.input], entries[args.collateral]
                check(script_entry["address"] == script_address and ada(script_entry) == 5_000_000
                      and script_entry["inlineDatum"] == expected_datum,
                      "Expected confirmed 5 ADA script input with original datum")
                check(collateral["datum"] is None and collateral["inlineDatum"] is None,
                      "Collateral must be a plain payment output")
                check(ada(collateral) == args.collateral_lovelace and
                      collateral["address"] == args.collateral_address,
                      "Collateral differs from the supplied output")
            check(args.collateral_lovelace > 1_010_000, "Collateral must leave at least 1 ADA return")
            script = copy(args.script, ".plutus")
            redeemer = copy(args.redeemer_file or FIXTURES / args.redeemer, ".redeemer.json")
            flags += ["--tx-in-script-file", script, "--tx-in-inline-datum-present",
                      "--tx-in-redeemer-file", redeemer, "--tx-in-collateral", args.collateral,
                      "--tx-total-collateral", "10000", "--tx-out-return-collateral",
                      f"{args.collateral_address}+{args.collateral_lovelace - 10000}"]
        slot = tips[150]["slot"]
        body = prefix + ".body"
        remote_files.append(body)
        log = cli(node, "transaction", "build", *flags, "--invalid-before", str(slot),
                  "--invalid-hereafter", str(slot + 7200), "--out-file", body)
        (output / "build.log").write_text(log + "\n")
        run(["docker", "cp", f"{node}:{body}", output / "tx.body"])
        view = run([args.cli, "debug", "transaction", "view", "--tx-body-file", output / "tx.body"])
        (output / "view.json").write_text(view + "\n")
        decoded = json.loads(view)
        check(decoded["era"] == "Conway" and decoded["validity range"] ==
              {"lower bound": slot, "upper bound": slot + 7200}, "Unexpected era or validity interval")
        fee = int(decoded["fee"].split()[0])
        outputs = decoded["outputs"]
        check(decoded["inputs"] == [args.input] and
              sum(x["amount"]["lovelace"] for x in outputs) + fee == input_lovelace,
              "Transaction does not balance")
        check(all(set(x["amount"]) == {"lovelace"} for x in outputs), "Expected ADA-only outputs")
        if args.mode == "spend":
            check(len(outputs) == 1 and outputs[0]["address"] == args.payout, "Payout mismatch")
            returned = decoded["return collateral"]
            check(decoded["collateral inputs"] == [args.collateral] and
                  returned["address"] == args.collateral_address and
                  returned["amount"] == {"lovelace": args.collateral_lovelace - 10000},
                  "Collateral input or return mismatch")
            check(decoded["total collateral"] == 10000 and
                  10000 >= ceil(fee * parameters["collateralPercentage"] / 100),
                  "Collateral does not cover the network requirement")
            costs = cli(node, "transaction", "calculate-plutus-script-cost", "online", "--tx-file", body)
            (output / "execution-cost.json").write_text(costs + "\n")
            [result] = json.loads(costs)
            check(result["scriptHash"] == script_hash and result["lovelaceCost"] <= fee,
                  "Execution result does not match the script or fee")
            check(all(0 < result["executionUnits"][unit] <= parameters["maxTxExecutionUnits"][unit]
                      for unit in ("memory", "steps")), "Execution exceeds transaction budget")
        else:
            [script_output] = [x for x in outputs if x["address"] == script_address]
            check(script_output["amount"] == {"lovelace": 5_000_000} and
                  script_output["datum"] == json.loads(datum.read_text()),
                  "Funding output mismatch")
            check(all(x["address"] in (script_address, args.payout) for x in outputs),
                  "Funding contains an unexpected output")
    finally:
        if remote_files:
            run(["docker", "exec", node, "rm", "-f", "--", *remote_files])


def reference(pair):
    return f"{pair[0].hex()}#{pair[1]}"


def verify(args, nodes, tips):
    original = envelope_body(args.signed)
    txid = digest(original)
    check(args.output_ref.startswith(txid + "#"), "Output reference must identify the signed spend")
    proofs = {}
    for asn, node in nodes.items():
        mounts = json.loads(run(["docker", "inspect", "--format", "{{json .Mounts}}", node]))
        database = args.db_root.resolve() / f"as{asn}"
        check(any(m["Type"] == "bind" and m["Destination"] == "/cardano/db" and
                  Path(m["Source"]).resolve() == database for m in mounts), "Incorrect database bind")
        body, encoded, _, _, proof = canonical_transaction(database, tips[asn], txid)
        check(original == encoded, "Original body byte mismatch")
        check(args.input in {reference(i) for i in body[0]}, "Script input absent from transaction body")
        check(args.collateral in {reference(i) for i in body[13]}, "Collateral absent from transaction body")
        entries = utxos(node, args.input, args.output_ref, args.collateral)
        check(args.input not in entries and args.collateral in entries, "Input/collateral state differs")
        output = entries[args.output_ref]
        check(output["address"] == args.payout and ada(output) == args.lovelace, "Payout differs")
        proofs[asn] = proof
    check(all(proof == proofs[150] for proof in proofs.values()), "Nodes disagree on block inclusion")
    return proofs


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    offline = modes.add_parser("verify-block", help="Verify a saved block against an original local signed envelope")
    offline.add_argument("--block", type=Path, required=True)
    offline.add_argument("--signed", type=Path, required=True)
    offline.add_argument("--block-hash", required=True)
    for mode in ("inspect", "funding", "spend", "verify-spend"):
        command = modes.add_parser(mode)
        command.add_argument("--project", required=True)
        if mode in ("funding", "spend"):
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--cli", type=Path, required=True)
            command.add_argument("--script", type=Path, required=True)
            command.add_argument("--script-hash", default=SCRIPT_HASH,
                                 help="Expected hash of --script (defaults to the original validator)")
            datum = command.add_mutually_exclusive_group()
            datum.add_argument("--datum", choices=SENSOR_FIXTURES, default="agri-001.json",
                               help="Inline datum fixture to create or require on the script input")
            datum.add_argument("--datum-file", type=Path, help="Custom inline datum JSON")
        if mode != "inspect":
            command.add_argument("--input", required=True)
            command.add_argument("--payout", required=True)
        if mode in ("spend", "verify-spend"):
            command.add_argument("--collateral", required=True)
        if mode == "spend":
            command.add_argument("--collateral-address", required=True)
            command.add_argument("--collateral-lovelace", type=int, required=True)
            redeemer = command.add_mutually_exclusive_group()
            redeemer.add_argument("--redeemer", default="agri-001.json",
                                  choices=(*SENSOR_FIXTURES, "malformed.json"))
            redeemer.add_argument("--redeemer-file", type=Path, help="Custom redeemer JSON")
        if mode == "verify-spend":
            command.add_argument("--signed", type=Path, required=True)
            command.add_argument("--db-root", type=Path, required=True)
            command.add_argument("--output-ref", required=True)
            command.add_argument("--lovelace", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "verify-block":
        header, raw_header, bodies, _, invalid = parts(args.block.read_bytes())
        check(digest(raw_header) == args.block_hash, "Unexpected containing block hash")
        original = envelope_body(args.signed)
        matches = [i for i, (_, raw) in enumerate(bodies) if raw == original and i not in invalid]
        check(len(matches) == 1, "Original body absent or marked invalid")
        print(json.dumps({"txid": digest(original), "block": header[0][0], "slot": header[0][1],
                          "block_hash": args.block_hash, "index": matches[0]}, indent=2))
        return
    nodes, tips, parameters = preflight(args.project)
    if args.mode == "inspect":
        print(json.dumps({"tips": tips, "parameters": parameters}, indent=2))
    elif args.mode == "verify-spend":
        print(json.dumps(verify(args, nodes, tips), indent=2))
    else:
        build(args, nodes, tips, parameters)


if __name__ == "__main__":
    main()
