#!/usr/bin/env python3
"""Stage separate B16 role directories and enter an existing lab network namespace."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


GATEWAY = "b16-as183h-Cardano-Node-4-10.183.0.71"
CANDIDATE = "b16-as184h-Cardano-Node-5-10.184.0.71"
PUBLIC = Path("identity-data/public/AS184.json")
TRUST = Path("identity-data/trust/administrator-public.pem")
CERT = Path("identity-data/enrollments/AS184-enrollment.json")
REGISTRY = tuple(Path("deployment/registry") / name
                 for name in ("membership-script.addr", "policy-id.txt"))
COMMON = ("identity.py", "prototype.py", "enrollment.py")


def copy_file(source, dest, relative):
    source_file = source / relative
    target = dest / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with source_file.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)


def stage(network, authority, gateway, candidate):
    folders = (
        (authority, (*COMMON, "create_authority.py")),
        (gateway, (*COMMON, "registry_policy.py")),
        (candidate, (*COMMON, "sidecar/remote_auth.py")),
    )
    for dest, names in folders:
        dest.mkdir(parents=True, exist_ok=False)
        for name in names:
            copy_file(network, dest, Path("scripts/did_auth") / name)
    for name in ("b16_n15_controlled_gateway.py", "b16_integrated_admission.py",
                 "b16_n15_firewall_controller.py"):
        copy_file(network, gateway, Path("scripts") / name)


def run_role(script, container, ip, *args):
    if os.geteuid():
        raise ValueError("Entering the lab network namespace requires root")
    pid = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.State.Pid}}", container], text=True).strip()
    if not pid.isdecimal() or int(pid) <= 1:
        raise ValueError(f"Expected a running container for {container}")
    prefix = ["nsenter", f"--net=/proc/{pid}/ns/net", "--"]
    addresses = subprocess.check_output([*prefix, "ip", "-brief", "-4", "address"], text=True)
    if not any(value.split("/")[0] == ip for value in addresses.split()):
        raise ValueError(f"Container namespace does not own the expected address {ip}")
    subprocess.run([*prefix, sys.executable, str(script), *args], check=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("operation", choices=("stage", "publish-identity", "publish-enrollment",
                                              "publish-registry", "gateway", "candidate"))
    args = parser.parse_args()
    root = args.experiment.resolve()
    if root.name != "B16-cardano-did-authentication":
        parser.error("Select the publication B16 experiment directory")
    network = root / "network"
    workspace = network / ".runtime/did-deployment"
    authority, gateway, candidate = (workspace / role
                                     for role in ("authority", "gateway", "candidate"))
    try:
        if args.operation == "stage":
            stage(network, authority, gateway, candidate)
            print(workspace)
        elif args.operation == "publish-identity":
            copy_file(candidate, authority, PUBLIC)
        elif args.operation == "publish-enrollment":
            for path in (PUBLIC, TRUST, CERT):
                copy_file(authority, gateway, path)
            for path in (TRUST, CERT):
                copy_file(authority, candidate, path)
        elif args.operation == "publish-registry":
            for path in REGISTRY:
                copy_file(network, gateway, path)
        elif args.operation == "gateway":
            run_role(gateway / "scripts/b16_n15_controlled_gateway.py", GATEWAY, "10.183.0.71")
        else:
            run_role(candidate / "scripts/did_auth/sidecar/remote_auth.py", CANDIDATE,
                     "10.184.0.71", "candidate", "--require-admission")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"B16 deployment operation failed: {exc}\n")


if __name__ == "__main__":
    main()
