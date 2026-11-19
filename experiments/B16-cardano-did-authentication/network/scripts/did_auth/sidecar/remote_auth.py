#!/usr/bin/env python3
"""B16 N13-C: one-shot remote DID authentication experiment.

This program does not authorize Cardano membership or modify firewalls.
"""

import argparse
import json
import socket
import sys
from pathlib import Path

DID_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DID_DIR))

from prototype import (
    AdmissionGateway,
    GATEWAY,
    signed_message,
    did_from_public_key,
    public_bytes,
)
from identity import load_private_key
from enrollment import verify_certificate

ROOT = DID_DIR.parents[1]

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


def load_public_identity():
    path = ROOT / "identity-data/public/AS184.json"
    return json.loads(path.read_text())


def gateway_mode():
    identity = load_public_identity()

    certificate_path = (
        ROOT / "identity-data/enrollments/AS184-enrollment.json"
    )

    certificate = json.loads(certificate_path.read_text())
    did = identity["did"]

    verify_certificate(
        certificate,
        expected_node=NODE,
        expected_ip=CANDIDATE_IP,
        expected_did=did,
    )

    verifier = AdmissionGateway({NODE: did})

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((GATEWAY_IP, PORT))
    server.listen(1)
    server.settimeout(60)

    print("B16_DID_GATEWAY_READY", flush=True)

    try:
        connection, peer = server.accept()

        with connection:
            connection.settimeout(10)

            if peer[0] != CANDIDATE_IP:
                raise ValueError("UNEXPECTED_SOURCE_IP")

            stream = connection.makefile("rwb")

            with stream:
                request = receive_json(stream)

                if request != {
                    "node": NODE,
                    "did": did,
                }:
                    raise ValueError("IDENTITY_REQUEST_MISMATCH")

                nonce = verifier.issue_challenge(NODE, did)

                send_json(stream, {
                    "type": "CHALLENGE",
                    "nonce": nonce,
                    "gateway": GATEWAY,
                })

                response = receive_json(stream)

                if response.get("type") != "RESPONSE":
                    raise ValueError("INVALID_RESPONSE_TYPE")

                signature_hex = response.get("signature")

                if not isinstance(signature_hex, str):
                    raise ValueError("INVALID_SIGNATURE_FORMAT")

                signature = bytes.fromhex(signature_hex)

                authenticated, reason = verifier.verify(
                    NODE, did, GATEWAY, nonce, signature
                )

                send_json(stream, {
                    "authenticated": authenticated,
                    "reason": reason,
                })

                result = {
                    "experiment": "B16-N13-C",
                    "mode": "REMOTE_DID_PROOF_OF_CONCEPT",
                    "peer_ip": peer[0],
                    "node": NODE,
                    "did_authenticated": authenticated,
                    "enrollment_valid": True,
                    "authentication_reason": reason,
                    "cardano_authorization_checked": False,
                    "network_admission": "NOT_GRANTED",
                    "firewall_modified": False,
                }

                print(json.dumps(result, indent=2), flush=True)

                if not authenticated:
                    raise ValueError("DID_AUTHENTICATION_FAILED")

    finally:
        server.close()


def candidate_mode(require_admission=False):
    identity = load_public_identity()

    key = load_private_key(NODE)

    if did_from_public_key(public_bytes(key)) != identity["did"]:
        raise ValueError("CANDIDATE_DID_KEY_MISMATCH")

    with socket.create_connection(
        (GATEWAY_IP, PORT), timeout=10, source_address=(CANDIDATE_IP, 0)
    ) as connection:

        connection.settimeout(10)

        stream = connection.makefile("rwb")

        with stream:
            send_json(stream, {
                "node": NODE,
                "did": identity["did"],
            })

            challenge = receive_json(stream)

            if (
                challenge.get("type") != "CHALLENGE"
                or challenge.get("gateway") != GATEWAY
                or not isinstance(challenge.get("nonce"), str)
            ):
                raise ValueError("INVALID_CHALLENGE")

            nonce = challenge["nonce"]

            signature = key.sign(
                signed_message(
                    NODE,
                    identity["did"],
                    GATEWAY,
                    nonce,
                )
            )

            send_json(stream, {
                "type": "RESPONSE",
                "signature": signature.hex(),
            })

            result = receive_json(stream)

            print(json.dumps(result, indent=2), flush=True)

            if result.get("authenticated") is not True:
                raise ValueError("REMOTE_AUTHENTICATION_REJECTED")
            if require_admission and (
                result.get("decision") != "ALLOW" or result.get("network_admission") != "GRANTED"
            ):
                raise ValueError("REMOTE_ADMISSION_NOT_GRANTED")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "role",
        choices=["gateway", "candidate"],
    )

    parser.add_argument("--require-admission", action="store_true")
    args = parser.parse_args()

    if args.role == "gateway":
        gateway_mode()
    else:
        candidate_mode(args.require_admission)


if __name__ == "__main__":
    main()
