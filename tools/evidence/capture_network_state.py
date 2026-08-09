#!/usr/bin/env python3
"""Capture a reproducible GenesisL1 network-state snapshot.

The snapshot is pinned to one finalized block height and combines:

* the exact CometBFT active validator set and voting power;
* Cosmos staking validator records across bonded, unbonding and unbonded states;
* every delegation relationship returned for every registered validator;
* staking-pool and native-supply state;
* validator, delegator and stake concentration metrics;
* raw JSON responses, CSV exports, a manifest and SHA-256 checksums.

Only the Python standard library is required.
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
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Any, Iterable

getcontext().prec = 90

CHAIN_ID = "genesis_29-2"
BOND_DENOM = "el1"
DISPLAY_DENOM = "L1"
DISPLAY_DECIMALS = 18
POWER_REDUCTION = 10**18
USER_AGENT = "GenesisL1-Network-State-Snapshot/3.0 (+https://genesisl1.com/)"
PROVIDERS = [
    {
        "name": "ANODE.TEAM",
        "rpc": "https://genesisl1.rpc.m.anode.team",
        "rest": "https://genesisl1.api.m.anode.team",
    },
    {
        "name": "GenesisL1 public",
        "rpc": "https://26657.genesisl1.org",
        "rest": "https://1317.genesisl1.org",
    },
    {
        "name": "UTSA",
        "rpc": "https://m-l1.rpc.utsa.tech",
        "rest": "https://m-l1.api.utsa.tech",
    },
]
STATUSES = (
    "BOND_STATUS_BONDED",
    "BOND_STATUS_UNBONDING",
    "BOND_STATUS_UNBONDED",
)


@dataclass(frozen=True)
class HttpResult:
    url: str
    raw: bytes
    payload: Any
    headers: dict[str, str]
    status: int


@dataclass(frozen=True)
class ValidatorRow:
    consensus_rank: int | None
    moniker: str
    operator_address: str
    consensus_address: str
    consensus_pubkey_b64: str
    status: str
    jailed: bool
    voting_power: int
    voting_power_share: Decimal
    cumulative_voting_power_share: Decimal
    tokens_atomic: int
    delegator_shares: str
    commission_rate: str
    website: str
    delegation_relationships: int
    delegated_balance_atomic: int


@dataclass(frozen=True)
class DelegationRow:
    delegator_address: str
    validator_operator_address: str
    validator_moniker: str
    validator_status: str
    validator_jailed: bool
    balance_atomic: int
    shares: str


@dataclass(frozen=True)
class DelegatorRow:
    rank_by_bonded_stake: int | None
    delegator_address: str
    bonded_amount_atomic: int
    nonbonded_amount_atomic: int
    total_amount_atomic: int
    active_validator_count: int
    all_validator_count: int


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    retries: int = 3,
) -> HttpResult:
    req_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return HttpResult(
                    url=url,
                    raw=raw,
                    payload=json.loads(raw.decode("utf-8")),
                    headers={key.lower(): value for key, value in response.headers.items()},
                    status=int(response.status),
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    assert last is not None
    raise last


def write_bytes(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    write_bytes(path, canonical_json_bytes(payload))


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_to_display(value: int, places: int = 6) -> str:
    amount = Decimal(value) / (Decimal(10) ** DISPLAY_DECIMALS)
    quant = Decimal(1).scaleb(-places)
    return format(amount.quantize(quant, rounding=ROUND_HALF_UP), f".{places}f")


def percent_fraction(value: Decimal, places: int = 8) -> str:
    return f"{value * Decimal(100):.{places}f}".rstrip("0").rstrip(".")


def percent_ratio(numerator: int, denominator: int, places: int = 8) -> str | None:
    if denominator == 0:
        return None
    return percent_fraction(Decimal(numerator) / Decimal(denominator), places)


def threshold_coefficient(values: list[int], *, numerator: int, denominator: int, strict: bool) -> int | None:
    total = sum(values)
    if total <= 0:
        return None
    cumulative = 0
    for index, value in enumerate(values, 1):
        cumulative += value
        left = cumulative * denominator
        right = total * numerator
        if (left > right) if strict else (left >= right):
            return index
    return None


def gini(values: list[int]) -> Decimal:
    positive = sorted(value for value in values if value > 0)
    if not positive:
        return Decimal(0)
    n = len(positive)
    total = sum(positive)
    numerator = sum((2 * index - n - 1) * value for index, value in enumerate(positive, 1))
    return Decimal(numerator) / Decimal(n * total)


def normalized_entropy(shares: Iterable[Decimal]) -> Decimal:
    values = [float(value) for value in shares if value > 0]
    if len(values) <= 1:
        return Decimal(0)
    entropy = -sum(value * math.log(value) for value in values)
    return Decimal(str(entropy / math.log(len(values))))


def concentration_metrics(values: list[int], prefix: str) -> dict[str, Any]:
    positive = sorted((value for value in values if value > 0), reverse=True)
    total = sum(positive)
    if total <= 0:
        return {
            f"{prefix}_count": 0,
            f"{prefix}_total_atomic": "0",
        }
    shares = [Decimal(value) / Decimal(total) for value in positive]
    hhi = sum((share * share for share in shares), Decimal(0))

    def top(count: int) -> str:
        return percent_fraction(sum(shares[:count], Decimal(0)))

    return {
        f"{prefix}_count": len(positive),
        f"{prefix}_total_atomic": str(total),
        f"{prefix}_largest_share_percent": top(1),
        f"{prefix}_top_3_share_percent": top(3),
        f"{prefix}_top_5_share_percent": top(5),
        f"{prefix}_top_10_share_percent": top(10),
        f"{prefix}_top_25_share_percent": top(25),
        f"{prefix}_coefficient_at_or_above_one_third": threshold_coefficient(
            positive, numerator=1, denominator=3, strict=False
        ),
        f"{prefix}_coefficient_strictly_above_one_third": threshold_coefficient(
            positive, numerator=1, denominator=3, strict=True
        ),
        f"{prefix}_coefficient_at_or_above_two_thirds": threshold_coefficient(
            positive, numerator=2, denominator=3, strict=False
        ),
        f"{prefix}_coefficient_strictly_above_two_thirds": threshold_coefficient(
            positive, numerator=2, denominator=3, strict=True
        ),
        f"{prefix}_hhi_fraction": format(hhi, "f"),
        f"{prefix}_hhi_10000": format(hhi * Decimal(10000), "f"),
        f"{prefix}_effective_count": format(Decimal(1) / hhi, "f"),
        f"{prefix}_gini_coefficient": format(gini(positive), "f"),
        f"{prefix}_normalized_entropy": format(normalized_entropy(shares), "f"),
    }


def consensus_pubkey_b64(staking_validator: dict[str, Any]) -> str:
    pubkey = staking_validator.get("consensus_pubkey") or {}
    return str(pubkey.get("key") or pubkey.get("value") or pubkey.get("ed25519") or "")


def comet_pubkey_b64(consensus_validator: dict[str, Any]) -> str:
    pubkey = consensus_validator.get("pub_key") or {}
    return str(pubkey.get("value") or pubkey.get("key") or "")


def verify_response_height(result: HttpResult, requested_height: int) -> str | None:
    observed = result.headers.get("x-cosmos-block-height")
    if observed is not None and int(observed) != requested_height:
        raise RuntimeError(f"REST height mismatch: requested {requested_height}, received {observed}")
    return observed


def fetch_status(rpc: str, raw_dir: pathlib.Path, timeout: float, retries: int) -> tuple[int, str, str, str]:
    result = request(f"{rpc}/status", timeout=timeout, retries=retries)
    write_bytes(raw_dir / "rpc-status.json", result.raw)
    body = result.payload["result"]
    sync = body["sync_info"]
    node = body["node_info"]
    return (
        int(sync["latest_block_height"]),
        str(sync.get("latest_block_time", "")),
        str(node.get("network", "")),
        str(node.get("version", "")),
    )


def fetch_block(
    rpc: str,
    height: int,
    raw_dir: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[str, str, str]:
    result = request(f"{rpc}/block?height={height}", timeout=timeout, retries=retries)
    write_bytes(raw_dir / "rpc-block.json", result.raw)
    body = result.payload["result"]
    header = body["block"]["header"]
    returned_height = int(header["height"])
    if returned_height != height:
        raise RuntimeError(f"RPC returned block {returned_height}, requested {height}")
    return (
        str(header.get("time", "")),
        str((body.get("block_id") or {}).get("hash", "")),
        str(header.get("app_hash", "")),
    )


def fetch_comet_validators(
    rpc: str,
    height: int,
    raw_dir: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"height": height, "page": page, "per_page": 100})
        result = request(f"{rpc}/validators?{query}", timeout=timeout, retries=retries)
        write_bytes(raw_dir / f"rpc-validators-page-{page}.json", result.raw)
        body = result.payload.get("result") or {}
        batch = body.get("validators") or []
        rows.extend(batch)
        total = int(body.get("total") or len(rows))
        pages.append({"page": page, "url": result.url, "count": len(batch), "total": total})
        if len(rows) >= total or not batch:
            return rows, pages
        page += 1
        if page > 100:
            raise RuntimeError("CometBFT validator pagination exceeded 100 pages")


def fetch_staking_validators_for_status(
    rest: str,
    height: int,
    status: str,
    raw_dir: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    key = ""
    page = 1
    status_slug = status.removeprefix("BOND_STATUS_").lower()
    while True:
        params: dict[str, str] = {
            "status": status,
            "pagination.limit": "200",
            "pagination.count_total": "true",
        }
        if key:
            params["pagination.key"] = key
        url = f"{rest}/cosmos/staking/v1beta1/validators?{urllib.parse.urlencode(params)}"
        result = request(
            url,
            headers={"x-cosmos-block-height": str(height)},
            timeout=timeout,
            retries=retries,
        )
        observed = verify_response_height(result, height)
        write_bytes(raw_dir / f"lcd-staking-validators-{status_slug}-page-{page}.json", result.raw)
        batch = result.payload.get("validators") or []
        rows.extend(batch)
        pagination = result.payload.get("pagination") or {}
        key = pagination.get("next_key") or ""
        pages.append(
            {
                "status": status,
                "page": page,
                "url": url,
                "count": len(batch),
                "pagination_total": pagination.get("total"),
                "response_height_header": observed,
            }
        )
        if not key:
            return rows, pages
        page += 1
        if page > 100:
            raise RuntimeError(f"Staking validator pagination exceeded 100 pages for {status}")


def fetch_all_staking_validators(
    rest: str,
    height: int,
    raw_dir: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_operator: dict[str, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    for status in STATUSES:
        rows, status_pages = fetch_staking_validators_for_status(
            rest, height, status, raw_dir, timeout, retries
        )
        pages.extend(status_pages)
        for row in rows:
            operator = str(row.get("operator_address") or "")
            if not operator:
                raise RuntimeError(f"Validator without operator address in {status}")
            previous = by_operator.get(operator)
            if previous is not None and previous != row:
                raise RuntimeError(f"Conflicting validator records for {operator}")
            by_operator[operator] = row
    return list(by_operator.values()), pages


def fetch_simple_rest(
    rest: str,
    height: int,
    endpoint: str,
    raw_path: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[HttpResult, str | None]:
    result = request(
        f"{rest}{endpoint}",
        headers={"x-cosmos-block-height": str(height)},
        timeout=timeout,
        retries=retries,
    )
    observed = verify_response_height(result, height)
    write_bytes(raw_path, result.raw)
    return result, observed


def fetch_supply(
    rest: str,
    height: int,
    raw_dir: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[int, str | None, str]:
    endpoints = [
        f"/cosmos/bank/v1beta1/supply/by_denom?{urllib.parse.urlencode({'denom': BOND_DENOM})}",
        f"/cosmos/bank/v1beta1/supply/{BOND_DENOM}",
    ]
    failures: list[str] = []
    for index, endpoint in enumerate(endpoints, 1):
        try:
            result, observed = fetch_simple_rest(
                rest,
                height,
                endpoint,
                raw_dir / f"lcd-bank-supply-attempt-{index}.json",
                timeout,
                retries,
            )
            amount = result.payload.get("amount")
            if isinstance(amount, dict):
                if amount.get("denom") != BOND_DENOM:
                    raise RuntimeError(f"Unexpected supply denom: {amount.get('denom')}")
                return int(amount["amount"]), observed, endpoint
            supplies = result.payload.get("supply") or []
            for coin in supplies:
                if coin.get("denom") == BOND_DENOM:
                    return int(coin["amount"]), observed, endpoint
            raise RuntimeError("Supply response did not contain the bond denom")
        except Exception as exc:
            failures.append(f"{endpoint}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(failures))


def fetch_validator_delegations(
    rest: str,
    height: int,
    validator: dict[str, Any],
    ordinal: int,
    raw_dir: pathlib.Path,
    timeout: float,
    retries: int,
) -> tuple[list[DelegationRow], list[dict[str, Any]]]:
    operator = str(validator["operator_address"])
    description = validator.get("description") or {}
    moniker = str(description.get("moniker") or operator)
    status = str(validator.get("status") or "")
    jailed = bool(validator.get("jailed"))
    rows: list[DelegationRow] = []
    pages: list[dict[str, Any]] = []
    key = ""
    page = 1
    while True:
        params: dict[str, str] = {
            "pagination.limit": "200",
            "pagination.count_total": "true",
        }
        if key:
            params["pagination.key"] = key
        quoted_operator = urllib.parse.quote(operator, safe="")
        url = (
            f"{rest}/cosmos/staking/v1beta1/validators/{quoted_operator}/delegations?"
            f"{urllib.parse.urlencode(params)}"
        )
        result = request(
            url,
            headers={"x-cosmos-block-height": str(height)},
            timeout=timeout,
            retries=retries,
        )
        observed = verify_response_height(result, height)
        folder = raw_dir / "delegations"
        write_bytes(folder / f"{ordinal:03d}-{operator}-page-{page}.json", result.raw)
        batch = result.payload.get("delegation_responses") or []
        for item in batch:
            delegation = item.get("delegation") or {}
            balance = item.get("balance") or {}
            denom = str(balance.get("denom") or "")
            if denom and denom != BOND_DENOM:
                raise RuntimeError(f"Unexpected delegation denom {denom} for {operator}")
            delegator = str(delegation.get("delegator_address") or "")
            if not delegator:
                raise RuntimeError(f"Delegation without delegator address for {operator}")
            rows.append(
                DelegationRow(
                    delegator_address=delegator,
                    validator_operator_address=operator,
                    validator_moniker=moniker,
                    validator_status=status,
                    validator_jailed=jailed,
                    balance_atomic=int(balance.get("amount") or 0),
                    shares=str(delegation.get("shares") or ""),
                )
            )
        pagination = result.payload.get("pagination") or {}
        key = pagination.get("next_key") or ""
        pages.append(
            {
                "validator_operator_address": operator,
                "validator_moniker": moniker,
                "validator_status": status,
                "page": page,
                "url": url,
                "count": len(batch),
                "pagination_total": pagination.get("total"),
                "response_height_header": observed,
            }
        )
        if not key:
            return rows, pages
        page += 1
        if page > 1000:
            raise RuntimeError(f"Delegation pagination exceeded 1000 pages for {operator}")


def build_validator_rows(
    comet_validators: list[dict[str, Any]],
    staking_validators: list[dict[str, Any]],
    delegations: list[DelegationRow],
) -> tuple[list[ValidatorRow], dict[str, Any]]:
    by_pubkey = {
        consensus_pubkey_b64(validator): validator
        for validator in staking_validators
        if consensus_pubkey_b64(validator)
    }
    by_operator_delegations: dict[str, list[DelegationRow]] = defaultdict(list)
    for row in delegations:
        by_operator_delegations[row.validator_operator_address].append(row)

    consensus_items = sorted(
        comet_validators,
        key=lambda item: (-int(item.get("voting_power") or 0), str(item.get("address") or "")),
    )
    total_power = sum(int(item.get("voting_power") or 0) for item in consensus_items)
    if total_power <= 0:
        raise RuntimeError("Total consensus voting power is zero")

    consensus_by_pubkey: dict[str, tuple[int, dict[str, Any], Decimal, Decimal]] = {}
    cumulative = Decimal(0)
    for rank, item in enumerate(consensus_items, 1):
        power = int(item.get("voting_power") or 0)
        share = Decimal(power) / Decimal(total_power)
        cumulative += share
        consensus_by_pubkey[comet_pubkey_b64(item)] = (rank, item, share, cumulative)

    rows: list[ValidatorRow] = []
    matched = 0
    for validator in staking_validators:
        pubkey = consensus_pubkey_b64(validator)
        consensus_match = consensus_by_pubkey.get(pubkey)
        if consensus_match is not None:
            matched += 1
            rank, consensus_item, share, cumulative_share = consensus_match
            voting_power = int(consensus_item.get("voting_power") or 0)
            consensus_address = str(consensus_item.get("address") or "")
        else:
            rank = None
            share = Decimal(0)
            cumulative_share = Decimal(0)
            voting_power = 0
            consensus_address = ""
        operator = str(validator.get("operator_address") or "")
        description = validator.get("description") or {}
        commission = ((validator.get("commission") or {}).get("commission_rates") or {}).get("rate") or ""
        validator_delegations = by_operator_delegations.get(operator, [])
        rows.append(
            ValidatorRow(
                consensus_rank=rank,
                moniker=str(description.get("moniker") or operator),
                operator_address=operator,
                consensus_address=consensus_address,
                consensus_pubkey_b64=pubkey,
                status=str(validator.get("status") or ""),
                jailed=bool(validator.get("jailed")),
                voting_power=voting_power,
                voting_power_share=share,
                cumulative_voting_power_share=cumulative_share,
                tokens_atomic=int(validator.get("tokens") or 0),
                delegator_shares=str(validator.get("delegator_shares") or ""),
                commission_rate=str(commission),
                website=str(description.get("website") or ""),
                delegation_relationships=len(validator_delegations),
                delegated_balance_atomic=sum(row.balance_atomic for row in validator_delegations),
            )
        )

    unmatched_consensus = len(consensus_items) - matched
    if unmatched_consensus:
        missing = [
            comet_pubkey_b64(item)
            for item in consensus_items
            if comet_pubkey_b64(item) not in by_pubkey
        ]
        raise RuntimeError(f"Unmatched consensus validators: {missing}")

    rows.sort(
        key=lambda row: (
            0 if row.status == "BOND_STATUS_BONDED" else 1,
            row.consensus_rank if row.consensus_rank is not None else 10**9,
            -row.tokens_atomic,
            row.operator_address,
        )
    )
    return rows, {
        "consensus_validator_count": len(consensus_items),
        "staking_validator_count_all_statuses": len(staking_validators),
        "matched_consensus_validators_by_pubkey": matched,
        "unmatched_consensus_validators": unmatched_consensus,
    }


def build_delegator_rows(delegations: list[DelegationRow]) -> list[DelegatorRow]:
    aggregate: dict[str, dict[str, Any]] = {}
    for row in delegations:
        state = aggregate.setdefault(
            row.delegator_address,
            {
                "bonded": 0,
                "nonbonded": 0,
                "all_validators": set(),
                "active_validators": set(),
            },
        )
        state["all_validators"].add(row.validator_operator_address)
        if row.validator_status == "BOND_STATUS_BONDED":
            state["bonded"] += row.balance_atomic
            state["active_validators"].add(row.validator_operator_address)
        else:
            state["nonbonded"] += row.balance_atomic

    bonded_order = sorted(
        (
            (address, data)
            for address, data in aggregate.items()
            if int(data["bonded"]) > 0
        ),
        key=lambda item: (-int(item[1]["bonded"]), item[0]),
    )
    rank_by_address = {address: rank for rank, (address, _) in enumerate(bonded_order, 1)}
    rows = [
        DelegatorRow(
            rank_by_bonded_stake=rank_by_address.get(address),
            delegator_address=address,
            bonded_amount_atomic=int(data["bonded"]),
            nonbonded_amount_atomic=int(data["nonbonded"]),
            total_amount_atomic=int(data["bonded"]) + int(data["nonbonded"]),
            active_validator_count=len(data["active_validators"]),
            all_validator_count=len(data["all_validators"]),
        )
        for address, data in aggregate.items()
    ]
    rows.sort(
        key=lambda row: (
            row.rank_by_bonded_stake is None,
            row.rank_by_bonded_stake if row.rank_by_bonded_stake is not None else 10**12,
            -row.total_amount_atomic,
            row.delegator_address,
        )
    )
    return rows


def calculate_metrics(
    validator_rows: list[ValidatorRow],
    delegation_rows: list[DelegationRow],
    delegator_rows: list[DelegatorRow],
    max_validators: int | None,
    pool_bonded: int,
    pool_not_bonded: int,
    total_supply: int,
) -> dict[str, Any]:
    active = [row for row in validator_rows if row.status == "BOND_STATUS_BONDED"]
    active.sort(key=lambda row: row.consensus_rank or 10**9)
    powers = [row.voting_power for row in active]
    power_shares = [row.voting_power_share for row in active]
    power_hhi = sum((share * share for share in power_shares), Decimal(0))

    def power_top(count: int) -> str:
        return percent_fraction(sum(power_shares[:count], Decimal(0)))

    status_counts = {status: sum(row.status == status for row in validator_rows) for status in STATUSES}
    jailed_counts = {status: sum(row.status == status and row.jailed for row in validator_rows) for status in STATUSES}
    validator_tokens = {status: sum(row.tokens_atomic for row in validator_rows if row.status == status) for status in STATUSES}

    active_delegations = [row for row in delegation_rows if row.validator_status == "BOND_STATUS_BONDED"]
    nonbonded_delegations = [row for row in delegation_rows if row.validator_status != "BOND_STATUS_BONDED"]
    active_delegator_amounts = [row.bonded_amount_atomic for row in delegator_rows if row.bonded_amount_atomic > 0]
    all_delegator_amounts = [row.total_amount_atomic for row in delegator_rows if row.total_amount_atomic > 0]

    consensus = {
        "basis": "CometBFT validator-set voting_power at the pinned height",
        "active_consensus_validators": len(active),
        "protocol_max_validators": max_validators,
        "active_set_utilization_percent": (
            percent_fraction(Decimal(len(active)) / Decimal(max_validators), 4)
            if max_validators
            else None
        ),
        "total_consensus_voting_power": str(sum(powers)),
        "largest_validator_share_percent": power_top(1),
        "top_3_share_percent": power_top(3),
        "top_5_share_percent": power_top(5),
        "top_10_share_percent": power_top(10),
        "coefficient_at_or_above_one_third": threshold_coefficient(
            powers, numerator=1, denominator=3, strict=False
        ),
        "coefficient_strictly_above_one_third": threshold_coefficient(
            powers, numerator=1, denominator=3, strict=True
        ),
        "coefficient_at_or_above_two_thirds": threshold_coefficient(
            powers, numerator=2, denominator=3, strict=False
        ),
        "coefficient_strictly_above_two_thirds": threshold_coefficient(
            powers, numerator=2, denominator=3, strict=True
        ),
        "hhi_fraction": format(power_hhi, "f"),
        "hhi_10000": format(power_hhi * Decimal(10000), "f"),
        "effective_validator_count": format(Decimal(1) / power_hhi, "f"),
        "gini_coefficient": format(gini(powers), "f"),
        "normalized_entropy": format(normalized_entropy(power_shares), "f"),
    }

    staking = {
        "bond_denom": BOND_DENOM,
        "display_denom": DISPLAY_DENOM,
        "display_decimals": DISPLAY_DECIMALS,
        "registered_validator_records": len(validator_rows),
        "bonded_validator_records": status_counts["BOND_STATUS_BONDED"],
        "unbonding_validator_records": status_counts["BOND_STATUS_UNBONDING"],
        "unbonded_validator_records": status_counts["BOND_STATUS_UNBONDED"],
        "jailed_bonded_validator_records": jailed_counts["BOND_STATUS_BONDED"],
        "jailed_unbonding_validator_records": jailed_counts["BOND_STATUS_UNBONDING"],
        "jailed_unbonded_validator_records": jailed_counts["BOND_STATUS_UNBONDED"],
        "pool_bonded_tokens_atomic": str(pool_bonded),
        "pool_bonded_tokens_l1": atomic_to_display(pool_bonded),
        "pool_not_bonded_tokens_atomic": str(pool_not_bonded),
        "pool_not_bonded_tokens_l1": atomic_to_display(pool_not_bonded),
        "pool_total_tokens_atomic": str(pool_bonded + pool_not_bonded),
        "pool_total_tokens_l1": atomic_to_display(pool_bonded + pool_not_bonded),
        "total_supply_atomic": str(total_supply),
        "total_supply_l1": atomic_to_display(total_supply),
        "bonded_ratio_total_supply_percent": percent_ratio(pool_bonded, total_supply),
        "bonded_ratio_staking_pool_percent": percent_ratio(pool_bonded, pool_bonded + pool_not_bonded),
        "bonded_validator_tokens_atomic": str(validator_tokens["BOND_STATUS_BONDED"]),
        "unbonding_validator_tokens_atomic": str(validator_tokens["BOND_STATUS_UNBONDING"]),
        "unbonded_validator_tokens_atomic": str(validator_tokens["BOND_STATUS_UNBONDED"]),
    }

    delegation = {
        "all_delegation_relationships": len(delegation_rows),
        "active_delegation_relationships": len(active_delegations),
        "nonbonded_delegation_relationships": len(nonbonded_delegations),
        "unique_delegators_all_statuses": len(delegator_rows),
        "unique_delegators_to_active_validators": sum(row.bonded_amount_atomic > 0 for row in delegator_rows),
        "unique_delegators_only_nonbonded": sum(
            row.bonded_amount_atomic == 0 and row.nonbonded_amount_atomic > 0 for row in delegator_rows
        ),
        "delegators_spread_across_multiple_active_validators": sum(
            row.active_validator_count > 1 for row in delegator_rows
        ),
        "delegated_to_active_validators_atomic": str(sum(row.balance_atomic for row in active_delegations)),
        "delegated_to_active_validators_l1": atomic_to_display(sum(row.balance_atomic for row in active_delegations)),
        "delegated_to_nonbonded_validators_atomic": str(sum(row.balance_atomic for row in nonbonded_delegations)),
        "delegated_to_nonbonded_validators_l1": atomic_to_display(sum(row.balance_atomic for row in nonbonded_delegations)),
        **concentration_metrics(active_delegator_amounts, "active_delegator"),
        **concentration_metrics(all_delegator_amounts, "all_delegator"),
    }

    crosschecks = {
        "pool_bonded_minus_bonded_validator_tokens_atomic": str(
            pool_bonded - validator_tokens["BOND_STATUS_BONDED"]
        ),
        "active_delegation_balances_minus_bonded_validator_tokens_atomic": str(
            sum(row.balance_atomic for row in active_delegations)
            - validator_tokens["BOND_STATUS_BONDED"]
        ),
        "consensus_power_scaled_atomic": str(sum(powers) * POWER_REDUCTION),
        "pool_bonded_minus_consensus_power_scaled_atomic": str(
            pool_bonded - sum(powers) * POWER_REDUCTION
        ),
        "all_delegation_balances_minus_all_validator_tokens_atomic": str(
            sum(row.balance_atomic for row in delegation_rows)
            - sum(row.tokens_atomic for row in validator_rows)
        ),
    }

    return {
        "consensus": consensus,
        "staking": staking,
        "delegation": delegation,
        "crosschecks": crosschecks,
    }


def write_validators_csv(path: pathlib.Path, rows: list[ValidatorRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "consensus_rank",
                "moniker",
                "operator_address",
                "consensus_address",
                "consensus_pubkey_b64",
                "status",
                "jailed",
                "voting_power",
                "voting_power_share_percent",
                "cumulative_voting_power_share_percent",
                "tokens_atomic",
                "tokens_l1",
                "delegator_shares",
                "commission_rate",
                "delegation_relationships",
                "delegated_balance_atomic",
                "delegated_balance_l1",
                "website",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.consensus_rank or "",
                    row.moniker,
                    row.operator_address,
                    row.consensus_address,
                    row.consensus_pubkey_b64,
                    row.status,
                    str(row.jailed).lower(),
                    row.voting_power,
                    percent_fraction(row.voting_power_share),
                    percent_fraction(row.cumulative_voting_power_share),
                    row.tokens_atomic,
                    atomic_to_display(row.tokens_atomic),
                    row.delegator_shares,
                    row.commission_rate,
                    row.delegation_relationships,
                    row.delegated_balance_atomic,
                    atomic_to_display(row.delegated_balance_atomic),
                    row.website,
                ]
            )


def write_delegations_csv(path: pathlib.Path, rows: list[DelegationRow]) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            0 if row.validator_status == "BOND_STATUS_BONDED" else 1,
            row.validator_operator_address,
            -row.balance_atomic,
            row.delegator_address,
        ),
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "delegator_address",
                "validator_operator_address",
                "validator_moniker",
                "validator_status",
                "validator_jailed",
                "balance_atomic",
                "balance_l1",
                "shares",
            ]
        )
        for row in ordered:
            writer.writerow(
                [
                    row.delegator_address,
                    row.validator_operator_address,
                    row.validator_moniker,
                    row.validator_status,
                    str(row.validator_jailed).lower(),
                    row.balance_atomic,
                    atomic_to_display(row.balance_atomic),
                    row.shares,
                ]
            )


def write_delegators_csv(path: pathlib.Path, rows: list[DelegatorRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank_by_bonded_stake",
                "delegator_address",
                "bonded_amount_atomic",
                "bonded_amount_l1",
                "nonbonded_amount_atomic",
                "nonbonded_amount_l1",
                "total_amount_atomic",
                "total_amount_l1",
                "active_validator_count",
                "all_validator_count",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.rank_by_bonded_stake or "",
                    row.delegator_address,
                    row.bonded_amount_atomic,
                    atomic_to_display(row.bonded_amount_atomic),
                    row.nonbonded_amount_atomic,
                    atomic_to_display(row.nonbonded_amount_atomic),
                    row.total_amount_atomic,
                    atomic_to_display(row.total_amount_atomic),
                    row.active_validator_count,
                    row.all_validator_count,
                ]
            )


def fmt_decimal(value: str, places: int) -> str:
    return f"{Decimal(value):.{places}f}"


def write_report(
    path: pathlib.Path,
    snapshot: dict[str, Any],
    validators: list[ValidatorRow],
    delegators: list[DelegatorRow],
) -> None:
    metadata = snapshot["metadata"]
    consensus = snapshot["metrics"]["consensus"]
    staking = snapshot["metrics"]["staking"]
    delegation = snapshot["metrics"]["delegation"]
    crosschecks = snapshot["metrics"]["crosschecks"]
    active = [row for row in validators if row.status == "BOND_STATUS_BONDED"]
    top_delegators = [row for row in delegators if row.rank_by_bonded_stake is not None][:25]

    lines = [
        "# GenesisL1 current network-state snapshot",
        "",
        f"**Pinned block:** `{metadata['pinned_height']}`  ",
        f"**Block time:** `{metadata['block_time_utc']}`  ",
        f"**Captured:** `{metadata['captured_at_utc']}`  ",
        f"**Block hash:** `{metadata['block_hash']}`  ",
        f"**Provider:** `{metadata['provider_name']}`",
        "",
        "This package measures the observable on-chain distribution of active consensus power, registered validator state, delegation relationships and bonded L1 at one block height.",
        "",
        "## Consensus",
        "",
        "| Metric | Exact result |",
        "|---|---:|",
        f"| Active consensus validators | **{consensus['active_consensus_validators']}** |",
        f"| Protocol maximum | **{consensus['protocol_max_validators']}** |",
        f"| Largest validator | **{consensus['largest_validator_share_percent']}%** |",
        f"| Top three | **{consensus['top_3_share_percent']}%** |",
        f"| Top five | **{consensus['top_5_share_percent']}%** |",
        f"| Top ten | **{consensus['top_10_share_percent']}%** |",
        f"| One-third coefficient (≥ 1/3) | **{consensus['coefficient_at_or_above_one_third']}** |",
        f"| One-third coefficient (> 1/3) | **{consensus['coefficient_strictly_above_one_third']}** |",
        f"| Two-thirds coefficient (≥ 2/3) | **{consensus['coefficient_at_or_above_two_thirds']}** |",
        f"| Two-thirds coefficient (> 2/3) | **{consensus['coefficient_strictly_above_two_thirds']}** |",
        f"| HHI (0–10,000) | **{fmt_decimal(consensus['hhi_10000'], 2)}** |",
        f"| Effective validator count | **{fmt_decimal(consensus['effective_validator_count'], 2)}** |",
        f"| Gini coefficient | **{fmt_decimal(consensus['gini_coefficient'], 4)}** |",
        f"| Normalized entropy | **{fmt_decimal(consensus['normalized_entropy'], 4)}** |",
        "",
        "## Stake and delegators",
        "",
        "| Metric | Exact result |",
        "|---|---:|",
        f"| Registered validator records | **{staking['registered_validator_records']}** |",
        f"| Bonded / unbonding / unbonded validators | **{staking['bonded_validator_records']} / {staking['unbonding_validator_records']} / {staking['unbonded_validator_records']}** |",
        f"| Bonded stake | **{staking['pool_bonded_tokens_l1']} L1** |",
        f"| Not-bonded staking-pool tokens | **{staking['pool_not_bonded_tokens_l1']} L1** |",
        f"| Native supply | **{staking['total_supply_l1']} L1** |",
        f"| Bonded / native supply | **{staking['bonded_ratio_total_supply_percent']}%** |",
        f"| Unique delegators to active validators | **{delegation['unique_delegators_to_active_validators']}** |",
        f"| Active delegation relationships | **{delegation['active_delegation_relationships']}** |",
        f"| Delegators using more than one active validator | **{delegation['delegators_spread_across_multiple_active_validators']}** |",
        f"| Largest active delegator share | **{delegation['active_delegator_largest_share_percent']}%** |",
        f"| Top ten active delegator share | **{delegation['active_delegator_top_10_share_percent']}%** |",
        f"| Active-delegator one-third coefficient | **{delegation['active_delegator_coefficient_at_or_above_one_third']}** |",
        f"| Active-delegator strict two-thirds coefficient | **{delegation['active_delegator_coefficient_strictly_above_two_thirds']}** |",
        f"| Effective active delegator count | **{fmt_decimal(delegation['active_delegator_effective_count'], 2)}** |",
        "",
        "## Active validator set",
        "",
        "| Rank | Validator | Voting power | Share | Bonded stake | Delegators |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in active:
        lines.append(
            f"| {row.consensus_rank} | {row.moniker.replace('|', '\\|')} | {row.voting_power:,} | "
            f"{percent_fraction(row.voting_power_share)}% | {atomic_to_display(row.tokens_atomic)} L1 | "
            f"{row.delegation_relationships} |"
        )

    lines.extend(
        [
            "",
            "## Largest bonded delegator addresses",
            "",
            "| Rank | Delegator address | Bonded stake | Active validators |",
            "|---:|---|---:|---:|",
        ]
    )
    for row in top_delegators:
        lines.append(
            f"| {row.rank_by_bonded_stake} | `{row.delegator_address}` | "
            f"{atomic_to_display(row.bonded_amount_atomic)} L1 | {row.active_validator_count} |"
        )

    lines.extend(
        [
            "",
            "## Internal cross-checks",
            "",
            "| Check | Atomic-unit difference |",
            "|---|---:|",
            f"| Staking pool bonded − bonded validator tokens | `{crosschecks['pool_bonded_minus_bonded_validator_tokens_atomic']}` |",
            f"| Active delegation balances − bonded validator tokens | `{crosschecks['active_delegation_balances_minus_bonded_validator_tokens_atomic']}` |",
            f"| Staking pool bonded − scaled consensus voting power | `{crosschecks['pool_bonded_minus_consensus_power_scaled_atomic']}` |",
            f"| All delegation balances − all validator tokens | `{crosschecks['all_delegation_balances_minus_all_validator_tokens_atomic']}` |",
            "",
            "Small nonzero differences can arise from share-to-token rounding at query time. The exact raw state and all derived tables are included so the calculations can be independently repeated.",
            "",
            "## Interpretation",
            "",
            "CometBFT commits a block with **more than two-thirds** of active voting power. The one-third coefficient is principally a liveness measure: a coordinated cohort at or above one-third can leave the remainder unable to exceed two-thirds, but cannot alone finalize arbitrary state.",
            "",
            "Delegator addresses are on-chain accounts, not proven independent people or institutions. Validator names do not establish independent beneficial ownership, key custody, hosting provider, jurisdiction or operational control. The snapshot therefore measures observable ledger distribution, not every social dimension of decentralization.",
            "",
            "## Files",
            "",
            "- `snapshot.json` — metadata, exact metrics and cross-checks.",
            "- `validators.csv` — all registered validator records and active consensus data.",
            "- `delegations.csv` — every returned validator/delegator relationship.",
            "- `delegators.csv` — unique-address aggregation across validators.",
            "- `raw/` — unmodified RPC and REST response bytes.",
            "- `SHA256SUMS.txt` and `MANIFEST.json` — integrity records.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "python tools/evidence/capture_network_state.py --output-root evidence/network-state",
            "cd evidence/network-state/<snapshot-directory>",
            "sha256sum -c SHA256SUMS.txt",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_checksums(directory: pathlib.Path) -> None:
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS.txt", "MANIFEST.json"}
    )
    checksum_rows: list[str] = []
    manifest: list[dict[str, Any]] = []
    for path in files:
        relative = path.relative_to(directory).as_posix()
        digest = sha256(path)
        checksum_rows.append(f"{digest}  {relative}")
        manifest.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest})
    (directory / "SHA256SUMS.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
    write_json(directory / "MANIFEST.json", {"algorithm": "SHA-256", "files": manifest})


def capture(provider: dict[str, str], args: argparse.Namespace, stage: pathlib.Path) -> dict[str, Any]:
    rpc = provider["rpc"].rstrip("/")
    rest = provider["rest"].rstrip("/")
    raw_dir = stage / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    tip_height, tip_time, network, comet_version = fetch_status(
        rpc, raw_dir, args.timeout, args.retries
    )
    if network != CHAIN_ID:
        raise RuntimeError(f"Unexpected chain ID: {network!r}")
    pinned_height = args.height if args.height is not None else tip_height - args.lag_blocks
    if pinned_height <= 0:
        raise RuntimeError("Pinned height must be positive")

    block_time, block_hash, app_hash = fetch_block(
        rpc, pinned_height, raw_dir, args.timeout, args.retries
    )
    comet_validators, comet_pages = fetch_comet_validators(
        rpc, pinned_height, raw_dir, args.timeout, args.retries
    )
    staking_validators, staking_pages = fetch_all_staking_validators(
        rest, pinned_height, raw_dir, args.timeout, args.retries
    )

    params_result, params_height = fetch_simple_rest(
        rest,
        pinned_height,
        "/cosmos/staking/v1beta1/params",
        raw_dir / "lcd-staking-params.json",
        args.timeout,
        args.retries,
    )
    pool_result, pool_height = fetch_simple_rest(
        rest,
        pinned_height,
        "/cosmos/staking/v1beta1/pool",
        raw_dir / "lcd-staking-pool.json",
        args.timeout,
        args.retries,
    )
    total_supply, supply_height, supply_endpoint = fetch_supply(
        rest, pinned_height, raw_dir, args.timeout, args.retries
    )

    delegation_rows: list[DelegationRow] = []
    delegation_pages: list[dict[str, Any]] = []
    sorted_validators = sorted(
        staking_validators,
        key=lambda validator: (
            0 if validator.get("status") == "BOND_STATUS_BONDED" else 1,
            -int(validator.get("tokens") or 0),
            str(validator.get("operator_address") or ""),
        ),
    )
    for ordinal, validator in enumerate(sorted_validators, 1):
        rows, pages = fetch_validator_delegations(
            rest,
            pinned_height,
            validator,
            ordinal,
            raw_dir,
            args.timeout,
            args.retries,
        )
        delegation_rows.extend(rows)
        delegation_pages.extend(pages)

    validator_rows, matching = build_validator_rows(
        comet_validators, staking_validators, delegation_rows
    )
    delegator_rows = build_delegator_rows(delegation_rows)

    params = params_result.payload.get("params") or {}
    pool = pool_result.payload.get("pool") or {}
    max_validators = int(params["max_validators"]) if params.get("max_validators") is not None else None
    pool_bonded = int(pool.get("bonded_tokens") or 0)
    pool_not_bonded = int(pool.get("not_bonded_tokens") or 0)
    computed = calculate_metrics(
        validator_rows,
        delegation_rows,
        delegator_rows,
        max_validators,
        pool_bonded,
        pool_not_bonded,
        total_supply,
    )

    metadata = {
        "schema": "org.genesisl1.network_state_snapshot.v3",
        "network": "GenesisL1",
        "chain_id": CHAIN_ID,
        "provider_name": provider["name"],
        "rpc_endpoint": rpc,
        "rest_endpoint": rest,
        "captured_at_utc": utc_now(),
        "rpc_latest_height_at_start": tip_height,
        "rpc_latest_time_at_start": tip_time,
        "pinned_height": pinned_height,
        "lag_blocks_from_rpc_tip": tip_height - pinned_height,
        "block_time_utc": block_time,
        "block_hash": block_hash,
        "app_hash": app_hash,
        "cometbft_version": comet_version,
        "request_height_verification": {
            "rpc_block_height": pinned_height,
            "rest_validator_page_headers": [page["response_height_header"] for page in staking_pages],
            "rest_delegation_page_headers": [page["response_height_header"] for page in delegation_pages],
            "rest_params_height_header": params_height,
            "rest_pool_height_header": pool_height,
            "rest_supply_height_header": supply_height,
            "rest_supply_endpoint": supply_endpoint,
        },
        "raw_rpc_validator_pages": comet_pages,
        "raw_rest_validator_pages": staking_pages,
        "raw_rest_delegation_pages": delegation_pages,
        "matching": matching,
        "methodology_version": "3.0.0",
    }
    snapshot = {"metadata": metadata, "metrics": computed}
    write_json(stage / "snapshot.json", snapshot)
    write_validators_csv(stage / "validators.csv", validator_rows)
    write_delegations_csv(stage / "delegations.csv", delegation_rows)
    write_delegators_csv(stage / "delegators.csv", delegator_rows)
    write_report(stage / "README.md", snapshot, validator_rows, delegator_rows)
    write_checksums(stage)
    return snapshot


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="evidence/network-state")
    parser.add_argument("--latest-pointer", default="", help="Optional JSON pointer file to the completed snapshot")
    parser.add_argument("--height", type=int)
    parser.add_argument("--lag-blocks", type=int, default=2)
    parser.add_argument("--rpc")
    parser.add_argument("--rest")
    parser.add_argument("--provider-name", default="custom")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args(argv)
    if bool(args.rpc) != bool(args.rest):
        parser.error("--rpc and --rest must be supplied together")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    providers = (
        [{"name": args.provider_name, "rpc": args.rpc, "rest": args.rest}]
        if args.rpc
        else PROVIDERS
    )
    output_root = pathlib.Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []

    for provider in providers:
        stage = output_root / f".capture-{int(time.time())}"
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        try:
            snapshot = capture(provider, args, stage)
            metadata = snapshot["metadata"]
            stamp = (
                str(metadata["block_time_utc"])
                .replace("-", "")
                .replace(":", "")
                .replace(".", "")
            )
            final = output_root / f"block-{metadata['pinned_height']}-{stamp}"
            shutil.rmtree(final, ignore_errors=True)
            stage.rename(final)
            if args.latest_pointer:
                pointer = pathlib.Path(args.latest_pointer)
                write_json(
                    pointer,
                    {
                        "schema": "org.genesisl1.network_state_latest_pointer.v1",
                        "pinned_height": metadata["pinned_height"],
                        "block_time_utc": metadata["block_time_utc"],
                        "block_hash": metadata["block_hash"],
                        "snapshot_directory": final.name,
                        "snapshot_relative_path": final.as_posix(),
                        "snapshot_sha256": sha256(final / "snapshot.json"),
                        "captured_at_utc": metadata["captured_at_utc"],
                    },
                )
            print(json.dumps(snapshot, indent=2))
            print(f"\nSnapshot: {final}")
            return 0
        except Exception as exc:
            failures.append(
                {
                    "provider": provider["name"],
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            shutil.rmtree(stage, ignore_errors=True)

    print(json.dumps({"captured_at_utc": utc_now(), "failures": failures}, indent=2), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
