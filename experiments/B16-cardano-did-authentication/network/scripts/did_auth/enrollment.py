#!/usr/bin/env python3
"""B16 administrator-signed DID enrollment certificates."""

import argparse
import base64
import getpass
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from prototype import public_key_from_did

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = Path(os.environ.get("CARDANO_EXPERIMENT_RUNTIME", ROOT / ".runtime")).expanduser().resolve()

ADMIN_KEY = (
    RUNTIME_ROOT / "secure/B16/administrator/administrator.pem"
)

TRUSTED_KEY = (
    ROOT / "identity-data/trust/administrator-public.pem"
)

PUBLIC_DIR = ROOT / "identity-data/public"
ENROLLMENT_DIR = ROOT / "identity-data/enrollments"

SCHEMA = "B16-DID-ENROLLMENT-v1"
NETWORK = "B16-cardano-5556"


def canonical(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def utc_now():
    return datetime.now(timezone.utc)


def parse_time(value):
    result = datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%SZ"
    )
    return result.replace(tzinfo=timezone.utc)


def issue():
    identity_path = PUBLIC_DIR / "AS184.json"

    identity = json.loads(identity_path.read_text())

    if identity["node"] != "AS184":
        raise ValueError("Incorrect node identity")

    if identity["algorithm"] != "Ed25519":
        raise ValueError("Unsupported identity algorithm")

    did = identity["did"]

    # Confirm that the DID represents the stored public key.
    verifier = public_key_from_did(did)

    stored_public = bytes.fromhex(
        identity["public_key_hex"]
    )

    derived_public = verifier.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    if derived_public != stored_public:
        raise ValueError("DID/public-key mismatch")

    password = getpass.getpass(
        "Administrator signing password: "
    )

    private_key = serialization.load_pem_private_key(
        ADMIN_KEY.read_bytes(),
        password=password.encode("utf-8"),
        backend=default_backend(),
    )

    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Incorrect administrator key type")

    # Confirm that the unlocked private key matches
    # the separately provisioned trusted public key.
    trusted_key = serialization.load_pem_public_key(
        TRUSTED_KEY.read_bytes(),
        backend=default_backend(),
    )

    if not isinstance(trusted_key, Ed25519PublicKey):
        raise ValueError("Incorrect trusted key type")

    trusted_bytes = trusted_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    issuer_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    if trusted_bytes != issuer_bytes:
        raise ValueError("Administrator key mismatch")

    now = utc_now()

    payload = {
        "schema": SCHEMA,
        "network": NETWORK,
        "issuer": "B16-ADMIN",
        "node": "AS184",
        "ip": "10.184.0.71",
        "did": did,
        "role": "candidate-relay",
        "serial": secrets.token_hex(16),
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (
            now + timedelta(days=30)
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    signature = private_key.sign(canonical(payload))

    certificate = {
        "payload": payload,
        "signature_algorithm": "Ed25519",
        "signature_base64": base64.b64encode(
            signature
        ).decode("ascii"),
    }

    ENROLLMENT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = ENROLLMENT_DIR / "AS184-enrollment.json"

    # Never silently overwrite an issued certificate.
    fd = os.open(
        str(target),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o644,
    )

    with os.fdopen(fd, "w") as file:
        json.dump(certificate, file, indent=2)
        file.write("\n")

    print("ENROLLMENT ISSUED")
    print("Node:", payload["node"])
    print("DID:", did)
    print("Serial:", payload["serial"])
    print("Expires:", payload["expires_at"])
    print("Certificate:", target)


def verify_certificate(
    certificate,
    expected_node,
    expected_ip,
    expected_did,
    now=None,
):
    if set(certificate) != {
        "payload",
        "signature_algorithm",
        "signature_base64",
    }:
        raise ValueError("Invalid certificate envelope")

    payload = certificate["payload"]

    if not isinstance(payload, dict):
        raise ValueError("Invalid enrollment payload")

    required = {
        "schema", "network", "issuer", "node",
        "ip", "did", "role", "serial",
        "issued_at", "expires_at",
    }

    if set(payload) != required:
        raise ValueError("Unexpected enrollment fields")

    if certificate["signature_algorithm"] != "Ed25519":
        raise ValueError("Unsupported signature algorithm")

    if payload["schema"] != SCHEMA:
        raise ValueError("Invalid enrollment schema")

    if payload["network"] != NETWORK:
        raise ValueError("Incorrect network")

    if payload["issuer"] != "B16-ADMIN":
        raise ValueError("Unknown issuer")

    if payload["role"] != "candidate-relay":
        raise ValueError("Incorrect enrollment role")

    if (
        payload["node"] != expected_node
        or payload["ip"] != expected_ip
        or payload["did"] != expected_did
    ):
        raise ValueError("Enrollment identity mismatch")

    if not isinstance(payload["serial"], str):
        raise ValueError("Invalid certificate serial")

    if len(payload["serial"]) != 32:
        raise ValueError("Invalid certificate serial length")

    int(payload["serial"], 16)

    # Validate the DID encoding and public key type.
    public_key_from_did(payload["did"])

    issued = parse_time(payload["issued_at"])
    expires = parse_time(payload["expires_at"])

    current = now if now is not None else utc_now()

    if current < issued:
        raise ValueError("Certificate not yet valid")

    if current >= expires:
        raise ValueError("Certificate expired")

    if expires <= issued:
        raise ValueError("Invalid certificate validity period")

    if expires - issued > timedelta(days=30):
        raise ValueError("Excessive certificate validity")

    trusted_key = serialization.load_pem_public_key(
        TRUSTED_KEY.read_bytes(),
        backend=default_backend(),
    )

    if not isinstance(trusted_key, Ed25519PublicKey):
        raise ValueError("Incorrect trusted key type")

    try:
        signature = base64.b64decode(
            certificate["signature_base64"],
            validate=True,
        )

        trusted_key.verify(
            signature,
            canonical(payload),
        )

    except (InvalidSignature, ValueError, TypeError):
        raise ValueError("Invalid administrator signature")

    return True


def verify_file():
    path = ENROLLMENT_DIR / "AS184-enrollment.json"

    certificate = json.loads(path.read_text())

    identity = json.loads(
        (PUBLIC_DIR / "AS184.json").read_text()
    )

    verify_certificate(
        certificate,
        expected_node="AS184",
        expected_ip="10.184.0.71",
        expected_did=identity["did"],
    )

    print("ENROLLMENT VERIFICATION: PASS")
    print("Administrator signature: VALID")
    print("Approved node: AS184")
    print("Approved DID:", identity["did"])


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=["issue", "verify"],
    )

    args = parser.parse_args()

    if args.action == "issue":
        issue()
    else:
        verify_file()


if __name__ == "__main__":
    main()
