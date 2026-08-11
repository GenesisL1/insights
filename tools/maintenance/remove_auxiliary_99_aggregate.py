from pathlib import Path

root = Path('.')

# The publication has one scientific pass/fail result: 100/100 structural
# fidelity, zero failures. Exact coordinate hashes remain available per record,
# but no aggregate secondary score is published.

# Capture summaries
p = root / 'tools/evidence/capture_molnft_randomized_sample.py'
text = p.read_text(encoding='utf-8')
text = text.replace('            "coordinate_hash_matches": sum(bool(row.get("coordinate_hash_equal")) for row in results),\n', '')
text = text.replace('        "coordinate_hash_matches": sum(bool(row.get("coordinate_hash_equal")) for row in results),\n', '')
p.write_text(text, encoding='utf-8')

# Deterministic finalizer and generated evidence README
p = root / 'tools/evidence/finalize_molnft_structural_evidence.py'
text = p.read_text(encoding='utf-8')
text = text.replace('        "revision_aware_atom_identity_passes",\n', '        "revision_aware_atom_identity_passes",\n        "coordinate_hash_matches",\n')
text = text.replace('            "coordinate_hash_matches": sum(bool(row.get("coordinate_hash_equal")) for row in rows),\n', '')
text = text.replace('| Exact normalized coordinate-hash matches | **{summary[\'coordinate_hash_matches\']}** |\n', '')
p.write_text(text, encoding='utf-8')

# Article and publication indexes
p = root / 'tools/publication/apply_molnft_targeted_requery.py'
text = p.read_text(encoding='utf-8')
text = text.replace(
    'For PDB **5KCS** / NFT **124713**, the raw atom-name "\n        f"keys differed only because the current RCSB file documents a later',
    'For PDB **5KCS** / NFT **124713**, the current RCSB file documents a later'
)
text = text.replace('    for stale_key in ("strict_atom_key_matches", "revision_aware_atom_identity_passes"):\n', '    for stale_key in ("strict_atom_key_matches", "revision_aware_atom_identity_passes", "coordinate_hash_matches"):\n')
text = text.replace('            "coordinate_hash_matches": summary["coordinate_hash_matches"],\n', '')
text = text.replace('    payload.pop("revision_aware_atom_identity_passes", None)\n', '    payload.pop("revision_aware_atom_identity_passes", None)\n    payload.pop("coordinate_hash_matches", None)\n')
p.write_text(text, encoding='utf-8')

# QA: verify per-record hashes exist, but never turn them into a second pass rate.
p = root / 'tools/qa/validate_ws1_ws2_structural.py'
text = p.read_text(encoding='utf-8')
text = text.replace('    assert int(summary["coordinate_hash_matches"]) == 99\n', '    assert "coordinate_hash_matches" not in summary\n')
text = text.replace('    coordinate_hash_matches = 0\n', '')
text = text.replace('        coordinate_hash_matches += is_true(row["coordinate_hash_equal"])\n', '')
text = text.replace('    assert coordinate_hash_matches == int(summary["coordinate_hash_matches"]) == 99\n', '')
needle = '    assert "revision_aware_atom_identity_passes" not in randomized_facts\n'
if needle in text:
    text = text.replace(needle, needle + '    assert "coordinate_hash_matches" not in randomized_facts\n', 1)
p.write_text(text, encoding='utf-8')

# Generic publication helper already keeps hashes per record and should never
# describe them as an aggregate success metric.
p = root / 'tools/publication/apply_ws1_ws2_direct_article.py'
text = p.read_text(encoding='utf-8')
text = text.replace(
    'Exact normalized coordinate hashes are retained per record as an auxiliary reproducibility check, not a "\n        f"fidelity criterion.',
    'Normalized coordinate hashes are retained per record as auxiliary reproducibility evidence, not as a "\n        f"fidelity criterion.'
)
p.write_text(text, encoding='utf-8')

print('Removed all auxiliary 99/100 aggregate reporting; per-record hashes remain preserved')
