#!/usr/bin/env python3
"""Revision-aware structural comparison for MOLNFT BinaryCIF evidence.

The primary identity path is the pre-existing canonical atom key.  When the
current RCSB comparator documents a later revision to ``_atom_site.label_atom_id``
and ``_atom_site.auth_atom_id``, a second, deliberately narrow path may pair
atoms by preserved ``_atom_site.id``.  That path is accepted only when every
non-name identity field agrees and the paired coordinates remain within the
precommitted tolerance.  It is a general audit rule, not a PDB-specific alias
list.
"""
from __future__ import annotations

import hashlib
import math
import pathlib
import struct
from collections import Counter
from typing import Any

import numpy as np

ATOM_NAME_ITEMS = {
    "_atom_site.label_atom_id",
    "_atom_site.auth_atom_id",
}


def _mapping_values(obj: Any) -> list[Any]:
    if hasattr(obj, "values"):
        try:
            return list(obj.values())
        except Exception:  # noqa: BLE001
            pass
    return []


def _get_item(obj: Any, names: list[str]) -> Any | None:
    for name in names:
        try:
            return obj[name]
        except Exception:  # noqa: BLE001
            pass
    return None


def _as_array(column: Any) -> np.ndarray:
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
    raise ValueError("could not convert BinaryCIF column to an array")


