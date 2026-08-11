from pathlib import Path

path = Path('tools/maintenance/remove_legacy_molnft_aggregate_identifiers.py')
text = path.read_text(encoding='utf-8')
text = text.replace(
    "    facts_function + 'def update_latest',\n",
    "    lambda _match: facts_function + 'def update_latest',\n",
    1,
)
text = text.replace(
    "    latest_function + 'def update_indexes',\n",
    "    lambda _match: latest_function + 'def update_indexes',\n",
    1,
)
path.write_text(text, encoding='utf-8')
print('Fixed regex replacement escaping in one-shot cleanup helper')
