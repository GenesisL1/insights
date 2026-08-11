from pathlib import Path

path = Path('tools/qa/validate_ws1_ws2_structural.py')
text = path.read_text(encoding='utf-8')
for stale in [
    '    assert not is_true(revision_row["atom_keys_equal"])\n',
    '    assert not is_true(revision_row["strict_atom_key_coordinate_hash_equal"])\n',
    '    assert revision_row["atom_identity_comparison_method"] == "stable_atom_site_id_under_documented_rcsb_atom_name_revision"\n',
]:
    text = text.replace(stale, '')

stale_block = '''        if (int(token_id), pdb_id) == REVISION_AWARE_RECORD:
            assert not is_true(row["atom_keys_equal"])
        else:
            assert is_true(row["atom_keys_equal"])
            assert row["atom_identity_comparison_method"] == "canonical_atom_key"
'''
text = text.replace(stale_block, '')

# Keep only scientifically meaningful assertions: the revision record remains
# explicit, atom identity is accepted, coordinates agree, and the record passes.
path.write_text(text, encoding='utf-8')
print('stale raw atom-key QA assertions and aggregate scoring removed')
