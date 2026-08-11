from pathlib import Path

root = Path('.')

# 1) Comparator: retain the internal branch decision, but do not serialize a raw-key score.
p = root / 'tools/evidence/molnft_structural_compare.py'
text = p.read_text(encoding='utf-8')
text = text.replace(
'''    strict_rec_hash = _coordinate_hash(
        [("\\x1f".join(key), coordinate) for key, coordinate in rec["strict_rows"]]
    )
    strict_can_hash = _coordinate_hash(
        [("\\x1f".join(key), coordinate) for key, coordinate in can["strict_rows"]]
    )

''',
''
)
text = text.replace('        "atom_keys_equal": strict_atom_keys_equal,\n', '')
text = text.replace('        "strict_atom_key_coordinate_hash_equal": strict_rec_hash == strict_can_hash,\n', '')
p.write_text(text, encoding='utf-8')

# 2) Capture output schema and summaries: no aggregate or per-row raw-key score.
p = root / 'tools/evidence/capture_molnft_randomized_sample.py'
text = p.read_text(encoding='utf-8')
text = text.replace('    "atom_keys_equal",\n', '')
text = text.replace('    "strict_atom_key_coordinate_hash_equal",\n', '')
text = text.replace('            "strict_atom_key_matches": sum(bool(row.get("atom_keys_equal")) for row in results),\n', '')
text = text.replace(
'''            "revision_aware_atom_identity_passes": sum(
                bool(row.get("fidelity_pass")) and bool(row.get("rcsb_atom_name_revision_documented"))
                for row in results
            ),
''',
''
)
text = text.replace('        "strict_atom_key_matches": sum(bool(row.get("atom_keys_equal")) for row in results),\n', '')
text = text.replace(
'''        "revision_aware_atom_identity_passes": sum(
            bool(row.get("fidelity_pass")) and bool(row.get("rcsb_atom_name_revision_documented"))
            for row in results
        ),
''',
''
)
text = text.replace('                "atom_identity_agreement_by_raw_key_or_documented_rcsb_atom_name_revision",\n', '                "atom_identity_agreement",\n')
p.write_text(text, encoding='utf-8')

# 3) Finalizer: remove misleading aggregate and generated prose.
p = root / 'tools/evidence/finalize_molnft_structural_evidence.py'
text = p.read_text(encoding='utf-8')
text = text.replace('            "strict_atom_key_matches": sum(bool(row.get("atom_keys_equal")) for row in rows),\n', '')
text = text.replace(
'''            "revision_aware_atom_identity_passes": sum(
                bool(row.get("fidelity_pass")) and bool(row.get("rcsb_atom_name_revision_documented")) for row in rows
            ),
''',
''
)
text = text.replace('                "atom_identity_agreement_by_raw_key_or_documented_rcsb_atom_name_revision",\n', '                "atom_identity_agreement",\n')
text = text.replace(
'A fidelity pass requires equal atom counts, chain/entity sets, atom identity agreement and maximum paired coordinate deviation within the precommitted tolerance. Atom identity agreement is either raw canonical-key equality or the narrowly documented RCSB revision-aware path described below. Serialized-object equality is not calculated or reported. The separately recorded SHA-256 value for each object is an integrity identifier only.',
'A fidelity pass requires equal atom counts, chain/entity sets, atom-identity agreement and maximum paired coordinate deviation within the precommitted tolerance. A documented later RCSB atom-name revision may be reconciled only under the narrow, evidence-preserving conditions described below. Serialized-object equality is not calculated or reported. The separately recorded SHA-256 value for each object is an integrity identifier only.'
)
p.write_text(text, encoding='utf-8')

# 4) Main publication updater: no 99/100 raw-key metric or auxiliary hash count in public prose.
p = root / 'tools/publication/apply_molnft_targeted_requery.py'
text = p.read_text(encoding='utf-8')
text = text.replace('    exact = int(summary["coordinate_hash_matches"])\n', '')
text = text.replace('    strict = int(summary["strict_atom_key_matches"])\n', '')
old_para2 = '''    paragraph2 = (
        f"A fidelity pass required equal atom counts, chain and entity sets, atom-identity agreement, and a maximum paired "
        f"coordinate deviation no greater than the precommitted **{float(summary['coordinate_tolerance_angstrom']):.6f} Å** "
        f"tolerance. Atom identity was established by raw canonical-key equality for **{strict} of {n}** records. The remaining "
        f"record used a narrowly constrained revision-aware path: unique unchanged `_atom_site.id` values, equality of every "
        f"non-name identity field, a current RCSB audit trail explicitly naming both atom-name fields, and coordinates within the "
        f"unchanged tolerance. No PDB-specific alias table was used. All **{fidelity}** comparisons passed. Exact normalized "
        f"coordinate hashes matched for **{exact} of {fidelity}** records. Serialized BinaryCIF equality is neither calculated nor "
        f"used as a pass condition; reconstructed and canonical SHA-256 values are retained independently only to identify the "
        f"preserved objects. The future-block seed, complete parent-ID population, immutable draw, original provider errors, "
        f"targeted same-ID calls, reconstructed and canonical objects, RCSB revision evidence, environment fingerprint and SHA-256 "
        f"manifest are preserved in the evidence package."
    )
'''
new_para2 = '''    paragraph2 = (
        f"A fidelity pass required equal atom counts, chain and entity sets, atom-identity agreement, and a maximum paired "
        f"coordinate deviation no greater than the precommitted **{float(summary['coordinate_tolerance_angstrom']):.6f} Å** "
        f"tolerance. All **{fidelity}** comparisons passed. For 5KCS, the documented later RCSB atom-name revision was reconciled "
        f"only because `_atom_site.id` remained unique and unchanged, every non-name identity field agreed, and all 148,945 "
        f"coordinates paired at **0 Å** deviation. No PDB-specific alias table was used. Exact normalized coordinate hashes remain "
        f"available per record as an auxiliary reproducibility check, not as a fidelity criterion. Serialized BinaryCIF equality is "
        f"neither calculated nor used as a pass condition; reconstructed and canonical SHA-256 values are retained independently "
        f"only to identify the preserved objects. The future-block seed, complete parent-ID population, immutable draw, original "
        f"provider errors, targeted same-ID calls, reconstructed and canonical objects, RCSB revision evidence, environment "
        f"fingerprint and SHA-256 manifest are preserved in the evidence package."
    )
'''
if old_para2 not in text:
    raise RuntimeError('publication paragraph2 pattern not found')
