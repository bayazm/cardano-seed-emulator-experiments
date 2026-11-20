#!/usr/bin/env python3
"""Generate the byte-exact B12 measurement demo and its Plutus data fixtures."""

import argparse
import hashlib
import json
from pathlib import Path

SENSOR_ID = "AGRI-002"
TIMESTAMP = "2026-11-20T10:00:00Z"
TEMPERATURE = "23.6"
HUMIDITY = "61"
EXPECTED_SHA256 = "b76cef7674424ef76659031a5cf22f1d9b38316c2fe1e71cdbd12c75fc30ac26"


def measurement(temperature=TEMPERATURE, humidity=HUMIDITY):
    return "|".join((SENSOR_ID, TIMESTAMP, temperature, humidity)).encode("utf-8")


def constructor(*fields):
    return {"constructor": 0, "fields": [{"bytes": field.hex()} for field in fields]}


def fixtures():
    original = measurement()
    sensor_id = SENSOR_ID.encode("utf-8")
    digest = hashlib.sha256(original).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Canonical measurement differs from the known SHA-256 commitment")
    altered = {
        "temperature": measurement(temperature="23.7"),
        "humidity": measurement(humidity="62"),
        "serialization": measurement(temperature="23.60"),
    }
    if any(hashlib.sha256(payload).hexdigest() == digest for payload in altered.values()):
        raise ValueError("A negative measurement fixture matched the commitment")
    return {
        "measurement.txt": original,
        "datum.json": constructor(sensor_id, bytes.fromhex(digest)),
        "redeemer.json": constructor(sensor_id, original),
        "wrong-id.json": constructor(b"AGRI-001", original),
        "malformed.json": {"int": 0},
        **{f"wrong-{label}.json": constructor(sensor_id, payload) for label, payload in altered.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New fixture directory, or existing directory with --verify")
    parser.add_argument("--verify", action="store_true", help="Compare every fixture against its canonical bytes")
    args = parser.parse_args()
    expected = fixtures()
    if not args.verify:
        args.output.mkdir(mode=0o700)
    for name, value in expected.items():
        encoded = value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode()
        target = args.output / name
        if args.verify:
            if target.read_bytes() != encoded:
                raise ValueError(f"Fixture mismatch: {name}")
        else:
            target.write_bytes(encoded)
    print(f"{EXPECTED_SHA256}  measurement.txt")


if __name__ == "__main__":
    main()
