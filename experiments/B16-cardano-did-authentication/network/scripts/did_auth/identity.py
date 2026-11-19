#!/usr/bin/env python3

"""B16 persistent Ed25519 DID identity management."""

import json
import os
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from prototype import did_from_public_key, public_bytes


ROOT = Path(__file__).resolve().parents[2]

IDENTITY_ROOT = ROOT / "identity-data"

PRIVATE_DIR = IDENTITY_ROOT / "keys"

PUBLIC_DIR = IDENTITY_ROOT / "public"


def create_identity(node):

    PRIVATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    PUBLIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    private_path = PRIVATE_DIR / f"{node}.pem"

    public_path = PUBLIC_DIR / f"{node}.json"

    if private_path.exists() or public_path.exists():
        raise FileExistsError(
            f"Identity already exists for {node}"
        )

    private_key = Ed25519PrivateKey.generate()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Create a new file exclusively, with owner-only permissions.
    fd = os.open(
        str(private_path),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(fd, "wb") as file:
        file.write(private_pem)

    public_key = public_bytes(private_key)

    did = did_from_public_key(public_key)

    public_record = {
        "node": node,
        "did": did,
        "algorithm": "Ed25519",
        "public_key_hex": public_key.hex(),
    }

    public_path.write_text(
        json.dumps(public_record, indent=2) + "\n"
    )

    return public_record


def load_private_key(node):

    private_path = PRIVATE_DIR / f"{node}.pem"

    data = private_path.read_bytes()

    return serialization.load_pem_private_key(
        data,
        password=None,
        backend=default_backend(),
    )


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python3 identity.py NODE"
        )

    record = create_identity(sys.argv[1])

    print(json.dumps(record, indent=2))
