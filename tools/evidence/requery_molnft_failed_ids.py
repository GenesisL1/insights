#!/usr/bin/env python3
"""Requery only failed direct-ID MOLNFT draws through the requested RPCA URLs.

The randomized draw is immutable. This command reads the existing results table,
selects only rows that are not successful, and retries those same NFT IDs. It
never draws replacement IDs and it never queries successful sample rows.

Two exact URLs are recorded:

* https://rpca.genesisl1.org — GenesisL1 EVM JSON-RPC;
* https://rpca.genesisl1.org/api — probed exactly as requested and retained even
  when it is not a JSON-RPC route.

For an ``out of gas`` default ``eth_call``, the same contract call is retried at
the same pinned block with an explicit call-gas allowance. Complete serialized
file equality is not evaluated. Reconstructed and canonical SHA-256 values are
preserved independently as integrity identifiers only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import requests

V2_PATH = pathlib.Path(__file__).with_name("capture_molnft_direct_randomized_sample_v2.py")
MODULE_SPEC = importlib.util.spec_from_file_location("genesisl1_ws1_direct_v2_requery", V2_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"could not load {V2_PATH}")
v2 = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = v2
MODULE_SPEC.loader.exec_module(v2)
base = v2.direct.base

ROOT_ENDPOINT = "https://rpca.genesisl1.org"
API_ENDPOINT = "https://rpca.genesisl1.org/api"
REQUESTED_ENDPOINTS = [ROOT_ENDPOINT, API_ENDPOINT]
GAS_OVERRIDE = "0x7fffffffffffffff"
SCHEMA = "org.genesisl1.molnft_targeted_requery.v1"
USER_AGENT = "GenesisL1-Insights-MOLNFT-targeted-requery/1.0"


class RequeryError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def call_data(selector: str, token_id: int) -> str:
    return selector + token_id.to_bytes(32, "big").hex()


def endpoint_slug(url: str) -> str:
    return url.removeprefix("https://").replace("/", "__")


@dataclass
class RpcObservation:
    url: str
    request: dict[str, Any]
    http_status: int | None
    headers: dict[str, str]
    body: bytes
    parsed: Any | None
    transport_error: str | None

    @property
    def error_message(self) -> str | None:
        if not isinstance(self.parsed, dict):
            return None
        error = self.parsed.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if error is not None:
            return str(error)
        return None

    @property
    def result(self) -> str | None:
        if isinstance(self.parsed, dict) and isinstance(self.parsed.get("result"), str):
            return self.parsed["result"]
        return None

    def compact(self) -> dict[str, Any]:
        result = self.result
        payload: dict[str, Any] = {
            "url": self.url,
            "http_status": self.http_status,
            "response_bytes": len(self.body),
            "response_sha256": sha256_bytes(self.body),
            "transport_error": self.transport_error,
            "error_message": self.error_message,
            "json_response": isinstance(self.parsed, (dict, list)),
        }
        if result is not None:
            payload["result_hex_characters"] = len(result)
        return payload


def post_rpc(
    session: requests.Session,
    url: str,
    payload: dict[str, Any],
    directory: pathlib.Path,
    label: str,
    timeout: float = 300.0,
) -> RpcObservation:
    directory.mkdir(parents=True, exist_ok=True)
    base.write_json(directory / f"{label}.request.json", {"url": url, "request": payload})
    status: int | None = None
    headers: dict[str, str] = {}
    body = b""
    parsed: Any | None = None
    transport_error: str | None = None
    try:
        response = session.post(url, data=json.dumps(payload, separators=(",", ":")), timeout=timeout)
        status = response.status_code
        headers = {key.lower(): value for key, value in response.headers.items()}
        body = response.content
    except Exception as exc:  # noqa: BLE001
        transport_error = f"{type(exc).__name__}: {exc}"

    if body:
        try:
            parsed = json.loads(body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            parsed = None

    response_suffix = "json" if parsed is not None else "txt"
    (directory / f"{label}.response.{response_suffix}").write_bytes(body)
    meta: dict[str, Any] = {
        "url": url,
        "http_status": status,
        "headers": headers,
        "bytes": len(body),
        "sha256": sha256_bytes(body),
        "transport_error": transport_error,
        "json_decoded": parsed is not None,
    }
    if isinstance(parsed, dict):
        if isinstance(parsed.get("error"), dict):
            meta["rpc_error"] = parsed["error"]
        if isinstance(parsed.get("result"), str):
            meta["result_hex_characters"] = len(parsed["result"])
    elif body:
        meta["response_preview"] = body[:500].decode("utf-8", "replace")
    base.write_json(directory / f"{label}.response.meta.json", meta)
    return RpcObservation(url, payload, status, headers, body, parsed, transport_error)


def rpc_payload(request_id: int, method: str, params: list[Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


def decode_metadata(result_hex: str) -> dict[str, Any]:
    try:
        decoded = base.abi_decode(["string"] * 11, bytes.fromhex(result_hex.removeprefix("0x")))
    except Exception as exc:  # noqa: BLE001
        raise RequeryError(f"could not decode getMetadata response: {type(exc).__name__}: {exc}") from exc
    return {
        "idcode": str(decoded[0]).strip().upper(),
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


def existing_structure_metadata(directory: pathlib.Path, token_id: int, pdb_id: str) -> dict[str, Any]:
    path = directory / "raw" / f"{pdb_id}-token-{token_id}" / "metadata-decoded.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_fetch(session: requests.Session, pdb_id: str, destination: pathlib.Path, record_dir: pathlib.Path) -> dict[str, Any]:
    url = base.RCSB_BCIF.format(pdb_id=pdb_id.lower())
    started = utc_now()
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    response.raise_for_status()
    data = response.content
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    result = {
        "url": url,
        "retrieved_at_utc": started,
        "status_code": response.status_code,
        "headers": {key.lower(): value for key, value in response.headers.items()},
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }
    base.write_json(record_dir / "canonical-fetch.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=pathlib.Path)
    args = parser.parse_args()
    directory = args.evidence.resolve()

    spec = json.loads((directory / "sample-spec.json").read_text(encoding="utf-8"))
    previous_summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    rows = read_csv(directory / "results.csv")
    failures = [row for row in rows if row.get("outcome") != "SUCCESS"]
    if not failures:
        raise RequeryError("results.csv contains no failed rows; targeted requery would query nothing")

    selected: list[dict[str, Any]] = []
    for row in failures:
        token_id = int(row["token_id"])
        pdb_id = str(row["pdb_id"]).upper()
        selected.append(
            {
                "draw_order": int(row["draw_order"]),
                "token_id": token_id,
                "pdb_id": pdb_id,
                "original_reason_code": row.get("reason_code"),
                "original_reason_detail": row.get("reason_detail"),
                "structure": existing_structure_metadata(directory, token_id, pdb_id),
            }
        )

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    contract = str(spec["contract_address"])
    height = base.hex_quantity(int(spec["B_pin"]))
    metadata_selector = str(spec["reconstruction"]["metadata_selector"])
    combined_selector = str(spec["reconstruction"]["combined_data_selector"])
    request_id = 0

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "performed_at_utc": utc_now(),
        "pinned_height": int(spec["B_pin"]),
        "contract_address": contract,
        "requested_endpoints": REQUESTED_ENDPOINTS,
        "gas_override": GAS_OVERRIDE,
        "selection_source": "failed rows in the pre-existing randomized results.csv",
        "initial_sample_size": int(previous_summary["N"]),
        "initial_successes": int(previous_summary["successes"]),
        "initial_failures": int(previous_summary["failures"]),
        "initial_failures_by_reason": previous_summary.get("failures_by_reason") or {},
        "queried_failed_records": selected,
        "queried_token_ids": [item["token_id"] for item in selected],
        "replacement_draws": 0,
        "successful_requeries": 0,
        "endpoint_observations": {},
        "record_results": [],
    }

    for endpoint in REQUESTED_ENDPOINTS:
        request_id += 1
        observation = post_rpc(
            session,
            endpoint,
            rpc_payload(request_id, "eth_chainId", []),
            directory / "raw" / "targeted-requery" / endpoint_slug(endpoint),
            "eth-chain-id",
            timeout=30,
        )
        chain_id: int | None = None
        if observation.result and observation.result.startswith("0x"):
            chain_id = int(observation.result, 16)
        report["endpoint_observations"][endpoint] = {
            "chain_id": chain_id,
            "probe": observation.compact(),
            "classification": (
                "GenesisL1 EVM JSON-RPC"
                if chain_id == int(spec["evm_chain_id"])
                else "not a working GenesisL1 EVM JSON-RPC route"
            ),
        }

    if report["endpoint_observations"][ROOT_ENDPOINT]["chain_id"] != int(spec["evm_chain_id"]):
        raise RequeryError(f"{ROOT_ENDPOINT} did not report GenesisL1 EVM chain ID {spec['evm_chain_id']}")

    for item in selected:
        token_id = int(item["token_id"])
        pdb_id = str(item["pdb_id"])
        raw_root = directory / "raw" / f"{pdb_id}-token-{token_id}" / "targeted-requery"
        record_report: dict[str, Any] = {
            "draw_order": item["draw_order"],
            "token_id": token_id,
            "pdb_id": pdb_id,
            "structure": item["structure"],
            "original_failure": {
                "reason_code": item["original_reason_code"],
                "reason_detail": item["original_reason_detail"],
            },
            "endpoint_calls": {},
            "replacement_draw": False,
            "final_reconstruction": None,
        }

        for endpoint in REQUESTED_ENDPOINTS:
            endpoint_dir = raw_root / endpoint_slug(endpoint)
            request_id += 1
            metadata = post_rpc(
                session,
                endpoint,
                rpc_payload(
                    request_id,
                    "eth_call",
                    [{"to": contract, "data": call_data(metadata_selector, token_id)}, height],
                ),
                endpoint_dir,
                "getMetadata-default",
            )
            request_id += 1
            combined_default = post_rpc(
                session,
                endpoint,
                rpc_payload(
                    request_id,
                    "eth_call",
                    [{"to": contract, "data": call_data(combined_selector, token_id)}, height],
                ),
                endpoint_dir,
                "getCombinedData-default",
            )
            endpoint_result: dict[str, Any] = {
                "metadata": metadata.compact(),
                "combined_default": combined_default.compact(),
            }

            if endpoint == ROOT_ENDPOINT:
                if not metadata.result:
                    raise RequeryError(f"{pdb_id} token {token_id}: root RPCA metadata call failed")
                decoded_metadata = decode_metadata(metadata.result)
                base.write_json(endpoint_dir / "metadata-decoded.json", decoded_metadata)
                if decoded_metadata["idcode"] != pdb_id:
                    raise RequeryError(
                        f"token {token_id}: expected PDB {pdb_id}, root RPCA returned {decoded_metadata['idcode']}"
                    )

                request_id += 1
                combined_high_gas = post_rpc(
                    session,
                    endpoint,
                    rpc_payload(
                        request_id,
                        "eth_call",
                        [
                            {
                                "to": contract,
                                "data": call_data(combined_selector, token_id),
                                "gas": GAS_OVERRIDE,
                            },
                            height,
                        ],
                    ),
                    endpoint_dir,
                    "getCombinedData-explicit-gas",
                )
                endpoint_result["combined_explicit_gas"] = combined_high_gas.compact()
                if not combined_high_gas.result:
                    raise RequeryError(
                        f"{pdb_id} token {token_id}: explicit-gas root RPCA call failed: "
                        f"{combined_high_gas.error_message or combined_high_gas.transport_error}"
                    )
                reconstructed = base.reconstruct_payload(combined_high_gas.result)
                reconstructed_path = directory / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif"
                reconstructed_path.parent.mkdir(parents=True, exist_ok=True)
                reconstructed_path.write_bytes(reconstructed)
                canonical_path = directory / "canonical" / f"{pdb_id}.bcif"
                canonical = canonical_fetch(session, pdb_id, canonical_path, endpoint_dir)
                record_report["final_reconstruction"] = {
                    "endpoint": endpoint,
                    "block": int(spec["B_pin"]),
                    "gas_override": GAS_OVERRIDE,
                    "reconstructed_path": reconstructed_path.relative_to(directory).as_posix(),
                    "reconstructed_bytes": len(reconstructed),
                    "reconstructed_sha256": sha256_bytes(reconstructed),
                    "canonical_path": canonical_path.relative_to(directory).as_posix(),
                    "canonical_bytes": canonical["bytes"],
                    "canonical_sha256": canonical["sha256"],
                    "serialized_hashes_are_integrity_identifiers_only": True,
                }
                report["successful_requeries"] += 1

            record_report["endpoint_calls"][endpoint] = endpoint_result

        report["record_results"].append(record_report)

    if report["successful_requeries"] != len(selected):
        raise RequeryError(
            f"only {report['successful_requeries']} of {len(selected)} failed records were reconstructed"
        )

    base.write_json(directory / "targeted-requery.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
