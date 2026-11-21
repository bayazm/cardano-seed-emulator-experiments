#!/usr/bin/env python3
"""Check saved B12 transactions against sampled live tips and local DB block bytes."""

import argparse
import hashlib
import io
import json
from pathlib import Path

import cbor2

PEERS = (150, 151, 152, 153)


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.blake2b(cbor2.dumps(value), digest_size=32).hexdigest()


def block_index(database, tip_height):
    paths = sorted((database / "immutable").glob("*.chunk"))
    paths += sorted((database / "volatile").glob("blocks-*.dat"))
    blocks = {}
    for path in paths:
        snapshot = path.read_bytes()
        stream = io.BytesIO(snapshot)
        decoder = cbor2.CBORDecoder(stream)
        while stream.tell() < len(snapshot):
            offset = stream.tell()
            try:
                record = decoder.decode()
            except cbor2.CBORDecodeEOF:
                if path.parent.name != "volatile":
                    raise
                break
            era, block = record
            if era != 7:
                continue
            header, bodies, _, _, invalid = block
            height, slot, parent = header[0][:3]
            if height > tip_height:
                continue
            if cbor2.dumps(record) != snapshot[offset:stream.tell()]:
                raise ValueError(f"Block did not round-trip byte-for-byte in {path} at {offset}")
            header_hash = digest(header)
            valid_txs = {digest(body) for index, body in enumerate(bodies) if index not in invalid}
            blocks[header_hash] = (height, slot, parent.hex() if parent else None, valid_txs)
    return blocks


def verify(database, tip, expected):
    blocks = block_index(database, tip["block"])
    cursor = tip["hash"]
    verified = set()
    lower = min(anchor["height"] for anchor in expected.values())
    for expected_height in range(tip["block"], lower - 1, -1):
        if cursor not in blocks:
            raise ValueError(f"Missing block {cursor} at height {expected_height}; use ChainSync for this history")
        height, slot, parent, txids = blocks[cursor]
        if height != expected_height or (height == tip["block"] and slot != tip["slot"]):
            raise ValueError(f"Broken chain link at {cursor}")
        for txid in txids & expected.keys():
            if expected[txid]["block_hash"] != cursor or expected[txid]["height"] != height:
                raise ValueError(f"Changed historical anchor for {txid}")
            verified.add(txid)
        cursor = parent
    if verified != expected.keys():
        raise ValueError(f"Missing historical transactions: {sorted(expected.keys() - verified)}")
    return {"tip_block": tip["block"], "tip_slot": tip["slot"], "tip_hash": tip["hash"],
            "verified_transactions": len(verified)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-root", type=Path, required=True)
    parser.add_argument("--tips", type=Path, required=True, help="collector directory containing asNNN-tip.json")
    parser.add_argument("--anchors", type=Path, required=True)
    args = parser.parse_args()
    expected = read(args.anchors)["transactions"]
    if len(expected) != 33:
        parser.error("Expected the 33 preserved B12 transaction anchors.")
    result = {f"AS{peer}": verify(args.db_root / f"as{peer}", read(args.tips / f"as{peer}-tip.json"), expected)
              for peer in PEERS}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
