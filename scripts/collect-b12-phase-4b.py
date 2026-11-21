#!/usr/bin/env python3
"""Collect read-only post-genesis evidence from the existing B12 deployment."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

NODES = (150, 151, 152, 153)
CAPTURE_NODES = (150, 153)
SOCKET = "/cardano/node.socket"
LOG = "/var/log/cardano-node.log"

DIAGNOSTICS = r"""
section() { printf '\n--- %s ---\n' "$*"; }
section clock; date -u +%FT%TZ
section process; ps -C cardano-node -o pid,ppid,user,stat,etimes,args
section socket; test -S /cardano/node.socket && echo 'Unix socket present'
stat -c '%A %U:%G %n' /cardano /cardano/node.socket
ss -xlpn
section versions; cardano-node --version; cardano-cli --version
section interfaces; ip -br addr; ip route
section listeners; ss -ltnp '( sport = :3001 )'
section peers; ss -tnpi state established '( sport = :3001 or dport = :3001 )'
section startup; grep -n 'cardano-node run' /start.sh
section config; cat /cardano/config.json /cardano/topology.json
section genesis
grep -E '"(startTime|systemStart|networkMagic|protocolMagic)"' \
    /cardano/byron-genesis.json /cardano/shelley-genesis.json
section credential_metadata
for name in kes.skey vrf.skey opcert.cert; do
    path=/cardano/producer/$name
    if test -e "$path"; then stat -c '%A %U:%G %s %n' "$path"; fi
