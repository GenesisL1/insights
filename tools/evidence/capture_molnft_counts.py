#!/usr/bin/env python3
"""Capture current MOLNFT collection counters at one GenesisL1 block.

This is a lightweight current-state capture. It records contract code, ERC-721
supply counters and the PDB v2 parent/child counters. The immutable 100-record
reconstruction audit is maintained separately under evidence/article-02/molnft.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import time
from typing import Any

import requests
from eth_utils import keccak, to_checksum_address

CHAIN_ID = 29
PROVIDERS = [
    ("GenesisL1 public", "https://rpc.genesisl1.org"),
    ("GenesisL1 direct", "https://rpca.genesisl1.org"),
    ("ANODE.TEAM", "https://genesisl1.rpc.m.anode.team"),
    ("UTSA", "https://m-l1.rpc.utsa.tech"),
]
CONTRACTS = {
    "pdb_v2": {
        "name": "MOLNFT PDB v2",
        "address": "0xd58B01f6C18086e5202cdC5D7Ad3E41790360102",
        "storage_generation": "v2_full_payload",
    },
    "pdb_v1": {
        "name": "MOLNFT PDB v1",
        "address": "0xDE3723766Bc32dcACD03C17BaA400A7B36837Eba",
        "storage_generation": "v1_legacy",
    },
    "af_v1": {
        "name": "MOLNFT AlphaFold/Swiss-Prot v1",
        "address": "0xBf7491af3407816DFa88a5EA4c82e8A2B1D721eD",
        "storage_generation": "v1_legacy",
    },
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def selector(signature: str) -> str:
    return "0x" + keccak(text=signature)[:4].hex()


def decode_uint(value: str) -> int:
    return int(value, 16)


def rpc(session: requests.Session, url: str, method: str, params: list[Any], request_id: int, timeout: float, retries: int) -> tuple[dict[str, Any], bytes]:
    body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = session.post(url, json=body, timeout=timeout)
            raw = response.content
            response.raise_for_status()
            payload = response.json()
            if payload.get("error") is not None:
                raise RuntimeError(str(payload["error"]))
            if "result" not in payload:
                raise RuntimeError("JSON-RPC response has no result")
            return payload, raw
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    assert last is not None
    raise last


def save_call(raw_root: pathlib.Path, name: str, url: str, method: str, params: list[Any], request_id: int, payload: dict[str, Any], raw: bytes) -> None:
    directory = raw_root / "molnft"
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / f"{name}.request.json", {"url": url, "jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
    (directory / f"{name}.response.json").write_bytes(raw)


def call_uint(session: requests.Session, url: str, address: str, signature: str, block_hex: str, request_id: int, raw_root: pathlib.Path, name: str, timeout: float, retries: int) -> int:
    params = [{"to": to_checksum_address(address), "data": selector(signature)}, block_hex]
    payload, raw = rpc(session, url, "eth_call", params, request_id, timeout, retries)
    save_call(raw_root, name, url, "eth_call", params, request_id, payload, raw)
    return decode_uint(str(payload["result"]))


def first_counter(session: requests.Session, url: str, address: str, signatures: list[str], block_hex: str, request_id: list[int], raw_root: pathlib.Path, prefix: str, timeout: float, retries: int) -> tuple[str, int]:
    errors: list[str] = []
    for signature in signatures:
        request_id[0] += 1
        try:
            value = call_uint(session, url, address, signature, block_hex, request_id[0], raw_root, f"{prefix}-{signature[:-2]}", timeout, retries)
            return signature, value
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{signature}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def capture(args: argparse.Namespace) -> dict[str, Any]:
    output = pathlib.Path(args.output_directory)
    output.mkdir(parents=True, exist_ok=True)
    raw_root = output / "raw"
    session = requests.Session()
    session.headers.update({"User-Agent": "GenesisL1-Current-State/2.0", "Accept": "application/json"})
    block_hex = hex(args.block)

    provider_name = ""
    provider_url = ""
    block_payload: dict[str, Any] | None = None
    request_id = [1000]
    provider_errors: list[str] = []
    for name, url in PROVIDERS:
        try:
            request_id[0] += 1
            chain, chain_raw = rpc(session, url, "eth_chainId", [], request_id[0], args.timeout, args.retries)
            if decode_uint(str(chain["result"])) != CHAIN_ID:
                raise RuntimeError("wrong EVM chain ID")
            save_call(raw_root, "evm-chain-id", url, "eth_chainId", [], request_id[0], chain, chain_raw)
            request_id[0] += 1
            block, block_raw = rpc(session, url, "eth_getBlockByNumber", [block_hex, False], request_id[0], args.timeout, args.retries)
            if not isinstance(block.get("result"), dict):
                raise RuntimeError("block unavailable")
            save_call(raw_root, "evm-block", url, "eth_getBlockByNumber", [block_hex, False], request_id[0], block, block_raw)
            provider_name, provider_url = name, url
            block_payload = block["result"]
            break
        except Exception as exc:  # noqa: BLE001
            provider_errors.append(f"{name}: {type(exc).__name__}: {exc}")
    if block_payload is None:
        raise RuntimeError("No EVM provider served the pinned block: " + "; ".join(provider_errors))

    rows: list[dict[str, Any]] = []
    for key, spec in CONTRACTS.items():
        address = to_checksum_address(spec["address"])
        request_id[0] += 1
        code_params = [address, block_hex]
        code, code_raw = rpc(session, provider_url, "eth_getCode", code_params, request_id[0], args.timeout, args.retries)
        save_call(raw_root, f"{key}-runtime-code", provider_url, "eth_getCode", code_params, request_id[0], code, code_raw)
        code_bytes = bytes.fromhex(str(code["result"]).removeprefix("0x"))
        if not code_bytes:
            raise RuntimeError(f"No runtime code for {key} at block {args.block}")
        request_id[0] += 1
        total_supply = call_uint(session, provider_url, address, "totalSupply()", block_hex, request_id[0], raw_root, f"{key}-total-supply", args.timeout, args.retries)
        rows.append({
            "key": key,
            "name": spec["name"],
            "address": address,
            "storage_generation": spec["storage_generation"],
            "total_supply": total_supply,
            "runtime_code_sha256": hashlib.sha256(code_bytes).hexdigest(),
        })

    parent_signature, parent_counter = first_counter(session, provider_url, CONTRACTS["pdb_v2"]["address"], ["nextParentId()", "nextNFTId()"], block_hex, request_id, raw_root, "pdb-v2", args.timeout, args.retries)
    child_signature, child_counter = first_counter(session, provider_url, CONTRACTS["pdb_v2"]["address"], ["nextChildId()"], block_hex, request_id, raw_root, "pdb-v2", args.timeout, args.retries)
    parent_records = max(parent_counter - 1, 0)
    child_chunks = max(child_counter - 100_000_000, 0)
    by_key = {row["key"]: row for row in rows}
    v2_total = int(by_key["pdb_v2"]["total_supply"])
    if parent_records + child_chunks != v2_total:
        raise RuntimeError(f"PDB v2 counter reconciliation failed: {parent_records} + {child_chunks} != {v2_total}")

    timestamp = dt.datetime.fromtimestamp(int(str(block_payload["timestamp"]), 16), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    counts = {
        "pdb_v2_parent_records": parent_records,
        "pdb_v2_total_tokens": v2_total,
        "pdb_v2_child_chunks": child_chunks,
        "pdb_v1_tokens": int(by_key["pdb_v1"]["total_supply"]),
        "af_v1_tokens": int(by_key["af_v1"]["total_supply"]),
        "legacy_v1_subtotal": int(by_key["pdb_v1"]["total_supply"]) + int(by_key["af_v1"]["total_supply"]),
    }
    result = {
        "schema": "org.genesisl1.molnft_current_state.v1",
        "pinned_height": args.block,
        "evm_block_hash": str(block_payload["hash"]),
        "evm_block_time_utc": timestamp,
        "captured_at_utc": utc_now(),
        "evm_chain_id": CHAIN_ID,
        "provider_name": provider_name,
        "provider_url": provider_url,
        "parent_counter_function": parent_signature,
        "child_counter_function": child_signature,
        "counts": counts,
        "contracts": rows,
        "scope": "Current contract counters only. Reconstruction fidelity is reported separately by the immutable 100-record audit.",
    }
    write_json(output / "molnft-state.json", result)
    with (output / "molnft-counts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key, value in counts.items():
            writer.writerow([key, value])
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", required=True, type=int)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = capture(args)
    except Exception as exc:  # noqa: BLE001
        print(f"capture failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
