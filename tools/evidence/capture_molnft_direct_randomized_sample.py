#!/usr/bin/env python3
"""Direct-token WS-1 randomized MOLNFT reconstruction and fidelity audit.

This implementation deliberately does not use GLAST or another off-chain token
index. The PDB v2 contract's pinned ``nextNFTId()`` value defines the parent
NFT-ID population as the inclusive integer range ``1..nextNFTId()-1``. A future
GenesisL1 block hash supplies the unpredictable seed. Only the selected IDs are
queried for ``getMetadata(uint256)`` and ``getCombinedData(uint256)``.

The module reuses the BinaryCIF parsing, canonicalization, fidelity comparison,
result writer and checksum implementation in
``capture_molnft_randomized_sample.py``.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

BASE_PATH = pathlib.Path(__file__).with_name("capture_molnft_randomized_sample.py")
MODULE_SPEC = importlib.util.spec_from_file_location("genesisl1_ws1_base", BASE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"could not load {BASE_PATH}")
base = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = base
MODULE_SPEC.loader.exec_module(base)

SCHEMA = "org.genesisl1.molnft_direct_randomized_fidelity.v1"
PDB_V2_CONTRACT = "0xd58B01f6C18086e5202cdC5D7Ad3E41790360102"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def direct_draw(population: list[int], seed: bytes, n: int) -> list[int]:
    """Draw without replacement using SHA-256 counter-mode rejection sampling."""
    remaining = list(population)
    if n > len(remaining):
        raise base.EvidenceError(f"N={n} exceeds parent-ID population {len(remaining)}")
    selected: list[int] = []
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


def write_direct_enumeration(path: pathlib.Path, first_id: int, last_id: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as handle:
            handle.write(b"token_id\n")
            for token_id in range(first_id, last_id + 1):
                handle.write(f"{token_id}\n".encode("ascii"))


def metadata_call(
    client: Any,
    address: str,
    metadata_selector: str,
    height: int,
    token_id: int,
    directory: pathlib.Path,
) -> tuple[str, dict[str, Any]]:
    call_data = metadata_selector + base.abi_encode(["uint256"], [token_id]).hex()
    raw = client.raw("eth_call", [{"to": address, "data": call_data}, base.hex_quantity(height)])
    fallback_dir = directory / "raw" / f"token-{token_id}"
    base.save_rpc(fallback_dir, "eth-call-metadata", raw)
    if raw.response.get("error") is not None:
        raise base.RecordFailure("RPC_ERROR", str(raw.response["error"]))
    result_hex = raw.response.get("result")
    if not result_hex or result_hex == "0x":
        raise base.RecordFailure("METADATA_MISSING", "getMetadata returned an empty result")
    try:
        decoded = base.abi_decode(["string"] * 11, bytes.fromhex(str(result_hex).removeprefix("0x")))
    except Exception as exc:  # noqa: BLE001
        raise base.RecordFailure("ABI_DECODE_FAIL", f"getMetadata: {exc}") from exc
    pdb_id = str(decoded[0]).strip().upper()
    if not base.PDB_RE.fullmatch(pdb_id):
        raise base.RecordFailure("METADATA_ID_INVALID", f"token {token_id} returned IDCODE={pdb_id!r}")

    final_dir = directory / "raw" / f"{pdb_id}-token-{token_id}"
    final_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(fallback_dir.glob("eth-call-metadata.*.json")):
        shutil.move(str(source), final_dir / source.name)
    try:
        fallback_dir.rmdir()
    except OSError:
        pass
    metadata = {
        "idcode": pdb_id,
        "header": str(decoded[1]),
        "accession_date": str(decoded[2]),
        "compound": str(decoded[3]),
        "source": str(decoded[4]),
        "authors": str(decoded[5]),
        "resolution": str(decoded[6]),
        "experiment_type": str(decoded[7]),
        "sequence_length": len(str(decoded[8])),
        "image_base64_characters": len(str(decoded[9])),
        "file_base64_characters": len(str(decoded[10])),
    }
    base.write_json(final_dir / "metadata-decoded.json", metadata)
    return pdb_id, metadata


def capture_direct_record(
    rpc_url: str,
    address: str,
    metadata_selector: str,
    combined_selector: str,
    height: int,
    token_id: int,
    directory: pathlib.Path,
    tolerance: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "token_id": token_id,
        "pdb_id": "UNKNOWN",
        "outcome": "FAILURE",
        "reason_code": "UNKNOWN",
        "reason_detail": "",
    }
    client = base.RpcClient([rpc_url], timeout=120.0)
    try:
        pdb_id, metadata = metadata_call(client, address, metadata_selector, height, token_id, directory)
        row["pdb_id"] = pdb_id
        row.update({
            "metadata_sequence_length": metadata["sequence_length"],
            "metadata_file_base64_characters": metadata["file_base64_characters"],
        })
        result = base.capture_record(
            client,
            address,
            combined_selector,
            height,
            token_id,
            pdb_id,
            directory,
            tolerance,
        )
        result.update({
            "metadata_sequence_length": metadata["sequence_length"],
            "metadata_file_base64_characters": metadata["file_base64_characters"],
        })
        return result
    except base.RecordFailure as exc:
        row["reason_code"] = exc.reason
        row["reason_detail"] = str(exc)
        return row
    except requests.Timeout as exc:
        row["reason_code"] = "RPC_TIMEOUT"
        row["reason_detail"] = str(exc)
        return row
    except Exception as exc:  # noqa: BLE001
        row["reason_code"] = "UNEXPECTED_ERROR"
        row["reason_detail"] = f"{type(exc).__name__}: {exc}"
        return row


def query_uint(client: Any, address: str, selector: str, height: int) -> tuple[int, Any]:
    raw = client.raw("eth_call", [{"to": address, "data": selector}, base.hex_quantity(height)])
    if raw.response.get("error") is not None:
        raise base.EvidenceError(str(raw.response["error"]))
    return base.decode_uint(str(raw.response.get("result"))), raw


def prepare_spec(repo: pathlib.Path, output: pathlib.Path, n: int, seed_delay: int) -> None:
    existing, _ = base.load_existing_context(repo)
    rpc_candidates = [base.find_rpc(existing)] + base.DEFAULT_RPC_CANDIDATES
    client = base.RpcClient([url for url in rpc_candidates if url])
    chain_id = base.decode_uint(client.call("eth_chainId", []))
    latest = base.decode_uint(client.call("eth_blockNumber", []))
    b_pin = latest - 12
    b_seed = latest + seed_delay
    next_selector = base.function_selector("nextNFTId()")
    metadata_selector = base.function_selector("getMetadata(uint256)")
    combined_selector = base.function_selector("getCombinedData(uint256)")
    next_value, _ = query_uint(client, PDB_V2_CONTRACT, next_selector, b_pin)
    if next_value <= 1:
        raise base.EvidenceError(f"unexpected nextNFTId()={next_value}")
    first_id = 1
    last_id = next_value - 1
    parent_count = last_id - first_id + 1
    if parent_count < n:
        raise base.EvidenceError(f"parent count {parent_count} is smaller than N={n}")

    # Boundary calls establish that the first and last IDs in the announced range
    # resolve as parent records at B_pin. The complete randomized sample tests the
    # range operationally without an off-chain index.
    first_pdb, _ = metadata_call(client, PDB_V2_CONTRACT, metadata_selector, b_pin, first_id, pathlib.Path(".tmp/ws1-spec-boundary"))
    last_pdb, _ = metadata_call(client, PDB_V2_CONTRACT, metadata_selector, b_pin, last_id, pathlib.Path(".tmp/ws1-spec-boundary"))
    shutil.rmtree(".tmp/ws1-spec-boundary", ignore_errors=True)

    lock = repo / "requirements.lock"
    spec = {
        "schema": "org.genesisl1.molnft_direct_sample_spec.v1",
        "announced_at_utc": utc_now(),
        "network": "GenesisL1",
        "cosmos_chain_id": "genesis_29-2",
        "evm_chain_id": chain_id,
        "contract_address": PDB_V2_CONTRACT,
        "B_pin": b_pin,
        "B_seed": b_seed,
        "N": n,
        "id_enumeration": {
            "algorithm": "direct_contract_parent_nft_id_range_v1",
            "basis": "inclusive parent NFT-ID range 1..nextNFTId(B_pin)-1",
            "off_chain_index_used": False,
            "parent_counter_function": "nextNFTId()",
            "parent_counter_selector": next_selector,
            "parent_counter_value": next_value,
            "parent_id_start": first_id,
            "parent_id_end": last_id,
            "parent_count": parent_count,
            "boundary_metadata": {
                "first_token_id": first_id,
                "first_pdb_id": first_pdb,
                "last_token_id": last_id,
                "last_pdb_id": last_pdb,
            },
        },
        "rng": {
            "seed_derivation": "keccak256(bytes.fromhex(evm_block_hash(B_seed)))",
            "draw_algorithm": "SHA-256 counter-mode rejection sampling without replacement v1",
            "ordering": "numeric NFT ID ascending",
        },
        "reconstruction": {
            "metadata_function": "getMetadata(uint256)",
            "metadata_selector": metadata_selector,
            "combined_data_function": "getCombinedData(uint256)",
            "combined_data_selector": combined_selector,
            "pipeline": [
                "eth_call getMetadata(token_id) at B_pin",
                "derive PDB ID directly from contract metadata",
                "eth_call getCombinedData(token_id) at B_pin",
                "ABI decode",
                "base64 decode",
                "gzip decompress if flagged",
                "BinaryCIF parse",
            ],
        },
        "fidelity": {
            "canonical_source": "https://models.rcsb.org/<PDB_ID>.bcif",
            "loss_model": "lossless BinaryCIF payload",
            "coordinate_tolerance_angstrom": 0.000001,
            "atom_order_normalization": "canonical atom key sort v1",
        },
        "environment": {
            "requirements_lock": "requirements.lock",
            "requirements_lock_sha256": base.sha256_file(lock),
        },
        "rpc_endpoint_selected_at_announcement": client.active_url,
        "latest_evm_height_observed_at_announcement": latest,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base.stable_json(spec))


def run_capture(
    repo: pathlib.Path,
    spec_path: pathlib.Path,
    precommit_sha: str,
    output_root: pathlib.Path,
    workers: int,
) -> pathlib.Path:
    started = utc_now()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    existing, _ = base.load_existing_context(repo)
    rpc_candidates = [spec.get("rpc_endpoint_selected_at_announcement"), base.find_rpc(existing)] + base.DEFAULT_RPC_CANDIDATES
    client = base.RpcClient([url for url in rpc_candidates if url], timeout=120.0)
    chain_id = base.decode_uint(client.call("eth_chainId", []))
    if chain_id != int(spec["evm_chain_id"]):
        raise base.EvidenceError(f"chain ID mismatch: spec {spec['evm_chain_id']}, RPC {chain_id}")
    latest = base.decode_uint(client.call("eth_blockNumber", []))
    if latest < int(spec["B_seed"]):
        raise base.EvidenceError(f"seed block is not yet available: current {latest}, B_seed {spec['B_seed']}")

    seed_block_raw = client.raw("eth_getBlockByNumber", [base.hex_quantity(int(spec["B_seed"])), False])
    seed_block = seed_block_raw.response.get("result")
    if not seed_block:
        raise base.EvidenceError("could not retrieve B_seed block")
    block_hash = str(seed_block["hash"])
    seed = base.keccak256(bytes.fromhex(block_hash.removeprefix("0x")))

    b_pin = int(spec["B_pin"])
    pin_block_raw = client.raw("eth_getBlockByNumber", [base.hex_quantity(b_pin), False])
    pin_block = pin_block_raw.response.get("result")
    if not pin_block:
        raise base.EvidenceError("could not retrieve B_pin block")

    directory = output_root / f"block-{b_pin}"
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    shutil.copy2(spec_path, directory / "sample-spec.json")
    base.save_rpc(directory / "raw" / "seed", "B-seed-block", seed_block_raw)
    base.save_rpc(directory / "raw" / "seed", "B-pin-block", pin_block_raw)
    base.write_json(
        directory / "seed-derivation.json",
        {
            "schema": "org.genesisl1.molnft_seed_derivation.v1",
            "sample_spec_precommit_sha": precommit_sha,
            "B_pin": b_pin,
            "B_pin_block_hash": pin_block["hash"],
            "B_seed": int(spec["B_seed"]),
            "B_seed_block_hash": block_hash,
            "derived_seed_hex": "0x" + seed.hex(),
            "derivation": "keccak256(bytes.fromhex(evm_block_hash(B_seed)))",
        },
    )

    enumeration = spec["id_enumeration"]
    first_id = int(enumeration["parent_id_start"])
    last_id = int(enumeration["parent_id_end"])
    expected_count = int(enumeration["parent_count"])
    next_value, counter_raw = query_uint(
        client,
        spec["contract_address"],
        enumeration["parent_counter_selector"],
        b_pin,
    )
    base.save_rpc(directory / "raw" / "enumeration", "nextNFTId", counter_raw)
    if next_value != int(enumeration["parent_counter_value"]):
        raise base.EvidenceError(
            f"pinned nextNFTId changed: spec={enumeration['parent_counter_value']} observed={next_value}"
        )
    if last_id - first_id + 1 != expected_count or last_id != next_value - 1:
        raise base.EvidenceError("sample specification contains an inconsistent parent NFT-ID range")

    write_direct_enumeration(directory / "parent-id-enumeration.csv.gz", first_id, last_id)
    enum_meta = {
        "method": "direct_contract_parent_nft_id_range",
        "off_chain_index_used": False,
        "parent_counter_function": "nextNFTId()",
        "parent_counter_value": next_value,
        "parent_id_start": first_id,
        "parent_id_end": last_id,
        "enumerated_parent_count": expected_count,
    }
    base.write_json(directory / "enumeration-method.json", enum_meta)

    drawn_token_ids = direct_draw(list(range(first_id, last_id + 1)), seed, int(spec["N"]))
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                capture_direct_record,
                client.active_url,
                spec["contract_address"],
                spec["reconstruction"]["metadata_selector"],
                spec["reconstruction"]["combined_data_selector"],
                b_pin,
                token_id,
                directory,
                float(spec["fidelity"]["coordinate_tolerance_angstrom"]),
            ): (index, token_id)
            for index, token_id in enumerate(drawn_token_ids, 1)
        }
        for future in as_completed(futures):
            index, token_id = futures[future]
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001
                row = {
                    "token_id": token_id,
                    "pdb_id": "UNKNOWN",
                    "outcome": "FAILURE",
                    "reason_code": "UNEXPECTED_ERROR",
                    "reason_detail": f"{type(exc).__name__}: {exc}",
                }
            row["draw_order"] = index
            results.append(row)
    results.sort(key=lambda row: int(row["draw_order"]))

    drawn_rows = [(int(row["token_id"]), str(row.get("pdb_id") or "UNKNOWN")) for row in results]
    base.write_draw(directory / "drawn-ids.csv", drawn_rows)
    base.write_results(directory / "results.csv", results)

    reason_counts = Counter(str(row["reason_code"]) for row in results)
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
        "enumerated_parent_count": expected_count,
        "enumeration_method": enum_meta,
        "direct_nft_id_queries": True,
        "off_chain_index_used": False,
        "successes": sum(row["outcome"] == "SUCCESS" for row in results),
        "failures": sum(row["outcome"] != "SUCCESS" for row in results),
        "failures_by_reason": dict(sorted((key, value) for key, value in reason_counts.items() if key != "SUCCESS")),
        "fidelity_passes": sum(bool(row.get("fidelity_pass")) for row in results),
        "byte_identical_records": sum(bool(row.get("byte_identical")) for row in results),
        "coordinate_tolerance_angstrom": spec["fidelity"]["coordinate_tolerance_angstrom"],
        "loss_model": spec["fidelity"]["loss_model"],
        "rpc_endpoint": client.active_url,
        "rpc_provider": "public GenesisL1 EVM JSON-RPC",
        "canonical_endpoint": base.RCSB_BCIF,
        "wall_clock_start_utc": started,
        "wall_clock_end_utc": utc_now(),
        "environment": base.environment(),
        "requirements_lock_sha256": base.sha256_file(repo / "requirements.lock"),
    }
    base.write_json(directory / "summary.json", summary)
    base.integrity(directory, {"precommit_sha": precommit_sha, "seed_block_hash": block_hash})
    return directory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--prepare-spec", type=pathlib.Path)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed-delay", type=int, default=30)
    parser.add_argument("--spec", type=pathlib.Path)
    parser.add_argument("--precommit-sha")
    parser.add_argument("--output-root", type=pathlib.Path, default=pathlib.Path("evidence/article-02/molnft"))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--recompute", type=pathlib.Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    if args.prepare_spec:
        prepare_spec(repo, args.prepare_spec, args.n, args.seed_delay)
        return 0
    if args.recompute:
        base.recompute(args.recompute.resolve())
        return 0
    if not args.spec or not args.precommit_sha:
        parser.error("capture requires --spec and --precommit-sha")
    output = run_capture(repo, args.spec.resolve(), args.precommit_sha, args.output_root.resolve(), args.workers)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