def _normalize_string(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    text = str(value)
    return "" if text in {".", "?", "None", "nan"} else text


def _read_block(path: pathlib.Path) -> Any:
    from biotite.structure.io.pdbx import BinaryCIFFile

    file = BinaryCIFFile.read(str(path))
    block = getattr(file, "block", None)
    if block is None:
        values = _mapping_values(file)
        block = values[0] if values else None
    if block is None:
        for key in getattr(file, "keys", lambda: [])():
            try:
                block = file[key]
                break
            except Exception:  # noqa: BLE001
                pass
    if block is None:
        raise ValueError("BinaryCIF has no data block")
    return block


def _category_arrays(block: Any, names: list[str]) -> dict[str, np.ndarray]:
    category = _get_item(block, names)
    if category is None:
        return {}
    arrays: dict[str, np.ndarray] = {}
    keys = getattr(category, "keys", lambda: [])()
    for key in keys:
        try:
            arrays[str(key)] = _as_array(category[key])
        except Exception:  # noqa: BLE001
            continue
    return arrays


def _revision_metadata(block: Any) -> dict[str, Any]:
    history = _category_arrays(block, ["pdbx_audit_revision_history", "_pdbx_audit_revision_history"])
    items = _category_arrays(block, ["pdbx_audit_revision_item", "_pdbx_audit_revision_item"])

    dates_by_ordinal: dict[str, str] = {}
    latest_structure_date: str | None = None
    if history:
        count = min(len(value) for value in history.values())
        for index in range(count):
            ordinal = _normalize_string(history.get("ordinal", np.asarray([index + 1] * count))[index])
            date = _normalize_string(history.get("revision_date", np.asarray([""] * count))[index])
            content_type = _normalize_string(history.get("data_content_type", np.asarray([""] * count))[index])
            if date:
                dates_by_ordinal[ordinal] = date
                if content_type in {"", "Structure model"}:
                    latest_structure_date = max(latest_structure_date or date, date)

    revision_items: list[dict[str, str]] = []
    if items:
        count = min(len(value) for value in items.values())
        for index in range(count):
            item = _normalize_string(items.get("item", np.asarray([""] * count))[index])
            ordinal = _normalize_string(items.get("revision_ordinal", np.asarray([""] * count))[index])
            content_type = _normalize_string(items.get("data_content_type", np.asarray([""] * count))[index])
            if item:
                revision_items.append(
                    {
                        "item": item,
                        "revision_ordinal": ordinal,
                        "revision_date": dates_by_ordinal.get(ordinal, ""),
                        "data_content_type": content_type,
                    }
                )

    atom_name_items = [entry for entry in revision_items if entry["item"] in ATOM_NAME_ITEMS]
    atom_name_dates = sorted({entry["revision_date"] for entry in atom_name_items if entry["revision_date"]})
    documented = ATOM_NAME_ITEMS.issubset({entry["item"] for entry in atom_name_items})
    return {
        "latest_structure_revision_date": latest_structure_date,
        "atom_name_revision_documented": documented,
        "atom_name_revision_dates": atom_name_dates,
        "atom_name_revision_items": atom_name_items,
    }


def _coordinate_hash(rows: list[tuple[str, tuple[float, float, float]]]) -> str:
    stream = bytearray()
    for _, coordinate in rows:
        for value in coordinate:
            normalized = 0.0 if value == 0.0 else float(value)
            stream.extend(struct.pack(">d", normalized))
    return hashlib.sha256(bytes(stream)).hexdigest()


def _id_sort_key(value: str) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def read_atom_table(path: pathlib.Path) -> dict[str, Any]:
    block = _read_block(path)
    category = _get_item(block, ["atom_site", "_atom_site"])
    if category is None:
        raise ValueError("BinaryCIF has no atom_site category")

    aliases = {
        "id": ["id"],
        "model": ["pdbx_PDB_model_num", "PDB_model_num"],
        "entity": ["label_entity_id"],
        "label_chain": ["label_asym_id"],
        "auth_chain": ["auth_asym_id"],
        "label_seq": ["label_seq_id"],
        "auth_seq": ["auth_seq_id"],
        "ins": ["pdbx_PDB_ins_code"],
        "label_atom": ["label_atom_id"],
        "auth_atom": ["auth_atom_id"],
        "label_comp": ["label_comp_id"],
        "auth_comp": ["auth_comp_id"],
        "alt": ["label_alt_id"],
        "element": ["type_symbol"],
        "x": ["Cartn_x"],
        "y": ["Cartn_y"],
        "z": ["Cartn_z"],
    }
    columns: dict[str, np.ndarray] = {}
    for logical, names in aliases.items():
        column = _get_item(category, names)
        if column is None:
            if logical in {"x", "y", "z"}:
                raise ValueError(f"BinaryCIF atom_site lacks {names[0]}")
            continue
        columns[logical] = _as_array(column)

    count = len(columns["x"])
    if count <= 0 or any(len(value) != count for value in columns.values()):
        raise ValueError("BinaryCIF atom_site columns have inconsistent row counts")

    def value(name: str, index: int, fallback: str = "") -> str:
        array = columns.get(name)
        return _normalize_string(array[index]) if array is not None else fallback

    records: list[dict[str, Any]] = []
    strict_rows: list[tuple[tuple[str, ...], tuple[float, float, float]]] = []
    by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for index in range(count):
        atom_id = value("id", index, str(index + 1))
        label_atom = value("label_atom", index)
        auth_atom = value("auth_atom", index)
        preferred_atom = label_atom or auth_atom
        coordinate = (
            float(columns["x"][index]),
            float(columns["y"][index]),
            float(columns["z"][index]),
        )
        record = {
            "id": atom_id,
            "model": value("model", index, "1"),
            "entity": value("entity", index),
            "label_chain": value("label_chain", index),
            "auth_chain": value("auth_chain", index),
            "label_seq": value("label_seq", index),
            "auth_seq": value("auth_seq", index),
            "ins": value("ins", index),
            "label_atom": label_atom,
            "auth_atom": auth_atom,
            "label_comp": value("label_comp", index),
            "auth_comp": value("auth_comp", index),
            "alt": value("alt", index),
            "element": value("element", index),
            "coordinate": coordinate,
        }
        records.append(record)
        strict_key = (
            record["model"],
            record["entity"],
            record["label_chain"],
            record["auth_chain"],
            record["label_seq"],
            record["auth_seq"],
            record["ins"],
            preferred_atom,
            record["alt"],
            record["element"],
            record["id"],
        )
        strict_rows.append((strict_key, coordinate))
        if atom_id in by_id:
            duplicate_ids.add(atom_id)
        else:
            by_id[atom_id] = record

    strict_rows.sort(key=lambda row: row[0])
    return {
        "count": count,
        "chains": sorted({record["label_chain"] for record in records}),
        "entities": sorted({record["entity"] for record in records}),
        "records": records,
        "by_id": by_id,
        "duplicate_ids": sorted(duplicate_ids, key=_id_sort_key),
        "strict_rows": strict_rows,
        "revision": _revision_metadata(block),
    }


_STABLE_FIELDS = (
    "model",
    "entity",
    "label_chain",
    "auth_chain",
    "label_seq",
    "auth_seq",
    "ins",
    "label_comp",
    "auth_comp",
    "alt",
    "element",
)


def _aggregate_name_changes(changes: list[dict[str, str]]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, ...]] = Counter()
    for change in changes:
        counter[
            (
                change["label_comp"],
                change["auth_comp"],
                change["from_label_atom"],
                change["to_label_atom"],
                change["from_auth_atom"],
                change["to_auth_atom"],
            )
        ] += 1
    return [
        {
            "label_comp_id": key[0],
            "auth_comp_id": key[1],
            "from_label_atom_id": key[2],
            "to_label_atom_id": key[3],
            "from_auth_atom_id": key[4],
            "to_auth_atom_id": key[5],
            "count": count,
        }
        for key, count in sorted(counter.items())
    ]


