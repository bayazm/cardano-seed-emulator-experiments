#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime, timezone

import admission_controller as registry
import registry_firewall as firewall


def verify_blockchain():
    return registry.verify_registry(authorized=True, revision=registry.EXPECTED_REVISION)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply authorized firewall changes")
    args = parser.parse_args()

    if not args.apply:
        verify_blockchain()
        print("Blockchain authorization: VERIFIED", flush=True)
        target = firewall.validate_target()
        for rule in firewall.RULES:
            chain = rule[0]
            count = sum(
                firewall.matches_rule(entry, rule)
                for entry in firewall.chain_rules(target, chain)
            )
            print(f"{chain} candidate DROP rules: {count}")
        print("DRY RUN: Firewall unchanged")
        return

    with firewall.operation_lock():
        snapshot = verify_blockchain()
        print("Blockchain authorization: VERIFIED", flush=True)
        target = firewall.validate_target()
        if verify_blockchain() != snapshot:
            raise RuntimeError("Registry changed before enforcement")
        removed = firewall.remove_blocks(target)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": "RELAY_ADMISSION",
        "node": registry.EXPECTED_NODE,
        "ip": registry.EXPECTED_IP,
        "peer": "AS183",
        "registry_utxo": snapshot["reference"],
        "registry_revision": snapshot["state"]["revision"],
        "blockchain_verification": "PASS",
        "firewall_modified": bool(removed),
        "rules_removed": removed,
    }

    print("\nNETWORK ADMISSION APPLIED")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ADMISSION ENFORCEMENT INCOMPLETE: {exc}", file=sys.stderr)
        sys.exit(1)