done
"""

PROTOCOL_EVENTS = re.compile(
    r"handshake|DiffusionInit|ConnectionManager|ChainSync|BlockFetch|"
    r"AddedToCurrentChain|SwitchedToAFork|ForgedBlock|"
    r"StartTimeInTheFuture|Error|Critical|Exception|Failed",
    re.IGNORECASE,
)


def utc():
    return datetime.now(timezone.utc)


def run(command, limit=25):
    try:
        return subprocess.run(command, capture_output=True, timeout=limit, check=False)
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            command, 124, error.stdout or b"",
            (error.stderr or b"") + b"\nHost command timed out.\n",
        )


def record(path, command, limit=25):
    result = run(command, limit)
    path.write_bytes(result.stdout)
    path.with_suffix(path.suffix + ".stderr").write_bytes(result.stderr)
    path.with_suffix(path.suffix + ".exit").write_text(f"{result.returncode}\n")
    return result


def discover(out):
    result = record(out / "containers.txt", [
        "docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}",
        "--format", '{{.ID}}\t{{.Label "com.docker.compose.service"}}\t{{.Status}}',
    ])
    if result.returncode:
        raise SystemExit(result.stderr.decode(errors="replace"))
    services = {}
    for line in result.stdout.decode().splitlines():
        container, service, _ = line.split("\t", 2)
        services.setdefault(service, []).append(container)
    nodes = {}
    for asn in NODES:
        matches = services.get(f"hnode_{asn}_host_0", [])
        if len(matches) == 1:
            nodes[asn] = matches[0]
        else:
            (out / f"as{asn}-discovery.txt").write_text(
                f"Expected one container, found {len(matches)}: {matches}\n"
            )
    return nodes


def diagnostics(out, asn, container, phase):
    prefix = out / f"as{asn}-{phase}"
    record(prefix.with_suffix(".inspect"), [
        "docker", "inspect", "--format", "{{.Name}} {{json .State}} restarts={{.RestartCount}}",
        container,
    ])
    record(prefix.with_suffix(".txt"), ["docker", "exec", container, "sh", "-c", DIAGNOSTICS])


def logs(out, asn, container):
    record(out / f"as{asn}-docker.log", ["docker", "logs", "--tail", "300", container])
    record(out / f"as{asn}-startup.log", ["docker", "exec", container, "head", "-n", "100", LOG])
    path = out / f"as{asn}-cardano.log"
    record(path, ["docker", "exec", container, "tail", "-n", "12000", LOG])
    with (out / f"as{asn}-protocol.log").open("w") as selected:
        for source in (out / f"as{asn}-startup.log", path):
            print(f"--- {source.name} ---", file=selected)
            for line in source.read_text(errors="replace").splitlines():
                if PROTOCOL_EVENTS.search(line) and "Reflection.TracerInfo" not in line:
                    print(line, file=selected)


def tip(out, round_number, asn, container):
    path = out / f"round-{round_number}-as{asn}"
    timestamp = utc().isoformat()
    path.with_suffix(".utc").write_text(timestamp + "\n")
    command = [
        "docker", "exec", container, "timeout", "20", "cardano-cli", "query", "tip",
        "--testnet-magic", str(MAGIC), "--socket-path", SOCKET,
    ]
    result = record(path.with_suffix(".json"), command)
    try:
        tip_data = json.loads(result.stdout) if result.returncode == 0 else {}
    except ValueError:
        tip_data = {}
    return timestamp, tip_data if isinstance(tip_data, dict) else {}, result.returncode


def capture(out, asn, container, interface, seconds):
    name = f"{out.name}-as{asn}-{interface}-tcp3001.pcap"
    container_path = f"/captures/{name}"
    host_path = RUNTIME / "captures" / name
    # Bound runtime inside the container and allow tcpdump to flush on SIGINT.
    record(out / f"as{asn}-{interface}-capture.log", [
        "docker", "exec", container, "timeout", "--signal=INT", "--kill-after=5",
        str(seconds), "tcpdump", "-i", interface, "-nn", "-s", "0", "-U",
        "-w", container_path, "tcp port 3001",
    ], seconds + 15)
    if not host_path.is_file():
        return interface, None, None, None
    with host_path.open("rb") as source:
        sha256 = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha256.update(chunk)
    digest = sha256.hexdigest()
    manifest = out / f"as{asn}-{interface}-pcap.sha256"
    manifest.write_text(f"{digest}  {host_path}\n")
    record(out / f"as{asn}-{interface}-checksum-check.txt", ["sha256sum", "-c", str(manifest)])
    decoded = record(out / f"as{asn}-{interface}-packets.txt", [
        "env", "TZ=UTC", "tcpdump", "-nn", "-tttt", "-r", str(host_path), "tcp port 3001",
    ])
    packets = len(decoded.stdout.splitlines()) if decoded.returncode == 0 else None
    return interface, host_path.stat().st_size, packets, digest


def collect_capture(out, asn, container):
    results = [capture(out, asn, container, "net0", 145)]
    if not results[0][2]:
        record(out / f"as{asn}-capture-interface-check.txt", [
            "docker", "exec", container, "sh", "-c",
            "tcpdump -D; ip -s link; ip route; ss -ltnp; ss -tnpi state established",
        ])
        results.append(capture(out, asn, container, "any", 65))
    return results


def summarize(out, nodes, rounds, captures):
    lines = [
        f"## Post-genesis collection {out.name}", "",
        f"Raw evidence is in `{out.name}/`. The scheduled genesis was {GENESIS.isoformat()}.",
        "", "### Node status and peer evidence", "",
    ]
    for asn in NODES:
        if asn not in nodes:
            lines.append(f"- AS{asn}: container discovery failed. See `as{asn}-discovery.txt`.")
            continue
        inspection = (out / f"as{asn}-after.inspect").read_text().strip()
        diagnostics_text = (out / f"as{asn}-after.txt").read_text(errors="replace")
        sections = dict(re.findall(r"^--- (.*?) ---\n(.*?)(?=^--- |\Z)",
                                   diagnostics_text, re.MULTILINE | re.DOTALL))
        process = sections.get("process", "")
        socket = sections.get("socket", "")
        listeners = sections.get("listeners", "")
        peers = sections.get("peers", "")
        endpoint = re.compile(r"(?:10\.15[0-3]\.0\.71|\*|0\.0\.0\.0|\[::\]):3001\b")
        peer_lines = [line for line in peers.splitlines() if endpoint.search(line)]
        lines.append(f"- AS{asn}: `{inspection or 'inspection unavailable'}`. "
                     f"Cardano process {'observed' if 'cardano-node run' in process else 'unconfirmed'}, "
                     f"Unix socket {'present' if 'Unix socket present' in socket else 'unconfirmed'}, "
                     f"TCP/3001 listener {'observed' if ':3001' in listeners else 'unconfirmed'}, "
                     f"established matching TCP rows {len(peer_lines) if peers else 'unavailable'}.")
        for line in peer_lines:
            lines.append(f"  - `{line.strip()}`")
    lines += ["", "### Tip observations", "",
              "| Round | Node | UTC | Block | Slot | Epoch | Era | Hash | CLI exit |",
              "|---:|---|---|---:|---:|---:|---|---|---:|"]
    by_height = {}
    chain_points = {asn: [] for asn in NODES}
    for number, observations in enumerate(rounds, 1):
        for asn in NODES:
            timestamp, data, code = observations.get(asn, ("—", {}, "—"))
            values = [str(data.get(key, "—")) for key in ("block", "slot", "epoch", "era", "hash")]
            height, digest = data.get("block"), data.get("hash")
            if type(height) is int and isinstance(digest, str) and re.fullmatch("[0-9a-fA-F]{64}", digest):
                chain_points[asn].append(height)
                by_height.setdefault(height, {}).setdefault(asn, set()).add(digest.lower())
            elif (code == 0 and data.get("slotInEpoch") == 0 and data.get("epoch") == 0
                  and all(key not in data for key in ("block", "slot", "hash"))):
                chain_points[asn].append("origin")
                values[0] = "origin"
            else:
                chain_points[asn].append(None)
            lines.append(f"| {number} | AS{asn} | {timestamp} | {' | '.join(values)} | {code} |")
    lines += [""]
    for asn, sequence in chain_points.items():
        if None in sequence:
            finding = "missing one or more valid chain points"
        else:
            # The origin precedes every numbered block.
            order = [-1 if point == "origin" else point for point in sequence]
            advanced = all(earlier < later for earlier, later in zip(order, order[1:]))
            finding = "advanced in both intervals" if advanced else "did not advance in both intervals"
        lines.append(f"- AS{asn}: {finding}. Observed chain points: {sequence}.")
    for height, observed in sorted(by_height.items(), reverse=True):
        digests = set().union(*observed.values())
        if len(digests) > 1:
            lines.append(f"- Observed hash disagreement at height {height}: " +
                         "; ".join(f"AS{asn} {', '.join(sorted(hashes))}"
                                   for asn, hashes in sorted(observed.items())) + ".")
    common = [(height, next(iter(observed[NODES[0]]))) for height, observed in by_height.items()
              if set(observed) == set(NODES) and len(set().union(*observed.values())) == 1]
    if common:
        height, digest = max(common)
        lines.append(f"- Highest common observed block: **{height}**, hash `{digest}`.")
    else:
        lines.append("- No matching common-height hash was established by the sampled tips. "
                     "Review chain-selection logs or collect additional synchronized tips.")
    lines += ["", "### Packet captures", ""]
    for asn in CAPTURE_NODES:
        for interface, size, packets, digest in captures.get(asn, [("net0", None, None, None)]):
            lines.append(f"- AS{asn}, `{interface}`: bytes={size}, decoded TCP/3001 "
                         f"records={packets}, SHA-256=`{digest}`.")
    lines += ["", "Review listener, peer, protocol, and capture diagnostics before marking "
              "Phase 4B complete. For initialization failures, correlate process status, "
              "startup arguments, runtime genesis, and credential metadata with the first "
              "relevant error in the startup and node logs.", ""]
    summary = "\n".join(lines)
    (out / "summary.md").write_text(summary)
    with (RUNTIME / "evidence" / "phase-4b-verification.md").open("a") as report:
        report.write("\n" + summary + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait", action="store_true", help="wait until 30 seconds after genesis")
    parser.add_argument("--runtime", type=Path, required=True,
                        help="Host runtime root whose captures directory is mounted in each node")
    parser.add_argument("--genesis-file", type=Path, required=True, help="Public Shelley genesis JSON")
    parser.add_argument("--project", default="b12-reproduction")
    args = parser.parse_args()
    global RUNTIME, PROJECT, GENESIS, MAGIC
    RUNTIME, PROJECT = args.runtime.resolve(strict=True), args.project
    genesis = json.loads(args.genesis_file.read_text())
    GENESIS = datetime.fromisoformat(genesis["systemStart"].replace("Z", "+00:00"))
    MAGIC = int(genesis["networkMagic"])
    (RUNTIME / "evidence").mkdir(mode=0o700, exist_ok=True)
    now = utc()
    print(f"Host UTC {now.isoformat()}; genesis {GENESIS.isoformat()}", flush=True)
    if now <= GENESIS and not args.wait:
        raise SystemExit("Genesis has not started. Run again after genesis or use --wait.")
    for tool in ("docker", "tcpdump", "sha256sum"):
        if not shutil.which(tool):
            raise SystemExit(f"Required host tool not found: {tool}")
    if args.wait:
        access = run(["docker", "ps", "--filter", f"label=com.docker.compose.project={PROJECT}",
                      "--format", "{{.ID}}"])
        if access.returncode:
            raise SystemExit(access.stderr.decode(errors="replace"))
        while (remaining := (GENESIS - utc()).total_seconds() + 30) > 0:
            time.sleep(min(remaining, 30))
    if utc() <= GENESIS:
        raise SystemExit("Host UTC is not later than genesis.")
    evidence = RUNTIME / "evidence"
    out = Path(tempfile.mkdtemp(prefix=utc().strftime("phase-4b-postgenesis-%Y%m%dT%H%M%SZ-"), dir=evidence))
    (out / "timing.txt").write_text(f"Collection UTC {utc().isoformat()}\nGenesis UTC {GENESIS.isoformat()}\n")
    print(f"Evidence directory: {out}", flush=True)
    nodes = discover(out)
    with ThreadPoolExecutor(max_workers=8) as workers:
        initial = [workers.submit(diagnostics, out, asn, container, "before")
                   for asn, container in nodes.items()]
        for future in initial:
            future.result()
        capture_jobs = {asn: workers.submit(collect_capture, out, asn, nodes[asn])
                        for asn in CAPTURE_NODES if asn in nodes}
        start = time.monotonic()
        rounds = []
        for number in range(1, 4):
            time.sleep(max(0, start + 60 * (number - 1) - time.monotonic()))
            jobs = {asn: workers.submit(tip, out, number, asn, container)
                    for asn, container in nodes.items()}
            rounds.append({asn: future.result() for asn, future in jobs.items()})
            print(f"Recorded tip round {number} at {utc().isoformat()}", flush=True)
        final = [workers.submit(diagnostics, out, asn, container, "after")
                 for asn, container in nodes.items()]
        final += [workers.submit(logs, out, asn, container) for asn, container in nodes.items()]
        for future in final:
            future.result()
        captures = {asn: future.result() for asn, future in capture_jobs.items()}
    summarize(out, nodes, rounds, captures)
    print(f"Report updated. Collection summary: {out / 'summary.md'}", flush=True)


if __name__ == "__main__":
    main()
