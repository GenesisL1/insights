# GenesisL1: Public Infrastructure for Verifiable AI and Sovereign Science

*A current, evidence-backed account of public ownership, network decentralization, molecular-data integrity and institution-operated scientific infrastructure.*

Scientific computing is becoming more capable, more autonomous and more difficult to audit. A result may depend on a dataset version, model checkpoint, execution environment, access right and sequence of machine actions distributed across services that can later change or disappear.

GenesisL1 is designed to make that computational lineage durable. It is a live public Layer 1 where scientific objects, models, rights, transactions and governance can share one independently verifiable history.

The central proposition is practical: **institutions should be able to verify scientific computation without surrendering control of the data that must remain private.**

## Public ownership is part of the architecture

GenesisL1 launched without a token sale, private round, venture allocation, founder allocation, team allocation, advisor allocation or private unlock schedule. Its disclosed bootstrap distributor retained no allocation after the public one-to-one transition. <sup><a href="#source-1">1</a></sup>

That origin does not by itself guarantee decentralization. It does remove a structural layer of private ownership and future insider vesting beneath the protocol. For scientific infrastructure, that matters: the system preserving evidence should disclose not only how it reaches consensus, but also whose reserved economic claims sit behind it.

The network’s community pool provides a second public mechanism. Protocol-funded resources can be allocated through on-chain governance for shared infrastructure, research tooling and ecosystem development. This is public patronage with a visible ledger rather than a private cap table.

## Current network state

<!-- CURRENT_NETWORK_BEGIN -->
At GenesisL1 block **13,439,614**, dated **August 11, 2026**, the active consensus set contained **28 validators** out of a protocol maximum of 50. The largest validator held **9.03%** of voting power; the top three held **23.20%**, the top five **35.89%**, and the top ten **63.22%**. 5 validators were required to reach one third of voting power and 11 to reach two thirds. The validator HHI was **520.73**, corresponding to an effective validator count of **19.20**. <sup><a href="#source-2">2</a></sup>

| Current observable state | Result |
|---|---:|
| Active consensus validators | **28 / 50** |
| Largest validator share | **9.03%** |
| Top-three / top-five / top-ten share | **23.20% / 35.89% / 63.22%** |
| Validators required for one third / two thirds | **5 / 11** |
| Validator HHI / effective validator count | **520.73 / 19.20** |
| Bonded stake | **24,957,676.89 L1** |
| Bonded share of native supply | **53.36%** |
| Unique delegator addresses to active validators | **1,371** |
| Largest / top-ten active-delegator share | **5.71% / 29.98%** |

Compared on the same two-decimal basis with the whitepaper reference state, the active set expanded from **20 to 28 validators**. The largest-validator share moved from **13.09% to 9.03%** (−4.06 percentage points), the top-three share from **35.62% to 23.20%** (−12.42 points), and the top-five share from **51.07% to 35.89%** (−15.18 points). The one-third coefficient widened from **3 to 5 validators**, and the two-thirds coefficient from **8 to 11**.

Delegation was also distributed across **1,371 active delegator addresses** and **2,063 active validator–delegator relationships**; **218 addresses** delegated across more than one active validator. The largest active delegator address represented **5.71%** of bonded delegation and the top ten represented **29.98%**. An address is not necessarily one beneficial owner: custodians can aggregate many users, while one party can control multiple addresses. These figures therefore measure observable ledger distribution, not complete social independence.
<!-- CURRENT_NETWORK_END -->

This is a snapshot, not a permanent label. Validator power, delegations and supply change continuously. The repository preserves the pinned block, raw responses, complete CSV tables, exact calculations and checksums so the published figures can be reproduced rather than trusted as screenshots.

## A common state for data, models, rights and agents

GenesisL1 combines several primitives that are usually separated across private databases and mutable APIs.

### MOLNFT: molecular records with durable identity

<!-- CURRENT_MOLNFT_BEGIN -->
At the current evidence block, the MOLNFT PDB v2 contract reported **229,271 parent molecular records** and **265,786 total ERC-721 tokens**, including **36,515 child chunks** used to extend larger payloads. Legacy PDB v1 and AlphaFold/Swiss-Prot v1 collections are reported separately because they represent a different storage generation and may overlap scientifically; they are not added to the PDB v2 parent count as one corpus total. <sup><a href="#source-2">2</a></sup>

