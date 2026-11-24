"""Verify B16 genesis checks with synthetic public bindings and no real keys."""

import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_genesis


class GenesisTests(unittest.TestCase):
    ERAS = ("Byron", "Shelley", "Alonzo", "Conway")

    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="b16-genesis-test-")
        self.addCleanup(workspace.cleanup)
        self.network = Path(workspace.name)
        self.active = self.network / "config/private-testnet-conway-v2"
        self.generated = self.network / "config/generated/testnet-conway-v2"
        self.active.mkdir(parents=True)
        config_path = Path(__file__).resolve().parents[1] / "config/private-testnet-conway-v2/config.json"
        self.config = json.loads(config_path.read_text())
        self.start = datetime(2099, 1, 1, tzinfo=timezone.utc)
        pools, stakes, funds = {}, {}, {}
        for index in range(1, 4):
            pool = self.generated / f"pools-keys/pool{index}"
            pool.mkdir(parents=True)
            for name in ("kes.skey", "vrf.skey"):
                (pool / name).write_text("synthetic placeholder")
            (pool / "opcert.cert").write_text(json.dumps(
                {"type": "NodeOperationalCertificate", "cborHex": "00"}
            ))
            for key in ("kes", "vrf"):
                (pool / f"{key}.vkey").write_text(json.dumps(
                    {"type": key, "cborHex": f"00{index}"}
                ))
            pools[f"pool{index}"] = {"poolId": f"pool{index}", "vrf": f"vrf-{index}"}
            stakes[f"stake-{index}"] = f"pool{index}"
            for role in ("base", "enterprise"):
                funds[f"{role}-{index}"] = verify_genesis.ALLOCATION
        self.genesis = {
            "Byron": {
                "startTime": int(self.start.timestamp()),
                "protocolConsts": {"protocolMagic": 5556, "k": 2160},
            },
            "Shelley": {
                "networkId": "Testnet", "networkMagic": 5556, "securityParam": 2160,
                "systemStart": self.start.isoformat(), "maxLovelaceSupply": 30_000_000_000_000_000,
                "protocolParams": {"protocolVersion": {"major": 9, "minor": 0}},
                "extraConfig": {
                    "initialFunds": {"data": funds},
                    "stakePools": {"data": pools},
                    "stakeCredentials": {"data": stakes},
                },
                "initialFunds": {}, "staking": {"pools": {}, "stake": {}},
            },
            "Alonzo": {
                "collateralPercentage": 150, "maxCollateralInputs": 3,
                "executionPrices": {"priceMemory": 1, "priceSteps": 1},
                "maxTxExUnits": {"memory": 2, "steps": 3},
            },
            "Conway": {"plutusV3CostModel": [1] * 251},
        }
        cardano = patch.object(verify_genesis.subprocess, "check_output", side_effect=self.cli)
        self.addCleanup(cardano.stop)
        cardano.start()
        self.mismatched_signing_key = None

    def write_inputs(self):
        for era in self.ERAS:
            filename = era.lower() + "-genesis.json"
            data = json.dumps(self.genesis[era]).encode()
            for directory in (self.active, self.generated):
                (directory / filename).write_bytes(data)
            self.config[f"{era}GenesisHash"] = hashlib.sha256(data).hexdigest()
        self.write_config()

    def write_config(self):
        (self.active / "config.json").write_text(json.dumps(self.config))

    def cli(self, command, *, text):
        self.assertTrue(text)
        _, *args = command
        if args[0] in ("hash", "byron"):
            return hashlib.sha256(Path(args[-1]).read_bytes()).hexdigest()
        if args[:2] == ["key", "verification-key"]:
            signing_key = Path(args[3])
            public = json.loads(signing_key.with_suffix(".vkey").read_text())
            if signing_key.name == self.mismatched_signing_key:
                public["cborHex"] = "ffff"
            Path(args[-1]).write_text(json.dumps(public))
            return ""
        if args[:3] == ["conway", "stake-pool", "id"]:
            return Path(args[-2]).parent.name
        if args[:2] == ["node", "key-hash-VRF"]:
            return "vrf-" + Path(args[-1]).parent.name[-1]
        if args[:3] == ["conway", "stake-address", "key-hash"]:
            return "stake-" + Path(args[-1]).parent.name[-1]
        if args[:2] == ["address", "build"]:
            self.assertEqual(args[-2:], ["--testnet-magic", "5556"])
            role = "base" if "--stake-verification-key-file" in args else "enterprise"
            return role + "-" + Path(args[3]).parent.name[-1]
        if args[:2] == ["address", "info"]:
            return json.dumps({"base16": args[-1]})
        self.fail(f"Unexpected CLI request {command}")

    def verify(self, *, future=False):
        with contextlib.redirect_stdout(io.StringIO()):
            verify_genesis.verify(self.network, Path("/synthetic/cardano-cli"),
                                  require_future_start=future)

    def test_complete_fresh_genesis(self):
        self.write_inputs()
        with patch.object(verify_genesis, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2098, 1, 1, tzinfo=timezone.utc)
            self.verify(future=True)

    def test_rejects_mismatched_magic(self):
        self.genesis["Byron"]["protocolConsts"]["protocolMagic"] = 5557
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "magic 5556"):
            self.verify()

    def test_rejects_mismatched_start(self):
        self.genesis["Byron"]["startTime"] += 1
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "start times differ"):
            self.verify()

    def test_rejects_nonfuture_start_in_fresh_mode(self):
        self.write_inputs()
        with patch.object(verify_genesis, "datetime", wraps=datetime) as clock:
            clock.now.return_value = self.start
            with self.assertRaisesRegex(ValueError, "later than the current UTC time"):
                self.verify(future=True)

    def test_rejects_divergent_active_genesis(self):
        self.write_inputs()
        (self.active / "alonzo-genesis.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Active and generated Alonzo"):
            self.verify()

    def test_rejects_incorrect_genesis_hash(self):
        self.write_inputs()
        self.config["ConwayGenesisHash"] = "00" * 32
        self.write_config()
        with self.assertRaisesRegex(ValueError, "Conway genesis hash mismatch"):
            self.verify()

    def test_rejects_wrong_protocol_version(self):
        self.genesis["Shelley"]["protocolParams"]["protocolVersion"]["major"] = 8
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "version 9.0"):
            self.verify()

    def test_rejects_wrong_cost_model_length(self):
        self.genesis["Conway"]["plutusV3CostModel"].pop()
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "Plutus V3 cost model"):
            self.verify()

    def test_rejects_stale_wallet_allocation(self):
        funds = self.genesis["Shelley"]["extraConfig"]["initialFunds"]["data"]
        funds["stale-wallet"] = funds.pop("enterprise-1")
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "six generated addresses"):
            self.verify()

    def test_rejects_stale_pool_or_stake_identity(self):
        self.genesis["Shelley"]["extraConfig"]["stakePools"]["data"]["pool1"]["vrf"] = "stale"
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "cold key or VRF"):
            self.verify()
        extra = self.genesis["Shelley"]["extraConfig"]
        extra["stakePools"]["data"]["pool1"]["vrf"] = "vrf-1"
        extra["stakeCredentials"]["data"]["stake-1"] = "pool2"
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "one generated stake delegator per pool"):
            self.verify()

    def test_rejects_missing_or_extra_producer_credentials(self):
        self.write_inputs()
        (self.generated / "pools-keys/pool4").mkdir()
        with self.assertRaisesRegex(ValueError, "exactly three"):
            self.verify()
        (self.generated / "pools-keys/pool4").rmdir()
        (self.generated / "pools-keys/pool3/opcert.cert").unlink()
        with self.assertRaisesRegex(ValueError, "Missing producer 3 opcert.cert"):
            self.verify()

    def test_rejects_mismatched_signing_key(self):
        self.write_inputs()
        self.mismatched_signing_key = "vrf.skey"
        with self.assertRaisesRegex(ValueError, "VRF signing key does not match"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
