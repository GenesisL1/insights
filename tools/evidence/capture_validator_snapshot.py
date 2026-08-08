#!/usr/bin/env python3
"""Capture a cryptographically reproducible GenesisL1 consensus snapshot.

The capture is pinned to one finalized block height. It preserves the exact raw
JSON bytes returned by CometBFT and Cosmos REST endpoints, calculates metrics
from CometBFT voting power, emits ranked CSV/Markdown/JSON results, and writes
SHA-256 checksums. Only the Python standard library is required.

Examples:
    python scripts/capture_validator_snapshot.py
    python scripts/capture_validator_snapshot.py --height 13412747
    python scripts/capture_validator_snapshot.py --output-root evidence/snapshots
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Any, Iterable

getcontext().prec = 80

CHAIN_ID = "genesis_29-2"
USER_AGENT = "GenesisL1-Decentralization-Snapshot/2.1 (+https://genesisl1.com/)"
PROVIDERS = [
    {"name": "ANODE.TEAM", "rpc": "https://genesisl1.rpc.m.anode.team", "rest": "https://genesisl1.api.m.anode.team"},
    {"name": "GenesisL1 public", "rpc": "https://26657.genesisl1.org", "rest": "https://1317.genesisl1.org"},
    {"name": "UTSA", "rpc": "https://m-l1.rpc.utsa.tech", "rest": "https://m-l1.api.utsa.tech"},
]


@dataclass(frozen=True)
class Response:
    url: str
    raw: bytes
    payload: Any
    headers: dict[str, str]


@dataclass(frozen=True)
class Row:
    rank: int
    moniker: str
    operator_address: str
    consensus_address: str
    consensus_pubkey_b64: str
    voting_power: int
    share: Decimal
    cumulative_share: Decimal
    tokens_atomic: int | None
    commission_rate: str
    website: str


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch(url: str, *, headers: dict[str, str] | None, timeout: float, retries: int) -> Response:
    all_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        all_headers.update(headers)
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=all_headers)
            with urllib.request.urlopen(req, timeout=timeout) as reply:
                raw = reply.read()
                return Response(url, raw, json.loads(raw.decode("utf-8")), {k.lower(): v for k, v in reply.headers.items()})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    assert last is not None
    raise last


def write_raw(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: pathlib.Path, value: Any) -> None:
    write_raw(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def pubkey_from_staking(value: dict[str, Any]) -> str:
    pk = value.get("consensus_pubkey") or {}
    return str(pk.get("key") or pk.get("value") or pk.get("ed25519") or "")


def pubkey_from_comet(value: dict[str, Any]) -> str:
    pk = value.get("pub_key") or {}
    return str(pk.get("value") or pk.get("key") or "")


def percent(value: Decimal, places: int = 8) -> str:
    return f"{value * Decimal(100):.{places}f}".rstrip("0").rstrip(".")


def threshold(powers: list[int], numerator: int, denominator: int, strict: bool) -> int | None:
    total = sum(powers)
    running = 0
    for index, power in enumerate(powers, 1):
        running += power
        left = running * denominator
        right = total * numerator
        if (left > right) if strict else (left >= right):
            return index
    return None


def gini(values: list[int]) -> Decimal:
    if not values or not sum(values):
        return Decimal(0)
    ordered = sorted(values)
    n = len(ordered)
    numerator = sum((2 * i - n - 1) * value for i, value in enumerate(ordered, 1))
    return Decimal(numerator) / Decimal(n * sum(ordered))


def entropy(shares: Iterable[Decimal]) -> Decimal:
    numbers = [float(x) for x in shares if x > 0]
    if len(numbers) <= 1:
        return Decimal(0)
    return Decimal(str(-sum(p * math.log(p) for p in numbers) / math.log(len(numbers))))


def get_status(rpc: str, raw_dir: pathlib.Path, timeout: float, retries: int) -> tuple[int, str, str, str]:
    response = fetch(f"{rpc}/status", headers=None, timeout=timeout, retries=retries)
    write_raw(raw_dir / "rpc-status.json", response.raw)
    result = response.payload["result"]
    sync = result["sync_info"]
    node = result["node_info"]
    return int(sync["latest_block_height"]), str(sync.get("latest_block_time", "")), str(node.get("network", "")), str(node.get("version", ""))


def get_block(rpc: str, height: int, raw_dir: pathlib.Path, timeout: float, retries: int) -> tuple[str, str, str]:
    response = fetch(f"{rpc}/block?height={height}", headers=None, timeout=timeout, retries=retries)
    write_raw(raw_dir / "rpc-block.json", response.raw)
    result = response.payload["result"]
    header = result["block"]["header"]
    returned = int(header["height"])
    if returned != height:
        raise RuntimeError(f"RPC returned block {returned}, requested {height}")
    return str(header.get("time", "")), str((result.get("block_id") or {}).get("hash", "")), str(header.get("app_hash", ""))


def get_comet_validators(rpc: str, height: int, raw_dir: pathlib.Path, timeout: float, retries: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"height": height, "page": page, "per_page": 100})
        response = fetch(f"{rpc}/validators?{query}", headers=None, timeout=timeout, retries=retries)
        write_raw(raw_dir / f"rpc-validators-page-{page}.json", response.raw)
        result = response.payload.get("result") or {}
        batch = result.get("validators") or []
        rows.extend(batch)
        total = int(result.get("total") or len(rows))
        pages.append({"page": page, "url": response.url, "count": len(batch), "total": total})
        if len(rows) >= total or not batch:
            return rows, pages
        page += 1
        if page > 100:
            raise RuntimeError("CometBFT pagination exceeded 100 pages")


def get_staking_validators(rest: str, height: int, raw_dir: pathlib.Path, timeout: float, retries: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    key = ""
    page = 1
    while True:
        params = {"status": "BOND_STATUS_BONDED", "pagination.limit": "200", "pagination.count_total": "true"}
        if key:
            params["pagination.key"] = key
        response = fetch(
            f"{rest}/cosmos/staking/v1beta1/validators?{urllib.parse.urlencode(params)}",
            headers={"x-cosmos-block-height": str(height)}, timeout=timeout, retries=retries,
        )
        observed = response.headers.get("x-cosmos-block-height")
        if observed is not None and int(observed) != height:
            raise RuntimeError(f"REST height mismatch: requested {height}, received {observed}")
        write_raw(raw_dir / f"lcd-staking-validators-page-{page}.json", response.raw)
        batch = response.payload.get("validators") or []
        rows.extend(batch)
        pagination = response.payload.get("pagination") or {}
        key = pagination.get("next_key") or ""
        pages.append({
            "page": page, "url": response.url, "count": len(batch),
            "pagination_total": pagination.get("total"), "response_height_header": observed,
        })
        if not key:
            return rows, pages
        page += 1
        if page > 100:
            raise RuntimeError("REST pagination exceeded 100 pages")


def get_staking_params(rest: str, height: int, raw_dir: pathlib.Path, timeout: float, retries: int) -> tuple[dict[str, Any], str | None]:
    response = fetch(
        f"{rest}/cosmos/staking/v1beta1/params",
        headers={"x-cosmos-block-height": str(height)}, timeout=timeout, retries=retries,
    )
    observed = response.headers.get("x-cosmos-block-height")
    if observed is not None and int(observed) != height:
        raise RuntimeError(f"Staking params height mismatch: requested {height}, received {observed}")
    write_raw(raw_dir / "lcd-staking-params.json", response.raw)
    return response.payload.get("params") or {}, observed


def merge_rows(comet: list[dict[str, Any]], staking: list[dict[str, Any]]) -> tuple[list[Row], dict[str, int]]:
    by_key = {pubkey_from_staking(item): item for item in staking if pubkey_from_staking(item)}
    temp: list[dict[str, Any]] = []
    matched = 0
    for item in comet:
        key = pubkey_from_comet(item)
        meta = by_key.get(key)
        if meta is not None:
            matched += 1
        description = (meta or {}).get("description") or {}
        commission = (((meta or {}).get("commission") or {}).get("commission_rates") or {}).get("rate") or ""
        tokens = int(meta["tokens"]) if meta is not None and meta.get("tokens") is not None else None
        temp.append({
            "moniker": str(description.get("moniker") or "Unmatched consensus validator"),
            "operator_address": str((meta or {}).get("operator_address") or ""),
            "consensus_address": str(item.get("address") or ""),
            "consensus_pubkey_b64": key,
            "voting_power": int(item.get("voting_power") or 0),
            "tokens_atomic": tokens,
            "commission_rate": str(commission),
            "website": str(description.get("website") or ""),
        })
    temp.sort(key=lambda x: (-x["voting_power"], x["consensus_address"]))
    total = sum(x["voting_power"] for x in temp)
    if total <= 0:
        raise RuntimeError("Total voting power is zero")
    running = Decimal(0)
    result: list[Row] = []
    for rank, item in enumerate(temp, 1):
        share = Decimal(item["voting_power"]) / Decimal(total)
        running += share
        result.append(Row(rank=rank, share=share, cumulative_share=running, **item))
    return result, {
        "consensus_validator_count": len(comet),
        "staking_bonded_validator_count": len(staking),
        "matched_by_consensus_pubkey": matched,
        "unmatched_consensus_validators": len(comet) - matched,
        "unused_staking_records": len(staking) - matched,
    }


def metrics(rows: list[Row], max_validators: int | None) -> dict[str, Any]:
    powers = [row.voting_power for row in rows]
    shares = [row.share for row in rows]
    total = sum(powers)
    hhi = sum((share * share for share in shares), Decimal(0))
    top = lambda n: sum(shares[:n], Decimal(0))
    return {
        "basis": "CometBFT validator-set voting_power at the pinned height",
        "active_consensus_validators": len(rows),
        "protocol_max_validators": max_validators,
        "active_set_utilization_percent": percent(Decimal(len(rows)) / Decimal(max_validators), 4) if max_validators else None,
        "total_consensus_voting_power": str(total),
        "largest_validator_share_percent": percent(top(1)),
        "top_3_share_percent": percent(top(3)),
        "top_5_share_percent": percent(top(5)),
        "top_10_share_percent": percent(top(10)),
        "coefficient_at_or_above_one_third": threshold(powers, 1, 3, False),
        "coefficient_strictly_above_one_third": threshold(powers, 1, 3, True),
        "coefficient_at_or_above_two_thirds": threshold(powers, 2, 3, False),
        "coefficient_strictly_above_two_thirds": threshold(powers, 2, 3, True),
        "hhi_fraction": format(hhi, "f"),
        "hhi_10000": format(hhi * Decimal(10000), "f"),
        "effective_validator_count": format(Decimal(1) / hhi, "f"),
        "gini_coefficient": format(gini(powers), "f"),
        "normalized_entropy": format(entropy(shares), "f"),
    }


def write_csv(path: pathlib.Path, rows: list[Row]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "rank", "moniker", "operator_address", "consensus_address", "consensus_pubkey_b64",
            "voting_power", "share_percent", "cumulative_share_percent", "tokens_atomic",
            "commission_rate", "website",
        ])
        for row in rows:
            writer.writerow([
                row.rank, row.moniker, row.operator_address, row.consensus_address, row.consensus_pubkey_b64,
                row.voting_power, percent(row.share), percent(row.cumulative_share),
                row.tokens_atomic if row.tokens_atomic is not None else "", row.commission_rate, row.website,
            ])


def write_report(path: pathlib.Path, snapshot: dict[str, Any], rows: list[Row]) -> None:
    meta, value = snapshot["metadata"], snapshot["metrics"]
    def short(number: str, places: int) -> str:
        return f"{Decimal(number):.{places}f}"
    lines = [
        "# GenesisL1 decentralization snapshot", "",
        f"**Pinned block:** `{meta['pinned_height']}`  ",
        f"**Block time:** `{meta['block_time_utc']}`  ",
        f"**Captured:** `{meta['captured_at_utc']}`  ",
        f"**Block hash:** `{meta['block_hash']}`  ",
        f"**Provider:** `{meta['provider_name']}`", "",
        "## Exact results", "", "| Metric | Result |", "|---|---:|",
        f"| Active consensus validators | **{value['active_consensus_validators']}** |",
        f"| Protocol maximum | **{value['protocol_max_validators']}** |",
        f"| Largest validator | **{value['largest_validator_share_percent']}%** |",
        f"| Top 3 | **{value['top_3_share_percent']}%** |",
        f"| Top 5 | **{value['top_5_share_percent']}%** |",
        f"| Top 10 | **{value['top_10_share_percent']}%** |",
        f"| One-third coefficient (≥ 1/3) | **{value['coefficient_at_or_above_one_third']}** |",
        f"| One-third coefficient (> 1/3) | **{value['coefficient_strictly_above_one_third']}** |",
        f"| Two-thirds coefficient (≥ 2/3) | **{value['coefficient_at_or_above_two_thirds']}** |",
        f"| Two-thirds coefficient (> 2/3) | **{value['coefficient_strictly_above_two_thirds']}** |",
        f"| HHI (0–10,000) | **{short(value['hhi_10000'], 2)}** |",
        f"| Effective validator count | **{short(value['effective_validator_count'], 2)}** |",
        f"| Gini coefficient | **{short(value['gini_coefficient'], 4)}** |",
        f"| Normalized entropy | **{short(value['normalized_entropy'], 4)}** |", "",
        "## Ranked validator set", "", "| Rank | Validator | Voting power | Share | Cumulative |", "|---:|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(f"| {row.rank} | {row.moniker.replace('|', '\\|')} | {row.voting_power:,} | {percent(row.share)}% | {percent(row.cumulative_share)}% |")
    lines += [
        "", "## Threshold interpretation", "",
        "CometBFT commits a block with **more than two-thirds** of voting power. The one-third coefficient is therefore principally a liveness measure: a coordinated cohort at or above one-third can leave the remainder unable to exceed two-thirds. It cannot, by itself, supply the signatures required to commit arbitrary state. The two-thirds coefficient is the smallest leading cohort whose cumulative voting power strictly exceeds the commit threshold.", "",
        "Validator entries prove on-chain voting-power distribution. They do not, by themselves, prove independent beneficial ownership, signing-key custody, hosting provider, jurisdiction or operational control.", "",
        "## Reproduce", "", "```bash", "python scripts/capture_validator_snapshot.py", "cd decentralization/latest && sha256sum -c SHA256SUMS.txt", "```", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checksums(directory: pathlib.Path) -> None:
    files = sorted(p for p in directory.rglob("*") if p.is_file() and p.name not in {"SHA256SUMS.txt", "MANIFEST.json"})
    rows, manifest = [], []
    for path in files:
        rel = path.relative_to(directory).as_posix()
        value = digest(path)
        rows.append(f"{value}  {rel}")
        manifest.append({"path": rel, "bytes": path.stat().st_size, "sha256": value})
    (directory / "SHA256SUMS.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    write_json(directory / "MANIFEST.json", {"algorithm": "SHA-256", "files": manifest})


def capture(provider: dict[str, str], args: argparse.Namespace, stage: pathlib.Path) -> dict[str, Any]:
    rpc, rest = provider["rpc"].rstrip("/"), provider["rest"].rstrip("/")
    raw_dir = stage / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    tip, tip_time, network, version = get_status(rpc, raw_dir, args.timeout, args.retries)
    if network != CHAIN_ID:
        raise RuntimeError(f"Unexpected chain ID: {network}")
    height = args.height if args.height else tip - args.lag_blocks
    block_time, block_hash, app_hash = get_block(rpc, height, raw_dir, args.timeout, args.retries)
    comet, comet_pages = get_comet_validators(rpc, height, raw_dir, args.timeout, args.retries)
    staking, rest_pages = get_staking_validators(rest, height, raw_dir, args.timeout, args.retries)
    params, params_height = get_staking_params(rest, height, raw_dir, args.timeout, args.retries)
    rows, matching = merge_rows(comet, staking)
    maximum = int(params["max_validators"]) if params.get("max_validators") is not None else None
    result = {
        "metadata": {
            "schema": "org.genesisl1.decentralization_snapshot.v2",
            "network": "GenesisL1", "chain_id": CHAIN_ID,
            "provider_name": provider["name"], "rpc_endpoint": rpc, "rest_endpoint": rest,
            "captured_at_utc": utc_now(), "rpc_latest_height_at_start": tip,
            "rpc_latest_time_at_start": tip_time, "pinned_height": height,
            "lag_blocks_from_rpc_tip": tip - height, "block_time_utc": block_time,
            "block_hash": block_hash, "app_hash": app_hash, "cometbft_version": version,
            "height_verification": {
                "rpc_block_height": height,
                "rest_validator_page_headers": [page["response_height_header"] for page in rest_pages],
                "rest_params_height_header": params_height,
            },
            "raw_rpc_validator_pages": comet_pages, "raw_rest_validator_pages": rest_pages,
            "matching": matching, "methodology_version": "2.1.0",
        },
        "metrics": metrics(rows, maximum),
    }
    write_json(stage / "snapshot.json", result)
    write_csv(stage / "validators.csv", rows)
    write_report(stage / "README.md", result, rows)
    checksums(stage)
    return result


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="decentralization/snapshots")
    parser.add_argument("--latest-dir", default="decentralization/latest")
    parser.add_argument("--height", type=int)
    parser.add_argument("--lag-blocks", type=int, default=2)
    parser.add_argument("--rpc")
    parser.add_argument("--rest")
    parser.add_argument("--provider-name", default="custom")
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--no-latest", action="store_true")
    value = parser.parse_args(argv)
    if bool(value.rpc) != bool(value.rest):
        parser.error("--rpc and --rest must be supplied together")
    return value


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv or sys.argv[1:])
    providers = [{"name": args.provider_name, "rpc": args.rpc, "rest": args.rest}] if args.rpc else PROVIDERS
    root = pathlib.Path(args.output_root)
    root.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    for provider in providers:
        stage = root / f".capture-{int(time.time())}"
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        try:
            result = capture(provider, args, stage)
            meta = result["metadata"]
            stamp = str(meta["block_time_utc"]).replace("-", "").replace(":", "").replace(".", "")
            final = root / f"height-{meta['pinned_height']}-{stamp}"
            shutil.rmtree(final, ignore_errors=True)
            stage.rename(final)
            if not args.no_latest:
                latest = pathlib.Path(args.latest_dir)
                shutil.rmtree(latest, ignore_errors=True)
                shutil.copytree(final, latest)
            print(json.dumps(result, indent=2))
            print(f"\nSnapshot: {final}")
            return 0
        except Exception as exc:  # provider fallback is deliberate
            errors.append({"provider": provider["name"], "type": type(exc).__name__, "message": str(exc)})
            shutil.rmtree(stage, ignore_errors=True)
    print(json.dumps({"captured_at_utc": utc_now(), "failures": errors}, indent=2), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
