#!/usr/bin/env python3
"""B16: read-only DID + Cardano admission integration."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DID_DIR = ROOT / "scripts" / "did_auth"

sys.path.insert(0, str(DID_DIR))

from identity import load_private_key
from prototype import (
    AdmissionGateway,
    GATEWAY,
    did_from_public_key,
    public_bytes,
    signed_message,
)
from enrollment import verify_certificate
from registry_policy import authorize_relay


NODES = {
    "AS180": "b16-as180h-Cardano-Node-1-10.180.0.71",
    "AS181": "b16-as181h-Cardano-Node-2-10.181.0.71",
    "AS182": "b16-as182h-Cardano-Node-3-10.182.0.71",
    "AS183": "b16-as183h-Cardano-Node-4-10.183.0.71",
}

EXPECTED_NODE = "AS184"
EXPECTED_IP = "10.184.0.71"
NETWORK_MAGIC = "5556"

REGISTRY_ADDR = (
    ROOT / "deployment/registry/membership-script.addr"
).read_text().strip()

POLICY_ID = (
    ROOT / "deployment/registry/policy-id.txt"
).read_text().strip()

TOKEN_HEX = "B15_REGISTRY".encode().hex()


def query_registry(container):
    command = [
        "docker", "exec", container,
        "cardano-cli", "query", "utxo",
        "--address", REGISTRY_ADDR,
        "--testnet-magic", NETWORK_MAGIC,
        "--socket-path", "/cardano/node.socket",
        "--output-json",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    return json.loads(result.stdout)


def decode_registry(datum):
    if not isinstance(datum, dict):
        raise ValueError("INVALID_REGISTRY_DATUM")

    if datum.get("constructor") != 0:
        raise ValueError("INVALID_REGISTRY_CONSTRUCTOR")

    fields = datum.get("fields")

    if not isinstance(fields, list) or len(fields) != 4:
        raise ValueError("INVALID_REGISTRY_FIELDS")

    node = bytes.fromhex(fields[0]["bytes"]).decode()
    ip = bytes.fromhex(fields[1]["bytes"]).decode()

    authorization = fields[2]

    if authorization not in (
        {"constructor": 0, "fields": []},
        {"constructor": 1, "fields": []},
    ):
        raise ValueError("INVALID_AUTHORIZATION_DATUM")

    revision = fields[3]["int"]

    if type(revision) is not int or revision < 0:
        raise ValueError("INVALID_REGISTRY_REVISION")

    return {
        "node": node,
        "ip": ip,
        "authorized": authorization["constructor"] == 1,
        "revision": revision,
    }


def validate_registry(utxos):
    matches = []

    for reference, output in utxos.items():
        quantity = (
            output.get("value", {})
            .get(POLICY_ID, {})
            .get(TOKEN_HEX, 0)
        )

        if quantity != 0:
            matches.append((reference, output, quantity))

    if len(matches) != 1:
        raise ValueError("REGISTRY_NFT_NOT_UNIQUE")

    reference, output, quantity = matches[0]

    if quantity != 1:
        raise ValueError("INVALID_NFT_QUANTITY")

    if output.get("address") != REGISTRY_ADDR:
        raise ValueError("INVALID_REGISTRY_ADDRESS")

    datum = output.get("inlineDatum")

    if datum is None:
        raise ValueError("MISSING_INLINE_DATUM")

    return {
        "reference": reference,
        "state": decode_registry(datum),
    }


def verify_live_registry():
    results = {}

    for name, container in NODES.items():
        results[name] = validate_registry(
            query_registry(container)
        )

    baseline = results["AS180"]

    if not all(
        result == baseline for result in results.values()
    ):
        raise ValueError("REGISTRY_CONSENSUS_MISMATCH")

    return baseline, list(results)


def verify_local_did():
    identity_path = (
        ROOT / "identity-data/public/AS184.json"
    )

    certificate_path = (
        ROOT / "identity-data/enrollments/AS184-enrollment.json"
    )

    identity = json.loads(identity_path.read_text())
    certificate = json.loads(certificate_path.read_text())

    if identity.get("node") != EXPECTED_NODE:
        raise ValueError("IDENTITY_NODE_MISMATCH")

    if identity.get("algorithm") != "Ed25519":
        raise ValueError("INVALID_IDENTITY_ALGORITHM")

    did = identity["did"]

    enrollment_valid = verify_certificate(
        certificate,
        expected_node=EXPECTED_NODE,
        expected_ip=EXPECTED_IP,
        expected_did=did,
    )

    key = load_private_key(EXPECTED_NODE)

    if did_from_public_key(public_bytes(key)) != did:
        raise ValueError("PRIVATE_KEY_DID_MISMATCH")

    if public_bytes(key).hex() != identity["public_key_hex"]:
        raise ValueError("PUBLIC_KEY_RECORD_MISMATCH")

    gateway = AdmissionGateway({
        EXPECTED_NODE: did
    })

    nonce = gateway.issue_challenge(
        EXPECTED_NODE, did
    )

    signature = key.sign(
        signed_message(
            EXPECTED_NODE,
            did,
            GATEWAY,
            nonce,
        )
    )

    authenticated, reason = gateway.verify(
        EXPECTED_NODE,
        did,
        GATEWAY,
        nonce,
        signature,
    )

    if not authenticated:
        raise ValueError(
            "DID_AUTHENTICATION_FAILED: " + reason
        )

    return authenticated, enrollment_valid


def main():
    authenticated, enrollment_valid = verify_local_did()

    registry, verified_nodes = verify_live_registry()

    state = registry["state"]

    allowed, reason = authorize_relay(
        authenticated=authenticated,
        enrollment_valid=enrollment_valid,
        node=EXPECTED_NODE,
        ip=EXPECTED_IP,
        registry=state,
    )

    decision = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "experiment": "B16-N13-B",
        "mode": "LOCAL_PROOF_OF_CONCEPT",
        "did_authentication": authenticated,
        "enrollment_valid": enrollment_valid,
        "registry_nft_valid": True,
        "registry_consensus": True,
        "verified_nodes": verified_nodes,
        "registry_utxo": registry["reference"],
        "registry_state": state,
        "decision": "ALLOW" if allowed else "DENY",
        "reason": reason,
        "firewall_modified": False,
    }

    print(json.dumps(decision, indent=2))

    # N13-B is specifically the unauthorized baseline.
    # Never treat an unexpected ALLOW as a successful test.
    if allowed:
        raise ValueError(
            "N13_B_UNEXPECTED_ALLOW: "
            "Expected initial unauthorized registry"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "B16 INTEGRATED ADMISSION FAILED:",
            str(exc),
            file=sys.stderr,
        )
        sys.exit(1)
