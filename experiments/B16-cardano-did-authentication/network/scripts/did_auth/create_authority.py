#!/usr/bin/env python3

"""B16: generate an encrypted administrator signing key."""

import getpass
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = Path(os.environ.get("CARDANO_EXPERIMENT_RUNTIME", ROOT / ".runtime")).expanduser().resolve()

PRIVATE_DIR = (
    RUNTIME_ROOT
    / "secure"
    / "B16"
    / "administrator"
)

PRIVATE_FILE = PRIVATE_DIR / "administrator.pem"

PUBLIC_FILE = (
    ROOT
    / "identity-data"
    / "trust"
    / "administrator-public.pem"
)


def main():

    PRIVATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    PUBLIC_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if PRIVATE_FILE.exists() or PUBLIC_FILE.exists():
        raise SystemExit(
            "Administrator identity already exists. "
            "Refusing to overwrite it."
        )

    password = getpass.getpass(
        "Administrator key password: "
    )

    confirmation = getpass.getpass(
        "Confirm password: "
    )

    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    if len(password) < 12:
        raise SystemExit(
            "Use a password of at least 12 characters."
        )

    private_key = Ed25519PrivateKey.generate()

    encrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=(
            serialization.BestAvailableEncryption(
                password.encode("utf-8")
            )
        ),
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    fd = os.open(
        str(PRIVATE_FILE),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(fd, "wb") as file:
        file.write(encrypted_pem)

    PUBLIC_FILE.write_bytes(public_pem)

    print()
    print("Administrator key generation: SUCCESS")
    print("Encrypted private key:", PRIVATE_FILE)
    print("Trusted public key:", PUBLIC_FILE)
    print("Private key permissions: 600")


if __name__ == "__main__":
    main()
