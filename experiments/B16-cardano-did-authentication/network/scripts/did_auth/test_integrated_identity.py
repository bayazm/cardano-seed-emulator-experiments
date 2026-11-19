#!/usr/bin/env python3
"""B16: DID authentication + administrator enrollment integration."""

import copy
import json
from datetime import timedelta

from identity import load_private_key
from prototype import (
    AdmissionGateway,
    GATEWAY,
    public_bytes,
    signed_message,
    did_from_public_key,
)
from enrollment import verify_certificate, parse_time


def load_record(node):
    with open("identity-data/public/" + node + ".json") as f:
        return json.load(f)


def authenticate(node, key, did, certificate, gateway):
    """Check enrollment first, then verify a signed challenge."""

    try:
        verify_certificate(
            certificate,
            expected_node=node,
            expected_ip="10.184.0.71",
            expected_did=did,
        )
    except ValueError as exc:
        return False, "ENROLLMENT_REJECTED: " + str(exc)

    nonce = gateway.issue_challenge(node, did)

    signature = key.sign(
        signed_message(node, did, GATEWAY, nonce)
    )

    return gateway.verify(
        node, did, GATEWAY, nonce, signature
    )


def main():
    as184 = load_record("AS184")
    as185 = load_record("AS185")

    key184 = load_private_key("AS184")
    key185 = load_private_key("AS185")

    # Confirm private keys correspond to published DIDs.
    assert did_from_public_key(public_bytes(key184)) == as184["did"]
    assert did_from_public_key(public_bytes(key185)) == as185["did"]

    with open(
        "identity-data/enrollments/AS184-enrollment.json"
    ) as f:
        certificate = json.load(f)

    gateway = AdmissionGateway({
        "AS184": as184["did"]
    })

    print("===== B16 INTEGRATED IDENTITY TESTS =====")

    # E9: Approved certificate + correct DID private key.
    e9 = authenticate(
        "AS184",
        key184,
        as184["did"],
        certificate,
        gateway,
    )

    assert e9[0] is True
    print("E9 legitimate enrolled relay: PASS", e9)

    # E10: Attacker presents AS184 certificate but uses own DID.
    e10 = authenticate(
        "AS184",
        key185,
        as185["did"],
        certificate,
        gateway,
    )

    assert e10[0] is False
    print("E10 attacker DID substitution: PASS", e10)

    # E11: Attacker claims AS184 DID with its own private key.
    nonce = gateway.issue_challenge("AS184", as184["did"])

    attacker_signature = key185.sign(
        signed_message("AS184", as184["did"], GATEWAY, nonce)
    )

    e11 = gateway.verify(
        "AS184",
        as184["did"],
        GATEWAY,
        nonce,
        attacker_signature,
    )

    assert e11[0] is False
    print("E11 private-key impersonation: PASS", e11)

    # E12: Modify enrollment IP but keep original signature.
    modified = copy.deepcopy(certificate)
    modified["payload"]["ip"] = "10.185.0.71"

    try:
        verify_certificate(
            modified,
            expected_node="AS184",
            expected_ip="10.185.0.71",
            expected_did=as184["did"],
        )
    except ValueError as exc:
        assert str(exc) == "Invalid administrator signature"
        print("E12 tampered administrator signature: PASS")
    else:
        raise AssertionError("Tampered certificate was accepted")

    # E13: Verify that an expired certificate is rejected.
    expiry = parse_time(certificate["payload"]["expires_at"])

    try:
        verify_certificate(
            certificate,
            expected_node="AS184",
            expected_ip="10.184.0.71",
            expected_did=as184["did"],
            now=expiry + timedelta(seconds=1),
        )
    except ValueError as exc:
        assert str(exc) == "Certificate expired"
        print("E13 expired certificate: PASS")
    else:
        raise AssertionError("Expired certificate was accepted")

    print()
    print("RESULT: 5/5 integrated identity tests passed")
    print("NOTE: Cardano authorization has NOT been checked.")


if __name__ == "__main__":
    main()
