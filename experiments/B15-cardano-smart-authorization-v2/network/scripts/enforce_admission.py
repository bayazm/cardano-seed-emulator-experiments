#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONTROLLER = ROOT / "scripts/admission_controller.py"

AS183 = "b15-as183h-Cardano-Node-4-10.183.0.71"
CANDIDATE_IP = "10.184.0.71"

INPUT_RULE = [
    "INPUT", "-s", CANDIDATE_IP,
    "-p", "tcp", "--dport", "3001", "-j", "DROP"
]

OUTPUT_RULE = [
    "OUTPUT", "-d", CANDIDATE_IP,
    "-p", "tcp", "--dport", "3001", "-j", "DROP"
]

RULES = [INPUT_RULE, OUTPUT_RULE]


def run(command):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def iptables(action, rule):
    return run([
        "docker", "exec", AS183,
        "iptables", "-w", action, *rule
    ])


def rule_exists(rule):
    result = subprocess.run(
        [
            "docker", "exec", AS183,
            "iptables", "-w", "-C", *rule
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        return True

    if result.returncode == 1:
        return False

    raise RuntimeError(result.stderr)


def verify_blockchain():
    result = run([
        sys.executable,
        str(CONTROLLER)
    ])

    print(result.stdout, flush=True)

    marker = "AUTHORIZATION VERIFICATION PASSED"

    if marker not in result.stdout:
        raise RuntimeError("Blockchain verification failed")

    decision = json.loads(
        result.stdout.split(marker, 1)[1].strip()
    )

    if not (
        decision["decision"] == "ALLOW"
        and decision["node"] == "AS184"
        and decision["ip"] == CANDIDATE_IP
        and decision["revision"] == 1
        and decision["mode"] == "DRY_RUN"
        and decision["firewall_modified"] is False
        and set(decision["verified_nodes"])
        == {"AS180", "AS181", "AS182", "AS183"}
    ):
        raise RuntimeError("Unexpected authorization decision")

    return decision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply authorized firewall changes"
    )
    args = parser.parse_args()

    decision = verify_blockchain()

    print("Blockchain authorization: VERIFIED")

    existing = [rule_exists(rule) for rule in RULES]

    if not all(existing):
        raise RuntimeError(
            "Expected firewall rules are missing; "
            "refusing to modify an unexpected firewall state"
        )

    if not args.apply:
        print("DRY RUN: Firewall unchanged")
        return

    removed = []

    try:
        for rule in RULES:
            iptables("-D", rule)
            removed.append(rule)

        if any(rule_exists(rule) for rule in RULES):
            raise RuntimeError("Firewall change verification failed")

    except Exception:
        # Restore rules removed during this attempt.
        for rule in reversed(removed):
            if not rule_exists(rule):
                iptables("-I", rule)
        raise

    record = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "event": "RELAY_ADMISSION",
        "node": "AS184",
        "ip": CANDIDATE_IP,
        "peer": "AS183",
        "registry_utxo": decision["registry_utxo"],
        "registry_revision": decision["revision"],
        "blockchain_verification": "PASS",
        "firewall_modified": True,
        "removed_rules": [
            "INPUT DROP from AS184 to TCP 3001",
            "OUTPUT DROP to AS184 TCP 3001",
        ],
    }

    print("\nNETWORK ADMISSION APPLIED")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"ADMISSION FAILED: {exc}",
            file=sys.stderr
        )
        sys.exit(1)
