#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime, timezone

import admission_controller as registry
import registry_firewall as firewall

REVOCATION_REVISION = 2


def verify_revocation():
    return registry.verify_registry(authorized=False, revision=REVOCATION_REVISION)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Enforce revocation")
    args = parser.parse_args()

    if not args.apply:
        verify_revocation()
        print("Blockchain revocation: VERIFIED", flush=True)
        print("DRY RUN: Firewall unchanged")
        return

    with firewall.operation_lock():
        snapshot = verify_revocation()
        print("Blockchain revocation: VERIFIED", flush=True)
        target = firewall.validate_target()
        if verify_revocation() != snapshot:
            raise RuntimeError("Registry changed before enforcement")
        added = firewall.ensure_blocked(target)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": "RELAY_REVOCATION",
        "node": registry.EXPECTED_NODE,
        "ip": registry.EXPECTED_IP,
        "peer": "AS183",
        "authorized": False,
        "registry_revision": snapshot["state"]["revision"],
        "registry_utxo": snapshot["reference"],
        "blockchain_verification": "PASS",
        "firewall_policy": "DROP",
        "firewall_modified": bool(added),
        "rules_added": added,
    }

    print("\nNETWORK REVOCATION ENFORCED")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"REVOCATION ENFORCEMENT INCOMPLETE: {exc}", file=sys.stderr)
        sys.exit(1)
