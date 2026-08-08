#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
errors=[]
def check(cond,msg):
    if not cond: errors.append(msg)

for p in ROOT.rglob('*'):
    if p.is_file():
        check(p.suffix not in {'.pyc','.pyo'}, f'compiled Python artifact: {p.relative_to(ROOT)}')
        check('__pycache__' not in p.parts, f'Python cache: {p.relative_to(ROOT)}')

article=(ROOT/'site/insights/genesisl1-decentralization-scientific-renaissance.html').read_text(encoding='utf-8')
check('github.com/GenesisL1/web3desk' not in article,'article still cites web3desk')
check('https://explorer.genesisl1.org/validators' in article,'validator explorer link missing')
check('9.35831582%' not in article,'machine precision leaked into article')
check('−12.32840292' not in article,'false precision delta leaked into article')
check('genesisl1-token-distribution-no-insider-allocation.html' not in [p.name for p in (ROOT/'site/insights').glob('*.html')], 'obsolete article file present')
for name in ['genesisl1-scientific-renaissance-hero','genesisl1-l1-utility-layer','genesisl1-consensus-widening','genesisl1-press-patron-public-record','genesisl1-institutional-sovereignty','genesisl1-institutional-stewardship','genesisl1-scientific-renaissance-card','genesisl1-scientific-renaissance-social-1200x630']:
    check((ROOT/f'content/article-02-next-verifiable-renaissance/figures/{name}.svg').exists(),f'missing source SVG {name}')
    check((ROOT/f'site/insights/assets/{name}.svg').exists(),f'missing site SVG {name}')
    check((ROOT/f'site/insights/assets/{name}.png').exists(),f'missing site PNG {name}')
for evidence in [ROOT/'evidence/article-02/consensus/block-13412747', ROOT/'evidence/article-02/molnft/block-13412747']:
    check((evidence/'SHA256SUMS.txt').exists(),f'missing checksums: {evidence}')
    check((evidence/'snapshot.json').exists(),f'missing snapshot: {evidence}')
if errors:
    print('\n'.join('FAIL: ' + e for e in errors), file=sys.stderr)
    raise SystemExit(1)
print('repository QA passed')
