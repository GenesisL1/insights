from pathlib import Path
import json,re

root=Path(__file__).resolve().parents[2]
f=json.loads((root/'LATEST_DELEGATION_SUMMARY.json').read_text())
h=f['pinned_height']; hd=f'{h:,}'
block=f'''The Article 02 evidence is now deliberately **longitudinal**. The August 11 snapshot remains preserved as a historical measurement rather than being overwritten; a second delegation-focused snapshot records the network four days later. Together they show why decentralization is better treated as a dynamic, reproducible process than as a permanent label.

At GenesisL1 block **{hd}**, dated **August 15, 2026**, the active consensus set contained **{f['active_validators']} validators** out of a protocol maximum of 50. The largest validator held **{float(f['largest_validator_share_percent']):.2f}%** of voting power; the top three held **{float(f['top_3_validator_share_percent']):.2f}%**, the top five **{float(f['top_5_validator_share_percent']):.2f}%**, and the top ten **{float(f['top_10_validator_share_percent']):.2f}%**. **{f['one_third_coefficient']} validators** were required to reach one third of voting power and **{f['two_thirds_coefficient']}** to reach two thirds. Validator HHI was **{float(f['validator_hhi_10000']):.2f}**, corresponding to an effective validator count of **{float(f['effective_validator_count']):.2f}**. <sup><a href="#source-2b">2b</a></sup>

| Latest observable state — block {hd} | Result |
|---|---:|
| Active consensus validators | **{f['active_validators']} / 50** |
| Largest / top-three / top-five share | **{float(f['largest_validator_share_percent']):.2f}% / {float(f['top_3_validator_share_percent']):.2f}% / {float(f['top_5_validator_share_percent']):.2f}%** |
| Validators required for one third / two thirds | **{f['one_third_coefficient']} / {f['two_thirds_coefficient']}** |
| Validator HHI / effective validator count | **{float(f['validator_hhi_10000']):.2f} / {float(f['effective_validator_count']):.2f}** |
| Bonded stake / native supply bonded | **{float(f['bonded_l1']):,.2f} L1 / {float(f['bonded_ratio_total_supply_percent']):.2f}%** |
| Active delegator addresses / relationships | **{f['active_delegators']:,} / {f['active_relationships']:,}** |
| Largest / top-five / top-ten active-delegator share | **{float(f['largest_delegator_share_percent']):.2f}% / {float(f['top_5_delegator_share_percent']):.2f}% / {float(f['top_10_delegator_share_percent']):.2f}%** |
| Active-delegator HHI / effective address count | **{float(f['delegator_hhi_10000']):.2f} / {float(f['effective_delegator_count']):.2f}** |
| Delegator one-third / two-thirds coefficients | **{f['delegator_one_third_coefficient']} / {f['delegator_two_thirds_coefficient']}** |

The delegation layer is visible separately from validator voting power. At the latest snapshot, **{f['active_delegators']:,} addresses** delegated to active validators across **{f['active_relationships']:,} active delegation relationships**; **{f['multi_validator_delegators']}** addresses delegated across multiple active validators. The largest active-delegator address represented **{float(f['largest_delegator_share_percent']):.2f}%** of active delegated stake, while the top five represented **{float(f['top_5_delegator_share_percent']):.2f}%**, the top ten **{float(f['top_10_delegator_share_percent']):.2f}%**, and the top 25 **{float(f['top_25_delegator_share_percent']):.2f}%**. Active-delegator HHI was **{float(f['delegator_hhi_10000']):.2f}**, with an effective address count of **{float(f['effective_delegator_count']):.2f}**.

An address is not an entity. Exchanges, custodians and multisigs can aggregate many beneficiaries into one address, while one party can control many addresses. Address-level dispersion is therefore neither an upper nor a lower bound on beneficial-owner dispersion; it is a distinct, weaker measurement of observable ledger distribution.

### Decentralization as an observed trajectory

| Pinned measurement | Active validators | Largest | Top 5 | ⅓ coefficient | ⅔ coefficient | HHI | Effective validators |
|---|---:|---:|---:|---:|---:|---:|---:|
| July whitepaper reference | **20** | **13.09%** | **51.07%** | **3** | **8** | — | — |
| Aug. 11 · block 13,439,825 | **28** | **9.03%** | **35.89%** | **5** | **11** | **520.73** | **19.20** |
| Aug. 15 · block {hd} | **{f['active_validators']}** | **{float(f['largest_validator_share_percent']):.2f}%** | **{float(f['top_5_validator_share_percent']):.2f}%** | **{f['one_third_coefficient']}** | **{f['two_thirds_coefficient']}** | **{float(f['validator_hhi_10000']):.2f}** | **{float(f['effective_validator_count']):.2f}** |

From the whitepaper reference to the latest pinned state, the active set expanded from **20 to {f['active_validators']} validators**; the largest-validator share declined from **13.09% to {float(f['largest_validator_share_percent']):.2f}%** and the top-five share from **51.07% to {float(f['top_5_validator_share_percent']):.2f}%**. The one-third cohort widened from **3 to {f['one_third_coefficient']} validators**, while the two-thirds cohort expanded from **8 to {f['two_thirds_coefficient']}**. Between the two reproducible August snapshots, top-five share moved from **35.89% to {float(f['top_5_validator_share_percent']):.2f}%**, HHI from **520.73 to {float(f['validator_hhi_10000']):.2f}**, and effective validator count from **19.20 to {float(f['effective_validator_count']):.2f}**.

These are measurements, not guarantees about future topology or organizational independence. Their value is precisely that they can be measured again. The repository preserves both August snapshots, raw responses, complete validator and delegation tables, calculations and SHA-256 manifests so later states can be compared without erasing earlier ones.'''

