#!/usr/bin/env python3
"""Corrected entry point for the direct NFT-ID WS-1 audit.

The PDB v2 contract returns a dynamic ABI string containing base64(gzip(BCIF)).
The original generic decoder considered the raw printable base64 string a
possible BinaryCIF before trying its decoded form. This wrapper makes payload
selection structural: base64 is decoded first when present, compression layers
are removed, and a candidate is accepted only if it is exactly one MessagePack
map containing BinaryCIF ``dataBlocks``.
"""
from __future__ import annotations

import base64
import gzip
import importlib.util
import pathlib
import re
import sys
import zlib
from typing import Any

import msgpack

DIRECT_PATH = pathlib.Path(__file__).with_name("capture_molnft_direct_randomized_sample.py")
SPEC = importlib.util.spec_from_file_location("genesisl1_ws1_direct", DIRECT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {DIRECT_PATH}")
direct = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = direct
SPEC.loader.exec_module(direct)

BASE64_RE = re.compile(br"^[A-Za-z0-9+/]*={0,2}$")


def unwrap(value: bytes) -> bytes:
    current = value.strip()
    for _ in range(4):
        if current.startswith(b"\x1f\x8b"):
            current = gzip.decompress(current)
            continue
        if current.startswith((b"x\x01", b"x\x5e", b"x\x9c", b"x\xda")):
            current = zlib.decompress(current)
            continue
        break
    return current


def is_binarycif(value: bytes) -> bool:
    try:
        parsed: Any = msgpack.unpackb(value, raw=False, strict_map_key=False)
    except Exception:  # noqa: BLE001
        return False
    return isinstance(parsed, dict) and isinstance(parsed.get("dataBlocks"), list) and bool(parsed["dataBlocks"])


def reconstruct_payload(result_hex: str) -> bytes:
    errors: list[str] = []
    for candidate in sorted(direct.base.dynamic_blobs(result_hex), key=len, reverse=True):
        stripped = b"".join(candidate.split())
        variants: list[tuple[str, bytes]] = []
        if len(stripped) % 4 == 0 and BASE64_RE.fullmatch(stripped):
            try:
                variants.append(("base64", base64.b64decode(stripped, validate=True)))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"base64: {exc}")
        variants.append(("raw", candidate))
        for label, value in variants:
            try:
                decoded = unwrap(value)
                if is_binarycif(decoded):
                    return decoded
                errors.append(f"{label}: decoded bytes were not one BinaryCIF MessagePack object")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{label}: {type(exc).__name__}: {exc}")
    raise direct.base.RecordFailure(
        "ABI_DECODE_FAIL",
        "could not identify a complete BinaryCIF payload: " + "; ".join(errors[-8:]),
    )


direct.base.reconstruct_payload = reconstruct_payload

if __name__ == "__main__":
    raise SystemExit(direct.main())