A separate, precommitted randomized audit tested reconstruction fidelity rather than merely reading counters. The sample size was fixed at **100 records** before the future seed block existed; IDs were drawn without replacement from the pinned PDB v2 parent range, with no off-chain token index and no replacement draws. The finalized result was **100 successful reconstructions, 100 of 100 canonical structural-fidelity passes and zero final failures**. <sup><a href="#source-3">3</a></sup>

One sampled record, 5KCS, had four atom-name labels changed by a documented later RCSB nomenclature revision. Stable atom IDs, every non-name identity field and all **148,945 Cartesian coordinates** remained aligned, with maximum deviation of **0 Å**. It is therefore recorded as a structural-fidelity pass, with the nomenclature revision retained transparently as provenance—not as a second score.
<!-- CURRENT_MOLNFT_END -->

The important distinction is between **identity and storage syntax**. A scientific object can remain the same molecular structure even when an external reference archive later normalizes a label. The audit therefore evaluates declared structural criteria—atom counts, chain and entity sets, atom identity and coordinate agreement—while preserving the exact reconstructed and canonical objects for independent inspection.

### Model NFTs and GL1F: replayable computational instruments

Model NFTs can bind a model’s identity, serialized parameters, access rules and invocation history. GL1F adds deterministic on-chain inference for supported model classes, so the same model bytes, input and execution rules can produce a replayable result across independent nodes. <sup><a href="#source-4">4</a></sup>

This does not make a model scientifically correct. It makes the computational instrument identifiable: another party can determine which model was used, under which rules, and what the network recorded.

### CIPNFT: protected disclosure with public provenance

CIPNFT provides a rights layer for confidential scientific assets. Its public implementation encrypts content client-side, records ciphertext and provenance on-chain, and supports recipient-bound disclosure without requiring a private application server to hold the scientific plaintext. <sup><a href="#source-5">5</a></sup>

Public verification and confidentiality are not opposites. The ledger can preserve object identity, rights, commitments and authorized outputs while raw genomes, clinical records, proprietary methods and personal identifiers remain under institutional custody.

### AI agents: action under inspectable rules

AI agents can discover registered objects, verify model and rights metadata, invoke deterministic computation and record authorized actions against the same public history. The value is not autonomy alone; it is **accountable autonomy**—machine action whose inputs, permissions and outputs can be inspected after the interface that initiated it has disappeared.

## Institutional sovereignty without isolation

A national genome program, public biobank, university or health-research authority should not need to upload sensitive source data to a common public database in order to participate in a shared verification system.

GenesisL1 supports a three-layer boundary:

1. **Sovereign custody.** Raw data, identities, consent records, encryption keys and internal access systems remain local.
2. **Protected disclosure.** CIPNFT can carry encrypted assets, rights and recipient-bound access when information must cross institutional boundaries.
3. **Common verification.** Public objects, commitments, model and method identities, authorized outputs and transaction history can be independently verified from any node.

An institution can therefore run an approved model within its own environment, publish only a permitted aggregate or commitment, and tie that output to a specific model, method and authorization record. Another institution can verify the lineage without receiving the underlying personal data.

This is **local custody, selective disclosure and shared proof**.

## What the ledger proves—and what it does not

On-chain verification can establish:

- which object, model, code, account and rights state were referenced;
- which transaction and execution path produced a recorded output;
- whether the same public state and deterministic rules reproduce that output;
- when a claim or asset entered the shared history and what later changed.

It cannot establish scientific truth by itself. Biological validity, clinical utility and causal interpretation still require appropriate datasets, experimental design, independent reproduction, peer review and, where applicable, laboratory or clinical testing.

The ledger is an evidence and coordination layer—not a substitute for science.

## L1 coin: protocol resource, not a private claim

L1 coin is the native resource used for transaction fees, smart-contract execution, staking security, governance and the community pool. Scientific applications may also use it for authorized access, model invocation or machine-to-machine settlement. <sup><a href="#source-1">1</a></sup>

L1 coin is not equity, a revenue claim or a promise of return. Its role is operational: it meters and secures the public protocol.

## A concrete institutional operating model

Participation should mean operation rather than endorsement. An institution can contribute by:

- running an independently controlled validator;
- preserving an archive node and local indexer;
- verifying one bounded scientific workflow from explicit inputs to authorized output;
- defining a memorandum covering custody, security, scientific scope, publication and continuity.

