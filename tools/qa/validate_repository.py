#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def verify_checksums(directory: Path) -> None:
    checksum_file = directory / "SHA256SUMS.txt"
    check(checksum_file.exists(), f"missing checksums: {directory}")
    if not checksum_file.exists():
        return
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = directory / relative
        check(path.exists(), f"checksum target missing: {path.relative_to(ROOT)}")
        if path.exists():
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            check(actual == expected, f"checksum mismatch: {path.relative_to(ROOT)}")


for path in ROOT.rglob("*"):
    if path.is_file():
        check(path.suffix not in {".pyc", ".pyo"}, f"compiled Python artifact: {path.relative_to(ROOT)}")
        check("__pycache__" not in path.parts, f"Python cache: {path.relative_to(ROOT)}")

article_path = ROOT / "site/insights/genesisl1-decentralization-scientific-renaissance.html"
article = article_path.read_text(encoding="utf-8")
state_path = ROOT / "content/article-02-next-verifiable-renaissance/network-state.json"
check(state_path.exists(), "current network-state facts file missing")
state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
current_snapshot = ROOT / state.get("snapshot_relative_path", "__missing__")

check("github.com/GenesisL1/web3desk" not in article, "article still cites web3desk")
check("https://explorer.genesisl1.org/validators" in article, "validator explorer link missing")
check("genesisl1-token-distribution-no-insider-allocation.html" not in [p.name for p in (ROOT / "site/insights").glob("*.html")], "obsolete article file present")
check(state.get("snapshot_url", "__missing__") in article, "article does not cite the current network-state snapshot")
check(state.get("pinned_height_display", "__missing__") in article, "article does not contain the current pinned height")
check(f"20 → {state.get('active_validators')}" in article, "article fact strip has stale active-set data")
check(f"51.07 → {state.get('top5_share_percent')}%" in article, "article fact strip has stale top-five data")
check(state.get("bonded_stake_display", "__missing__") in article, "article does not contain current bonded stake")
check(f"{int(state.get('unique_active_delegators', -1)):,}" in article, "article does not contain current delegator count")
check(not re.search(r"\b\d+\.\d{3,}%", article), "machine precision percentage leaked into publication article")
check(not re.search(r"[−+]\d+\.\d{3,} points", article), "false-precision delta leaked into publication article")

for name in [
    "genesisl1-scientific-renaissance-hero",
    "genesisl1-l1-utility-layer",
    "genesisl1-consensus-widening",
    "genesisl1-press-patron-public-record",
    "genesisl1-institutional-sovereignty",
    "genesisl1-institutional-stewardship",
    "genesisl1-scientific-renaissance-card",
    "genesisl1-scientific-renaissance-social-1200x630",
]:
    check((ROOT / f"content/article-02-next-verifiable-renaissance/figures/{name}.svg").exists(), f"missing source SVG {name}")
    check((ROOT / f"site/insights/assets/{name}.svg").exists(), f"missing site SVG {name}")
    check((ROOT / f"site/insights/assets/{name}.png").exists(), f"missing site PNG {name}")

for evidence in [
    current_snapshot,
    ROOT / "evidence/article-02/consensus/block-13412747",
    ROOT / "evidence/article-02/molnft/block-13412747",
]:
    check((evidence / "snapshot.json").exists(), f"missing snapshot: {evidence}")
    verify_checksums(evidence)

for required in ["validators.csv", "delegations.csv", "delegators.csv", "raw/lcd-staking-pool.json"]:
    check((current_snapshot / required).exists(), f"missing current network-state file: {required}")

if (current_snapshot / "snapshot.json").exists():
    snapshot = json.loads((current_snapshot / "snapshot.json").read_text(encoding="utf-8"))
    check(snapshot.get("metadata", {}).get("schema") == "org.genesisl1.network_state_snapshot.v3", "unexpected current snapshot schema")
    check(snapshot.get("metadata", {}).get("pinned_height") == state.get("pinned_height"), "facts/snapshot height mismatch")
    consensus = snapshot.get("metrics", {}).get("consensus", {})
    staking = snapshot.get("metrics", {}).get("staking", {})
    delegation = snapshot.get("metrics", {}).get("delegation", {})
    check(consensus.get("active_consensus_validators") == state.get("active_validators"), "facts/snapshot active-validator mismatch")
    check(staking.get("pool_bonded_tokens_l1") == state.get("bonded_stake_l1"), "facts/snapshot bonded-stake mismatch")
    check(delegation.get("unique_delegators_to_active_validators") == state.get("unique_active_delegators"), "facts/snapshot delegator-count mismatch")
    with (current_snapshot / "validators.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    active_rows = [row for row in rows if row["status"] == "BOND_STATUS_BONDED"]
    check(len(active_rows) == state.get("active_validators"), "active validator CSV count mismatch")

if errors:
    print("\n".join("FAIL: " + error for error in errors), file=sys.stderr)
    raise SystemExit(1)
print("repository QA passed")