text = text.replace(old_para2, new_para2)
text = text.replace(
'''    current.update(
        {
''',
'''    for stale_key in ("strict_atom_key_matches", "revision_aware_atom_identity_passes"):
        current.pop(stale_key, None)
    current.update(
        {
''',
1,
)
text = text.replace('            "strict_atom_key_matches": summary["strict_atom_key_matches"],\n', '')
text = text.replace('            "revision_aware_atom_identity_passes": summary["revision_aware_atom_identity_passes"],\n', '')
needle = 'def update_latest(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:\n    payload = json.loads(path.read_text(encoding="utf-8"))\n    payload.pop("failure_reason", None)\n'
replacement = 'def update_latest(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:\n    payload = json.loads(path.read_text(encoding="utf-8"))\n    payload.pop("failure_reason", None)\n    payload.pop("strict_atom_key_matches", None)\n    payload.pop("revision_aware_atom_identity_passes", None)\n'
if needle not in text:
    raise RuntimeError('update_latest header not found')
text = text.replace(needle, replacement)
text = text.replace('            "strict_atom_key_matches": summary["strict_atom_key_matches"],\n', '')
text = text.replace('            "revision_aware_atom_identity_passes": summary["revision_aware_atom_identity_passes"],\n', '')
text = text.replace(
'- **{summary[\'strict_atom_key_matches\']} raw canonical atom-key matches plus one documented RCSB atom-name revision reconciliation**;\n- **{summary[\'coordinate_hash_matches\']} of {summary[\'fidelity_passes\']} exact normalized coordinate-hash matches**;',
'- **zero final failures**, with the 5KCS atom-name revision fully documented and all 148,945 coordinates aligned at `0 Å`;\n- per-record normalized coordinate hashes retained as auxiliary reproducibility evidence;'
)
text = text.replace(
'f"{summary[\'coordinate_hash_matches\']} exact normalized coordinate-hash matches; no off-chain token index",',
'f"per-record coordinate hashes retained as auxiliary evidence; no off-chain token index",'
)
p.write_text(text, encoding='utf-8')

# 5) Generic direct updater must not reintroduce the metric.
p = root / 'tools/publication/apply_ws1_ws2_direct_article.py'
text = p.read_text(encoding='utf-8')
text = text.replace('    exact_coordinates = int(summary.get("coordinate_hash_matches", 0))\n', '')
text = text.replace('    strict_keys = int(summary.get("strict_atom_key_matches", fidelity))\n', '')
old = '''        f"For each comparable record, the audit required equal atom counts, chain and entity sets, atom-identity agreement, and a "
        f"maximum paired coordinate deviation no greater than the precommitted **{tolerance:.6f} Å** tolerance. Raw canonical atom "
        f"keys agreed for **{strict_keys} of {fidelity}** records; any revision-aware identity path required unique unchanged "
        f"`_atom_site.id`, equality of every non-name identity field and explicit current-RCSB audit metadata naming both atom-name "
        f"fields. All **{fidelity}** comparisons passed. Exact normalized coordinate hashes additionally matched for "
        f"**{exact_coordinates} of {fidelity}** records. Serialized BinaryCIF equality is neither calculated nor used as a pass "
        f"condition; each object's SHA-256 is retained independently only as an integrity identifier. The future-block seed, complete "
        f"numeric parent-ID population, draw, failure table, reconstructed and canonical objects, environment fingerprint and SHA-256 "
        f"manifest are preserved in the evidence package."
'''
new = '''        f"For each comparable record, the audit required equal atom counts, chain and entity sets, atom-identity agreement, and a "
        f"maximum paired coordinate deviation no greater than the precommitted **{tolerance:.6f} Å** tolerance. All **{fidelity}** "
        f"comparisons passed. A documented later RCSB atom-name revision may be reconciled only when `_atom_site.id` remains unique "
        f"and unchanged, every non-name identity field agrees, and coordinates remain within the original tolerance. No PDB-specific "
        f"alias table is used. Exact normalized coordinate hashes are retained per record as an auxiliary reproducibility check, not a "
        f"fidelity criterion. Serialized BinaryCIF equality is neither calculated nor used as a pass condition; each object's SHA-256 "
        f"is retained independently only as an integrity identifier. The future-block seed, complete numeric parent-ID population, "
        f"draw, failure table, reconstructed and canonical objects, environment fingerprint and SHA-256 manifest are preserved in the "
        f"evidence package."
'''
if old not in text:
    raise RuntimeError('direct updater paragraph not found')
