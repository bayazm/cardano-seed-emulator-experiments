#!/usr/bin/env python3
"""Check B12-P9 isolation before using a fresh or previously occupied daemon."""

import argparse
import ipaddress
import json
from pathlib import Path
import subprocess

import yaml


def run(*command):
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def networks(settings):
    return [ipaddress.ip_network(item["subnet"]) for item in settings if item.get("subnet")]


def check_running(parser, compose, runtime):
    services = yaml.safe_load(compose.read_text())["services"]
    ids = run("docker", "ps", "-aq").split()
    containers = json.loads(run("docker", "inspect", *ids)) if ids else []
    peers = {f"hnode_{asn}_host_0": asn for asn in range(150, 154)}
    seen = set()
    for container in containers:
        labels = container["Config"]["Labels"] or {}
        service = labels.get("com.docker.compose.service")
        if labels.get("com.docker.compose.project") != "b12-p9" or service not in services or service in seen:
            parser.error("Unexpected, unrelated or duplicate container on the rehearsal daemon.")
        seen.add(service)
        fixed_name = services[service].get("container_name")
        if fixed_name and container["Name"].lstrip("/") != fixed_name:
            parser.error(f"Unexpected container name for {service}.")
        if service in peers:
            if not container["State"]["Running"]:
                parser.error(f"Expected a running Cardano container for {service}.")
            expected = {
                "/cardano/db": runtime / "cardano-data/testnet-conway-113-v2" / f"as{peers[service]}",
                "/captures": runtime / "captures",
            }
            actual = {mount["Destination"]: Path(mount["Source"]).resolve()
                      for mount in container["Mounts"] if mount["Type"] == "bind"}
            if any(actual.get(dest) != path for dest, path in expected.items()):
                parser.error(f"Wrong rehearsal database or capture bind for {service}.")
    if not peers.keys() <= seen:
        parser.error("The rehearsal is missing one or more Cardano peers.")
    print("Four rehearsal Cardano containers and their runtime mounts verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--historical-engine-id", type=Path)
    target.add_argument("--fresh-host", action="store_true",
                        help="Require an empty Docker host without historical experiment resources")
    target.add_argument("--verify-running", action="store_true",
                        help="Check the running single-host B12-P9 rehearsal against its Compose plan")
    parser.add_argument("--compose", type=Path, help="compiled and normalized Compose YAML")
    parser.add_argument("--runtime", type=Path, help="dedicated B12-P9 root for database and capture bind mounts")
    parser.add_argument("--sequential", action="store_true",
                        help="require the historical daemon with B12-4242 already removed from Docker")
    parser.add_argument("--historical-runtime", type=Path,
                        help="original B12-4242 runtime root for the sequential mount check")
    args = parser.parse_args()

    if args.verify_running:
        if args.sequential or args.historical_runtime or not (args.compose and args.runtime):
            parser.error("--verify-running requires --compose and --runtime, without historical options.")
        check_running(parser, args.compose, args.runtime.resolve())
        return

    historic = args.historical_engine_id.read_text().strip() if args.historical_engine_id else None
    current = run("docker", "info", "--format", "{{.ID}}")
    if not current or (args.historical_engine_id and not historic):
        parser.error("The Docker engine identities must be known.")
    if args.fresh_host:
        if args.sequential or args.historical_runtime:
            parser.error("Fresh-host mode cannot use historical deployment options.")
        if run("docker", "ps", "-aq"):
            parser.error("Fresh-host mode requires no existing containers.")
        for project in ("b12-reproduction", "b12-p9"):
            if run("docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"):
                parser.error(f"Fresh-host mode found existing {project} Docker networks.")
    elif args.sequential:
        if current != historic or not all((args.compose, args.runtime, args.historical_runtime)):
            parser.error("Sequential mode requires the historical engine, normalized Compose, and both runtime roots.")
        old_runtime = args.historical_runtime.resolve()
        new_runtime = args.runtime.resolve()
        if old_runtime == new_runtime or old_runtime in new_runtime.parents or new_runtime in old_runtime.parents:
            parser.error("B12-4242 and B12-P9 runtime directories must be disjoint.")
        old_networks = run("docker", "network", "ls", "-q", "--filter",
                           "label=com.docker.compose.project=b12-reproduction")
        if old_networks:
            parser.error("B12-4242 still owns Docker networks on this daemon.")
    elif current == historic:
        parser.error("Use a different Docker daemon from B12-4242.")

    old_project = run("docker", "ps", "-aq", "--filter",
                      "label=com.docker.compose.project=b12-reproduction")
    if old_project:
        parser.error("The selected daemon contains B12-4242 containers.")
    new_project = run("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=b12-p9")
    if new_project:
        parser.error("The selected daemon already contains a B12-P9 deployment.")
    if args.compose is None:
        print(f"{'Fresh' if args.fresh_host else 'Separate'} Docker daemon confirmed: {current}")
        return
    if args.runtime is None:
        parser.error("--compose requires --runtime.")
    runtime = args.runtime.resolve()
    plan = yaml.safe_load(args.compose.read_text())
    existing = set(run("docker", "ps", "-a", "--format", "{{.Names}}").splitlines())
    planned = {service["container_name"] for service in plan["services"].values()
               if "container_name" in service}
    if existing & planned:
        parser.error(f"Container name collisions: {sorted(existing & planned)}")

    ids = run("docker", "network", "ls", "-q").split()
    ipam = [entry for network in json.loads(run("docker", "network", "inspect", *ids))
            for entry in network["IPAM"]["Config"] or []] if ids else []
    allocated = networks([{"subnet": entry.get("Subnet")} for entry in ipam])
    desired = networks([entry for network in plan["networks"].values()
                        for entry in network.get("ipam", {}).get("config", [])])
    for subnet in desired:
        overlaps = [str(other) for other in allocated
                    if other.version == subnet.version and subnet.overlaps(other)]
        if overlaps:
            parser.error(f"Subnet {subnet} overlaps existing allocations: {overlaps}")

    listening = {line.split()[3].rsplit(":", 1)[-1] for line in run("ss", "-H", "-ltn").splitlines()}
    published = set()
    cardano_databases = set()
    for index, asn in enumerate(range(150, 154), start=1):
        service = plan["services"][f"hnode_{asn}_host_0"]
        if service.get("container_name") != f"as{asn}h-Cardano-Node-{index}-10.{asn}.0.71":
            parser.error(f"Unexpected generated Cardano service name for AS{asn}.")
        addresses = {entry.get("ipv4_address") for entry in service.get("networks", {}).values()}
        if f"10.{asn}.0.71" not in addresses:
            parser.error(f"Expected the historical private address for AS{asn} inside the isolated VM.")
        mounts = service.get("volumes", [])
        db_paths = [entry["source"] for entry in mounts
                    if isinstance(entry, dict) and entry.get("target") == "/cardano/db"]
        if len(db_paths) != 1 or db_paths[0] in cardano_databases:
            parser.error(f"Expected a unique DB mount for AS{asn}.")
        cardano_databases.add(db_paths[0])

    for service in plan["services"].values():
        for port in service.get("ports", []):
            if not isinstance(port, dict):
                parser.error("Provide normalized Compose config with mapped port entries.")
            if port.get("published") and port.get("protocol", "tcp") == "tcp":
                published.add(str(port["published"]))
        for volume in service.get("volumes", []):
            if isinstance(volume, str):
                source, target, *_ = volume.split(":", 2)
            else:
                source, target = volume.get("source", ""), volume["target"]
            if target not in ("/cardano/db", "/captures"):
                continue
            if not source or runtime not in Path(source).resolve().parents:
                parser.error(f"Expected {target} to bind below the B12-P9 runtime root: {source}")
    if published & listening:
        parser.error(f"Published TCP port collisions: {sorted(published & listening)}")
    mode = "Fresh" if args.fresh_host else ("Sequential" if args.sequential else "Separate")
    print(f"{mode} Docker daemon {current}, {len(planned)} names and {len(desired)} subnets checked.")


if __name__ == "__main__":
    main()
