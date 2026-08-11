#!/usr/bin/env python3
"""Validate the compact current Article 02 publication tree."""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content" / "article-02-next-verifiable-renaissance"
PUBLIC_FILES = [
    ROOT / "README.md",
    CONTENT / "article.md",
    CONTENT / "press-release.md",
    ROOT / "site" / "insights" / "genesisl1-decentralization-scientific-renaissance.html",
    ROOT / "site" / "insights" / "genesisl1-verifiable-ai-sovereign-science-press-release.html",
    ROOT / "site" / "decentralization" / "index.html",
    ROOT / "evidence" / "article-02" / "README.md",
]


def load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value


def words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--molnft", required=True, type=pathlib.Path)
    args = parser.parse_args()

    snapshot = load(args.snapshot)
    molnft = load(args.molnft)
    facts = load(CONTENT / "network-state.json")
    audit = load(ROOT / "evidence" / "article-02" / "molnft" / "block-13436937" / "summary.json")

    height = int(snapshot["metadata"]["pinned_height"])
    height_display = f"{height:,}"
    assert facts["pinned_height"] == height
    assert facts["snapshot_relative_path"] == args.snapshot.resolve().parent.relative_to(ROOT.resolve()).as_posix()
    assert int(molnft["pinned_height"]) == height
    assert int(audit["N"]) == int(audit["successes"]) == int(audit["fidelity_passes"]) == 100
    assert int(audit["failures"]) == 0
    assert audit["failures_by_reason"] == {}

    consensus = snapshot["metrics"]["consensus"]
    staking = snapshot["metrics"]["staking"]
    delegation = snapshot["metrics"]["delegation"]
    assert facts["active_validators"] == int(consensus["active_consensus_validators"])
    assert facts["registered_validators"] == int(staking["registered_validator_records"])
    assert facts["unique_active_delegators"] == int(delegation["active_delegator_count"])
    assert facts["molnft"]["counts"] == molnft["counts"]
    assert int(molnft["counts"]["pdb_v2_parent_records"]) + int(molnft["counts"]["pdb_v2_child_chunks"]) == int(molnft["counts"]["pdb_v2_total_tokens"])

    article = (CONTENT / "article.md").read_text(encoding="utf-8")
    press = (CONTENT / "press-release.md").read_text(encoding="utf-8")
    assert 1500 <= words(article) <= 2400, words(article)
    assert 450 <= words(press) <= 750, words(press)
    assert height_display in article and height_display in press
    assert f"{facts['active_validators']} active consensus validators" in press
    assert "100 of 100 canonical structural-fidelity passes" in article
    assert "100 of 100 structural-fidelity passes" in press
    assert "zero final failures" in article.lower()
    assert "no replacement draws" in article.lower()

    forbidden_public = [
        "99 of 100",
        "99/100",
        "strict raw atom",
        "raw canonical-key",
        "ws-1",
        "ws-2",
        "provider-level out-of-gas responses for exactly two",
        "returned http 404 and is not a json-rpc route",
        "13,431,722",
        "block-13431722",
        "13,412,747",
        "block-13412747",
        "8 / 8",
    ]
    for path in PUBLIC_FILES:
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden_public:
            assert phrase.lower() not in text, f"{path} contains retired public wording: {phrase}"
        assert height_display.lower() in text, f"{path} does not contain current block {height_display}"

    html_paths = PUBLIC_FILES[3:6]
    for path in html_paths:
        text = path.read_text(encoding="utf-8")
        assert "<!doctype html>" in text.lower()
        assert "application/ld+json" in text
        assert "</html>" in text.lower()

    assert not (ROOT / "migration").exists()
    assert not (ROOT / "evidence" / "article-02" / "consensus").exists()
    assert not (ROOT / "evidence" / "article-02" / "molnft" / "block-13412747").exists()
    network_blocks = sorted((ROOT / "evidence" / "article-02" / "network-state").glob("block-*"))
    assert network_blocks == [args.snapshot.resolve().parent], network_blocks
    workflows = sorted(path.name for path in (ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows == ["publish-current.yml"], workflows
    assert len((ROOT / "README.md").read_text(encoding="utf-8").splitlines()) <= 55

    with (args.snapshot.parent / "validators.csv").open(encoding="utf-8", newline="") as handle:
        validators = list(csv.DictReader(handle))
    assert len(validators) == int(staking["registered_validator_records"])

    print(
        f"Validated current publication at block {height_display}: "
        f"{facts['active_validators']} validators, {facts['unique_active_delegators']:,} active delegators, "
        "100/100 MOLNFT structural-fidelity passes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
