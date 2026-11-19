#!/usr/bin/env python3

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REGISTRY_ADDRESS = (
    ROOT / "deployment/registry/membership-script.addr"
).read_text().strip()

POLICY_ID = (
    ROOT / "deployment/registry/policy-id.txt"
).read_text().strip()

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


def query_registry(container):
    result = subprocess.run(
        [
            "docker", "exec", container,
            "cardano-cli", "query", "utxo",
            "--address", REGISTRY_ADDRESS,
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


def find_registry(utxos):
    matches = []

    for reference, output in utxos.items():
        quantity = (
            output.get("value", {})
            .get(POLICY_ID, {})
            .get(TOKEN_NAME, 0)
        )

        if quantity != 0:
            matches.append((reference, output, quantity))

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one registry output; found {len(matches)}"
        )

    reference, output, quantity = matches[0]

    if quantity != 1:
        raise ValueError("Invalid registry NFT quantity")

    if output.get("address") != REGISTRY_ADDRESS:
        raise ValueError("Unexpected registry address")

    datum = output.get("inlineDatum")

    if datum is None:
        raise ValueError("Registry inline datum is missing")

    return reference, decode_registry(datum)


def main():
    results = {}

    for name, container in AUTHORIZED_NODES.items():
        utxos = query_registry(container)
        reference, state = find_registry(utxos)

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
        raise ValueError("Authorized nodes disagree on registry state")

    state = first["state"]

    if state["node"] != EXPECTED_NODE:
        raise ValueError("Unexpected node identity")

    if state["ip"] != EXPECTED_IP:
        raise ValueError("Unexpected node IP address")

    if state["revision"] != EXPECTED_REVISION:
        raise ValueError("Unexpected registry revision")

    if not state["authorized"]:
        raise ValueError("AS184 is not authorized")

    decision = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "ALLOW",
        "node": state["node"],
        "ip": state["ip"],
        "revision": state["revision"],
        "registry_utxo": first["reference"],
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
