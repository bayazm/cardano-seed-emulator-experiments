#!/usr/bin/env python3
"""B16 N13-D: remote DID authentication + live Cardano decision.

One-shot academic experiment. No firewall modification.
"""

import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts/did_auth"))
sys.path.insert(0, str(ROOT / "scripts"))

from prototype import AdmissionGateway, GATEWAY, public_key_from_did
from enrollment import verify_certificate
from registry_policy import authorize_relay
from b16_integrated_admission import verify_live_registry

NODE = "AS184"
CANDIDATE_IP = "10.184.0.71"
GATEWAY_IP = "10.183.0.71"
PORT = 4040


def send_json(stream, message):
    stream.write(
        (json.dumps(message, separators=(",", ":")) + "\n").encode()
    )
    stream.flush()


def receive_json(stream):
    line = stream.readline(16385)
    if not line or len(line) > 16384 or not line.endswith(b"\n"):
        raise ValueError("INVALID_PROTOCOL_MESSAGE")
    result = json.loads(line)
    if not isinstance(result, dict):
        raise ValueError("INVALID_PROTOCOL_OBJECT")
    return result


def main():
    identity = json.loads(
        (ROOT / "identity-data/public/AS184.json").read_text()
    )
    certificate = json.loads(
        (
            ROOT
            / "identity-data/enrollments/AS184-enrollment.json"
        ).read_text()
    )

    if identity.get("node") != NODE:
        raise ValueError("IDENTITY_NODE_MISMATCH")

    if identity.get("algorithm") != "Ed25519":
        raise ValueError("INVALID_IDENTITY_ALGORITHM")

    did = identity["did"]

    # Confirm the public identity record is internally consistent.
    from cryptography.hazmat.primitives import serialization

    derived_public = public_key_from_did(did).public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    if derived_public.hex() != identity.get("public_key_hex"):
        raise ValueError("DID_PUBLIC_KEY_MISMATCH")

    enrollment_valid = verify_certificate(
        certificate,
        expected_node=NODE,
        expected_ip=CANDIDATE_IP,
        expected_did=did,
    )

    verifier = AdmissionGateway({NODE: did})

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((GATEWAY_IP, PORT))
        server.listen(1)
        server.settimeout(120)

        print("B16_REMOTE_ADMISSION_GATEWAY_READY", flush=True)

        connection, peer = server.accept()

        with connection:
            connection.settimeout(15)
            with connection.makefile("rwb") as stream:

                if peer[0] != CANDIDATE_IP:
                    raise ValueError("UNEXPECTED_SOURCE_IP")

                request = receive_json(stream)

                if request != {"node": NODE, "did": did}:
                    raise ValueError("IDENTITY_REQUEST_MISMATCH")

                nonce = verifier.issue_challenge(NODE, did)

                send_json(stream, {
                    "type": "CHALLENGE",
                    "nonce": nonce,
                    "gateway": GATEWAY,
                })

                response = receive_json(stream)

                if (
                    response.get("type") != "RESPONSE"
                    or not isinstance(response.get("signature"), str)
                ):
                    raise ValueError("INVALID_AUTHENTICATION_RESPONSE")

                signature = bytes.fromhex(response["signature"])

                authenticated, auth_reason = verifier.verify(
                    NODE, did, GATEWAY, nonce, signature
                )

                # Fail closed: no registry query failure grants admission.
                registry_valid = False
                consensus_valid = False
                registry = None
                state = None
                verified_nodes = []
                decision = "DENY"
                reason = auth_reason

                if authenticated and enrollment_valid:
                    try:
                        registry, verified_nodes = verify_live_registry()
                        state = registry["state"]
                        registry_valid = True
                        consensus_valid = True

                        allowed, reason = authorize_relay(
                            authenticated=authenticated,
                            enrollment_valid=enrollment_valid,
                            node=NODE,
                            ip=CANDIDATE_IP,
                            registry=state,
                        )

                        decision = "ALLOW" if allowed else "DENY"

                    except Exception as exc:
                        decision = "DENY"
                        reason = "REGISTRY_VERIFICATION_FAILED"
                        print(
                            "Registry verification error:",
                            type(exc).__name__,
                            str(exc),
                            file=sys.stderr,
                            flush=True,
                        )

                # This experiment never grants firewall access.
                result = {
                    "timestamp_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "experiment": "B16-N13-D",
                    "mode": "REMOTE_LIVE_CARDANO_DRY_RUN",
                    "peer_ip": peer[0],
                    "node": NODE,
                    "did_authenticated": authenticated,
                    "enrollment_valid": enrollment_valid,
                    "registry_nft_valid": registry_valid,
                    "registry_consensus": consensus_valid,
                    "verified_nodes": verified_nodes,
                    "registry_utxo": (
                        registry["reference"] if registry else None
                    ),
                    "registry_state": state,
                    "decision": decision,
                    "reason": reason,
                    "network_admission": "NOT_GRANTED",
                    "firewall_modified": False,
                }

                send_json(stream, {
                    "authenticated": authenticated,
                    "reason": auth_reason,
                    "decision": decision,
                    "authorization_reason": reason,
                    "network_admission": "NOT_GRANTED",
                })

                print(json.dumps(result, indent=2), flush=True)

                # An ALLOW would be unexpected during the
                # initial unauthorized N13-D experiment.
                if decision != "DENY":
                    raise RuntimeError("UNEXPECTED_ALLOW_IN_N13_D")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "B16_REMOTE_ADMISSION_ERROR:",
            type(exc).__name__,
            str(exc),
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
