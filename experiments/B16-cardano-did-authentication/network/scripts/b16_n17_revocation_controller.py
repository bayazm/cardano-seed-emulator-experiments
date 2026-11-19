#!/usr/bin/env python3
"""B16 N17: blockchain-verified AS184 network revocation."""

import argparse
import json
import subprocess
from datetime import datetime, timezone

import admission_controller as registry
import b16_n15_firewall_controller as firewall


NETWORK_MAGIC = "5556"
SOCKET = "/cardano/node.socket"

NODES = {
    "AS180": "b16-as180h-Cardano-Node-1-10.180.0.71",
    "AS181": "b16-as181h-Cardano-Node-2-10.181.0.71",
    "AS182": "b16-as182h-Cardano-Node-3-10.182.0.71",
    "AS183": "b16-as183h-Cardano-Node-4-10.183.0.71",
}



def query_node(container):
    result = subprocess.run(
        [
            "docker", "exec", container,
            "cardano-cli", "query", "utxo",
            "--address", registry.REGISTRY_ADDRESS,
            "--testnet-magic", NETWORK_MAGIC,
            "--socket-path", SOCKET,
            "--output-json",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    utxos = json.loads(result.stdout)

    return registry.find_registry(utxos)


def verify_blockchain(expected_utxo):
    results = {}

    for name, container in NODES.items():
        reference, state = query_node(container)

        results[name] = {
            "reference": reference,
            "state": state,
        }

        print(
            f"{name}: authorized={state['authorized']} "
            f"revision={state['revision']} "
            f"UTxO={reference}",
            flush=True,
        )

    first = results["AS180"]

    if not all(result == first for result in results.values()):
        raise RuntimeError("REGISTRY_DISAGREEMENT")

    reference = first["reference"]
    state = first["state"]

    if reference != expected_utxo:
        raise RuntimeError("UNEXPECTED_REGISTRY_UTXO")

    if state["node"] != "AS184":
        raise RuntimeError("UNEXPECTED_NODE")

    if state["ip"] != "10.184.0.71":
        raise RuntimeError("UNEXPECTED_IP")

    if state["authorized"] is not False:
        raise RuntimeError("NODE_NOT_REVOKED")

    if state["revision"] != 2:
        raise RuntimeError("UNEXPECTED_REVISION")

    return reference


def firewall_status():
    result = {}

    for chain in ("INPUT", "OUTPUT"):
        drop = firewall.exists(chain, firewall.CANDIDATE_IP, "DROP")
        accept = firewall.exists(chain, firewall.CANDIDATE_IP, "ACCEPT")
        attacker_drop = firewall.exists(chain, firewall.ATTACKER_IP, "DROP")

        result[chain] = {
            "as184_drop": drop,
            "as184_accept": accept,
            "as185_drop": attacker_drop,
        }

        if not drop or not attacker_drop:
            raise RuntimeError(f"BASELINE_DROP_MISSING_{chain}")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-utxo", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    reference = verify_blockchain(args.expected_utxo)
    before = firewall_status()

    if args.apply:
        # Recheck immediately before changing firewall state.
        if verify_blockchain(args.expected_utxo) != reference:
            raise RuntimeError("REGISTRY_CHANGED")

        firewall_status()
        firewall.revoke()

        after = firewall_status()

        for chain in ("INPUT", "OUTPUT"):
            if after[chain]["as184_accept"]:
                raise RuntimeError(f"ACCEPT_STILL_PRESENT_{chain}")

        decision = "REVOKE_ENFORCED"
    else:
        after = before
        decision = "DRY_RUN"

    record = {
        "experiment": "B16-N17",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "node": "AS184",
        "ip": "10.184.0.71",
        "authorized": False,
        "revision": 2,
        "registry_utxo": reference,
        "verified_nodes": list(NODES),
        "firewall_before": before,
        "firewall_after": after,
    }

    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
