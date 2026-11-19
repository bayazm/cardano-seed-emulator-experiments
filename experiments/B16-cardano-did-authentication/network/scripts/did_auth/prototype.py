#!/usr/bin/env python3
"""B16: standalone DID authentication prototype."""

import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
PREFIX = b"\xed\x01"
GATEWAY = "AS183"
CONTEXT = "SEED-B16-DID-AUTH-v1"


def base58_encode(data):
    number = int.from_bytes(data, "big")
    encoded = ""

    while number:
        number, remainder = divmod(number, 58)
        encoded = ALPHABET[remainder] + encoded

    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading_zeroes + encoded


def base58_decode(value):
    number = 0

    for character in value:
        if character not in ALPHABET:
            raise ValueError("Invalid Base58 character")
        number = number * 58 + ALPHABET.index(character)

    length = (number.bit_length() + 7) // 8
    raw = number.to_bytes(length, "big") if length else b""

    leading_zeroes = len(value) - len(value.lstrip("1"))
    return b"\x00" * leading_zeroes + raw


def public_bytes(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def did_from_public_key(key_bytes):
    if len(key_bytes) != 32:
        raise ValueError("Invalid Ed25519 public key length")

    return "did:key:z" + base58_encode(PREFIX + key_bytes)


def public_key_from_did(did):
    if not did.startswith("did:key:z"):
        raise ValueError("Unsupported DID format")

    encoded = did[len("did:key:z"):]
    raw = base58_decode(encoded)

    if len(raw) != 34 or not raw.startswith(PREFIX):
        raise ValueError("Unsupported DID key type")

    if base58_encode(raw) != encoded:
        raise ValueError("Noncanonical DID encoding")

    return Ed25519PublicKey.from_public_bytes(raw[2:])


def signed_message(node, did, gateway, nonce):
    # Length-prefix fields to prevent ambiguous concatenation.
    fields = [CONTEXT, node, did, gateway, nonce]

    message = b""

    for field in fields:
        value = field.encode("utf-8")
        message += len(value).to_bytes(4, "big") + value

    return message


class AdmissionGateway:
    def __init__(self, enrollment, ttl_seconds=30):
        # enrollment: {"AS184": "did:key:..."}
        self.enrollment = dict(enrollment)
        self.ttl_seconds = ttl_seconds
        self.pending = {}

    def issue_challenge(self, node, did):
        nonce = secrets.token_hex(32)

        self.pending[nonce] = {
            "node": node,
            "did": did,
            "gateway": GATEWAY,
            "expires": time.monotonic() + self.ttl_seconds,
        }

        return nonce

    def verify(self, node, did, gateway, nonce, signature):
        # Consume the challenge even if authentication fails.
        # A response cannot be retried or replayed.
        record = self.pending.pop(nonce, None)

        if record is None:
            return False, "UNKNOWN_OR_REPLAYED_CHALLENGE"

        if time.monotonic() > record["expires"]:
            return False, "EXPIRED_CHALLENGE"

        if (
            record["node"] != node
            or record["did"] != did
            or record["gateway"] != gateway
            or gateway != GATEWAY
        ):
            return False, "CHALLENGE_CONTEXT_MISMATCH"

        if self.enrollment.get(node) != did:
            return False, "DID_NOT_ENROLLED_FOR_NODE"

        try:
            verifier = public_key_from_did(did)
            verifier.verify(
                signature,
                signed_message(node, did, gateway, nonce),
            )
        except (InvalidSignature, ValueError, TypeError):
            return False, "INVALID_SIGNATURE_OR_DID"

        return True, "IDENTITY_AUTHENTICATED"


def demonstrate():
    as184_key = Ed25519PrivateKey.generate()
    as185_key = Ed25519PrivateKey.generate()

    as184_did = did_from_public_key(public_bytes(as184_key))
    as185_did = did_from_public_key(public_bytes(as185_key))

    gateway = AdmissionGateway({"AS184": as184_did})

    print("B16 DID AUTHENTICATION PROTOTYPE")
    print("AS184 DID:", as184_did)
    print("AS185 DID:", as185_did)

    # E1: Legitimate AS184
    nonce = gateway.issue_challenge("AS184", as184_did)
    signature = as184_key.sign(
        signed_message("AS184", as184_did, GATEWAY, nonce)
    )
    e1 = gateway.verify(
        "AS184", as184_did, GATEWAY, nonce, signature
    )
    print("E1 legitimate identity:", e1)

    # E2: Unknown DID claims AS184 identity
    nonce2 = gateway.issue_challenge("AS184", as185_did)
    signature2 = as185_key.sign(
        signed_message("AS184", as185_did, GATEWAY, nonce2)
    )
    e2 = gateway.verify(
        "AS184", as185_did, GATEWAY, nonce2, signature2
    )
    print("E2 unapproved DID:", e2)

    # E3: AS185 signs while claiming AS184's DID
    nonce3 = gateway.issue_challenge("AS184", as184_did)
    signature3 = as185_key.sign(
        signed_message("AS184", as184_did, GATEWAY, nonce3)
    )
    e3 = gateway.verify(
        "AS184", as184_did, GATEWAY, nonce3, signature3
    )
    print("E3 impersonation:", e3)

    # E4: Replay the successful E1 response
    e4 = gateway.verify(
        "AS184", as184_did, GATEWAY, nonce, signature
    )
    print("E4 replay:", e4)

    # E5: Signature created for a different gateway
    nonce5 = gateway.issue_challenge("AS184", as184_did)
    signature5 = as184_key.sign(
        signed_message("AS184", as184_did, "AS999", nonce5)
    )
    e5 = gateway.verify(
        "AS184", as184_did, GATEWAY, nonce5, signature5
    )
    print("E5 wrong-gateway signature:", e5)

    assert e1[0] is True
    assert all(result[0] is False for result in (e2, e3, e4, e5))

    print("\nRESULT: 5/5 authentication scenarios passed")


if __name__ == "__main__":
    demonstrate()
