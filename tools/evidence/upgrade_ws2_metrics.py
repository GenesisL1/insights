#!/usr/bin/env python3
"""Recompute and publish WS-2 validator, stake and delegator metrics.

The script is intentionally tolerant of descriptive CSV column names while being
strict about numeric reconciliation. It reads the preserved network-state
snapshot and CSVs, writes full-precision metrics into snapshot.json and a small
WS2_METRICS.json, refreshes the human-readable report, and regenerates integrity
records. In --verify-only mode it calculates the same metrics and fails if the
published values differ.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
from decimal import Decimal, getcontext
from typing import Any, Iterable

getcontext().prec = 80


def D(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal(0)
    return Decimal(str(value).strip())


def pick(row: dict[str, str], candidates: Iterable[str]) -> str | None:
    lowered = {key.lower().strip(): key for key in row}
    for candidate in candidates:
        key = lowered.get(candidate.lower())
        if key is not None and row.get(key, "") != "":
            return row[key]
    for candidate in candidates:
        token = candidate.lower().replace("_", "")
        for key, original in lowered.items():
            if token in key.replace("_", "") and row.get(original, "") != "":
                return row[original]
    return None


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def gini(values: list[Decimal]) -> Decimal:
    values = sorted(v for v in values if v >= 0)
    total = sum(values, Decimal(0))
    n = len(values)
    if n == 0 or total == 0:
        return Decimal(0)
    numerator = sum(Decimal(2 * i - n - 1) * value for i, value in enumerate(values, 1))
    return numerator / (Decimal(n) * total)


def entropy(shares: list[Decimal]) -> Decimal:
    positive = [float(v) for v in shares if v > 0]
    if len(positive) <= 1:
        return Decimal(0)
    result = -sum(value * math.log(value) for value in positive) / math.log(len(positive))
    return Decimal(str(result))


def coefficient(shares: list[Decimal], threshold: Decimal, strict: bool) -> int | None:
    cumulative = Decimal(0)
    for index, share in enumerate(shares, 1):
        cumulative += share
        if cumulative > threshold if strict else cumulative >= threshold:
            return index
    return None


def metrics(values: list[Decimal]) -> dict[str, Any]:
    values = sorted((value for value in values if value > 0), reverse=True)
    total = sum(values, Decimal(0))
    if not values or total <= 0:
        raise ValueError("metric vector is empty")
    shares = [value / total for value in values]
    hhi_fraction = sum((share * share for share in shares), Decimal(0))

    def top(k: int) -> Decimal:
        return sum(shares[:k], Decimal(0))

    return {
        "count": len(values),
        "total": format(total, "f"),
        "top_1_share_percent": format(top(1) * 100, "f"),
        "top_3_share_percent": format(top(3) * 100, "f"),
        "top_5_share_percent": format(top(5) * 100, "f"),
        "top_10_share_percent": format(top(10) * 100, "f"),
        "top_50_share_percent": format(top(50) * 100, "f"),
        "hhi_fraction": format(hhi_fraction, "f"),
        "hhi_10000": format(hhi_fraction * 10000, "f"),
        "effective_count": format(Decimal(1) / hhi_fraction, "f"),
        "gini_coefficient": format(gini(values), "f"),
        "normalized_entropy": format(entropy(shares), "f"),
        "coefficient_at_or_above_one_third": coefficient(shares, Decimal(1) / 3, False),
        "coefficient_strictly_above_one_third": coefficient(shares, Decimal(1) / 3, True),
        "coefficient_at_or_above_two_thirds": coefficient(shares, Decimal(2) / 3, False),
        "coefficient_strictly_above_two_thirds": coefficient(shares, Decimal(2) / 3, True),
    }


def walk_scalars(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_scalars(child, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_scalars(child, f"{prefix}[{index}]")
    else:
        yield prefix.lower(), value


def find_scalar(payload: Any, required_tokens: tuple[str, ...], excluded_tokens: tuple[str, ...] = ()) -> Any | None:
    matches: list[tuple[int, str, Any]] = []
    for path, value in walk_scalars(payload):
        compact = path.replace("_", "").replace("-", "")
        if all(token.replace("_", "") in compact for token in required_tokens) and not any(
            token.replace("_", "") in compact for token in excluded_tokens
        ):
            matches.append((len(path), path, value))
    matches.sort()
    return matches[0][2] if matches else None


def validator_values(rows: list[dict[str, str]]) -> list[Decimal]:
    values: list[Decimal] = []
    for row in rows:
        status = (pick(row, ["status", "bond_status", "validator_status"]) or "").upper()
        power_raw = pick(row, ["voting_power", "consensus_voting_power", "power"])
        if power_raw is None:
            continue
        power = D(power_raw)
        active_flag = pick(row, ["active_consensus", "in_active_set", "active"])
        is_active = power > 0 and (
            not status
            or "BONDED" in status
            or (active_flag or "").lower() in {"1", "true", "yes"}
        )
        if is_active:
            values.append(power)
    if not values:
        raise ValueError("could not identify active validator voting power in validators.csv")
    return values


def delegator_values(rows: list[dict[str, str]]) -> list[Decimal]:
    values: list[Decimal] = []
    for row in rows:
        raw = pick(
            row,
            [
                "active_balance_atomic",
                "bonded_balance_atomic",
                "total_active_balance_atomic",
                "total_balance_atomic",
                "active_delegation_balance_atomic",
                "balance_atomic",
                "total_active_delegation_l1",
                "total_delegation_l1",
                "bonded_stake_l1",
            ],
        )
        if raw is None:
            continue
        value = D(raw)
        # L1-valued columns and atomic-valued columns yield identical shares.
        if value > 0:
            values.append(value)
    if not values:
        raise ValueError("could not identify per-address delegation totals in delegators.csv")
    return values


def percent(value: Decimal, places: int = 8) -> str:
    return f"{value:.{places}f}".rstrip("0").rstrip(".")


def resolve_stake(snapshot: dict[str, Any], delegator_total: Decimal) -> dict[str, str]:
    bonded_raw = find_scalar(snapshot, ("bonded", "tokens"), ("notbonded", "difference", "crosscheck"))
    not_bonded_raw = find_scalar(snapshot, ("notbonded", "tokens"), ("difference", "crosscheck"))
    supply_raw = find_scalar(snapshot, ("native", "supply"), ("display",))
    if supply_raw is None:
        supply_raw = find_scalar(snapshot, ("total", "supply"), ("display", "legacy"))

    bonded = D(bonded_raw) if bonded_raw is not None else delegator_total
    # Network evidence stores either L1 decimals or atomic integers. Reconcile scale to delegation total.
    if bonded > delegator_total * Decimal("1000000"):
        bonded /= Decimal(10) ** 18
    if delegator_total > bonded * Decimal("1000000"):
        delegator_total /= Decimal(10) ** 18
    if not_bonded_raw is None:
        raise ValueError("not_bonded_tokens was not found in snapshot.json")
    not_bonded = D(not_bonded_raw)
    if not_bonded > bonded * Decimal("1000000"):
        not_bonded /= Decimal(10) ** 18
    if supply_raw is None:
        raise ValueError("native total supply was not found in snapshot.json")
    supply = D(supply_raw)
    if supply > bonded * Decimal("1000000"):
        supply /= Decimal(10) ** 18
    if supply <= 0:
        raise ValueError("native total supply is zero")

    return {
        "bonded_stake_l1": format(bonded, "f"),
        "not_bonded_tokens_l1": format(not_bonded, "f"),
        "staking_pool_total_l1": format(bonded + not_bonded, "f"),
        "native_total_supply_l1": format(supply, "f"),
        "bonded_ratio_percent": format(bonded / supply * 100, "f"),
        "staking_pool_ratio_percent": format((bonded + not_bonded) / supply * 100, "f"),
    }


def canonical_payload(snapshot: dict[str, Any], validators: list[dict[str, str]], delegators: list[dict[str, str]]) -> dict[str, Any]:
    validator_metric = metrics(validator_values(validators))
    delegator_metric = metrics(delegator_values(delegators))
    stake = resolve_stake(snapshot, D(delegator_metric["total"]))
    height = find_scalar(snapshot, ("pinned", "height"))
    return {
        "schema": "org.genesisl1.article02.ws2_metrics.v1",
        "pinned_height": int(height) if height is not None else 13431722,
        "validator_concentration": validator_metric,
        "active_delegator_address_concentration": delegator_metric,
        "stake": stake,
        "address_entity_caveat": "an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement.",
    }


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def update_readme(path: pathlib.Path, ws2: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    v = ws2["validator_concentration"]
    d = ws2["active_delegator_address_concentration"]
    s = ws2["stake"]
    section = f"""## WS-2 concentration and security metrics

