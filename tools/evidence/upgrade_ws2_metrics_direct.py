#!/usr/bin/env python3
"""WS-2 entry point for the published network-state CSV schema.

The original metric engine is retained; this wrapper binds its delegator parser
to the exact columns emitted by the block-13,431,722 capture.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from decimal import Decimal
from typing import Any

BASE_PATH = pathlib.Path(__file__).with_name("upgrade_ws2_metrics.py")
SPEC = importlib.util.spec_from_file_location("genesisl1_ws2_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


def delegator_values(rows: list[dict[str, str]]) -> list[Decimal]:
    values: list[Decimal] = []
    candidates = [
        "bonded_amount_atomic",
        "bonded_amount_l1",
        "active_balance_atomic",
        "bonded_balance_atomic",
        "total_active_balance_atomic",
        "total_balance_atomic",
        "active_delegation_balance_atomic",
        "balance_atomic",
        "total_active_delegation_l1",
        "total_delegation_l1",
        "bonded_stake_l1",
    ]
    for row in rows:
        raw = base.pick(row, candidates)
        if raw is None:
            continue
        value = base.D(raw)
        if value > 0:
            values.append(value)
    if not values:
        raise ValueError("could not identify per-address bonded delegation totals in delegators.csv")
    return values


base.delegator_values = delegator_values

if __name__ == "__main__":
    raise SystemExit(base.main())
