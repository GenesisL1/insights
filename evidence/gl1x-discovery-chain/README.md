# GL1X discovery chain — evidence for Article 04

The article *GL1X: The Ledger Is Now a Laboratory* follows one record, the on-chain haemoglobin structure **4HHB** (MolNFT v2 / PDB Bank, contract `0xd58b01f6c18086e5202cdc5d7ad3e41790360102`, token `93945`), through GL1X in ten steps — nine MCP calls, since steps 4 and 5 read one answer — and quotes the archive's size. Its numbers come from gl1x.com's MCP server on **20 October 2026**, with GL1X 3.4.1 serving: the ten steps, the archive and the example searches at 05:34–05:44 UTC, the L1 coin's figures at 06:27 UTC.

The first capture was made on 18 October 2026 (GL1X 3.4.0 serving for steps 1–9, at 08:13–08:37 UTC; the collection list, the mint block, a recheck of the BLAST hits and step 10 at 09:30–09:37 UTC). The re-run of 20 October gave the same results for every step; only the proof's block, the timings and the order of two search results that tie changed.

| File | What it holds |
|---|---|
| `recorded-results-2026-10-20.json` | The re-run of 20 October: the fields the article quotes, copied from each answer, with the route, its arguments and the answer's own timestamps. Its `extras.l1_coin` holds the chain-state snapshot from around midnight UTC, read while the Cosmos node that gl1x.com reads was not answering; the article uses the figures read at 06:27 UTC instead (`live-2026-10-20.json`). |
| `live-2026-10-20.json` | The figures the campaign texts quote: server counts, the archive, the L1 coin (read at 06:27 UTC, every chain-state snapshot refreshed at 06:24–06:26 UTC) and the example searches. |
| `recorded-results.json`, `live-2026-10-18.json` | The first capture, of 18 October, in the same form. |
| `capture.py` | Re-runs the same queries through the public API (standard-library Python, read-only) and saves every raw answer with its request, time and SHA-256, plus `SHA256SUMS.txt`. |

On both days the server counted 87 MCP tools, 186 API routes and 30 documentation pages.

## Reproduce

```bash
python3 capture.py https://gl1x.com raw-$(date -u +%F)
```

The archive grows and the indexes are rebuilt, so later captures give later numbers: what stays fixed is the record itself, its proof (anyone can replay the five `eth_call`s at the block the proof names — 13,869,469 on 20 October — against their own GenesisL1 node; the proof lists them) and the method.

| Step | MCP tool | Public API route |
|---|---|---|
| Archive size | `molecule_collections`, `get_stats` | `GET /api/network/summary`, `GET /api/bio/overview`, `GET /api/stats`, `GET /api/bio/collections` |
| The record's mint | `api_request` | `GET /api/v2/tokens/{contract}/instances/{token}/transfers` |
| 1 Find | `molecule_search` | `GET /api/bio/search?q=4HHB` |
| 2 Prove | `molecule_sequence_proof` | `GET /api/bio/records/{contract}/{token}/proof` |
| 3 Ligands | `molecule_ligands` | `GET /api/bio/records/{contract}/{token}/ligands` |
| 4–5 Archive-wide, found with | `ligand_sites` (one call) | `GET /api/bio/ligands/HEM` |
| 6 pH | `ph_environment` | `GET /api/bio/records/{contract}/{token}/ph?env=…&chain=B` |
| 7 Structure search | `structure_search` | `POST /api/bio/structure/search` |
| 8 BLAST | `blast_search` | `POST /api/bio/blast` (the script asks for 8 hits, as the recheck did) |
| 9 Literature | `pubmed_search` | `GET /api/bio/pubmed/search?title=…` |
| 10 Dataset | `bio_dataset` | `POST /api/bio/dataset` (BLAST hits, GL1F format, 25 rows) |
| Onward: a model | `gl1f_predict` | `POST /api/gl1f/forest/models/{id}/predict` (described in the article, not run: a model must first be trained off chain and minted) |

## What the evidence does and does not show

- It shows what gl1x.com answered: counts, timings of single requests on the production server, hits and the proof's result.
- Timings are measurements of one query each, not benchmarks (the benchmarks are in the GL1X documentation): on 20 October BLAST took 0.25 and 0.28 s in two calls, structure search 1.0 and 0.85 s; on 18 October 0.25 s and 0.82 s.
- The haem counts of step 4 and 5 come from samples: residue shares from the first 20,000 sites, the components "found with" haem from the first 5,000 haem records. "Found with" means in the same record, not in the same site.
- The first eight BLAST hits tie (146/146 identities, the same bit score and E-value). Equal scores are listed by database position, so the order of the 5-HMF complexes among them carries no meaning.
- Broccoli draws its map in the browser from up to 2,000 records (200 by default); `pubmed_search` returns the records and their shared MeSH topics, not the map.
- The pH value of β His146 is a structure-based estimate (`gl1x-ph-1`) on fixed coordinates; the measured value it is compared with (8.1) comes from Ohe & Kajita (1980) through PKAD, as recorded in the GL1X pKa benchmark data.
- "Druggable" pockets are pockets above 0.5 on GL1X's druggability score, which is not a probability that a drug binds.
