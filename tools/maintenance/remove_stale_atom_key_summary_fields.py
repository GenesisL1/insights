from pathlib import Path

path = Path('tools/evidence/finalize_molnft_structural_evidence.py')
text = path.read_text(encoding='utf-8')
old = '    for obsolete in ["byte_identical_records", "complete_file_hash_role"]:\n'
new = '    for obsolete in [\n        "byte_identical_records",\n        "complete_file_hash_role",\n        "strict_atom_key_matches",\n        "revision_aware_atom_identity_passes",\n    ]:\n'
if old not in text:
    raise RuntimeError('finalizer obsolete-field block not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('stale raw-key summary fields will be removed during finalization')
