"""Manage the two AS183 rules for the B15 candidate's TCP port."""

import fcntl
import json
import os
import re
import shlex
import subprocess
from contextlib import contextmanager

from admission_controller import AUTHORIZED_NODES, EXPECTED_IP, ROOT

LOCK_PATH = ROOT / ".runtime/b15-firewall.lock"
AS183_SERVICE = "hnode_183_host_0"
AS183_IP = "10.183.0.71"

RULES = (
    ("INPUT", "-s", EXPECTED_IP, "-p", "tcp", "--dport", "3001", "-j", "DROP"),
    ("OUTPUT", "-d", EXPECTED_IP, "-p", "tcp", "--dport", "3001", "-j", "DROP"),
)


@contextmanager
def operation_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another B15 enforcement operation holds the lock") from exc
        yield


def docker(*args):
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout


def validate_target(expected_id=None):
    project = os.environ.get("COMPOSE_PROJECT_NAME", "output")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
        raise ValueError("Invalid B15 Compose project name")

    name = AUTHORIZED_NODES["AS183"]
    (target,) = json.loads(docker("inspect", "--type", "container", name))
    target_id = target["Id"]
    if target.get("Name") != f"/{name}" or not re.fullmatch(r"[0-9a-f]{64}", target_id):
        raise RuntimeError("Unexpected AS183 container identity")
    if expected_id is not None and target_id != expected_id:
        raise RuntimeError("AS183 container identity changed during enforcement")
    if target["State"].get("Running") is not True:
        raise RuntimeError("AS183 container is stopped")

    labels = target["Config"]["Labels"] or {}
    if labels.get("com.docker.compose.project") != project:
        raise RuntimeError("Unexpected AS183 Compose project")
    if labels.get("com.docker.compose.service") != AS183_SERVICE:
        raise RuntimeError("Unexpected AS183 Compose service")

    network_name = f"{project}_net_183_net0"
    network = target["NetworkSettings"]["Networks"].get(network_name)
    mode = target["HostConfig"]["NetworkMode"]
    network_id = network.get("NetworkID", "") if network else ""
    if not network or (
        mode != network_name
        and not (re.fullmatch(r"[0-9a-f]{64}", network_id) and mode == network_id)
    ):
        raise RuntimeError("Unexpected AS183 network namespace")
    if network.get("IPAddress") != AS183_IP:
        raise RuntimeError("Unexpected AS183 IPv4 address")

    addresses = docker("exec", target_id, "ip", "-o", "-4", "addr", "show", "scope", "global")
    ipv4 = [
        fields[3].split("/", 1)[0]
        for fields in map(str.split, addresses.splitlines())
        if len(fields) >= 4 and fields[2] == "inet"
    ]
    if ipv4.count(AS183_IP) != 1:
        raise RuntimeError("Unexpected AS183 IPv4 address in its network namespace")
    return target_id


def change_rule(target, *args):
    validate_target(expected_id=target)
    docker("exec", target, "iptables", "-w", *args)


def chain_rules(target, chain):
    rules = []
    for line in docker("exec", target, "iptables", "-w", "-S", chain).splitlines():
        fields = shlex.split(line)
        if fields[:2] == ["-A", chain]:
            rules.append(tuple(fields[1:]))
    return rules


def matches_rule(entry, rule):
    chain, direction, ip, *spec = rule
    # iptables -S prints the host mask and normally the implicit TCP match.
    return any(
        entry == (chain, direction, host, *body)
        for host in (ip, f"{ip}/32")
        for body in (spec, ["-p", "tcp", "-m", "tcp", *spec[2:]])
    )


def ensure_blocked(target):
    """Try both directions and report every failure, keeping successful drops."""
    added = 0
    errors = []
    for rule in RULES:
        chain = rule[0]
        try:
            entries = chain_rules(target, chain)
            if entries and matches_rule(entries[0], rule):
                continue
            change_rule(target, "-I", chain, "1", *rule[1:])
            added += 1
        except Exception as exc:
            errors.append(f"{chain} update: {exc}")

    for rule in RULES:
        chain = rule[0]
        try:
            entries = chain_rules(target, chain)
            if not entries or not matches_rule(entries[0], rule):
                errors.append(f"{chain} has no leading candidate DROP")
        except Exception as exc:
            errors.append(f"{chain} verification: {exc}")

    if errors:
        raise RuntimeError("; ".join(errors))
    return added


def remove_blocks(target):
    """Remove only matching candidate DROP rules, including duplicates."""
    removed = 0
    try:
        for rule in RULES:
            for entry in chain_rules(target, rule[0]):
                if matches_rule(entry, rule):
                    change_rule(target, "-D", *entry)
                    removed += 1
        for rule in RULES:
            if any(matches_rule(entry, rule) for entry in chain_rules(target, rule[0])):
                raise RuntimeError(f"{rule[0]} still contains a candidate DROP")
    except Exception as exc:
        try:
            ensure_blocked(target)
        except Exception as recovery:
            raise RuntimeError(
                f"{exc}; recovery incomplete: {recovery}"
            ) from exc
        raise RuntimeError(f"{exc}; candidate DROPs restored at chain heads") from exc
    return removed
