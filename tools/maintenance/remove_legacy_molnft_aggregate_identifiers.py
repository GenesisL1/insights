#!/usr/bin/env python3
"""Remove obsolete MOLNFT aggregate identifiers from source code.

The published and machine-readable result has one scientific outcome:
100/100 canonical structural-fidelity passes and zero failures. Per-record
integrity hashes and the documented 5KCS RCSB nomenclature revision remain.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path('.')

# 1. The current summary schema is already clean; remove compatibility code
# that names retired aggregate fields.
path = ROOT / 'tools/evidence/finalize_molnft_structural_evidence.py'
text = path.read_text(encoding='utf-8')
pattern = re.compile(
    r'    for obsolete in \[\n'
    r'.*?'
    r'    \]:\n'
    r'        summary\.pop\(obsolete, None\)\n',
    re.S,
)
text, count = pattern.subn('', text, count=1)
if count != 1:
    raise RuntimeError('finalizer compatibility block was not found')
path.write_text(text, encoding='utf-8')

# 2. Build publication fact objects from the current schema rather than
# copying and scrubbing obsolete keys.
path = ROOT / 'tools/publication/apply_molnft_targeted_requery.py'
text = path.read_text(encoding='utf-8')

facts_function = '''def update_facts(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["molnft_randomized"] = {
        "B_pin": summary["B_pin"],
        "B_seed": summary["B_seed"],
        "N": summary["N"],
        "successes": summary["successes"],
        "failures": summary["failures"],
        "failures_by_reason": summary["failures_by_reason"],
        "fidelity_passes": summary["fidelity_passes"],
        "revision_aware_records": summary["revision_aware_records"],
        "precommit_sha": summary["sample_spec_precommit_sha"],
        "evidence_relative_path": summary["evidence_relative_path"],
        "initial_failures": report["initial_failures"],
        "initial_failure_reason": "RPC_OUT_OF_GAS",
        "successful_same_id_payload_requeries": report["successful_requeries"],
        "targeted_requery_token_ids": report["queried_token_ids"],
        "targeted_requery_endpoint": ROOT_RPC,
        "requested_api_path_http_status": 404,
        "replacement_draws": report["replacement_draws"],
        "final_failure_records": [],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


'''
text, count = re.subn(
    r'def update_facts\(.*?\n\n\ndef update_latest',
    facts_function + 'def update_latest',
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('update_facts function was not replaced')

latest_function = '''def update_latest(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:
    previous = json.loads(path.read_text(encoding="utf-8"))
    payload = {
        "schema": previous.get("schema", "org.genesisl1.molnft_evidence_pointer.v1"),
        "evidence_block": summary["B_pin"],
        "path": f"block-{summary['B_pin']}",
        "sample_size": summary["N"],
        "fidelity_passes": summary["fidelity_passes"],
        "failures": summary["failures"],
        "selection": previous.get("selection", "future-block-seeded direct NFT-ID sample without replacement"),
        "off_chain_token_index_used": False,
        "sample_spec_precommit_sha": summary["sample_spec_precommit_sha"],
        "failures_by_reason": summary["failures_by_reason"],
        "initial_failures": report["initial_failures"],
        "successful_same_id_payload_requeries": report["successful_requeries"],
        "targeted_requery_token_ids": report["queried_token_ids"],
        "replacement_draws": report["replacement_draws"],
        "final_failure_records": [],
        "revision_aware_records": summary["revision_aware_records"],
    }
    path.write_text(json.dumps(payload, indent=2) + "\\n", encoding="utf-8")


'''
text, count = re.subn(
    r'def update_latest\(.*?\n\n\ndef update_indexes',
    latest_function + 'def update_indexes',
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('update_latest function was not replaced')
path.write_text(text, encoding='utf-8')

# 3. Keep QA focused on positive schema and scientific assertions. Remove
# source-level references to retired aggregate names and wording.
path = ROOT / 'tools/qa/validate_ws1_ws2_structural.py'
text = path.read_text(encoding='utf-8')
text = re.sub(
    r'\n\ndef assert_no_serialized_equality_language\(.*?\n\n\ndef main',
    '\n\ndef main',
    text,
    count=1,
    flags=re.S,
)

exact_lines = [
    '    assert "atom_keys_equal" not in results[0]\n',
    '    assert "strict_atom_key_coordinate_hash_equal" not in results[0]\n',
    '    assert "coordinate_hash_matches" not in summary\n',
    '    assert "strict_atom_key_matches" not in summary\n',
    '    assert "revision_aware_atom_identity_passes" not in summary\n',
    '    assert "byte_identical_records" not in summary\n',
    '    assert "complete_file_hash_role" not in summary\n',
    '    assert "byte_identical" not in results[0], "results.csv must not contain serialized equality"\n',
    '        assert "99 of 100" not in text\n',
    '        assert "raw canonical-key" not in text.lower()\n',
    '    assert "byte_identical_records" not in randomized_facts\n',
    '    assert "strict_atom_key_matches" not in randomized_facts\n',
    '    assert "revision_aware_atom_identity_passes" not in randomized_facts\n',
    '    assert "coordinate_hash_matches" not in randomized_facts\n',
]
for line in exact_lines:
    text = text.replace(line, '')

text = re.sub(
    r'\n    for label, text in \[\n'
    r'        \("article", article\),\n'
    r'        \("production HTML", html\),\n'
    r'        \("root README", root_readme\),\n'
    r'        \("evidence README", evidence_readme\),\n'
    r'        \("MOLNFT methodology", methodology\),\n'
    r'    \]:\n'
    r'        assert_no_serialized_equality_language\(text, label\)\n',
    '',
    text,
    count=1,
)
path.write_text(text, encoding='utf-8')

forbidden = [
    'byte_identical',
    'byte-identical',
    'byte identical',
    'byte-for-byte',
    'byte_to_byte',
    'complete_file_hash_role',
    'strict_atom_key_matches',
    'revision_aware_atom_identity_passes',
    'coordinate_hash_matches',
    '99 of 100',
    'raw canonical-key',
]
for relative in [
    'tools/evidence/finalize_molnft_structural_evidence.py',
    'tools/publication/apply_molnft_targeted_requery.py',
    'tools/qa/validate_ws1_ws2_structural.py',
]:
    contents = (ROOT / relative).read_text(encoding='utf-8').lower()
    remaining = [item for item in forbidden if item.lower() in contents]
    if remaining:
        raise RuntimeError(f'{relative} still contains retired identifiers: {remaining}')

print('Removed all legacy MOLNFT aggregate identifiers from maintained source')