The objective is not to place every scientific byte on a blockchain. It is to make the identity, provenance, rights and permitted computational history of important scientific objects durable enough to survive individual applications, vendors and sponsors.

## The verifiable scientific renaissance

The printing press made knowledge portable. Scientific journals made claims inspectable. Networked computing made collaboration global. The next step is to make computational scientific history independently verifiable.

GenesisL1 brings public ownership, measurable consensus, molecular-data provenance, deterministic model execution, encrypted rights and accountable agents into one live scientific Layer 1.

The result is not a promise that every claim is true. It is a stronger foundation for discovering **what was used, who was authorized, what was executed and whether another institution can verify it**.

---

## Frequently asked questions

### What is the current GenesisL1 validator state?

At the latest pinned publication block, GenesisL1 had 28 active consensus validators. The largest held 9.03% of voting power; 5 validators were required to reach one third and 11 to reach two thirds. Exact data and raw responses are preserved in the current evidence snapshot.

### What did the randomized MOLNFT audit find?

The precommitted 100-record audit produced 100 successful reconstructions, 100 canonical structural-fidelity passes, zero final failures and no replacement draws. The documented 5KCS atom-name revision is preserved as provenance and does not represent structural loss.

### Can sensitive scientific data remain local?

Yes. Raw data, identities, consent records and keys can remain under local institutional custody while the shared ledger carries permitted commitments, encrypted assets, model and method identities, rights and authorized outputs.

### Is blockchain verification the same as scientific validation?

No. Blockchain verification establishes the computational and rights record. Scientific validity still depends on domain evidence, experimental design, reproduction, peer review and appropriate laboratory or clinical validation.

### What is L1 coin used for?

L1 coin pays network fees, meters smart-contract execution, secures consensus through staking, participates in governance and supports the community pool. It is not equity or a promise of return.

## Sources and verification

<!-- CURRENT_SOURCES_BEGIN -->
1. <span id="source-1"></span>**GenesisL1 Technical Whitepaper, Version 1.0, July 2026.** Public distribution, protocol architecture, L1 coin utility, governance and institutional operation. [Whitepaper ↗](https://genesisl1.com/whitepaper.pdf)
2. <span id="source-2"></span>**GenesisL1 current network and protocol-state snapshot at block 13,439,614.** Raw CometBFT, Cosmos and EVM responses; complete validator and delegation tables; current MOLNFT counters; calculations and SHA-256 manifest. [Current evidence ↗](https://github.com/GenesisL1/insights/tree/main/evidence/article-02/network-state/block-13439614)
3. <span id="source-3"></span>**GenesisL1 randomized MOLNFT reconstruction evidence at block 13,436,937.** Precommitted sample, future-block seed, direct NFT-ID calls, reconstructed and canonical BinaryCIF objects, per-record outcomes and checksums. [Audit evidence ↗](https://github.com/GenesisL1/insights/tree/main/evidence/article-02/molnft/block-13436937)
4. <span id="source-4"></span>**GenesisL1 Forest / GL1F.** Deterministic model representation and inference tooling. [Source ↗](https://github.com/GenesisL1/Forest) · [Technical paper ↗](https://gl1f.com/GL1F.pdf)
5. <span id="source-5"></span>**GenesisL1 CIPNFT.** Client-side encryption, on-chain ciphertext provenance and recipient-bound disclosure. [Source ↗](https://github.com/GenesisL1/cipnft)
6. **CometBFT consensus specification, v0.38.** Voting-power and commit-threshold model. [Specification ↗](https://docs.cometbft.com/v0.38/spec/consensus/consensus)
<!-- CURRENT_SOURCES_END -->

<!-- CURRENT_MEASUREMENT_BEGIN -->
**Measurement note.** Current validator, delegator, stake and MOLNFT counter figures are pinned to GenesisL1 block 13,439,614. Publication comparisons use two-decimal displayed values consistently; exact integers and higher-precision calculations remain in the machine-readable snapshot. The randomized MOLNFT reconstruction audit is a separate immutable experiment pinned to block 13,436,937.
<!-- CURRENT_MEASUREMENT_END -->

This article is informational and published by GenesisL1 about GenesisL1. Nothing here is an offer, a promise of return or investment advice.
