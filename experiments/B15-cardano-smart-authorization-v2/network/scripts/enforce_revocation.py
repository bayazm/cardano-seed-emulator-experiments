#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

import admission_controller as registry

AS183 = "b15-as183h-Cardano-Node-4-10.183.0.71"
IP = "10.184.0.71"

RULES = [
    ["INPUT", "-s", IP, "-p", "tcp",
     "--dport", "3001", "-j", "DROP"],

    ["OUTPUT", "-d", IP, "-p", "tcp",
     "--dport", "3001", "-j", "DROP"],
]


def docker_iptables(action, rule):
    return subprocess.run(
        ["docker", "exec", AS183,
         "iptables", "-w", action, *rule],
        capture_output=True,
        text=True,
        timeout=30,
    )


def rule_exists(rule):
    result = docker_iptables("-C", rule)

    if result.returncode == 0:
        return True

    if result.returncode == 1:
        return False

    raise RuntimeError(result.stderr)


def verify_revocation():
    results = {}

    for name, container in registry.AUTHORIZED_NODES.items():
        utxos = registry.query_registry(container)

        reference, state = registry.find_registry(utxos)

        results[name] = {
            "reference": reference,
            "state": state,
        }

        print(
            f"{name}: authorized={state['authorized']} "
            f"revision={state['revision']}",
            flush=True,
        )

    first = results["AS180"]

    if not all(value == first for value in results.values()):
        raise RuntimeError("Registry disagreement between nodes")

    state = first["state"]

    if state["node"] != "AS184":
        raise RuntimeError("Unexpected node identity")

    if state["ip"] != IP:
        raise RuntimeError("Unexpected node IP")

    if state["authorized"] is not False:
        raise RuntimeError("Node has not been revoked")

    if state["revision"] != 2:
        raise RuntimeError("Unexpected registry revision")

    return first["reference"]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Enforce revocation"
    )

    args = parser.parse_args()

    reference = verify_revocation()

    print("\nBLOCKCHAIN REVOCATION VERIFIED")

    if not args.apply:
        print("DRY RUN: Firewall unchanged")
        return

    # Recheck the current registry immediately
    # before modifying the firewall.
    if verify_revocation() != reference:
        raise RuntimeError("Registry changed during verification")

    added = []

    for rule in RULES:
        if not rule_exists(rule):
            result = docker_iptables("-I", rule)

            if result.returncode != 0:
                raise RuntimeError(result.stderr)

            added.append(rule)

    if not all(rule_exists(rule) for rule in RULES):
        raise RuntimeError("Firewall verification failed")

    record = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "event": "RELAY_REVOCATION",
        "node": "AS184",
        "ip": IP,
        "peer": "AS183",
        "authorized": False,
        "registry_revision": 2,
        "registry_utxo": reference,
        "blockchain_verification": "PASS",
        "firewall_policy": "DROP",
        "rules_added": len(added),
    }

    print("\nNETWORK REVOCATION ENFORCED")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"REVOCATION ENFORCEMENT FAILED: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
