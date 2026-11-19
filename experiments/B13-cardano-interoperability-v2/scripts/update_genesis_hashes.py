#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

CLI = (
    PROJECT_DIR
    / "resources/cardano-static/bin/cardano-cli"
)

GENESIS_FILES = {
    "Byron": "byron-genesis.json",
    "Shelley": "shelley-genesis.json",
    "Alonzo": "alonzo-genesis.json",
    "Conway": "conway-genesis.json",
}


def calculate_hash(filepath):
    if filepath.name == "byron-genesis.json":
        command = [
            str(CLI),
            "byron",
            "genesis",
            "print-genesis-hash",
            "--genesis-json",
            str(filepath),
        ]
    else:
        command = [
            str(CLI),
            "hash",
            "genesis-file",
            "--genesis",
            str(filepath),
        ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


for network in ("A", "B"):

    config_dir = PROJECT_DIR / "config" / f"network-{network}"

    config_file = config_dir / "config.json"

    with config_file.open() as f:
        config = json.load(f)

    print(f"\n========== Network {network} ==========")

    for era, filename in GENESIS_FILES.items():

        genesis_path = config_dir / filename

        genesis_hash = calculate_hash(genesis_path)

        config[f"{era}GenesisFile"] = filename
        config[f"{era}GenesisHash"] = genesis_hash

        print(f"{era}: {genesis_hash}")

    with config_file.open("w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print(f"Updated: {config_file}")
