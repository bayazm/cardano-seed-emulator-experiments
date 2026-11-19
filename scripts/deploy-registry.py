#!/usr/bin/env python3
"""Deploy and update the B15/B16 registry on an explicitly selected lab network."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


MAGIC = ("--testnet-magic", "5556")
SOCKET = ("--socket-path", "/cardano/node.socket")
TOKEN = b"B15_REGISTRY"
PROFILES = {
    "B15-cardano-smart-authorization-v2": "b15",
    "B16-cardano-did-authentication": "b16",
}
UTXO = re.compile(r"([0-9a-f]{64})#(0|[1-9][0-9]*)")


def run(*command):
    return subprocess.run(list(map(str, command)), check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def constructor(index, *fields):
    return {"constructor": index, "fields": list(fields)}


def datum(revision):
    return constructor(0, {"bytes": b"AS184".hex()}, {"bytes": b"10.184.0.71".hex()},
                       constructor(revision % 2), {"int": revision})


def cbor_bytes(value):
    header = bytes([0x40 + len(value)]) if len(value) < 24 else bytes([0x58, len(value)])
    return (header + value).hex()


def output_reference(reference):
    match = UTXO.fullmatch(reference)
    if not match:
        raise ValueError("Expected a lowercase TxId#TxIx")
    index = int(match[2])
    if index > 65535:
        raise ValueError("TxIx exceeds uint16")
    if index < 24:
        encoded = f"{index:02x}"
    elif index < 256:
        encoded = f"18{index:02x}"
    else:
        encoded = f"19{index:04x}"
    return "d87982" + cbor_bytes(bytes.fromhex(match[1])) + encoded


def apply_script(blueprint, directory, module, purpose, parameters, filename):
    source = blueprint
    for index, parameter in enumerate(parameters):
        target = directory / f"{module}-{index}.json"
        run("aiken", "blueprint", "apply", "-i", source, "-o", target,
            "-m", module, "-v", module, parameter)
        source = target
    validators = json.loads(source.read_text())["validators"]
    validator, = [entry for entry in validators if entry["title"] == f"{module}.{module}.{purpose}"]
    if validator.get("parameters"):
        raise ValueError(f"{module} still has unapplied parameters")
    script = directory / filename
    write_json(script, {"type": "PlutusScriptV3", "description": "",
                        "cborHex": validator["compiledCode"]})
    return script, validator["hash"]


class Deployment:
    def __init__(self, root, funding_prefix, container):
        self.root = root
        self.network = root / "network"
        self.cli = self.network / "resources/cardano-static/bin/cardano-cli"
        self.state = self.network / "deployment/registry"
        self.private = self.network / ".runtime/registry-private"
        self.funding = funding_prefix.resolve()
        self.admin = self.private / "administrator"
        prefix = PROFILES[root.name]
        self.nodes = [f"{prefix}-as{asn}h-Cardano-Node-{asn-179}-10.{asn}.0.71"
                      for asn in range(180, 184)]
        self.container = container or self.nodes[0]
        if self.container not in self.nodes:
            raise ValueError("Select a producer or incumbent relay from this experiment")

    def remote(self, container, *args):
        return run("docker", "exec", container, *args)

    def query(self, container, address):
        return json.loads(self.remote(container, "cardano-cli", "conway", "query", "utxo",
                                      "--address", address, "--output-json", *MAGIC, *SOCKET))

    def write_wallet(self):
        self.private.mkdir(parents=True, exist_ok=True)
        if not self.funding.with_suffix(".skey").is_file():
            raise ValueError("Funding signing key missing")
        if not self.admin.with_suffix(".skey").exists() and not self.admin.with_suffix(".vkey").exists():
            run(self.cli, "address", "key-gen", "--verification-key-file", self.admin.with_suffix(".vkey"),
                "--signing-key-file", self.admin.with_suffix(".skey"))
        if not self.admin.with_suffix(".skey").is_file() or not self.admin.with_suffix(".vkey").is_file():
            raise ValueError("Incomplete administrator key pair")
        print(self.wallet())

    def wallet(self):
        return run(self.cli, "address", "build", "--payment-verification-key-file",
                   self.funding.with_suffix(".vkey"), *MAGIC)

    def admin_hash(self):
        return run(self.cli, "address", "key-hash", "--payment-verification-key-file",
                   self.admin.with_suffix(".vkey"))

    def inputs(self, wallet, *references):
        if len(set(references)) != len(references):
            raise ValueError("Funding, collateral and script inputs must be distinct")
        outputs = self.query(self.container, wallet)
        for reference in references:
            if not UTXO.fullmatch(reference or "") or reference not in outputs:
                raise ValueError("Supply confirmed wallet UTXO references from funds")
            if set(outputs[reference]["value"]) != {"lovelace"}:
                raise ValueError("This workflow expects pure ADA wallet inputs")

    def prepare(self, reference):
        output_reference(reference)
        self.inputs(self.wallet(), reference)
        self.state.mkdir(parents=True, exist_ok=False)
        blueprint = self.root / "relay-authorization/plutus.json"
        if json.loads(blueprint.read_text())["preamble"]["plutusVersion"] != "v3":
            raise ValueError("Expected a Plutus V3 blueprint")

        policy_script, policy_hash = apply_script(
            blueprint, self.state, "registry_mint", "mint",
            [output_reference(reference)], "registry-mint.plutus")
        policy = run(self.cli, "conway", "transaction", "policyid", "--script-file", policy_script)
        if policy != policy_hash:
            raise ValueError("Policy hash differs between Aiken and Cardano CLI")
        administrator = self.admin_hash()
        membership, _ = apply_script(
            blueprint, self.state, "relay_membership", "spend",
            [cbor_bytes(bytes.fromhex(administrator)), cbor_bytes(bytes.fromhex(policy)),
             cbor_bytes(TOKEN)], "relay-membership.plutus")
        address = run(self.cli, "address", "build", "--payment-script-file", membership, *MAGIC)
        (self.state / "policy-id.txt").write_text(policy + "\n")
        (self.state / "membership-script.addr").write_text(address + "\n")
        write_json(self.state / "parameters.json", {"mint_input": reference,
                   "administrator": administrator, "funding_address": self.wallet()})

    def asset(self):
        return (self.state / "policy-id.txt").read_text().strip() + "." + TOKEN.hex()

    def address(self):
        return (self.state / "membership-script.addr").read_text().strip()

    def verify(self, revision):
        policy, token = self.asset().split(".")
        observations = []
        for node in self.nodes:
            outputs = self.query(node, self.address())
            matches = [(ref, obj) for ref, obj in outputs.items()
                       if obj["value"].get(policy, {}).get(token, 0)]
            if len(matches) != 1:
                raise ValueError(f"{node}: expected one registry output")
            reference, output = matches[0]
            if output["value"][policy][token] != 1 or output.get("inlineDatum") != datum(revision):
                raise ValueError(f"{node}: unexpected registry asset or revision")
            observations.append((reference, output["value"]["lovelace"]))
        if len(set(observations)) != 1:
            raise ValueError("Registry observations disagree across incumbents")
        ref, amount = observations[0]
        print(json.dumps({"reference": ref, "revision": revision, "lovelace": amount}))
        return ref, amount

    def transaction(self, args):
        wallet = self.wallet()
        operation = args.operation
        self.inputs(wallet, args.input, *([args.collateral] if operation != "collateral" else []))
        if operation != "collateral":
            parameters = json.loads((self.state / "parameters.json").read_text())
            if wallet != parameters["funding_address"] or self.admin_hash() != parameters["administrator"]:
                raise ValueError("Wallet or administrator differs from the applied deployment")
        command = ["--tx-in", args.input]
        public_files = {}
        if operation == "collateral":
            if args.lovelace <= 0:
                raise ValueError("Collateral output must be positive")
            command += ["--tx-out", f"{wallet}+{args.lovelace}"]
        elif operation == "mint":
            if args.input != parameters["mint_input"] or args.lovelace <= 0:
                raise ValueError("Use the applied mint input and positive registry lovelace")
            public_files["mint.json"] = {"int": 0}
            public_files["datum.json"] = datum(0)
            public_files["mint.plutus"] = self.state / "registry-mint.plutus"
            command += ["--mint", f"1 {self.asset()}", "--mint-script-file", "@mint.plutus",
                        "--mint-redeemer-file", "@mint.json"]
            amount = args.lovelace
        else:
            revision = 1 if operation == "authorize" else 2
            reference, amount = self.verify(revision - 1)
            public_files["datum.json"] = datum(revision)
            public_files["redeemer.json"] = constructor(0, constructor(revision - 1), datum(revision))
            public_files["membership.plutus"] = self.state / "relay-membership.plutus"
            command += ["--tx-in", reference, "--tx-in-script-file", "@membership.plutus",
                        "--tx-in-inline-datum-present", "--tx-in-redeemer-file", "@redeemer.json",
                        "--required-signer-hash", parameters["administrator"], "--witness-override", "2"]
        if operation != "collateral":
            command += ["--tx-in-collateral", args.collateral, "--tx-out",
                        f"{self.address()}+{amount}+1 {self.asset()}",
                        "--tx-out-inline-datum-file", "@datum.json"]
        command += ["--change-address", wallet, *MAGIC, *SOCKET, "--out-file", "@body"]
        self.build_and_submit(args, command, public_files)

    def build_and_submit(self, args, command, public_files):
        with tempfile.TemporaryDirectory(prefix=f"{args.operation}-", dir=self.private) as work:
            local = Path(work)
            remote = self.remote(self.container, "mktemp", "-d", "/tmp/cardano-registry.XXXXXXXX")
            if not re.fullmatch(r"/tmp/cardano-registry\.[A-Za-z0-9]{8}", remote):
                raise ValueError("Unexpected container temporary path")
            try:
                for name, value in public_files.items():
                    path = value if isinstance(value, Path) else local / name
                    if not isinstance(value, Path):
                        write_json(path, value)
                    run("docker", "cp", path, f"{self.container}:{remote}/{name}")
                expanded = [f"{remote}/{item[1:]}" if item.startswith("@") else item for item in command]
                self.remote(self.container, "cardano-cli", "conway", "transaction", "build", *expanded)
                run("docker", "cp", f"{self.container}:{remote}/body", local / "body")
                txid = run(self.cli, "conway", "transaction", "txid", "--tx-body-file", local / "body",
                           "--output-text")
                if not args.submit:
                    print(f"Built {args.operation} transaction {txid}; submission disabled")
                    return
                flags = ["--signing-key-file", self.funding.with_suffix(".skey")]
                if args.operation in ("authorize", "revoke"):
                    flags += ["--signing-key-file", self.admin.with_suffix(".skey")]
                run(self.cli, "conway", "transaction", "sign", "--tx-body-file", local / "body",
                    *flags, *MAGIC, "--out-file", local / "signed")
                run("docker", "cp", local / "signed", f"{self.container}:{remote}/signed")
                self.remote(self.container, "cardano-cli", "conway", "transaction", "submit",
                            "--tx-file", f"{remote}/signed", *MAGIC, *SOCKET)
                print(f"Submitted {args.operation} transaction {txid}; query for confirmation")
            finally:
                self.remote(self.container, "rm", "-f", "--",
                            *(f"{remote}/{name}" for name in (*public_files, "body", "signed")))
                self.remote(self.container, "rmdir", "--", remote)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--funding-key", type=Path, required=True, help="Payment key prefix without extension")
    parser.add_argument("--container", help="Exact build/query container name; defaults to AS180")
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("wallet", "funds", "prepare", "collateral", "mint", "authorize", "revoke", "verify"):
        operation = sub.add_parser(name)
        if name in ("prepare", "collateral", "mint", "authorize", "revoke"):
            operation.add_argument("--input", required=True)
        if name in ("mint", "authorize", "revoke"):
            operation.add_argument("--collateral", required=True)
        if name in ("collateral", "mint"):
            operation.add_argument("--lovelace", type=int, default=5_000_000)
        if name in ("collateral", "mint", "authorize", "revoke"):
            operation.add_argument("--submit", action="store_true")
        if name == "verify":
            operation.add_argument("--revision", type=int, choices=(0, 1, 2), required=True)
    args = parser.parse_args()
    root = args.experiment.resolve()
    if root.name not in PROFILES:
        parser.error("Select the publication B15 v2 or B16 experiment directory")
    try:
        deployment = Deployment(root, args.funding_key, args.container)
        if args.operation == "wallet":
            deployment.write_wallet()
        elif args.operation == "funds":
            print(json.dumps(deployment.query(deployment.container, deployment.wallet()), indent=2))
        elif args.operation == "prepare":
            deployment.prepare(args.input)
        elif args.operation == "verify":
            deployment.verify(args.revision)
        else:
            deployment.transaction(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Registry operation failed: {exc}\n")


if __name__ == "__main__":
    main()