article=root/'content/article-02-next-verifiable-renaissance/article.md'
s=article.read_text()
s=re.sub(r'<!-- CURRENT_NETWORK_BEGIN -->.*?<!-- CURRENT_NETWORK_END -->','<!-- CURRENT_NETWORK_BEGIN -->\n'+block+'\n<!-- CURRENT_NETWORK_END -->',s,flags=re.S)
s=s.replace('2. <span id="source-2"></span>**GenesisL1 current network and protocol-state snapshot at block 13,439,825.**','2. <span id="source-2"></span>**GenesisL1 preserved network and protocol-state snapshot at block 13,439,825.**')
if 'id="source-2b"' not in s:
    s=s.replace('3. <span id="source-3"></span>',f'2b. <span id="source-2b"></span>**GenesisL1 latest delegation-focused snapshot at block {hd}.** Raw validator and delegation responses, complete tables, concentration metrics and SHA-256 manifest. [Latest delegation evidence ↗](https://github.com/GenesisL1/insights/tree/main/evidence/article-02/delegation-state/block-{h})\n3. <span id="source-3"></span>')
s=s.replace('At the latest pinned publication block, GenesisL1 had 28 active consensus validators. The largest held 9.03% of voting power; 5 validators were required to reach one third and 11 to reach two thirds. Exact data and raw responses are preserved in the current evidence snapshot.',f'At the latest delegation-focused snapshot, GenesisL1 had {f["active_validators"]} active consensus validators. The largest held {float(f["largest_validator_share_percent"]):.2f}% of voting power; {f["one_third_coefficient"]} validators were required to reach one third and {f["two_thirds_coefficient"]} to reach two thirds. The earlier block-13,439,825 snapshot remains preserved as a historical comparison point.')
article.write_text(s.rstrip()+'\n')

css=root/'site/insights/article-02.css'
c=css.read_text().replace('--max: 1320px; --article: 790px; --toc: 250px;','--max: 1580px; --article: 980px; --toc: 260px;').replace('gap:86px;','gap:72px;',1)
css.write_text(c)

# Keep author in machine-readable metadata but remove the visible byline from article surfaces.
for name in ['genesisl1-decentralization-scientific-renaissance.html','genesisl1-institutional-briefing-verifiable-ai-sovereign-science.html']:
    p=root/'site/insights'/name
    if p.exists():
        x=p.read_text().replace('<span>By Mikhail Fedorov</span>','').replace('<span>Mikhail Fedorov</span>','')
        p.write_text(x)

# A small machine-readable publication pointer makes the two-snapshot model explicit.
p=root/'content/article-02-next-verifiable-renaissance/delegation-state-latest.json'
p.write_text(json.dumps({'schema':'org.genesisl1.article02.delegation_latest.v1','latest':f,'preserved_history':[{'pinned_height':13439825,'role':'Article 02 historical network/protocol snapshot'},{'pinned_height':h,'role':'latest delegation-focused snapshot'}]},indent=2,sort_keys=True)+'\n')
print(json.dumps({'latest_height':h,'active_validators':f['active_validators'],'active_delegators':f['active_delegators']},indent=2))
