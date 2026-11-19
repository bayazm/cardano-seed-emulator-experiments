#!/usr/bin/env python3
"""B16: relay admission policy using verified registry state."""


def authorize_relay(
    authenticated,
    enrollment_valid,
    node,
    ip,
    registry,
):
    """
    Evaluate relay admission.

    SECURITY CONTRACT:
    - authenticated must come from successful challenge verification.
    - enrollment_valid must come from certificate verification.
    - registry must come from a trusted Cardano registry reader.

    This function does not perform those verifications itself.
    """

    if authenticated is not True:
        return False, "DID_AUTHENTICATION_FAILED"

    if enrollment_valid is not True:
        return False, "ENROLLMENT_INVALID"

    if not isinstance(registry, dict):
        return False, "INVALID_REGISTRY"

    required = {
        "node",
        "ip",
        "authorized",
        "revision",
    }

    if set(registry) != required:
        return False, "INVALID_REGISTRY_STRUCTURE"

    if registry["node"] != node:
        return False, "REGISTRY_NODE_MISMATCH"

    if registry["ip"] != ip:
        return False, "REGISTRY_IP_MISMATCH"

    if type(registry["revision"]) is not int:
        return False, "INVALID_REGISTRY_REVISION"

    if registry["revision"] < 0:
        return False, "INVALID_REGISTRY_REVISION"

    if type(registry["authorized"]) is not bool:
        return False, "INVALID_AUTHORIZATION_STATE"

    if registry["authorized"] is not True:
        return False, "CARDANO_AUTHORIZATION_REVOKED"

    return True, "ADMISSION_POLICY_SATISFIED"
