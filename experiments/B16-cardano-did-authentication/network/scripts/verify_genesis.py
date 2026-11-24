#!/usr/bin/env python3
"""Verify the local B16 genesis and its public key bindings before startup."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

MAGIC = "5556"
ALLOCATION = 4_500_000_000_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def verify_start(start, *, require_future_start):
    if require_future_start:
        require(start > datetime.now(timezone.utc),
                f"Genesis start {start.isoformat()} must be later than the current UTC time")


def verify(network, cli, *, require_future_start=False):
    config_dir = network / "config/private-testnet-conway-v2"
    generated = network / "config/generated/testnet-conway-v2"
    config = read(config_dir / "config.json")

    def call(*args):
        return subprocess.check_output([str(cli), *map(str, args)], text=True).strip()

    require(config["Protocol"] == "Cardano" and config["RequiresNetworkMagic"] == "RequiresMagic",
            "Unexpected node protocol or magic configuration")
    for era in ("Shelley", "Allegra", "Mary", "Alonzo", "Babbage", "Conway"):
        require(config.get(f"Test{era}HardForkAtEpoch") == 0, f"{era} must start at epoch zero")
    require(config.get("TestDijkstraHardForkAtEpoch") is None
            and config["ExperimentalHardForksEnabled"] is False
            and config["ExperimentalProtocolsEnabled"] is False, "Unexpected experimental fork settings")

    genesis = {}
    for era in ("Byron", "Shelley", "Alonzo", "Conway"):
        filename = f"{era.lower()}-genesis.json"
        path = config_dir / filename
        require(config[f"{era}GenesisFile"] == filename, f"Unexpected {era} genesis filename")
        require(path.read_bytes() == (generated / filename).read_bytes(),
                f"Active and generated {era} genesis files differ")
        if era == "Byron":
            digest = call("byron", "genesis", "print-genesis-hash", "--genesis-json", path)
        else:
            digest = call("hash", "genesis-file", "--genesis", path)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) and config[f"{era}GenesisHash"] == digest,
                f"{era} genesis hash mismatch")
        genesis[era] = read(path)

    shelley = genesis["Shelley"]
    byron = genesis["Byron"]
    require(shelley["networkId"] == "Testnet" and
            shelley["networkMagic"] == byron["protocolConsts"]["protocolMagic"] == int(MAGIC),
            "Expected Byron and Shelley magic 5556")
    start = datetime.fromisoformat(shelley["systemStart"].replace("Z", "+00:00"))
    require(start == datetime.fromtimestamp(byron["startTime"], timezone.utc),
            "Byron and Shelley start times differ")
    require(byron["protocolConsts"]["k"] == shelley["securityParam"],
            "Byron and Shelley security parameters differ")
    require(shelley["protocolParams"]["protocolVersion"] == {"major": 9, "minor": 0},
            "Expected initial protocol version 9.0")
    require(shelley["maxLovelaceSupply"] == 30_000_000_000_000_000,
            "Unexpected maximum lovelace supply")
    alonzo = genesis["Alonzo"]
    cost_model = genesis["Conway"]["plutusV3CostModel"]
    require(alonzo["collateralPercentage"] > 0 and alonzo["maxCollateralInputs"] >= 1
            and all(alonzo["executionPrices"][key] > 0 for key in ("priceMemory", "priceSteps"))
            and all(alonzo["maxTxExUnits"][key] > 0 for key in ("memory", "steps"))
            and isinstance(cost_model, list) and len(cost_model) == 251
            and all(type(coefficient) is int for coefficient in cost_model),
            "Unexpected collateral, execution parameters or Plutus V3 cost model")

    def raw_address(*args):
        address = call("address", "build", *args, "--testnet-magic", MAGIC)
        return json.loads(call("address", "info", "--address", address))["base16"]

    extra = shelley["extraConfig"]
    funds = extra["initialFunds"]["data"]
    pools = extra["stakePools"]["data"]
    delegates = extra["stakeCredentials"]["data"]
    require(not shelley["initialFunds"] and not any(shelley["staking"].values()),
            "Unexpected duplicate funding or staking in legacy fields")
    indexes = range(1, 4)
    require({p.name for p in (generated / "pools-keys").glob("pool*") if p.is_dir()}
            == {f"pool{i}" for i in indexes}, "Expected exactly three producer key directories")
    pool_ids, stake_ids, kes_keys, vrf_keys, addresses = set(), set(), set(), set(), set()
    for i in indexes:
        pool = generated / f"pools-keys/pool{i}"
        for filename in ("kes.skey", "vrf.skey", "opcert.cert"):
            require((pool / filename).is_file(), f"Missing producer {i} {filename}")
        certificate = read(pool / "opcert.cert")
        require(certificate["type"] == "NodeOperationalCertificate"
                and re.fullmatch(r"(?:[0-9a-fA-F]{2})+", certificate["cborHex"]),
                f"Invalid producer {i} operational certificate envelope")
        with TemporaryDirectory(prefix="b16-genesis-public-") as temporary:
            for key in ("kes", "vrf"):
                derived_path = Path(temporary) / f"{key}.vkey"
                call("key", "verification-key", "--signing-key-file", pool / f"{key}.skey",
                     "--verification-key-file", derived_path)
                derived = read(derived_path)
                expected = read(pool / f"{key}.vkey")
                require(all(derived[field] == expected[field] for field in ("type", "cborHex")),
                        f"Producer {i} {key.upper()} signing key does not match verification key")
        pool_id = call("conway", "stake-pool", "id", "--cold-verification-key-file",
                       pool / "cold.vkey", "--output-hex")
        vrf = call("node", "key-hash-VRF", "--verification-key-file", pool / "vrf.vkey")
        kes_keys.add(read(pool / "kes.vkey")["cborHex"])
        pool_ids.add(pool_id)
        vrf_keys.add(vrf)
        require(pools.get(pool_id, {}).get("poolId") == pool_id and pools[pool_id]["vrf"] == vrf,
                f"Producer {i} cold key or VRF does not match genesis")
        delegator = generated / f"stake-delegators/delegator{i}"
        stake = call("conway", "stake-address", "key-hash", "--stake-verification-key-file",
                     delegator / "staking.vkey")
        stake_ids.add(stake)
        addresses.add(raw_address("--payment-verification-key-file", delegator / "payment.vkey",
                                  "--stake-verification-key-file", delegator / "staking.vkey"))
        addresses.add(raw_address("--payment-verification-key-file",
                                  generated / f"utxo-keys/utxo{i}/utxo.vkey"))
    require(len(kes_keys) == len(vrf_keys) == len(pool_ids) == 3 and pool_ids == set(pools),
            "Expected three distinct producer pools, KES keys and VRF keys")
    require(len(stake_ids) == 3 and stake_ids == set(delegates)
            and set(delegates.values()) == pool_ids, "Expected one generated stake delegator per pool")
    require(len(addresses) == 6 and funds == dict.fromkeys(addresses, ALLOCATION),
            "Expected six generated addresses funded with 4,500,000,000,000,000 lovelace each")
    verify_start(start, require_future_start=require_future_start)
    print(f"B16 genesis verified. Magic {MAGIC}, start {start.isoformat()}, protocol 9.0, "
          "three producer pools, six funded addresses, four matching genesis hashes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cli", type=Path, help="Use an independently installed Cardano CLI")
    parser.add_argument("--require-future-start", action="store_true",
                        help="Reject a genesis start at or before the current UTC time")
    args = parser.parse_args()
    try:
        verify(args.network, args.cli or args.network / "resources/cardano-static/bin/cardano-cli",
               require_future_start=args.require_future_start)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"B16 genesis verification failed: {exc}\n")


if __name__ == "__main__":
    main()
