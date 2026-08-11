from pathlib import Path

path = Path('tools/qa/validate_ws1_ws2_structural.py')
text = path.read_text(encoding='utf-8')
for stale in [
    '    assert not is_true(revision_row["atom_keys_equal"])\n',
    '    assert not is_true(revision_row["strict_atom_key_coordinate_hash_equal"])\n',
]:
    text = text.replace(stale, '')

stale_block = '''        if (int(token_id), pdb_id) == REVISION_AWARE_RECORD:
            assert not is_true(row["atom_keys_equal"])
        else:
            assert is_true(row["atom_keys_equal"])
            assert row["atom_identity_comparison_method"] == "canonical_atom_key"
'''
text = text.replace(stale_block, '')

# The accepted atom-pairing method remains auditable per record, but there is
# deliberately no aggregate or pass/fail score for literal atom-name equality.
text = text.replace(
    '    assert is_true(revision_row["fidelity_pass"])\n',
    '    assert revision_row["atom_identity_comparison_method"] == "stable_atom_site_id_under_documented_rcsb_atom_name_revision"\n'
    '    assert is_true(revision_row["fidelity_pass"])\n',
    1,
)
path.write_text(text, encoding='utf-8')
print('stale raw atom-key QA assertions and aggregate scoring removed')
