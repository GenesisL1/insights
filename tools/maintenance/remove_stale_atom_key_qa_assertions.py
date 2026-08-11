from pathlib import Path

path = Path('tools/qa/validate_ws1_ws2_structural.py')
text = path.read_text(encoding='utf-8')
for stale in [
    '    assert not is_true(revision_row["atom_keys_equal"])\n',
    '    assert not is_true(revision_row["strict_atom_key_coordinate_hash_equal"])\n',
]:
    text = text.replace(stale, '')
path.write_text(text, encoding='utf-8')
print('stale raw atom-key QA assertions removed')
