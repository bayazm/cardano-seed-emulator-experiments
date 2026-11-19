#!/usr/bin/env python3
"""B16 N15-C: narrowly scoped AS184 firewall enforcement.

grant() is intended to be called only by the trusted admission
gateway after fresh DID authentication and live registry verification.

No standalone command is provided for granting access.
"""

import subprocess

GATEWAY_CONTAINER = "b16-as183h-Cardano-Node-4-10.183.0.71"
CANDIDATE_IP = "10.184.0.71"
ATTACKER_IP = "10.185.0.71"
CARDANO_PORT = "3001"


def iptables(*args):
    command = [
        "docker", "exec", "-u", "0",
        GATEWAY_CONTAINER,
        "iptables", "-w", *args,
    ]
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def rule_args(chain, ip, target):
    if chain == "INPUT":
        return [
            "-s", ip, "-p", "tcp",
            "--dport", CARDANO_PORT, "-j", target,
        ]

    if chain == "OUTPUT":
        return [
            "-d", ip, "-p", "tcp",
            "--dport", CARDANO_PORT, "-j", target,
        ]

    raise ValueError("INVALID_CHAIN")


def exists(chain, ip, target):
    try:
        iptables("-C", chain, *rule_args(chain, ip, target))
        return True
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1:
            return False
        raise


def verify_baseline():
    for chain in ("INPUT", "OUTPUT"):
        if not exists(chain, CANDIDATE_IP, "DROP"):
            raise RuntimeError("AS184_DROP_RULE_MISSING")

        if not exists(chain, ATTACKER_IP, "DROP"):
            raise RuntimeError("AS185_DROP_RULE_MISSING")

        if exists(chain, CANDIDATE_IP, "ACCEPT"):
            raise RuntimeError("AS184_ALREADY_ADMITTED")


def revoke():
    """Remove AS184-specific ACCEPT rules; preserve DROP rules."""
    for chain in ("INPUT", "OUTPUT"):
        while exists(chain, CANDIDATE_IP, "ACCEPT"):
            iptables(
                "-D", chain,
                *rule_args(chain, CANDIDATE_IP, "ACCEPT"),
            )


def grant():
    """Apply AS184 admission rules after trusted authorization."""
    verify_baseline()

    try:
        for chain in ("INPUT", "OUTPUT"):
            # Place ACCEPT after AS185's existing DROP at position 1.
            iptables(
                "-I", chain, "2",
                *rule_args(chain, CANDIDATE_IP, "ACCEPT"),
            )

        for chain in ("INPUT", "OUTPUT"):
            if not exists(chain, CANDIDATE_IP, "ACCEPT"):
                raise RuntimeError("AS184_ACCEPT_NOT_INSTALLED")

            if not exists(chain, ATTACKER_IP, "DROP"):
                raise RuntimeError("AS185_PROTECTION_MISSING")

    except Exception:
        revoke()
        raise


if __name__ == "__main__":
    import sys

    # Emergency rollback only. Granting access requires the gateway.
    if sys.argv[1:] != ["revoke"]:
        raise SystemExit("Usage: python3 b16_n15_firewall_controller.py revoke")

    revoke()
    print("AS184_ACCEPT_RULES_REMOVED")