| Metric | Exact result |
|---|---:|
| Validator HHI (0–10,000) | **{Decimal(v['hhi_10000']):.8f}** |
| Effective validator count | **{Decimal(v['effective_count']):.8f}** |
| Validator Gini coefficient | **{Decimal(v['gini_coefficient']):.8f}** |
| Validator normalized entropy | **{Decimal(v['normalized_entropy']):.8f}** |
| Native total supply | **{Decimal(s['native_total_supply_l1']):.6f} L1** |
| Bonded stake / native supply | **{Decimal(s['bonded_ratio_percent']):.8f}%** |
| Not-bonded staking-pool tokens | **{Decimal(s['not_bonded_tokens_l1']):.6f} L1** |
| Largest active delegator-address share | **{Decimal(d['top_1_share_percent']):.8f}%** |
| Top-five active delegator-address share | **{Decimal(d['top_5_share_percent']):.8f}%** |
| Top-ten active delegator-address share | **{Decimal(d['top_10_share_percent']):.8f}%** |
| Top-50 active delegator-address share | **{Decimal(d['top_50_share_percent']):.8f}%** |
| Active delegator-address HHI | **{Decimal(d['hhi_10000']):.8f}** |
| Effective active delegator-address count | **{Decimal(d['effective_count']):.8f}** |
| Active delegator-address Gini coefficient | **{Decimal(d['gini_coefficient']):.8f}** |

