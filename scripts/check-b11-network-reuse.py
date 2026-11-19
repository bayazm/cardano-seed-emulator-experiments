#!/usr/bin/env python3
"""Inspect Docker without mutations and emit a B11 external-network candidate."""

import argparse
import collections
import ipaddress
import json
from pathlib import Path
import subprocess

import yaml


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def read_inventory():
    network_ids = docker("network", "ls", "-q").splitlines()
    container_ids = docker("ps", "-aq").splitlines()
    networks = json.loads(docker("network", "inspect", *network_ids)) if network_ids else []
    # Collect only attachment and lifecycle data. Full container inspection
    # also includes environments and mounts that are unnecessary here.
    template = '{{json .Name}}\t{{json .State.Status}}\t{{json .NetworkSettings.Networks}}\t{{json .Config.Labels}}'
    containers = []
    if container_ids:
        for line in docker("inspect", "--format", template, *container_ids).splitlines():
            name, status, attachments, labels = map(json.loads, line.split("\t"))
            service = (labels or {}).get("com.docker.compose.service")
            containers.append((name.lstrip("/"), status, attachments or {}, service))
    images = docker("image", "ls", "--format", "{{.Repository}}:{{.Tag}}").splitlines()
    return networks, containers, images


def compare(compose, networks, containers, images=()):
    mapping = {}
    issues = []
    proposed_names = {service["container_name"] for service in compose["services"].values()
                      if "container_name" in service}
    for tag in images:
        if tag.startswith("b11verifyzdmsrhh0-") or tag.startswith("b11verifyzdmsrhh0_"):
            issues.append(f"Run image tag already exists: {tag}")
    for name, _, _, _ in containers:
        if name in proposed_names or name.startswith(("b11verifyzdmsrhh0-", "b11verifyzdmsrhh0_")):
            issues.append(f"Container name already exists: {name}")

    for key, wanted in compose["networks"].items():
        expected, = wanted["ipam"]["config"]
        subnet = ipaddress.ip_network(expected["subnet"])
        matches = [n for n in networks if any(item.get("Subnet") == str(subnet)
                   for item in n["IPAM"].get("Config") or [])]
        if len(matches) != 1:
            issues.append(f"{key}: expected one exact network for {subnet}, found {len(matches)}")
            continue

        net, = matches
        name = net["Name"]
        configs = net["IPAM"].get("Config") or []
        gateway = expected.get("gateway", str(next(subnet.hosts())))
        ipam = configs[0]
        if (len(configs) != 1 or ipam.get("Gateway") != gateway
                or ipam.get("IPRange", "") != expected.get("ip_range", "")
                or (ipam.get("AuxiliaryAddresses") or {}) != expected.get("aux_addresses", {})):
            issues.append(f"{key}/{name}: IPAM mismatch (expected {subnet}, gateway {gateway}; "
                          f"found gateway {ipam.get('Gateway')})")
        if (net["Driver"] != wanted.get("driver", "bridge") or net["Scope"] != "local"
                or net.get("Internal", False) != wanted.get("internal", False)
                or net.get("EnableIPv6", False) != wanted.get("enable_ipv6", False)
                or net["IPAM"]["Driver"] != wanted["ipam"].get("driver", "default")
                or net["IPAM"].get("Options")
                or (net.get("Options") or {}) != {k: str(v) for k, v in wanted.get("driver_opts", {}).items()}):
            issues.append(f"{key}/{name}: driver, scope, flags or driver options differ")
        logical_name = (net.get("Labels") or {}).get("com.docker.compose.network")
        if logical_name and logical_name != key:
            issues.append(f"{key}/{name}: historical Compose network key is {logical_name}")
        if net.get("Containers"):
            issues.append(f"{key}/{name}: existing live or retained Docker endpoints")

        historical = collections.defaultdict(set)
        for cname, status, attachments, service in containers:
            endpoint = attachments.get(name)
            if endpoint is None:
                continue
            if status not in {"created", "exited", "dead"} or endpoint.get("IPAddress"):
                issues.append(f"{key}/{name}: occupied attachment from {cname} ({status})")
            reservation = (endpoint.get("IPAMConfig") or {}).get("IPv4Address")
            if reservation:
                historical[service or f"unlabeled:{cname}"].add(reservation)
        planned = {
            service: config["networks"][key]["ipv4_address"]
            for service, config in compose["services"].items()
            if key in config.get("networks", {})
        }
        for service, address in planned.items():
            if historical.get(service) != {address}:
                seen = ", ".join(sorted(historical.get(service, []))) or "no verified attachment"
                issues.append(f"{key}/{name}: {service} expects {address}; history shows {seen}")
            if any(address in addresses for other, addresses in historical.items() if other != service):
                issues.append(f"{key}/{name}: another historical service requests {address}")
        mapping[key] = name
        print(f"{key} => {name} | {subnet} | expected gateway {gateway} | {len(planned)} service slots")
    return mapping, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Run-only B11 Compose file")
    parser.add_argument("output", type=Path, help="New Compose file in the same build directory")
    args = parser.parse_args()
    if args.source.resolve().parent != args.output.resolve().parent:
        parser.error("Keep the output beside the source to preserve build paths")
    try:
        compose = yaml.safe_load(args.source.read_text())
        if len(compose.get("networks", {})) != 22 or "seedemu-ether-client" in compose.get("services", {}):
            parser.error("Expected the B11 run-only Compose configuration with 22 networks")
        mapping, issues = compare(compose, *read_inventory())
        if issues:
            parser.exit(1, "Network reuse not cleared:\n- " + "\n- ".join(issues) + "\n")
        compose["networks"] = {key: {"external": True, "name": name} for key, name in mapping.items()}
        with args.output.open("x") as stream:
            yaml.safe_dump(compose, stream, sort_keys=False)
        print(f"External network candidate written to {args.output}")
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as exc:
        parser.exit(1, f"Network reuse not cleared: {exc}\n")


if __name__ == "__main__":
    main()
