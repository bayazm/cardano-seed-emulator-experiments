"""Read Conway ChainDB records and hash the original CBOR byte slices."""
import hashlib
import io
import json

import cbor2


def digest(raw):
    return hashlib.blake2b(raw, digest_size=32).hexdigest()


def head(stream, major):
    tag = stream.read(1)
    if not tag or tag[0] >> 5 != major:
        raise ValueError("Unexpected CBOR container")
    size = tag[0] & 31
    if size < 24:
        return size
    if size == 31:
        return None
    if size > 27:
        raise ValueError("Invalid CBOR length")
    width = 1 << (size - 24)
    length = stream.read(width)
    if len(length) != width:
        raise ValueError("Truncated CBOR length")
    return int.from_bytes(length, "big")


def item(raw, stream, decoder):
    start = stream.tell()
    value = decoder.decode()
    return value, raw[start:stream.tell()]


def entries(stream, size):
    count = 0
    while size is None or count < size:
        if size is None and stream.getbuffer()[stream.tell()] == 255:
            stream.read(1)
            return
        yield count
        count += 1


def parts(raw):
    stream = io.BytesIO(raw)
    decoder = cbor2.CBORDecoder(stream)
    if head(stream, 4) != 2 or decoder.decode() != 7 or head(stream, 4) != 5:
        raise ValueError("Expected a Conway block record")
    header, header_bytes = item(raw, stream, decoder)
    bodies = [item(raw, stream, decoder) for _ in entries(stream, head(stream, 4))]
    witnesses = decoder.decode()
    auxiliary = {}
    for _ in entries(stream, head(stream, 5)):
        index = decoder.decode()
        auxiliary[index] = item(raw, stream, decoder)
    invalid = decoder.decode()
    if len(bodies) != len(witnesses) or stream.tell() != len(raw):
        raise ValueError("Invalid Conway record framing")
    return header, header_bytes, bodies, auxiliary, invalid


def envelope_body(path):
    raw = bytes.fromhex(json.loads(path.read_text())["cborHex"])
    stream = io.BytesIO(raw)
    if head(stream, 4) != 4:
        raise ValueError("Expected a signed transaction envelope")
    return item(raw, stream, cbor2.CBORDecoder(stream))[1]


def canonical_transaction(database, tip, txid, lower=0):
    """Return the exact block and transaction slices on the sampled tip's chain."""
    files = sorted((database / "immutable").glob("*.chunk"))
    files += sorted((database / "volatile").glob("blocks-*.dat"))
    records = {}
    for path in files:
        raw = path.read_bytes()
        stream = io.BytesIO(raw)
        decoder = cbor2.CBORDecoder(stream)
        while stream.tell() < len(raw):
            offset = stream.tell()
            try:
                record, encoded = item(raw, stream, decoder)
            except cbor2.CBORDecodeEOF:
                if path.parent.name != "volatile":
                    raise
                break
            if record[0] != 7 or not lower <= record[1][0][0][0] <= tip["block"]:
                continue
            header, header_bytes, bodies, aux, invalid = parts(encoded)
            height, slot, previous = header[0][:3]
            block_hash = digest(header_bytes)
            proof = None
            for index, (body, body_bytes) in enumerate(bodies):
                if index not in invalid and digest(body_bytes) == txid:
                    proof = (body, body_bytes, aux.get(index), encoded, {
                        "block": height, "slot": slot, "block_hash": block_hash,
                        "transaction_index": index, "txid": txid,
                        "block_record_sha256": hashlib.sha256(encoded).hexdigest(),
                    })
            records[block_hash] = (height, slot, previous.hex() if previous else None, proof)
    cursor = tip["hash"]
    for height in range(tip["block"], lower - 1, -1):
        number, slot, cursor, proof = records[cursor]
        if number != height or (height == tip["block"] and slot != tip["slot"]):
            raise ValueError("ChainDB ancestry does not match sampled tip")
        if proof:
            return proof
    raise ValueError(f"{txid} was not included on sampled chain")
