#!/usr/bin/env python3
"""Captures the raw answers behind the article "GL1X: The Ledger Is Now a
Laboratory" from GL1X's public API: the same queries its MCP tools ran,
saved as they come, with the time, the request and a SHA-256 of each.

usage: python3 capture.py [BASE_URL] [OUT_DIR]
       (defaults: https://gl1x.com and ./raw-<UTC date>)
Standard library only. Read-only: every request is a search, a read or a
computation; nothing is written.
"""
import datetime
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://gl1x.com").rstrip("/")
NOW = datetime.datetime.now(datetime.timezone.utc)
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else f"raw-{NOW:%Y-%m-%d}")
C = "0xd58b01f6c18086e5202cdc5d7ad3e41790360102"
T = "93945"
TITLE = "THE CRYSTAL STRUCTURE OF HUMAN DEOXYHAEMOGLOBIN AT 1.74 ANGSTROMS RESOLUTION"
BETA = ("VHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENF"
        "RLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH")

QUERIES = [
    ("00-network-summary", "GET", "/api/network/summary", None),
    ("00-bio-overview", "GET", "/api/bio/overview", None),
    ("00-stats", "GET", "/api/stats", None),
    ("00-collections", "GET", "/api/bio/collections", None),
    ("01-record-mint", "GET", f"/api/v2/tokens/{C}/instances/{T}/transfers", None),
    ("01-molecule-search", "GET", "/api/bio/search?" + urllib.parse.urlencode({"q": "4HHB", "limit": 5}), None),
    ("02-sequence-proof", "GET", f"/api/bio/records/{C}/{T}/proof", None),
    ("03-record-ligands", "GET", f"/api/bio/records/{C}/{T}/ligands", None),
    ("04-ligand-sites-HEM", "GET", "/api/bio/ligands/HEM?limit=1", None),
    ("06-ph-environment", "GET", f"/api/bio/records/{C}/{T}/ph?" + urllib.parse.urlencode({"env": "blood,7.2,7.6,lysosome", "chain": "B"}), None),
    ("07-structure-search", "POST", "/api/bio/structure/search", {"query": {"contract": C, "token_id": T, "chain": "B"}, "limit": 8}),
    ("08-blast", "POST", "/api/bio/blast", {"query": ">4HHB_B\n" + BETA, "max_target_seqs": 8}),
    ("09-pubmed-title", "GET", "/api/bio/pubmed/search?" + urllib.parse.urlencode({"title": TITLE, "max": 3}), None),
    ("10-dataset-gl1f", "POST", "/api/bio/dataset", {"blast": {"query": BETA}, "max_rows": 25, "format": "gl1f",
                                                    "include_sequence": False}),
]


def fetch(method, path, body):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Accept": "application/json", "User-Agent": "GL1X-evidence-capture/1.0",
                                          **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"base": BASE, "started_at": NOW.isoformat(), "requests": []}
    sums = []
    for name, method, path, body in QUERIES:
        at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        status, raw = fetch(method, path, body)
        f = OUT / f"{name}.json"
        f.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        sums.append(f"{digest}  {f.name}")
        manifest["requests"].append({"file": f.name, "method": method, "url": BASE + path, "body": body,
                                     "status": status, "at": at, "bytes": len(raw), "sha256": digest})
        print(f"{status} {name} ({len(raw):,} bytes)")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    mdig = hashlib.sha256((OUT / "manifest.json").read_bytes()).hexdigest()
    sums.append(f"{mdig}  manifest.json")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"saved in {OUT}/")


if __name__ == "__main__":
    main()
