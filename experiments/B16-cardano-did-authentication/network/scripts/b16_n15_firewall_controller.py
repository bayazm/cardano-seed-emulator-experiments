#!/usr/bin/env python3
"""B16 N15-C: narrowly scoped AS184 firewall enforcement.

grant() is intended to be called only by the trusted admission
gateway after fresh DID authentication and live registry verification.

No standalone command is provided for granting access.
"""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess

GATEWAY_CONTAINER = "b16-as183h-Cardano-Node-4-10.183.0.71"
GATEWAY_SERVICE = "hnode_183_host_0"
GATEWAY_IP = "10.183.0.71"
LOCK_PATH = Path("/run/b16-firewall.lock")
CANDIDATE_IP = "10.184.0.71"
ATTACKER_IP = "10.185.0.71"
CARDANO_PORT = "3001"
CHAINS = ("INPUT", "OUTPUT")


class FirewallRollbackError(RuntimeError):
    """Admission failed and the deny baseline could not be verified."""


@contextmanager
def operation_lock():
    fd = os.open(LOCK_PATH, os.O_RDONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise RuntimeError("UNSAFE_B16_FIREWALL_LOCK")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("B16_FIREWALL_OPERATION_IN_PROGRESS") from exc
        yield
    finally:
        os.close(fd)


def docker(*args):
    return subprocess.run(
        ["docker", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout


def validate_target(expected_id=None):
    project = os.environ.get("COMPOSE_PROJECT_NAME", "output")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
        raise ValueError("INVALID_B16_COMPOSE_PROJECT")

    (target,) = json.loads(docker("inspect", "--type", "container", GATEWAY_CONTAINER))
    target_id = target.get("Id")
    if (target.get("Name") != f"/{GATEWAY_CONTAINER}" or not isinstance(target_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", target_id)):
        raise RuntimeError("UNEXPECTED_AS183_CONTAINER_IDENTITY")
    if expected_id is not None and target_id != expected_id:
        raise RuntimeError("AS183_CONTAINER_IDENTITY_CHANGED")
    if target["State"].get("Running") is not True:
        raise RuntimeError("AS183_CONTAINER_NOT_RUNNING")
    labels = target["Config"]["Labels"] or {}
    if labels.get("com.docker.compose.project") != project:
        raise RuntimeError("UNEXPECTED_AS183_COMPOSE_PROJECT")
    if labels.get("com.docker.compose.service") != GATEWAY_SERVICE:
        raise RuntimeError("UNEXPECTED_AS183_COMPOSE_SERVICE")

    network_name = f"{project}_net_183_net0"
    networks = target["NetworkSettings"]["Networks"]
    mode = target["HostConfig"]["NetworkMode"]
    if set(networks) != {network_name}:
        raise RuntimeError("UNEXPECTED_AS183_NETWORK")
    network = networks[network_name]
    network_id = network.get("NetworkID")
    if not isinstance(network_id, str) or not re.fullmatch(r"[0-9a-f]{64}", network_id):
        raise RuntimeError("UNEXPECTED_AS183_NETWORK_ID")
    if mode not in (network_name, network_id):
        raise RuntimeError("UNEXPECTED_AS183_NETWORK_MODE")
    if network.get("IPAddress") != GATEWAY_IP:
        raise RuntimeError("UNEXPECTED_AS183_IPV4_ADDRESS")
    addresses = docker("exec", target_id, "ip", "-o", "-4", "addr", "show", "scope", "global")
    ipv4 = [
        fields[3].split("/", 1)[0]
        for fields in map(str.split, addresses.splitlines())
        if len(fields) >= 4 and fields[2] == "inet"
    ]
    if ipv4 != [GATEWAY_IP]:
        raise RuntimeError("UNEXPECTED_AS183_NAMESPACE_IPV4_ADDRESS")
    return target_id


def iptables(target, *args):
    if args[0] != "-S":
        validate_target(expected_id=target)
    return docker("exec", "-u", "0", target, "iptables", "-w", "5", *args)


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


def chain_rules(target, chain):
    rules = []
    for line in iptables(target, "-S", chain).splitlines():
        fields = shlex.split(line)
        if fields[:2] == ["-A", chain]:
            rules.append(fields[2:])
    return rules


def matches_rule(entry, rule):
    direction, ip, *spec = rule
    # iptables -S can print the host mask and the implicit TCP match.
    return any(
        entry == [direction, host, *body]
        for host in (ip, f"{ip}/32")
        for body in (spec, ["-p", "tcp", "-m", "tcp", *spec[2:]])
    )


def exists(chain, ip, verdict):
    target = validate_target()
    rule = rule_args(chain, ip, verdict)
    return any(matches_rule(entry, rule) for entry in chain_rules(target, chain))


def verify_rule_order(chain, entries, *, admitted):
    expected = [rule_args(chain, ATTACKER_IP, "DROP")]
    if admitted:
        expected.append(rule_args(chain, CANDIDATE_IP, "ACCEPT"))
    expected.append(rule_args(chain, CANDIDATE_IP, "DROP"))
    if len(entries) < len(expected) or not all(
        matches_rule(entry, rule) for entry, rule in zip(entries, expected)
    ):
        raise RuntimeError(f"AS183_RULE_ORDER_MISMATCH: {chain}")


def verify_baseline(target):
    for chain in CHAINS:
        entries = chain_rules(target, chain)
        accept = rule_args(chain, CANDIDATE_IP, "ACCEPT")
        if any(matches_rule(entry, accept) for entry in entries):
            raise RuntimeError("AS184_ALREADY_ADMITTED")
        verify_rule_order(chain, entries, admitted=False)


def revoke():
    """Remove AS184-specific ACCEPT rules and verify both deny baselines."""
    with operation_lock():
        revoke_rules(validate_target())


def revoke_rules(target):
    failures = []
    for chain in CHAINS:
        rule = rule_args(chain, CANDIDATE_IP, "ACCEPT")
        try:
            for entry in chain_rules(target, chain):
                if matches_rule(entry, rule):
                    iptables(target, "-D", chain, *rule)
            entries = chain_rules(target, chain)
            if any(matches_rule(entry, rule) for entry in entries):
                raise RuntimeError("AS184_ACCEPT_STILL_PRESENT")
            verify_rule_order(chain, entries, admitted=False)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError,
                subprocess.SubprocessError) as exc:
            failures.append(f"{chain}: {getattr(exc, 'stderr', None) or exc}")
    if failures:
        raise RuntimeError("AS184_REVOCATION_FAILED: " + "; ".join(failures))


def grant():
    """Apply AS184 admission rules after trusted authorization."""
    with operation_lock():
        grant_rules(validate_target())


def grant_rules(target):
    verify_baseline(target)

    try:
        for chain in CHAINS:
            # Place ACCEPT after AS185's existing DROP at position 1.
            iptables(
                target, "-I", chain, "2",
                *rule_args(chain, CANDIDATE_IP, "ACCEPT"),
            )

        for chain in CHAINS:
            verify_rule_order(chain, chain_rules(target, chain), admitted=True)

    except Exception as exc:
        try:
            revoke_rules(target)
        except Exception as rollback:
            original = getattr(exc, "stderr", None) or exc
            raise FirewallRollbackError(
                f"AS184_ROLLBACK_FAILED: admission error: {original}; rollback: {rollback}"
            ) from exc
        raise


if __name__ == "__main__":
    import sys

    # Emergency rollback only. Granting access requires the gateway.
    if sys.argv[1:] != ["revoke"]:
        raise SystemExit("Usage: python3 b16_n15_firewall_controller.py revoke")

    revoke()
    print("AS184_ACCEPT_RULES_REMOVED")