def compare_bcif(reconstructed: pathlib.Path, canonical: pathlib.Path, tolerance: float) -> dict[str, Any]:
    rec = read_atom_table(reconstructed)
    can = read_atom_table(canonical)
    rec_strict_keys = [row[0] for row in rec["strict_rows"]]
    can_strict_keys = [row[0] for row in can["strict_rows"]]
    strict_atom_keys_equal = rec_strict_keys == can_strict_keys

    pairing_method = "canonical_atom_key"
    atom_identity_agreement = strict_atom_keys_equal
    documented_revision = False
    revision_date: str | None = None
    name_changes: list[dict[str, str]] = []
    stable_field_mismatch_count = 0
    paired_rows_rec: list[tuple[str, tuple[float, float, float]]] = []
    paired_rows_can: list[tuple[str, tuple[float, float, float]]] = []

    if strict_atom_keys_equal:
        paired_rows_rec = [("\x1f".join(key), coordinate) for key, coordinate in rec["strict_rows"]]
        paired_rows_can = [("\x1f".join(key), coordinate) for key, coordinate in can["strict_rows"]]
    else:
        same_unique_ids = (
            not rec["duplicate_ids"]
            and not can["duplicate_ids"]
            and set(rec["by_id"]) == set(can["by_id"])
            and len(rec["by_id"]) == rec["count"] == can["count"]
        )
        if same_unique_ids:
            ordered_ids = sorted(rec["by_id"], key=_id_sort_key)
            for atom_id in ordered_ids:
                left = rec["by_id"][atom_id]
                right = can["by_id"][atom_id]
                if any(left[field] != right[field] for field in _STABLE_FIELDS):
                    stable_field_mismatch_count += 1
                if left["label_atom"] != right["label_atom"] or left["auth_atom"] != right["auth_atom"]:
                    name_changes.append(
                        {
                            "id": atom_id,
                            "label_comp": left["label_comp"],
                            "auth_comp": left["auth_comp"],
                            "from_label_atom": left["label_atom"],
                            "to_label_atom": right["label_atom"],
                            "from_auth_atom": left["auth_atom"],
                            "to_auth_atom": right["auth_atom"],
                        }
                    )
                paired_rows_rec.append((atom_id, left["coordinate"]))
                paired_rows_can.append((atom_id, right["coordinate"]))

            can_revision = can["revision"]
            rec_latest = rec["revision"].get("latest_structure_revision_date")
            candidate_dates = [
                date
                for date in can_revision.get("atom_name_revision_dates") or []
                if not rec_latest or date > rec_latest
            ]
            documented_revision = bool(
                name_changes
                and stable_field_mismatch_count == 0
                and can_revision.get("atom_name_revision_documented")
                and candidate_dates
            )
            if documented_revision:
                revision_date = max(candidate_dates)
                pairing_method = "stable_atom_site_id_with_documented_rcsb_atom_name_revision"
                atom_identity_agreement = True

    max_deviation: float | None = None
    coordinate_agreement = False
    if paired_rows_rec and len(paired_rows_rec) == len(paired_rows_can):
        deviations = [
            math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left[1], right[1])))
            for left, right in zip(paired_rows_rec, paired_rows_can)
        ]
        max_deviation = max(deviations, default=0.0)
        coordinate_agreement = max_deviation <= tolerance

    rec_coordinate_hash = _coordinate_hash(paired_rows_rec) if paired_rows_rec else ""
    can_coordinate_hash = _coordinate_hash(paired_rows_can) if paired_rows_can else ""
    strict_rec_hash = _coordinate_hash(
        [("\x1f".join(key), coordinate) for key, coordinate in rec["strict_rows"]]
    )
    strict_can_hash = _coordinate_hash(
        [("\x1f".join(key), coordinate) for key, coordinate in can["strict_rows"]]
    )

    atom_count_equal = rec["count"] == can["count"]
    chain_ids_equal = rec["chains"] == can["chains"]
    entity_ids_equal = rec["entities"] == can["entities"]
    fidelity_pass = all(
        [
            atom_count_equal,
            chain_ids_equal,
            entity_ids_equal,
            atom_identity_agreement,
            coordinate_agreement,
        ]
    )
    return {
        "reconstructed_atom_count": rec["count"],
        "canonical_atom_count": can["count"],
        "atom_count_equal": atom_count_equal,
        "reconstructed_chain_ids": rec["chains"],
        "canonical_chain_ids": can["chains"],
        "chain_ids_equal": chain_ids_equal,
        "reconstructed_entity_ids": rec["entities"],
        "canonical_entity_ids": can["entities"],
        "entity_ids_equal": entity_ids_equal,
        "atom_keys_equal": strict_atom_keys_equal,
        "atom_identity_agreement": atom_identity_agreement,
        "atom_identity_comparison_method": pairing_method,
        "stable_atom_site_id_sets_equal": set(rec["by_id"]) == set(can["by_id"]),
        "stable_identity_field_mismatch_count": stable_field_mismatch_count,
        "rcsb_atom_name_revision_documented": documented_revision,
        "rcsb_atom_name_revision_date": revision_date,
        "reconstructed_latest_structure_revision_date": rec["revision"].get("latest_structure_revision_date"),
        "canonical_latest_structure_revision_date": can["revision"].get("latest_structure_revision_date"),
        "atom_name_change_count": len(name_changes),
        "atom_name_changes": _aggregate_name_changes(name_changes),
        "reconstructed_coordinate_sha256": rec_coordinate_hash,
        "canonical_coordinate_sha256": can_coordinate_hash,
        "coordinate_hash_equal": bool(rec_coordinate_hash) and rec_coordinate_hash == can_coordinate_hash,
        "strict_atom_key_coordinate_hash_equal": strict_rec_hash == strict_can_hash,
        "coordinate_hash_ordering_method": pairing_method,
        "max_coordinate_deviation_angstrom": max_deviation,
        "coordinate_tolerance_angstrom": tolerance,
        "coordinate_agreement": coordinate_agreement,
        "fidelity_pass": fidelity_pass,
    }
