#!/usr/bin/env python3
"""Stage B12-P9 sources or generate fresh genesis after deployment approval."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / "B12-cardano"
MAGIC = 4343
VERSION = {"major": 9, "minor": 0}
PROFILE = "private-testnet-conway-v2"
GENERATED = "testnet-conway-v2"
ERAS = ("Byron", "Shelley", "Alonzo", "Conway")
EPOCH_ZERO = ("Shelley", "Allegra", "Mary", "Alonzo", "Babbage", "Conway")
MARKER = "b12-p9-source.json"


def load(path):
    return json.loads(path.read_text())


def save(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli_run(cli, *args):
    return subprocess.run(
        [str(cli), *map(str, args)], check=True, text=True, stdout=subprocess.PIPE,
    ).stdout.strip()


def stage(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    paths = [Path("blockchain.py")]
    profile = Path("config") / PROFILE
    paths += [profile / "config.json"]
    paths += [profile / f"topology-node{i}.json" for i in range(1, 5)]
    validator = Path("smart-contract/sensor-validation")
    paths += [validator / name for name in (
        "aiken.toml", "aiken.lock",
        "validators/sensor_validator.ak", "validators/sensor_hash_validation.ak",
    )]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)

    compiler = root / "blockchain.py"
    source_text = compiler.read_text()
    old_summary = 'print("Network magic: 4242")'
    if source_text.count(old_summary) != 1:
        raise ValueError("The B12 compiler summary changed. Review its staged adaptation.")
    compiler.write_text(source_text.replace(old_summary, f'print("Network magic: {MAGIC}")')
                        .replace("network magic 4242, TCP", f"network magic {MAGIC}, TCP"))

    spec_path = Path("config/specs/shelley-spec.json")
    spec = load(SOURCE / spec_path)
    spec["networkMagic"] = MAGIC
    spec["protocolParams"]["protocolVersion"] = VERSION
    (root / spec_path).parent.mkdir()
    save(root / spec_path, spec)
    validate_inputs(root)
    save(root / MARKER, {
        "profile": "B12-P9", "magic": MAGIC, "protocolVersion": VERSION,
        "original_sources": {str(path): sha256(SOURCE / path) for path in [*paths, spec_path]},
        "staged_sources": {str(path): sha256(root / path) for path in [*paths, spec_path]},
    })


def validate_inputs(root):
    config = load(root / "config" / PROFILE / "config.json")
    spec = load(root / "config/specs/shelley-spec.json")
    if spec["networkMagic"] != MAGIC or spec["protocolParams"]["protocolVersion"] != VERSION:
        raise ValueError("The staged Shelley input must specify magic 4343 and protocol 9.0.")
    expected = {f"Test{era}HardForkAtEpoch": 0 for era in EPOCH_ZERO}
    triggers = {key: value for key, value in config.items() if re.fullmatch(r"Test.*HardForkAtEpoch", key)}
    if triggers != expected or config.get("ExperimentalHardForksEnabled") is not False:
        raise ValueError("Expected exactly the epoch-zero transitions through Conway.")
    for index in range(1, 5):
        topology = load(root / "config" / PROFILE / f"topology-node{index}.json")
        root_group, = topology["localRoots"]
        peers = {(peer["address"], peer["port"]) for peer in root_group["accessPoints"]}
        if peers != {(f"10.{asn}.0.71", 3001) for asn in range(150, 154) if asn != 149 + index}:
            raise ValueError(f"Unexpected topology for node {index}")
    return config, spec


def genesis(root, bundle, minutes):
    marker = load(root / MARKER)
    if marker["profile"] != "B12-P9" or marker["magic"] != MAGIC:
        raise ValueError("Target is not a staged B12-P9 root.")
    for name, digest in marker["staged_sources"].items():
        if sha256(root / name) != digest:
            raise ValueError(f"Staged source changed: {name}")
    config, spec = validate_inputs(root)
    config_dir = root / "config" / PROFILE
    generated = root / "config/generated" / GENERATED
    if (generated.parent.exists() or list(config_dir.glob("*-genesis.json"))
            or (root / "output").exists() or (root / ".runtime").exists()):
        raise ValueError("Use a fresh staged root for genesis generation.")

    cli = bundle / "bin/cardano-cli"
    versions = {name: cli_run(bundle / "bin" / name, "--version")
                for name in ("cardano-node", "cardano-cli")}
    if not versions["cardano-node"].startswith("cardano-node 11.1.3 ") or not versions["cardano-cli"].startswith("cardano-cli 11.2.3.0 "):
        raise ValueError("Use the checksum-verified Cardano Node 11.1.3 release bundle.")
    resources = root / "resources"
    if resources.exists():
        raise ValueError("The staged resources directory must be absent before generation.")
    start = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).replace(microsecond=0)

    with tempfile.TemporaryDirectory(prefix=".genesis-", dir=root) as temporary:
        fresh = Path(temporary) / "generated"
        cli_run(
            cli, "conway", "genesis", "create-testnet-data",
            "--spec-shelley", root / "config/specs/shelley-spec.json",
            "--testnet-magic", MAGIC, "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--genesis-keys", 3, "--pools", 3, "--stake-delegators", 3, "--utxo-keys", 3,
            "--committee-keys", 0, "--drep-keys", 0,
            "--total-supply", spec["maxLovelaceSupply"], "--delegated-supply", 300_000_000_000,
            "--out-dir", fresh,
        )
        shelley = load(fresh / "shelley-genesis.json")
        byron = load(fresh / "byron-genesis.json")
        conway = load(fresh / "conway-genesis.json")
        alonzo = load(fresh / "alonzo-genesis.json")
        if shelley["protocolParams"]["protocolVersion"] != VERSION:
            raise ValueError("The CLI did not retain protocol 9.0 from the input spec. No genesis files were installed.")
        if shelley["networkMagic"] != MAGIC or byron["protocolConsts"]["protocolMagic"] != MAGIC:
            raise ValueError("The generated genesis network identifiers disagree.")
        if datetime.fromisoformat(shelley["systemStart"].replace("Z", "+00:00")) != start or byron["startTime"] != int(start.timestamp()):
            raise ValueError("The generated genesis start times disagree.")
        model = conway["plutusV3CostModel"]
        if not model or any(type(entry) is not int for entry in model):
            raise ValueError("The Conway genesis lacks a usable Plutus V3 cost-model vector.")
        fees = shelley["protocolParams"]
        if fees["minFeeA"] < 0 or fees["minFeeB"] < 0 or fees["minFeeA"] + fees["minFeeB"] <= 0:
            raise ValueError("Expected nonnegative fee coefficients with at least one positive coefficient.")
        if alonzo["collateralPercentage"] <= 0 or alonzo["maxCollateralInputs"] < 1:
            raise ValueError("The generated genesis does not permit collateral.")
        for units in ("maxTxExUnits", "maxBlockExUnits"):
            if min(alonzo[units].values()) <= 0:
                raise ValueError(f"Expected positive {units}.")
        if min(alonzo["executionPrices"].values()) <= 0:
            raise ValueError("Expected positive execution prices.")
        for pool in range(1, 4):
            for credential in ("kes.skey", "vrf.skey", "opcert.cert"):
                if not (fresh / "pools-keys" / f"pool{pool}" / credential).is_file():
                    raise ValueError(f"Missing producer credential file for pool {pool}: {credential}")

        checksums = {}
        for era in ERAS:
            name = f"{era.lower()}-genesis.json"
            source = fresh / name
            command = ("byron", "genesis", "print-genesis-hash", "--genesis-json") if era == "Byron" else (
                "hash", "genesis-file", "--genesis",
            )
            digest = cli_run(cli, *command, source)
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"Invalid {era} genesis hash.")
            config[f"{era}GenesisFile"] = name
            config[f"{era}GenesisHash"] = digest
            checksums[name] = {"cardano_hash": digest, "sha256": sha256(source)}

        generated.parent.mkdir()
        fresh.rename(generated)
        for name in checksums:
            with (generated / name).open("rb") as source, (config_dir / name).open("xb") as target:
                shutil.copyfileobj(source, target)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        resources.mkdir()
        (resources / "cardano-static").symlink_to(bundle, target_is_directory=True)
        save(root / "b12-p9-genesis-manifest.json", {
            "magic": MAGIC, "protocolVersion": VERSION, "systemStart": start.isoformat(),
            "binaryVersions": versions, "plutusV3CostModelEntries": len(model),
            "fees": {key: fees[key] for key in ("minFeeA", "minFeeB")},
            "alonzo": {key: alonzo[key] for key in (
                "collateralPercentage", "maxCollateralInputs", "executionPrices", "maxTxExUnits",
                "maxBlockExUnits",
            )},
            "genesis": checksums, "config_sha256": sha256(config_path),
        })


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    staging = commands.add_parser("stage", help="copy public source files and prepare an input specification")
    staging.add_argument("directory", type=Path)
    generation = commands.add_parser("genesis", help="generate genesis and keys in a previously staged root")
    generation.add_argument("directory", type=Path)
    generation.add_argument("--bundle", type=Path, required=True)
    generation.add_argument("--minutes", type=int, default=30)
    args = parser.parse_args()
    root = args.directory.resolve()
    if args.command == "stage":
        stage(root)
    else:
        if args.minutes < 5:
            parser.error("Choose a start at least five minutes in the future.")
        genesis(root, args.bundle.resolve(), args.minutes)


if __name__ == "__main__":
    main()