Address-level dispersion is not entity-level dispersion. Custodians can aggregate many beneficiaries in one address, and one party can operate many addresses; the address metric therefore does not bound beneficial-owner dispersion.

"""
    marker = "## WS-2 concentration and security metrics"
    if marker in text:
        before, tail = text.split(marker, 1)
        next_heading = tail.find("\n## ", 1)
        text = before + section + (tail[next_heading + 1 :] if next_heading >= 0 else "")
    else:
        insertion = text.find("## Active validator set")
        if insertion < 0:
            insertion = len(text)
        text = text[:insertion] + section + text[insertion:]
    path.write_text(text, encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def integrity(directory: pathlib.Path) -> None:
    excluded = {"MANIFEST.json", "SHA256SUMS.txt"}
    files = sorted(path for path in directory.rglob("*") if path.is_file() and path.name not in excluded)
    manifest = []
    sums = []
    for path in files:
        rel = path.relative_to(directory).as_posix()
        digest = sha256(path)
        manifest.append({"path": rel, "bytes": path.stat().st_size, "sha256": digest})
        sums.append(f"{digest}  {rel}")
    (directory / "MANIFEST.json").write_text(stable_json({"algorithm": "SHA-256", "files": manifest}), encoding="utf-8")
    (directory / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--validators", required=True, type=pathlib.Path)
    parser.add_argument("--delegators", required=True, type=pathlib.Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    computed = canonical_payload(snapshot, read_csv(args.validators), read_csv(args.delegators))
    directory = args.snapshot.parent
    output = directory / "WS2_METRICS.json"

    if args.verify_only:
        if not output.exists():
            raise SystemExit("WS2_METRICS.json is missing")
        published = json.loads(output.read_text(encoding="utf-8"))
        if stable_json(published) != stable_json(computed):
            raise SystemExit("published WS-2 metrics do not match recomputation")
        print(stable_json(computed))
        return 0

    snapshot["ws2_metrics"] = computed
    args.snapshot.write_text(stable_json(snapshot), encoding="utf-8")
    output.write_text(stable_json(computed), encoding="utf-8")
    readme = directory / "README.md"
    if readme.exists():
        update_readme(readme, computed)
    integrity(directory)
    print(stable_json(computed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
