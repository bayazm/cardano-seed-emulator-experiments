#!/usr/bin/env python3
"""Prepare fresh Cardano configuration in a reviewed experiment copy."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess


ERAS = ("Byron", "Shelley", "Alonzo", "Conway")
PROFILES = {
    "B11-cardano": ("private-testnet-d0", "testnet-02", 450_000_000_000, 0),
    "B12-cardano": ("private-testnet-conway-v2", "testnet-conway-v2", 300_000_000_000, 3),
    "B14-cardano-relay-admission": (
        "private-testnet-conway-v2", "testnet-conway-v2", 300_000_000_000, 3
    ),
    "B15-cardano-smart-authorization-v2": (
        "private-testnet-conway-v2", "testnet-conway-v2", 15_000_000_000_000_000, 3
    ),
    "B16-cardano-did-authentication": (
        "private-testnet-conway-v2", "testnet-conway-v2", 15_000_000_000_000_000, 3
    ),
}
B13_PROFILES = {
    "B13-cardano-interoperability-v2": 0,
    "B13-cardano-same-magic": 20,
    "B13-cardano-same-time": 0,
    "B13-cardano-node-join": 0,
}


def run_cli(cli, *args):
    return subprocess.run(
        [str(cli), *map(str, args)], check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def generate(cli, config_dir, generated, spec_path, start, pools, total, delegated, utxo_keys):
    config_path = config_dir / "config.json"
    config = json.loads(config_path.read_text())
    spec = json.loads(spec_path.read_text())

    if generated.exists() or any(config_dir.glob("*-genesis.json")):
        raise SystemExit(f"Existing genesis material detected at {config_dir} or {generated}")

    generated.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    run_cli(
        cli, "conway", "genesis", "create-testnet-data",
        "--spec-shelley", spec_path,
        "--genesis-keys", pools,
        "--pools", pools,
        "--stake-delegators", pools,
        "--utxo-keys", utxo_keys,
        "--total-supply", total,
        "--delegated-supply", delegated,
        "--testnet-magic", spec["networkMagic"],
        "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--out-dir", generated,
    )
    # CLI versions can supply their own initial protocol version. Keep the
    # scenario's recorded initial version while retaining generated bindings.
    shelley_path = generated / "shelley-genesis.json"
    shelley = json.loads(shelley_path.read_text())
    shelley["protocolParams"]["protocolVersion"] = spec["protocolParams"]["protocolVersion"]
    shelley_path.write_text(json.dumps(shelley, indent=2) + "\n")

    for era in ERAS:
        filename = f"{era.lower()}-genesis.json"
        source = generated / filename
        if era == "Byron":
            digest = run_cli(cli, "byron", "genesis", "print-genesis-hash", "--genesis-json", source)
        else:
            digest = run_cli(cli, "hash", "genesis-file", "--genesis", source)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SystemExit(f"Unexpected genesis hash for {era}")
        config[f"{era}GenesisFile"] = filename
        config[f"{era}GenesisHash"] = digest

    for era in ERAS:
        filename = f"{era.lower()}-genesis.json"
        with (generated / filename).open("rb") as source, (config_dir / filename).open("xb") as dest:
            shutil.copyfileobj(source, dest)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"{config_dir}: magic {spec['networkMagic']}, start {start.isoformat()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--minutes", type=int, default=30)
    args = parser.parse_args()
    if args.minutes < 5:
        parser.error("Choose a start at least five minutes in the future.")

    root = args.experiment.resolve()
    name = root.name
    if name not in PROFILES and name not in B13_PROFILES:
        parser.error(f"Unknown experiment directory: {name}")
    code = root / "network" if name.startswith(("B15", "B16")) else root
    config = code / "config"
    cli = code / "resources/cardano-static/bin/cardano-cli"
    if not cli.is_file():
        parser.error(f"Cardano CLI missing at {cli}")

    start = (datetime.now(timezone.utc) + timedelta(minutes=args.minutes)).replace(microsecond=0)
    if name in B13_PROFILES:
        for network, delay in (("A", 0), ("B", B13_PROFILES[name])):
            generate(
                cli, config / f"network-{network}", config / "generated" / f"network-{network}",
                config / "specs" / f"shelley-spec-{network}.json",
                start + timedelta(minutes=delay), 1, 450_000_000_000, 300_000_000_000, 1,
            )
    else:
        runtime, generated, delegated, utxo_keys = PROFILES[name]
        total = json.loads((config / "specs/shelley-spec.json").read_text())["maxLovelaceSupply"]
        generate(
            cli, config / runtime, config / "generated" / generated,
            config / "specs/shelley-spec.json", start, 3, total, delegated, utxo_keys,
        )


if __name__ == "__main__":
    main()
