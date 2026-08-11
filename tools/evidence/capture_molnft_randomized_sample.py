#!/usr/bin/env python3
"""Run or deterministically recompute the WS-1 MOLNFT randomized fidelity audit.

The capture consumes a pre-committed sample specification, waits for the future
seed block, enumerates the actual parent-token set at B_pin, draws without
replacement from a block-derived seed, reconstructs each selected on-chain
BinaryCIF, fetches the corresponding canonical RCSB BinaryCIF, and publishes a
per-record fidelity result including all failures.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
import pathlib
import platform
import re
import shutil
import struct
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

import numpy as np

import molnft_structural_compare as structural_compare
import requests
from Crypto.Hash import keccak
from eth_abi import decode as abi_decode, encode as abi_encode

SCHEMA = "org.genesisl1.molnft_randomized_fidelity.v1"
PDB_RE = re.compile(r"^[0-9][A-Z0-9]{3}$")
ZERO_ADDRESS = "0x" + "00" * 20
DEFAULT_RPC_CANDIDATES = [
    "https://rpc.genesisl1.org",
    "https://evm.genesisl1.org",
]
BLOCKSCOUT_ABI = "https://explorer.genesisl1.org/api?module=contract&action=getabi&address={address}"
RCSB_BCIF = "https://models.rcsb.org/{pdb_id}.bcif"
RCSB_HOLDINGS = [
    "https://data.rcsb.org/rest/v1/holdings/current/entry_ids",
    "https://data.rcsb.org/rest/v1/holdings/removed/entry_ids",
    "https://data.rcsb.org/rest/v1/holdings/unreleased/entry_ids",
]
USER_AGENT = "GenesisL1-Insights-WS1/1.0 (+https://github.com/GenesisL1/insights)"


class EvidenceError(RuntimeError):
    pass


class RecordFailure(EvidenceError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(value))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def keccak256(value: bytes) -> bytes:
    digest = keccak.new(digest_bits=256)
    digest.update(value)
    return digest.digest()


def function_selector(signature: str) -> str:
    return "0x" + keccak256(signature.encode("ascii"))[:4].hex()


def event_topic(signature: str) -> str:
    return "0x" + keccak256(signature.encode("ascii")).hex()


def hex_quantity(value: int) -> str:
    return hex(int(value))


def decode_uint(result: str) -> int:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise EvidenceError(f"invalid uint result: {result!r}")
    return int(result, 16)


def recursive_values(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from recursive_values(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from recursive_values(child, f"{path}[{index}]")
    else:
        yield path.lower(), value


def find_address(payload: Any) -> str:
    candidates: list[tuple[int, str]] = []
    for path, value in recursive_values(payload):
        if isinstance(value, str) and re.fullmatch(r"0x[a-fA-F0-9]{40}", value):
            score = 0
            compact = path.replace("_", "").replace("-", "")
            if "pdbv2" in compact:
                score += 100
            if "pdb" in compact:
                score += 30
            if "contract" in compact:
                score += 10
            candidates.append((score, value))
    if not candidates:
        raise EvidenceError("could not find the PDB v2 contract address in existing snapshot")
    candidates.sort(reverse=True)
    return candidates[0][1]


def find_rpc(payload: Any) -> str | None:
    candidates: list[tuple[int, str]] = []
    for path, value in recursive_values(payload):
        if isinstance(value, str) and value.startswith("http"):
            compact = path.replace("_", "").replace("-", "")
            score = 0
            if "rpc" in compact:
                score += 50
            if "evm" in compact:
                score += 30
            if "endpoint" in compact:
                score += 10
            if "explorer" in value or "github" in value or "rcsb" in value:
                score -= 100
            candidates.append((score, value.rstrip("/")))
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates and candidates[0][0] > 0 else None


def find_numeric(payload: Any, tokens: tuple[str, ...]) -> int | None:
    matches: list[tuple[int, int]] = []
    for path, value in recursive_values(payload):
        compact = path.replace("_", "").replace("-", "")
        if all(token.replace("_", "") in compact for token in tokens):
            try:
                matches.append((len(path), int(str(value))))
            except (ValueError, TypeError):
                pass
    matches.sort()
    return matches[0][1] if matches else None


@dataclass
class RawRpc:
    request: dict[str, Any]
    raw_response: bytes
    response: dict[str, Any]


class RpcClient:
    def __init__(self, urls: list[str], timeout: float = 60.0):
        self.urls = []
        for url in urls:
            clean = url.rstrip("/")
            if clean and clean not in self.urls:
                self.urls.append(clean)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Content-Type": "application/json"})
        self.active_url = self._choose()
        self.counter = 0

    def _choose(self) -> str:
        errors = []
        for url in self.urls:
            try:
                response = requests.post(
                    url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []},
                    timeout=15,
                    headers={"User-Agent": USER_AGENT},
                )
                payload = response.json()
                if response.ok and payload.get("result"):
                    return url
                errors.append(f"{url}: {payload}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: {type(exc).__name__}: {exc}")
        raise EvidenceError("no EVM RPC endpoint was usable: " + "; ".join(errors))

    def raw(self, method: str, params: list[Any], retries: int = 4) -> RawRpc:
        self.counter += 1
        request_payload = {"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params}
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self.session.post(self.active_url, data=json.dumps(request_payload, separators=(",", ":")), timeout=self.timeout)
                raw = response.content
                parsed = json.loads(raw.decode("utf-8"))
                if not response.ok:
                    raise EvidenceError(f"HTTP {response.status_code}: {parsed}")
                return RawRpc(request_payload, raw, parsed)
            except Exception as exc:  # noqa: BLE001
                last = exc
                if attempt < retries:
                    time.sleep(min(2**attempt, 10))
        assert last is not None
        raise last

    def call(self, method: str, params: list[Any], retries: int = 4) -> Any:
        raw = self.raw(method, params, retries)
        if raw.response.get("error") is not None:
            raise EvidenceError(f"RPC {method} error: {raw.response['error']}")
        return raw.response.get("result")

    def batch(self, calls: list[tuple[str, list[Any], int]], retries: int = 4) -> list[dict[str, Any]]:
        payload = [
            {"jsonrpc": "2.0", "id": call_id, "method": method, "params": params}
            for method, params, call_id in calls
        ]
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self.session.post(self.active_url, data=json.dumps(payload, separators=(",", ":")), timeout=max(self.timeout, 120))
                parsed = response.json()
                if not response.ok or not isinstance(parsed, list):
                    raise EvidenceError(f"batch HTTP/RPC error: {response.status_code} {parsed}")
                return parsed
            except Exception as exc:  # noqa: BLE001
                last = exc
                if attempt < retries:
                    time.sleep(min(2**attempt, 10))
        assert last is not None
        raise last


def load_existing_context(repo: pathlib.Path) -> tuple[dict[str, Any], pathlib.Path]:
    snapshots = sorted(repo.glob("evidence/article-02/molnft/block-*/snapshot.json"))
    if not snapshots:
        raise EvidenceError("existing MOLNFT snapshot was not found")
    path = snapshots[-1]
    return json.loads(path.read_text(encoding="utf-8")), path.parent


def selector_from_request(directory: pathlib.Path, pattern: str) -> str:
    matches = sorted(directory.glob(f"raw/{pattern}"))
    if not matches:
        raise EvidenceError(f"existing raw request not found: {pattern}")
    payload = json.loads(matches[0].read_text(encoding="utf-8"))
    candidates = payload if isinstance(payload, list) else [payload]
    for candidate in candidates:
        params = candidate.get("params") or []
        if params and isinstance(params[0], dict):
            data = params[0].get("data")
            if isinstance(data, str) and data.startswith("0x") and len(data) >= 10:
                return data[:10]
    raise EvidenceError(f"could not extract selector from {matches[0]}")


def eth_call(client: RpcClient, address: str, data: str, height: int) -> str:
    return client.call("eth_call", [{"to": address, "data": data}, hex_quantity(height)])


def call_counter(client: RpcClient, address: str, selector: str, height: int) -> int:
    return decode_uint(eth_call(client, address, selector, height))


def contract_abi(address: str) -> list[dict[str, Any]]:
    response = requests.get(BLOCKSCOUT_ABI.format(address=address), headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result")
    if isinstance(result, str):
        result = json.loads(result)
    if not isinstance(result, list):
        raise EvidenceError("verified contract ABI was not returned by the explorer")
    return result


def first_code_block(client: RpcClient, address: str, high: int) -> int:
    low = 0
    if client.call("eth_getCode", [address, hex_quantity(high)]) in ("0x", "0x0", None):
        raise EvidenceError("contract has no code at B_pin")
    while low < high:
        middle = (low + high) // 2
        code = client.call("eth_getCode", [address, hex_quantity(middle)])
        if code in ("0x", "0x0", None):
            low = middle + 1
        else:
            high = middle
    return low


def event_signature(item: dict[str, Any]) -> str:
    return f"{item['name']}({','.join(inp['type'] for inp in item.get('inputs', []))})"


def decode_event_log(event: dict[str, Any], log: dict[str, Any]) -> dict[str, Any]:
    inputs = event.get("inputs", [])
    indexed = [item for item in inputs if item.get("indexed")]
    nonindexed = [item for item in inputs if not item.get("indexed")]
    values: dict[str, Any] = {}
    topics = log.get("topics") or []
    for item, topic in zip(indexed, topics[1:]):
        typ = item["type"]
        name = item.get("name") or f"indexed_{len(values)}"
        if typ.startswith("uint"):
            values[name] = int(topic, 16)
        elif typ == "address":
            values[name] = "0x" + topic[-40:]
        elif typ == "bytes32":
            raw = bytes.fromhex(topic[2:])
            try:
                text = raw.rstrip(b"\x00").decode("ascii")
                values[name] = text if text else topic
            except UnicodeDecodeError:
                values[name] = topic
        else:
            values[name] = topic
    if nonindexed:
        raw = bytes.fromhex((log.get("data") or "0x")[2:])
        decoded = abi_decode([item["type"] for item in nonindexed], raw)
        for item, value in zip(nonindexed, decoded):
            name = item.get("name") or f"value_{len(values)}"
            if isinstance(value, bytes):
                try:
                    value = value.rstrip(b"\x00").decode("ascii")
                except UnicodeDecodeError:
                    value = "0x" + value.hex()
            values[name] = value
    return values


def extract_pdb_token(values: dict[str, Any]) -> tuple[str, int] | None:
    pdb_candidates: list[tuple[int, str]] = []
    token_candidates: list[tuple[int, int]] = []
    for name, value in values.items():
        lname = name.lower()
        if isinstance(value, str):
            text = value.upper().strip().replace("PDB:", "")
            if PDB_RE.fullmatch(text):
                score = 100 if "pdb" in lname else 10
                pdb_candidates.append((score, text))
        if isinstance(value, int) and value >= 0:
            score = 0
            if "token" in lname or "nft" in lname:
                score += 100
            if "parent" in lname:
                score += 30
            if "child" in lname:
                score -= 100
            token_candidates.append((score, value))
    if not pdb_candidates or not token_candidates:
        return None
    pdb_candidates.sort(reverse=True)
    token_candidates.sort(reverse=True)
    return pdb_candidates[0][1], token_candidates[0][1]


def rpc_logs_raw(client: RpcClient, address: str, topic0: str, start: int, end: int) -> RawRpc:
    return client.raw(
        "eth_getLogs",
        [{"address": address, "fromBlock": hex_quantity(start), "toBlock": hex_quantity(end), "topics": [topic0]}],
    )


def fetch_event_logs(
    client: RpcClient,
    address: str,
    topic0: str,
    start: int,
    end: int,
    raw_dir: pathlib.Path,
) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    queue: list[tuple[int, int]] = [(start, end)]
    part = 0
    while queue:
        left, right = queue.pop()
        try:
            result = rpc_logs_raw(client, address, topic0, left, right)
            if result.response.get("error") is not None:
                raise EvidenceError(str(result.response["error"]))
            rows = result.response.get("result") or []
            if len(rows) > 5000 and left < right:
                middle = (left + right) // 2
                queue.extend([(middle + 1, right), (left, middle)])
                continue
            part += 1
            raw_dir.mkdir(parents=True, exist_ok=True)
            path = raw_dir / f"logs-{part:05d}-{left}-{right}.json.gz"
            with gzip.open(path, "wb", mtime=0) as handle:
                handle.write(result.raw_response)
            logs.extend(rows)
        except Exception:  # noqa: BLE001
            if left >= right:
                raise
            middle = (left + right) // 2
            queue.extend([(middle + 1, right), (left, middle)])
    logs.sort(key=lambda row: (int(row.get("blockNumber", "0x0"), 16), int(row.get("logIndex", "0x0"), 16)))
    return logs


def enumerate_by_events(
    client: RpcClient,
    address: str,
    height: int,
    expected_count: int,
    abi: list[dict[str, Any]],
    raw_dir: pathlib.Path,
) -> tuple[list[tuple[int, str]], dict[str, Any]]:
    deployment = first_code_block(client, address, height)
    events = [item for item in abi if item.get("type") == "event"]
    scored: list[tuple[int, dict[str, Any]]] = []
    for event in events:
        inputs = event.get("inputs", [])
        has_text = any(item.get("type") in {"string", "bytes32"} for item in inputs)
        has_uint = any(str(item.get("type", "")).startswith("uint") for item in inputs)
        if not (has_text and has_uint):
            continue
        haystack = (event.get("name", "") + " " + " ".join(item.get("name", "") for item in inputs)).lower()
        score = sum(weight for token, weight in [("pdb", 100), ("mint", 30), ("nft", 20), ("parent", 20), ("child", -80)] if token in haystack)
        scored.append((score, event))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    diagnostics = []
    for score, event in scored[:8]:
        signature = event_signature(event)
        topic0 = event_topic(signature)
        candidate_dir = raw_dir / (event.get("name") or "event")
        logs = fetch_event_logs(client, address, topic0, deployment, height, candidate_dir)
        pairs = []
        for log in logs:
            try:
                extracted = extract_pdb_token(decode_event_log(event, log))
                if extracted is not None:
                    pdb_id, token_id = extracted
                    pairs.append((token_id, pdb_id))
            except Exception:  # noqa: BLE001
                continue
        unique = sorted(set(pairs))
        diagnostics.append({"event": signature, "score": score, "logs": len(logs), "decoded_pairs": len(unique)})
        token_ids = {token for token, _ in unique}
        pdb_ids = {pdb for _, pdb in unique}
        if len(unique) == expected_count and len(token_ids) == expected_count and len(pdb_ids) == expected_count:
            return unique, {
                "method": "verified_parent_mint_event",
                "event_signature": signature,
                "event_topic0": topic0,
                "deployment_block": deployment,
                "diagnostics": diagnostics,
            }
    raise EvidenceError("no verified contract event reconciled to the parent counter: " + json.dumps(diagnostics))


def encode_string_call(selector: str, value: str) -> str:
    return selector + abi_encode(["string"], [value]).hex()


def rcsb_identifier_universe() -> list[str]:
    identifiers: set[str] = set()
    errors = []
    for url in RCSB_HOLDINGS:
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                values: Iterable[Any] = []
                for child in payload.values():
                    if isinstance(child, list):
                        values = list(values) + child
            elif isinstance(payload, list):
                values = payload
            else:
                values = []
            for value in values:
                text = str(value).upper().strip()
                if PDB_RE.fullmatch(text):
                    identifiers.add(text)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
    if not identifiers:
        raise EvidenceError("RCSB holdings endpoints yielded no identifiers: " + "; ".join(errors))
    return sorted(identifiers)


def enumerate_by_explicit_pdb_index(
    client: RpcClient,
    address: str,
    height: int,
    expected_count: int,
    selector: str,
    raw_dir: pathlib.Path,
) -> tuple[list[tuple[int, str]], dict[str, Any]]:
    identifiers = rcsb_identifier_universe()
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "rcsb-identifier-universe.txt.gz").write_bytes(gzip.compress(("\n".join(identifiers) + "\n").encode("ascii"), mtime=0))
    pairs: list[tuple[int, str]] = []
    batch_size = 250
    for offset in range(0, len(identifiers), batch_size):
        chunk = identifiers[offset : offset + batch_size]
        calls = [
            (
                "eth_call",
                [{"to": address, "data": encode_string_call(selector, pdb_id)}, hex_quantity(height)],
                offset + index + 1,
            )
            for index, pdb_id in enumerate(chunk)
        ]
        responses = client.batch(calls)
        by_id = {int(item["id"]): item for item in responses}
        raw_payload = stable_json(responses)
        with gzip.open(raw_dir / f"index-batch-{offset // batch_size + 1:05d}.json.gz", "wb", mtime=0) as handle:
            handle.write(raw_payload)
        for index, pdb_id in enumerate(chunk):
            response = by_id.get(offset + index + 1, {})
            if response.get("error") is not None or response.get("result") in (None, "0x"):
                continue
            token_id = decode_uint(response["result"])
            if token_id > 0:
                pairs.append((token_id, pdb_id))
    unique = sorted(set(pairs))
    if len({token for token, _ in unique}) != len(unique) or len({pdb for _, pdb in unique}) != len(unique):
        raise EvidenceError("explicit PDB index produced duplicate token IDs or PDB IDs")
    if len(unique) != expected_count:
        raise EvidenceError(f"explicit PDB index count {len(unique)} does not reconcile to parent counter {expected_count}")
    return unique, {
        "method": "explicit_pdbid_contract_index_with_exact_counter_reconciliation",
        "selector": selector,
        "identifier_universe_count": len(identifiers),
    }


def deterministic_draw(rows: list[tuple[int, str]], seed: bytes, n: int) -> list[tuple[int, str]]:
    remaining = sorted(rows, key=lambda row: (row[0], row[1]))
    if n > len(remaining):
        raise EvidenceError(f"N={n} exceeds enumerated parent count {len(remaining)}")
    selected = []
    counter = 0
    maximum = 1 << 256
    while len(selected) < n:
        digest = hashlib.sha256(seed + counter.to_bytes(8, "big")).digest()
        counter += 1
        integer = int.from_bytes(digest, "big")
        limit = maximum - (maximum % len(remaining))
        if integer >= limit:
            continue
        index = integer % len(remaining)
        selected.append(remaining.pop(index))
    return selected


def dynamic_blobs(result_hex: str) -> list[bytes]:
    raw = bytes.fromhex(result_hex[2:] if result_hex.startswith("0x") else result_hex)
    blobs: list[bytes] = []
    if not raw:
        return blobs
    # Standard ABI dynamic offsets in the return head.
    for pos in range(0, min(len(raw), 32 * 16), 32):
        offset = int.from_bytes(raw[pos : pos + 32], "big")
        if offset % 32 or offset + 32 > len(raw):
            continue
        length = int.from_bytes(raw[offset : offset + 32], "big")
        if 0 <= length <= len(raw) - offset - 32:
            value = raw[offset + 32 : offset + 32 + length]
            if value not in blobs:
                blobs.append(value)
    # Some contracts return bytes directly without an offset wrapper.
    if not blobs and len(raw) >= 32:
        length = int.from_bytes(raw[:32], "big")
        if 0 <= length <= len(raw) - 32:
            blobs.append(raw[32 : 32 + length])
    return blobs


def reconstruct_payload(result_hex: str) -> bytes:
    candidates = dynamic_blobs(result_hex)
    errors = []
    for candidate in sorted(candidates, key=len, reverse=True):
        variants = [candidate]
        try:
            variants.append(base64.b64decode(candidate, validate=True))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"base64: {exc}")
        for value in variants:
            try:
                if value.startswith(b"\x1f\x8b"):
                    value = gzip.decompress(value)
                elif value.startswith((b"x\x9c", b"x\xda")):
                    import zlib

                    value = zlib.decompress(value)
                # BinaryCIF is MessagePack and normally starts with a map marker.
                if len(value) > 100 and value[:1] not in {b"{", b"[", b"<"}:
                    return value
            except Exception as exc:  # noqa: BLE001
                errors.append(f"decompress: {exc}")
    raise RecordFailure("ABI_DECODE_FAIL", "could not identify a decodable BinaryCIF payload: " + "; ".join(errors[-5:]))


def mapping_values(obj: Any) -> list[Any]:
    if hasattr(obj, "values"):
        try:
            return list(obj.values())
        except Exception:  # noqa: BLE001
            pass
    return []


def get_item(obj: Any, names: list[str]) -> Any | None:
    for name in names:
        try:
            return obj[name]
        except Exception:  # noqa: BLE001
            pass
    return None


def as_array(column: Any) -> np.ndarray:
    for method_name in ("as_array", "as_numpy_array"):
        method = getattr(column, method_name, None)
        if callable(method):
            for args in ((), (str,), (float,)):
                try:
                    return np.asarray(method(*args))
                except Exception:  # noqa: BLE001
                    pass
    for attr in ("array", "data"):
        value = getattr(column, attr, None)
        if value is not None:
            try:
                return np.asarray(value)
            except Exception:  # noqa: BLE001
                pass
    raise EvidenceError("could not convert BinaryCIF column to an array")


def normalize_string(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    text = str(value)
    return "" if text in {".", "?", "None", "nan"} else text


def atom_table(path: pathlib.Path) -> dict[str, Any]:
    from biotite.structure.io.pdbx import BinaryCIFFile

    file = BinaryCIFFile.read(str(path))
    block = getattr(file, "block", None)
    if block is None:
        values = mapping_values(file)
        block = values[0] if values else None
    if block is None:
        for key in getattr(file, "keys", lambda: [])():
            try:
                block = file[key]
                break
            except Exception:  # noqa: BLE001
                pass
    if block is None:
        raise EvidenceError("BinaryCIF has no data block")
    category = get_item(block, ["atom_site", "_atom_site"])
    if category is None:
        raise EvidenceError("BinaryCIF has no atom_site category")

    aliases = {
        "id": ["id"],
        "model": ["pdbx_PDB_model_num", "PDB_model_num"],
        "entity": ["label_entity_id"],
        "label_chain": ["label_asym_id"],
        "auth_chain": ["auth_asym_id"],
        "label_seq": ["label_seq_id"],
        "auth_seq": ["auth_seq_id"],
        "ins": ["pdbx_PDB_ins_code"],
        "atom": ["label_atom_id", "auth_atom_id"],
        "alt": ["label_alt_id"],
        "element": ["type_symbol"],
        "x": ["Cartn_x"],
        "y": ["Cartn_y"],
        "z": ["Cartn_z"],
    }
    columns: dict[str, np.ndarray] = {}
    required = {"x", "y", "z"}
    for logical, names in aliases.items():
        column = get_item(category, names)
        if column is None:
            if logical in required:
                raise EvidenceError(f"BinaryCIF atom_site lacks {names[0]}")
            continue
        columns[logical] = as_array(column)
    count = len(columns["x"])
    if count <= 0 or any(len(value) != count for value in columns.values()):
        raise EvidenceError("BinaryCIF atom_site columns have inconsistent row counts")

    def value(name: str, index: int, fallback: str = "") -> str:
        array = columns.get(name)
        return normalize_string(array[index]) if array is not None else fallback

    rows = []
    for index in range(count):
        key = (
            value("model", index, "1"),
            value("entity", index),
            value("label_chain", index),
            value("auth_chain", index),
            value("label_seq", index),
            value("auth_seq", index),
            value("ins", index),
            value("atom", index),
            value("alt", index),
            value("element", index),
            value("id", index, str(index + 1)),
        )
        coordinate = (float(columns["x"][index]), float(columns["y"][index]), float(columns["z"][index]))
        rows.append((key, coordinate))
    rows.sort(key=lambda row: row[0])
    stream = bytearray()
    for key, coordinate in rows:
        encoded_key = "\x1f".join(key).encode("utf-8")
        stream.extend(struct.pack(">I", len(encoded_key)))
        stream.extend(encoded_key)
        stream.extend(struct.pack(">ddd", *coordinate))
    return {
        "count": count,
        "chains": sorted({value("label_chain", index) for index in range(count)}),
        "entities": sorted({value("entity", index) for index in range(count)}),
        "rows": rows,
        "coordinate_hash": sha256_bytes(bytes(stream)),
    }


def compare_bcif(reconstructed: pathlib.Path, canonical: pathlib.Path, tolerance: float) -> dict[str, Any]:
    return structural_compare.compare_bcif(reconstructed, canonical, tolerance)


def save_rpc(raw_dir: pathlib.Path, label: str, raw: RawRpc) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    write_json(raw_dir / f"{label}.request.json", raw.request)
    (raw_dir / f"{label}.response.json").write_bytes(raw.raw_response)


def capture_record(
    client: RpcClient,
    address: str,
    combined_selector: str,
    height: int,
    token_id: int,
    pdb_id: str,
    directory: pathlib.Path,
    tolerance: float,
) -> dict[str, Any]:
    raw_dir = directory / "raw" / f"{pdb_id}-token-{token_id}"
    reconstructed_path = directory / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif"
    canonical_path = directory / "canonical" / f"{pdb_id}.bcif"
    reconstructed_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    base = {
        "token_id": token_id,
        "pdb_id": pdb_id,
        "outcome": "FAILURE",
        "reason_code": "UNKNOWN",
        "reason_detail": "",
    }
    try:
        call_data = combined_selector + abi_encode(["uint256"], [token_id]).hex()
        try:
            raw = client.raw("eth_call", [{"to": address, "data": call_data}, hex_quantity(height)])
            save_rpc(raw_dir, "eth-call-combined", raw)
            if raw.response.get("error") is not None:
                raise RecordFailure("RPC_ERROR", str(raw.response["error"]))
            result_hex = raw.response.get("result")
            if not result_hex:
                raise RecordFailure("CHUNK_MISSING", "eth_call returned an empty result")
        except requests.Timeout as exc:
            raise RecordFailure("RPC_TIMEOUT", str(exc)) from exc
        except RecordFailure:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RecordFailure("RPC_ERROR", str(exc)) from exc

        try:
            reconstructed = reconstruct_payload(result_hex)
        except RecordFailure:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RecordFailure("DECOMPRESS_FAIL", str(exc)) from exc
        reconstructed_path.write_bytes(reconstructed)

        canonical_url = RCSB_BCIF.format(pdb_id=pdb_id.lower())
        try:
            started = utc_now()
            response = requests.get(canonical_url, headers={"User-Agent": USER_AGENT}, timeout=90)
            if response.status_code != 200:
                raise RecordFailure("CANONICAL_UNAVAILABLE", f"HTTP {response.status_code}")
            canonical = response.content
            canonical_path.write_bytes(canonical)
            write_json(
                raw_dir / "canonical-fetch.json",
                {
                    "url": canonical_url,
                    "retrieved_at_utc": started,
                    "status_code": response.status_code,
                    "headers": {key.lower(): value for key, value in response.headers.items()},
                    "bytes": len(canonical),
                    "sha256": sha256_bytes(canonical),
                },
            )
        except RecordFailure:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RecordFailure("CANONICAL_UNAVAILABLE", str(exc)) from exc

        try:
            comparison = compare_bcif(reconstructed_path, canonical_path, tolerance)
        except Exception as exc:  # noqa: BLE001
            raise RecordFailure("PARSE_FAIL", str(exc)) from exc

        base.update(comparison)
        base.update(
            {
                "reconstructed_bytes": len(reconstructed),
                "canonical_bytes": len(canonical),
                "reconstructed_sha256": sha256_bytes(reconstructed),
                "canonical_sha256": sha256_bytes(canonical),
            }
        )
        if not comparison["fidelity_pass"]:
            raise RecordFailure("FIDELITY_MISMATCH", "one or more declared fidelity checks failed")
        base["outcome"] = "SUCCESS"
        base["reason_code"] = "SUCCESS"
        return base
    except RecordFailure as exc:
        base["reason_code"] = exc.reason
        base["reason_detail"] = str(exc)
        return base
    except Exception as exc:  # noqa: BLE001
        base["reason_code"] = "UNEXPECTED_ERROR"
        base["reason_detail"] = f"{type(exc).__name__}: {exc}"
        return base


RESULT_FIELDS = [
    "draw_order",
    "token_id",
    "pdb_id",
    "outcome",
    "reason_code",
    "reason_detail",
    "reconstructed_bytes",
    "canonical_bytes",
    "reconstructed_sha256",
    "canonical_sha256",
    "reconstructed_atom_count",
    "canonical_atom_count",
    "atom_count_equal",
    "reconstructed_chain_ids",
    "canonical_chain_ids",
    "chain_ids_equal",
    "reconstructed_entity_ids",
    "canonical_entity_ids",
    "entity_ids_equal",
    "atom_identity_agreement",
    "atom_identity_comparison_method",
    "stable_atom_site_id_sets_equal",
    "stable_identity_field_mismatch_count",
    "rcsb_atom_name_revision_documented",
    "rcsb_atom_name_revision_date",
    "reconstructed_latest_structure_revision_date",
    "canonical_latest_structure_revision_date",
    "atom_name_change_count",
    "atom_name_changes",
    "reconstructed_coordinate_sha256",
    "canonical_coordinate_sha256",
    "coordinate_hash_equal",
    "coordinate_hash_ordering_method",
    "max_coordinate_deviation_angstrom",
    "coordinate_tolerance_angstrom",
    "coordinate_agreement",
    "fidelity_pass",
]


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, float):
        return format(value, ".12g")
    return value if value is not None else ""


def write_results(path: pathlib.Path, results: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in results:
            writer.writerow({field: csv_value(row.get(field)) for field in RESULT_FIELDS})


def write_enumeration(path: pathlib.Path, rows: list[tuple[int, str]]) -> None:
    buffer = ["token_id,pdb_id\n"] + [f"{token_id},{pdb_id}\n" for token_id, pdb_id in sorted(rows)]
    with gzip.open(path, "wb", mtime=0) as handle:
        handle.write("".join(buffer).encode("ascii"))


def write_draw(path: pathlib.Path, rows: list[tuple[int, str]]) -> None:
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["draw_order", "token_id", "pdb_id"])
        for index, (token_id, pdb_id) in enumerate(rows, 1):
            writer.writerow([index, token_id, pdb_id])


def environment() -> dict[str, Any]:
    packages = {}
    for name in ["beautifulsoup4", "biotite", "eth-abi", "msgpack", "numpy", "pycryptodome", "requests"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
    }


def integrity(directory: pathlib.Path, extra_manifest: dict[str, Any] | None = None) -> None:
    excluded = {"MANIFEST.json", "SHA256SUMS.txt"}
    files = sorted(path for path in directory.rglob("*") if path.is_file() and path.name not in excluded)
    manifest_files = []
    sums = []
    for path in files:
        relative = path.relative_to(directory).as_posix()
        digest = sha256_file(path)
        manifest_files.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest})
        sums.append(f"{digest}  {relative}")
    manifest = {"algorithm": "SHA-256", "files": manifest_files}
    if extra_manifest:
        manifest.update(extra_manifest)
    write_json(directory / "MANIFEST.json", manifest)
    (directory / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")


def read_draw(path: pathlib.Path) -> list[tuple[int, str]]:
    rows = []
    with path.open(newline="", encoding="ascii") as handle:
        for row in csv.DictReader(handle):
            rows.append((int(row["token_id"]), row["pdb_id"]))
    return rows


def recompute(directory: pathlib.Path) -> None:
    spec = json.loads((directory / "sample-spec.json").read_text(encoding="utf-8"))
    tolerance = float(spec["fidelity"]["coordinate_tolerance_angstrom"])
    old_summary = json.loads((directory / "summary.json").read_text(encoding="utf-8")) if (directory / "summary.json").exists() else {}
    results = []
    for index, (token_id, pdb_id) in enumerate(read_draw(directory / "drawn-ids.csv"), 1):
        reconstructed = directory / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif"
        canonical = directory / "canonical" / f"{pdb_id}.bcif"
        row = {"draw_order": index, "token_id": token_id, "pdb_id": pdb_id, "outcome": "FAILURE", "reason_code": "MISSING_FILE", "reason_detail": ""}
        if reconstructed.exists() and canonical.exists():
            try:
                comparison = compare_bcif(reconstructed, canonical, tolerance)
                row.update(comparison)
                row.update(
                    {
                        "reconstructed_bytes": reconstructed.stat().st_size,
                        "canonical_bytes": canonical.stat().st_size,
                        "reconstructed_sha256": sha256_file(reconstructed),
                        "canonical_sha256": sha256_file(canonical),
                    }
                )
                row["outcome"] = "SUCCESS" if comparison["fidelity_pass"] else "FAILURE"
                row["reason_code"] = "SUCCESS" if comparison["fidelity_pass"] else "FIDELITY_MISMATCH"
            except Exception as exc:  # noqa: BLE001
                row["reason_code"] = "PARSE_FAIL"
                row["reason_detail"] = str(exc)
        results.append(row)
    write_results(directory / "results.csv", results)
    reason_counts = Counter(row["reason_code"] for row in results)
    summary = dict(old_summary)
    summary.update(
        {
            "N": len(results),
            "successes": sum(row["outcome"] == "SUCCESS" for row in results),
            "failures": sum(row["outcome"] != "SUCCESS" for row in results),
            "failures_by_reason": dict(sorted((key, value) for key, value in reason_counts.items() if key != "SUCCESS")),
            "fidelity_passes": sum(bool(row.get("fidelity_pass")) for row in results),
            "coordinate_tolerance_passes": sum(bool(row.get("coordinate_agreement")) for row in results),
            "coordinate_hash_matches": sum(bool(row.get("coordinate_hash_equal")) for row in results),
            "revision_aware_records": [
                {
                    "draw_order": row.get("draw_order"),
                    "token_id": row.get("token_id"),
                    "pdb_id": row.get("pdb_id"),
                    "rcsb_atom_name_revision_date": row.get("rcsb_atom_name_revision_date"),
                    "reconstructed_latest_structure_revision_date": row.get("reconstructed_latest_structure_revision_date"),
                    "canonical_latest_structure_revision_date": row.get("canonical_latest_structure_revision_date"),
                    "atom_name_change_count": row.get("atom_name_change_count"),
                    "atom_name_changes": row.get("atom_name_changes") or [],
                    "max_coordinate_deviation_angstrom": row.get("max_coordinate_deviation_angstrom"),
                }
                for row in results
                if row.get("rcsb_atom_name_revision_documented")
            ],
            "fidelity_pass_definition": [
                "atom_count_equal",
                "chain_ids_equal",
                "entity_ids_equal",
                "atom_identity_agreement",
                "coordinate_agreement_within_precommitted_tolerance",
            ],
            "coordinate_hash_role": "exact normalized coordinate hashes are recorded separately in the accepted atom-pairing order; equality is not required when the declared coordinate tolerance passes",
            "coordinate_hash_algorithm": "SHA-256 over big-endian float64 XYZ triples in accepted atom-pairing order with signed zero normalized",
            "deterministic_recompute_at_utc": old_summary.get("deterministic_recompute_at_utc"),
        }
    )
    write_json(directory / "summary.json", summary)
    seed = json.loads((directory / "seed-derivation.json").read_text(encoding="utf-8"))
    integrity(directory, {"precommit_sha": seed["sample_spec_precommit_sha"], "seed_block_hash": seed["B_seed_block_hash"]})


def prepare_spec(repo: pathlib.Path, output: pathlib.Path, n: int, seed_delay: int) -> None:
    existing, old_dir = load_existing_context(repo)
    address = find_address(existing)
    rpc_candidates = [find_rpc(existing)] + DEFAULT_RPC_CANDIDATES
    client = RpcClient([url for url in rpc_candidates if url])
    chain_id = decode_uint(client.call("eth_chainId", []))
    latest = decode_uint(client.call("eth_blockNumber", []))
    b_pin = latest - 12
    b_seed = latest + seed_delay
    combined_selector = selector_from_request(old_dir, "rpc-combined-*.request.json")
    next_nft_selector = selector_from_request(old_dir, "rpc-pdb-v2-nextNFTId.request.json")
    glast_selector = selector_from_request(old_dir, "glast-*.request.json")
    lock = repo / "requirements.lock"
    spec = {
        "schema": "org.genesisl1.molnft_sample_spec.v1",
        "announced_at_utc": utc_now(),
        "network": "GenesisL1",
        "cosmos_chain_id": "genesis_29-2",
        "evm_chain_id": chain_id,
        "contract_address": address,
        "B_pin": b_pin,
        "B_seed": b_seed,
        "N": n,
        "id_enumeration": {
            "algorithm": "verified_parent_mint_event_or_explicit_pdbid_contract_index_with_exact_counter_reconciliation_v1",
            "draw_population": "actual unique (token_id, PDB_ID) parent set at B_pin",
            "forbidden_assumption": "parent token IDs are not assumed to be contiguous",
            "parent_counter_selector": next_nft_selector,
            "pdb_index_selector": glast_selector,
        },
        "rng": {
            "seed_derivation": "keccak256(bytes.fromhex(evm_block_hash(B_seed)))",
            "draw_algorithm": "SHA-256 counter-mode rejection sampling without replacement v1",
            "ordering": "numeric token_id ascending, then uppercase PDB_ID",
        },
        "reconstruction": {
            "combined_data_selector": combined_selector,
            "pipeline": ["eth_call", "ABI decode", "base64 decode", "gzip decompress if flagged", "BinaryCIF parse"],
        },
        "fidelity": {
            "canonical_source": "https://models.rcsb.org/<PDB_ID>.bcif",
            "loss_model": "lossless BinaryCIF payload",
            "coordinate_tolerance_angstrom": 0.000001,
            "atom_order_normalization": "canonical atom key sort v1",
        },
        "environment": {
            "requirements_lock": "requirements.lock",
            "requirements_lock_sha256": sha256_file(lock),
        },
        "rpc_endpoint_selected_at_announcement": client.active_url,
        "latest_evm_height_observed_at_announcement": latest,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(stable_json(spec))


def run_capture(repo: pathlib.Path, spec_path: pathlib.Path, precommit_sha: str, output_root: pathlib.Path, workers: int) -> pathlib.Path:
    started = utc_now()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    existing, old_dir = load_existing_context(repo)
    rpc_candidates = [spec.get("rpc_endpoint_selected_at_announcement"), find_rpc(existing)] + DEFAULT_RPC_CANDIDATES
    client = RpcClient([url for url in rpc_candidates if url])
    chain_id = decode_uint(client.call("eth_chainId", []))
    if chain_id != int(spec["evm_chain_id"]):
        raise EvidenceError(f"chain ID mismatch: spec {spec['evm_chain_id']}, RPC {chain_id}")
    latest = decode_uint(client.call("eth_blockNumber", []))
    if latest < int(spec["B_seed"]):
        raise EvidenceError(f"seed block is not yet available: current {latest}, B_seed {spec['B_seed']}")

    seed_block_raw = client.raw("eth_getBlockByNumber", [hex_quantity(int(spec["B_seed"])), False])
    if seed_block_raw.response.get("error") is not None or not seed_block_raw.response.get("result"):
        raise EvidenceError("could not retrieve B_seed block")
    seed_block = seed_block_raw.response["result"]
    block_hash = seed_block["hash"]
    seed = keccak256(bytes.fromhex(block_hash[2:]))

    b_pin = int(spec["B_pin"])
    pin_block_raw = client.raw("eth_getBlockByNumber", [hex_quantity(b_pin), False])
    pin_block = pin_block_raw.response.get("result")
    if not pin_block:
        raise EvidenceError("could not retrieve B_pin block")

    directory = output_root / f"block-{b_pin}"
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    shutil.copy2(spec_path, directory / "sample-spec.json")
    (directory / "raw" / "seed").mkdir(parents=True, exist_ok=True)
    save_rpc(directory / "raw" / "seed", "B-seed-block", seed_block_raw)
    save_rpc(directory / "raw" / "seed", "B-pin-block", pin_block_raw)
    seed_derivation = {
        "schema": "org.genesisl1.molnft_seed_derivation.v1",
        "sample_spec_precommit_sha": precommit_sha,
        "B_pin": b_pin,
        "B_pin_block_hash": pin_block["hash"],
        "B_seed": int(spec["B_seed"]),
        "B_seed_block_hash": block_hash,
        "derived_seed_hex": "0x" + seed.hex(),
        "derivation": "keccak256(bytes.fromhex(evm_block_hash(B_seed)))",
    }
    write_json(directory / "seed-derivation.json", seed_derivation)

    next_selector = spec["id_enumeration"]["parent_counter_selector"]
    current_counter = call_counter(client, spec["contract_address"], next_selector, b_pin)
    old_parent = find_numeric(existing, ("parent", "record"))
    if old_parent is None:
        old_parent = 229271
    old_counter_raw = json.loads(sorted(old_dir.glob("raw/rpc-pdb-v2-nextNFTId.response.json"))[0].read_text(encoding="utf-8"))
    old_result = old_counter_raw.get("result") if isinstance(old_counter_raw, dict) else None
    old_counter = decode_uint(old_result) if old_result else old_parent + 1
    offset = old_counter - old_parent
    expected_count = current_counter - offset
    if expected_count <= 0:
        raise EvidenceError(f"invalid parent counter reconciliation: counter={current_counter}, offset={offset}")

    abi = contract_abi(spec["contract_address"])
    enumeration_raw = directory / "raw" / "enumeration"
    try:
        enumeration, enum_meta = enumerate_by_events(
            client,
            spec["contract_address"],
            b_pin,
            expected_count,
            abi,
            enumeration_raw / "events",
        )
    except Exception as event_error:  # noqa: BLE001
        enumeration, enum_meta = enumerate_by_explicit_pdb_index(
            client,
            spec["contract_address"],
            b_pin,
            expected_count,
            spec["id_enumeration"]["pdb_index_selector"],
            enumeration_raw / "explicit-index",
        )
        enum_meta["event_attempt_error"] = str(event_error)
    enum_meta.update({"expected_parent_count": expected_count, "enumerated_parent_count": len(enumeration), "counter_value": current_counter, "counter_offset": offset})
    write_json(directory / "enumeration-method.json", enum_meta)
    write_enumeration(directory / "parent-id-enumeration.csv.gz", enumeration)

    drawn = deterministic_draw(enumeration, seed, int(spec["N"]))
    write_draw(directory / "drawn-ids.csv", drawn)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                capture_record,
                client,
                spec["contract_address"],
                spec["reconstruction"]["combined_data_selector"],
                b_pin,
                token_id,
                pdb_id,
                directory,
                float(spec["fidelity"]["coordinate_tolerance_angstrom"]),
            ): index
            for index, (token_id, pdb_id) in enumerate(drawn, 1)
        }
        for future in as_completed(futures):
            index = futures[future]
            row = future.result()
            row["draw_order"] = index
            results.append(row)
    results.sort(key=lambda row: int(row["draw_order"]))
    write_results(directory / "results.csv", results)

    reason_counts = Counter(row["reason_code"] for row in results)
    summary = {
        "schema": SCHEMA,
        "B_pin": b_pin,
        "B_pin_block_hash": pin_block["hash"],
        "B_seed": int(spec["B_seed"]),
        "B_seed_block_hash": block_hash,
        "sample_spec_precommit_sha": precommit_sha,
        "contract_address": spec["contract_address"],
        "evm_chain_id": chain_id,
        "N": int(spec["N"]),
        "enumerated_parent_count": len(enumeration),
        "enumeration_method": enum_meta,
        "successes": sum(row["outcome"] == "SUCCESS" for row in results),
        "failures": sum(row["outcome"] != "SUCCESS" for row in results),
        "failures_by_reason": dict(sorted((key, value) for key, value in reason_counts.items() if key != "SUCCESS")),
        "fidelity_passes": sum(bool(row.get("fidelity_pass")) for row in results),
        "coordinate_tolerance_passes": sum(bool(row.get("coordinate_agreement")) for row in results),
        "coordinate_hash_matches": sum(bool(row.get("coordinate_hash_equal")) for row in results),
        "revision_aware_records": [
            {
                "draw_order": row.get("draw_order"),
                "token_id": row.get("token_id"),
                "pdb_id": row.get("pdb_id"),
                "rcsb_atom_name_revision_date": row.get("rcsb_atom_name_revision_date"),
                "reconstructed_latest_structure_revision_date": row.get("reconstructed_latest_structure_revision_date"),
                "canonical_latest_structure_revision_date": row.get("canonical_latest_structure_revision_date"),
                "atom_name_change_count": row.get("atom_name_change_count"),
                "atom_name_changes": row.get("atom_name_changes") or [],
                "max_coordinate_deviation_angstrom": row.get("max_coordinate_deviation_angstrom"),
            }
            for row in results
            if row.get("rcsb_atom_name_revision_documented")
        ],
        "fidelity_pass_definition": [
            "atom_count_equal",
            "chain_ids_equal",
            "entity_ids_equal",
            "atom_identity_agreement_by_raw_key_or_documented_rcsb_atom_name_revision",
            "coordinate_agreement_within_precommitted_tolerance",
        ],
        "coordinate_hash_role": "exact normalized coordinate hashes are recorded separately in the accepted atom-pairing order; equality is not required when the declared coordinate tolerance passes",
        "coordinate_hash_algorithm": "SHA-256 over big-endian float64 XYZ triples in accepted atom-pairing order with signed zero normalized",
        "coordinate_tolerance_angstrom": spec["fidelity"]["coordinate_tolerance_angstrom"],
        "loss_model": spec["fidelity"]["loss_model"],
        "rpc_endpoint": client.active_url,
        "rpc_provider": "public GenesisL1 EVM JSON-RPC",
        "canonical_endpoint": RCSB_BCIF,
        "wall_clock_start_utc": started,
        "wall_clock_end_utc": utc_now(),
        "environment": environment(),
        "requirements_lock_sha256": sha256_file(repo / "requirements.lock"),
    }
    write_json(directory / "summary.json", summary)
    integrity(directory, {"precommit_sha": precommit_sha, "seed_block_hash": block_hash})
    return directory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--prepare-spec", type=pathlib.Path)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed-delay", type=int, default=60)
    parser.add_argument("--spec", type=pathlib.Path)
    parser.add_argument("--precommit-sha")
    parser.add_argument("--output-root", type=pathlib.Path, default=pathlib.Path("evidence/article-02/molnft/randomized"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--recompute", type=pathlib.Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    if args.prepare_spec:
        prepare_spec(repo, args.prepare_spec, args.n, args.seed_delay)
        return 0
    if args.recompute:
        recompute(args.recompute.resolve())
        return 0
    if not args.spec or not args.precommit_sha:
        parser.error("capture requires --spec and --precommit-sha")
    output = run_capture(repo, args.spec.resolve(), args.precommit_sha, args.output_root.resolve(), args.workers)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