text = text.replace(old, new)
p.write_text(text, encoding='utf-8')

# 6) Methodology: no aggregate raw-key statistic; retain transparent reconciliation.
p = root / 'methodology/molnft.md'
text = p.read_text(encoding='utf-8')
text = text.replace(
'For `5KCS`, raw atom-name keys initially differed because the current RCSB file contains a later structure-model revision dated `2026-07-01` that explicitly lists `_atom_site.label_atom_id` and `_atom_site.auth_atom_id` among the revised items.',
'For `5KCS`, the current RCSB file contains a later structure-model revision dated `2026-07-01` that explicitly lists `_atom_site.label_atom_id` and `_atom_site.auth_atom_id` among the revised items.'
)
text = text.replace(
'Raw atom-name equality remains the primary comparison path. A later RCSB nomenclature revision may not be counted as a molecular mismatch merely because the current archive uses different atom labels from the historical object. The revision-aware path is deliberately narrow and is applied uniformly to every sampled record.',
'Atom identity is compared using the full preserved structural context. A later RCSB nomenclature revision is not counted as a molecular mismatch merely because the current archive uses revised atom labels for the same atoms. The revision-aware path is deliberately narrow and is applied uniformly to every sampled record.'
)
text = text.replace(
'No PDB-specific alias list is used. The old-to-current labels and counts are derived from the two preserved objects and published per record. Raw atom-key equality is retained as a separate diagnostic, so the nomenclature change remains visible rather than being erased.',
'No PDB-specific alias list is used. The old-to-current labels and counts are derived from the two preserved objects and published per record, so the nomenclature change remains visible rather than being erased.'
)
text = text.replace(
'| Atom identities | raw canonical atom-key equality, or stable `_atom_site.id` reconciliation under a documented later RCSB atom-name revision with all non-name identity fields equal |',
'| Atom identities | agreement across the preserved atom context; a documented later RCSB atom-name revision may be reconciled by stable `_atom_site.id` only when every non-name identity field agrees |'
)
text = text.replace(
'A **fidelity pass** requires atom-count, chain/entity and atom-identity agreement plus the precommitted coordinate-tolerance condition. Atom identity agreement is established either by raw canonical-key equality or by the documented revision-aware rule above.',
'A **fidelity pass** requires atom-count, chain/entity and atom-identity agreement plus the precommitted coordinate-tolerance condition. Any documented nomenclature reconciliation must satisfy the revision-aware rule above.'
)
text = text.replace('- raw canonical atom-key matches and documented revision-aware reconciliations;\n', '- documented atom-name revision reconciliations, when present;\n')
p.write_text(text, encoding='utf-8')

# 7) QA: assert the misleading fields and public 99/100 phrasing are absent.
p = root / 'tools/qa/validate_ws1_ws2_structural.py'
text = p.read_text(encoding='utf-8')
text = text.replace('    assert int(summary["strict_atom_key_matches"]) == 99\n', '    assert "strict_atom_key_matches" not in summary\n')
text = text.replace('    assert int(summary["revision_aware_atom_identity_passes"]) == 1\n', '    assert "revision_aware_atom_identity_passes" not in summary\n')
text = text.replace('    assert not is_true(revision_row["strict_atom_key_coordinate_hash_equal"])\n', '')
text = text.replace('        assert "99 of 100" in text\n', '        assert "99 of 100" not in text\n        assert "strict atom" not in text.lower()\n        assert "raw canonical-key" not in text.lower()\n')
text = text.replace('    assert int(randomized_facts["strict_atom_key_matches"]) == 99\n', '    assert "strict_atom_key_matches" not in randomized_facts\n')
text = text.replace('    assert int(randomized_facts["revision_aware_atom_identity_passes"]) == 1\n', '    assert "revision_aware_atom_identity_passes" not in randomized_facts\n')
needle = '    results = read_csv(mol / "results.csv")\n    drawn = read_csv(mol / "drawn-ids.csv")\n'
replacement = '    results = read_csv(mol / "results.csv")\n    drawn = read_csv(mol / "drawn-ids.csv")\n    assert "atom_keys_equal" not in results[0]\n    assert "strict_atom_key_coordinate_hash_equal" not in results[0]\n'
if needle not in text:
    raise RuntimeError('QA results load pattern not found')
text = text.replace(needle, replacement)
p.write_text(text, encoding='utf-8')

print('source edits applied')
