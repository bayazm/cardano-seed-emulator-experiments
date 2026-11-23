#!/usr/bin/env python3

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPLOYMENT = ROOT / "deployment/registry"

TOKEN_NAME = "B15_REGISTRY".encode().hex()

EXPECTED_NODE = "AS184"
EXPECTED_IP = "10.184.0.71"
EXPECTED_REVISION = 1

NETWORK_MAGIC = "5556"

AUTHORIZED_NODES = {
    "AS180": "b15-as180h-Cardano-Node-1-10.180.0.71",
    "AS181": "b15-as181h-Cardano-Node-2-10.181.0.71",
    "AS182": "b15-as182h-Cardano-Node-3-10.182.0.71",
    "AS183": "b15-as183h-Cardano-Node-4-10.183.0.71",
}


def registry_parameters():
    address = (DEPLOYMENT / "membership-script.addr").read_text().strip()
    policy = (DEPLOYMENT / "policy-id.txt").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{56}", policy):
        raise ValueError("Invalid registry policy ID")
    if not address:
        raise ValueError("Registry script address is missing")
    return address, policy


def query_registry(container, address):
    result = subprocess.run(
        [
            "docker", "exec", container,
            "cardano-cli", "query", "utxo",
            "--address", address,
            "--output-json",
            "--testnet-magic", NETWORK_MAGIC,
            "--socket-path", "/cardano/node.socket",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    return json.loads(result.stdout)


def decode_registry(datum):
    if (
        not isinstance(datum, dict)
        or datum.get("constructor") != 0
        or not isinstance(datum.get("fields"), list)
        or len(datum["fields"]) != 4
    ):
        raise ValueError("Invalid registry datum structure")

    fields = datum["fields"]

    node = bytes.fromhex(fields[0]["bytes"]).decode("utf-8")
    ip = bytes.fromhex(fields[1]["bytes"]).decode("utf-8")

    authorized_field = fields[2]

    if authorized_field not in (
        {"constructor": 0, "fields": []},
        {"constructor": 1, "fields": []},
    ):
        raise ValueError("Invalid authorization field")

    authorized = authorized_field["constructor"] == 1
    revision = fields[3]["int"]

    if type(revision) is not int or revision < 0:
        raise ValueError("Invalid registry revision")

    return {
        "node": node,
        "ip": ip,
        "authorized": authorized,
        "revision": revision,
    }


def find_registry(utxos, address, policy):
    matches = []

    for reference, output in utxos.items():
        quantity = (
            output.get("value", {})
            .get(policy, {})
            .get(TOKEN_NAME, 0)
        )

        if type(quantity) is not int or quantity < 0:
            raise ValueError("Invalid registry NFT quantity")
        if quantity:
            matches.append((reference, output, quantity))

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one registry output; found {len(matches)}"
        )

    reference, output, quantity = matches[0]

    if quantity != 1:
        raise ValueError("Invalid registry NFT quantity")

    if output.get("address") != address:
        raise ValueError("Unexpected registry address")

    if not re.fullmatch(r"[0-9a-f]{64}#[0-9]+", reference):
        raise ValueError("Invalid registry output reference")

    datum = output.get("inlineDatum")

    if datum is None:
        raise ValueError("Registry inline datum is missing")

    return reference, decode_registry(datum)


def verify_registry(*, authorized, revision):
    address, policy = registry_parameters()
    results = {}

    for name, container in AUTHORIZED_NODES.items():
        utxos = query_registry(container, address)
        reference, state = find_registry(utxos, address, policy)

        results[name] = {
            "reference": reference,
            "state": state,
        }

        print(
            f"{name}: NFT={reference} "
            f"authorized={state['authorized']} "
            f"revision={state['revision']}",
            flush=True,
        )

    first = results["AS180"]

    if not all(result == first for result in results.values()):
        raise ValueError("Incumbent nodes disagree on registry reference or datum")

    state = first["state"]

    if state["node"] != EXPECTED_NODE:
        raise ValueError("Unexpected node identity")

    if state["ip"] != EXPECTED_IP:
        raise ValueError("Unexpected node IP address")

    if state["revision"] != revision:
        raise ValueError("Unexpected registry revision")

    if state["authorized"] is not authorized:
        raise ValueError("Unexpected registry authorization state")

    return {**first, "address": address, "policy": policy}


def main():
    snapshot = verify_registry(authorized=True, revision=EXPECTED_REVISION)
    state = snapshot["state"]

    decision = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "ALLOW",
        "node": state["node"],
        "ip": state["ip"],
        "revision": state["revision"],
        "registry_utxo": snapshot["reference"],
        "verified_nodes": list(AUTHORIZED_NODES),
        "mode": "DRY_RUN",
        "firewall_modified": False,
    }

    print("\nAUTHORIZATION VERIFICATION PASSED")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"\nAUTHORIZATION DENIED: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
