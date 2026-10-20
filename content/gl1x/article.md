---
slug: gl1x-blockchain-explorer-mcp-bioinformatics
kicker: Article 04 · Platform
title_tag: "GL1X: GenesisL1's MCP Explorer and On-Chain Bioinformatics Lab"
h1: "GL1X: The Ledger Is Now a Laboratory"
deck: "GenesisL1 is the Layer 1 built for science. Its explorer, GL1X, has become the network's instrument: it follows every movement of the L1 coin, works on over a million molecular records and opens both to AI agents. Other explorers have MCP servers; to our knowledge, only GL1X brings on-chain scientific data, a wide range of bioinformatics tools and an MCP server for agents together under one roof."
measured: "20 October 2026 (UTC), on https://gl1x.com running GL1X 3.4.1: the archive and the 4HHB walk-through at 05:34–05:44, the L1 figures at 06:27 (block 13,869,694)"
---

## Science finally has a ledger it can work on {#a-ledger-science-can-work-on}

Every great instrument changed what science could ask. The telescope turned the sky into data. The sequencer turned the genome into text. GenesisL1 asks the next question: what happens when the ledger itself becomes an instrument — when the records of science, the models built on them and the rights around them live on a public chain that anyone can read, verify and build on?

GenesisL1 is a sovereign Layer 1 built for decentralized science. It has produced blocks since November 2021, joins a Cosmos SDK chain to an integrated EVM, and holds what most blockchains never attempt: more than a million molecular records, machine-learning models stored and run as NFTs, encrypted intellectual property, and a community-governed treasury for public goods. The [technical foundation](./genesisl1-desci-blockchain-verifiable-ai-model-nfts.html) of the network is described in the first article of this series.

A ledger like that needs more than a block explorer. It needs an instrument — one that a scientist, a student and an AI agent can all pick up. That instrument is **GL1X**.

## GL1X, the instrument of GenesisL1 {#the-instrument-of-genesisl1}

GL1X is the explorer of GenesisL1 and its on-chain bioinformatics laboratory, in one open-source program. For the ledger, it shows everything: every block, transaction, account, token, contract, validator and governance proposal, on the EVM and the Cosmos side alike. For the science, it does the work: it searches sequences, compares three-dimensional structures, maps where molecules bind, models how a protein behaves at the pH of the stomach or the blood, reads the literature and turns results into datasets for AI models that run on chain.

It serves two kinds of visitors at once. A scientist in a browser and an AI agent working through the Model Context Protocol see the same records, run the same tools and get the same answers. Other explorers now give agents MCP access to ledger data; what sets GL1X apart is what stands behind its server. To our knowledge, it is the only blockchain explorer that brings on-chain scientific and molecular data, a wide range of bioinformatics tools and an MCP server for AI agents together under one roof.

The scale is already real. On 20 October 2026, [gl1x.com](https://gl1x.com/) indexed **1,035,581 molecular records** in nine collections — experimental structures from the Protein Data Bank, AlphaFold models, HLA records — holding **2,069,579 sequences** and **611 million residues**. It had analysed **998,926 structures** atom by atom: **4.18 million pockets**, **2.35 million interfaces** between chains and **3.68 million ligand instances** of **42,240 chemical components**. Every record can be searched, compared and cited, and its sequences proved.

## The L1 coin, in full view {#the-l1-coin-in-full-view}

At the centre of GenesisL1 is its native coin, **L1**. It is the network's working resource, and GL1X treats it that way. L1 pays for every transaction and computation. It prices the permanent writes that put scientific data and models on chain. Validators and delegators bond it to secure consensus, and bonded L1 weights every governance vote. Applications can settle in it — access to a model, the sale of an encrypted research file. And a share of it flows into a community pool that only governance can spend, to fund the network's public goods.

Because L1 is how GenesisL1 works, a large part of GL1X is devoted to following it: total and circulating supply; staking, with every delegation; [validators](https://gl1x.com/validators) with their voting power, commission and uptime; [governance](https://gl1x.com/governance) proposals across every generation of the chain, with their votes; the [community pool](https://gl1x.com/community-pool) and what governance has spent from it; [accounts](https://gl1x.com/accounts) ranked by all the L1 they hold — liquid, staked, unbonding and rewards; IBC transfers to other chains; and every transaction, on both sides of the network. One account is one page, in both of its address forms, `0x…` and `genesis1…`.

On 20 October 2026, GL1X showed L1 at work:

- **52.6%** of all L1 bonded to secure the network, through **37 active validators** and **3,153 stakers**;
- **5.56 million L1** — 11.6% of supply — in the community pool, held for public goods;
- **113 governance proposals** on record;
- **1,345,838 transactions** and **52,811 accounts** on the ledger.

<figure class="wide"><button class="hero-button" data-lightbox="./assets/gl1x-l1-agents-infographic.webp" type="button"><img alt="Infographic: questions about the L1 coin asked in plain language by an AI assistant such as Claude or ChatGPT, answered through gl1x.com/mcp from the GenesisL1 ledger — 52.6% of L1 bonded, 37 active validators, 5.56 million L1 in the community pool, and every transaction" height="1000" loading="lazy" src="./assets/gl1x-l1-agents-infographic.webp" width="1600"/></button><figcaption>Ask the chain: any question about L1 becomes a call to GL1X, answered from the ledger itself. Figures from gl1x.com on 20 October 2026.</figcaption></figure>

Any of it can be asked in plain language. Connect Claude or ChatGPT to `https://gl1x.com/mcp` and ask: *How much L1 is staked, and with which validators? What is in the community pool, and which proposals have spent from it? What did this account do this month? Trace this transaction.* The assistant answers from GL1X's index of the chain rather than from memory, and gives the blocks, accounts and transactions to check it against.

## AI agents, first-class researchers {#ai-agents-first-class-researchers}

The [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) is the open standard through which AI assistants use tools. GL1X speaks it natively: the same program that serves the explorer's pages answers agents at **`https://gl1x.com/mcp`**. There is no key to request, no account to open and no separate service in between. Every tool is read-only — an agent can look, search, compute and prove, but it never signs anything and never moves a coin.

Behind that one address sit **87 tools**: 31 for the ledger, 43 for the laboratory, 6 for AI models stored on chain and 7 for a game of chess against a neural network that lives in a smart contract. The documentation's 30 pages are served to agents too, so an agent can read how a tool works before it uses it, and five ready-made prompts chain the tools into complete workflows: a scientific report on any record, a machine-learning dataset of a protein's relatives, an account overview, the chain's status and a sequence proof.

<figure class="wide"><button class="hero-button" data-lightbox="./assets/gl1x-mcp-87-tools-infographic.webp" type="button"><img alt="Infographic: the 87 MCP tools of GL1X grouped by what they reach — 31 ledger tools, 43 laboratory tools, 6 GL1F model tools and 7 chess tools — around one MCP endpoint" height="1000" loading="lazy" src="./assets/gl1x-mcp-87-tools-infographic.webp" width="1600"/></button><figcaption>One endpoint, 87 read-only tools: the ledger, the laboratory, on-chain AI models and chess.</figcaption></figure>

Connecting takes a minute:

- **Claude** — add a custom connector with the URL `https://gl1x.com/mcp`.
- **ChatGPT** — where your plan offers developer mode, turn it on and add the same URL as a custom app.
- **Claude Code** — `claude mcp add --transport http gl1x https://gl1x.com/mcp`.
- **Cursor, VS Code, Windsurf** and other clients that support remote servers — add a remote MCP server with the same URL; clients that only start local programs can use the relay `gl1x mcp --url https://gl1x.com/mcp`.
- **No assistant at all** — the [MCP page](https://gl1x.com/dapps/mcp) lists every tool and runs it in the browser, and [`/llms.txt`](https://gl1x.com/llms.txt) introduces GL1X to any language model.

Other explorers have opened their ledgers to agents too: [Blockscout](https://docs.blockscout.com/devs/mcp-server) and [Etherscan](https://docs.etherscan.io/ai/mcp), for example, run MCP servers for blockchain data. The difference lies in what GL1X's server reaches. Beside the ledger stand the scientific records stored on GenesisL1 and the research suite that works on them, all served by the same program as the explorer — a combination that, to our knowledge, no other blockchain explorer offers. The full reference is [MCP: the explorer as tools for agents and LLMs](https://gl1x.com/docs/mcp).

<figure><button class="hero-button" data-lightbox="./assets/gl1x-mcp-page-screenshot.webp" type="button"><img alt="Screenshot of the GL1X MCP page: 'Give an AI agent the whole GenesisL1 explorer', with the endpoint https://gl1x.com/mcp, 87 tools, protocol 2025-11-25, Streamable HTTP" height="1272" loading="lazy" src="./assets/gl1x-mcp-page-screenshot.webp" width="2188"/></button><figcaption>The MCP page of the explorer: one endpoint, and the connection lines for any MCP client.</figcaption></figure>

## A laboratory over a million molecules {#a-laboratory-over-a-million-molecules}

*Bioinformatics onchain* is GL1X's research suite. Each tool is a page in the browser, a route in the API and a tool for agents, so a question asked by a person and a question asked by an agent are the same question.

- **Find anything.** Search a million records by PDB ID, protein name, UniProt accession, sequence or a short motif. [Search](https://gl1x.com/bio/search) · [how it works](https://gl1x.com/docs/molnft)
- **Compare sequences.** BLAST, compatible with the NCBI standard, across 1,288,423 protein sequences, in a fraction of a second. [BLAST](https://gl1x.com/bio/blast) · [the engine](https://gl1x.com/docs/blast)
- **Compare shapes.** Find proteins that fold alike across 1,558,073 chains, even when their sequences have drifted apart. [Structure search](https://gl1x.com/bio/structure) · [the method](https://gl1x.com/docs/structures)
- **See what binds.** Drugs, cofactors, metals and sugars — 3.68 million ligand instances, each with the residues that hold it. [Ligands](https://gl1x.com/bio/ligands) · [the index](https://gl1x.com/docs/ligands)
- **Find where a drug could bind.** 4.18 million pockets scored for druggability, and 2.35 million interfaces between chains. [Pockets](https://gl1x.com/bio/pockets) · [interfaces](https://gl1x.com/bio/interfaces) · [analysis](https://gl1x.com/docs/analysis)
- **Ask the chemistry.** How a protein's charges change in the stomach, the blood or a lysosome — 19 body and cell environments. [Research workbench](https://gl1x.com/bio/workbench) · [pH environments](https://gl1x.com/docs/ph)
- **Work with peptides.** Digest proteins with 24 enzymes, find peptides unique to one protein across the archive, compute masses, fragments and isotope patterns, identify spectra. [Proteomics](https://gl1x.com/bio/proteomics) · [the tools](https://gl1x.com/docs/proteomics)
- **Follow evolution.** Align families, map conservation, find residues that co-evolve, scan variants. [Families](https://gl1x.com/bio/families) · [the methods](https://gl1x.com/docs/families)
- **Read the literature.** PubMed, mapped into topics by Broccoli. [PubMed](https://gl1x.com/bio/pubmed) · [Broccoli](https://gl1x.com/docs/broccoli)
- **Build training data.** Turn search hits or any list of records into a dataset ready for GL1F, GenesisL1's on-chain machine learning. [Datasets](https://gl1x.com/bio/datasets) · [GL1F](https://gl1x.com/gl1f)
- **Prove it.** Derive any record's sequences again from the chain and CID-checked IPFS, and check them. [Proofs](https://gl1x.com/docs/molnft#proofs)

<figure><button class="hero-button" data-lightbox="./assets/gl1x-research-suite-screenshot.webp" type="button"><img alt="Screenshot of the Bioinformatics onchain page of GL1X: cards for molecular search, BLAST, profile HMM search, structure search, ligands, the research workbench, pockets, interfaces, patterns, 3D templates, modifications, proteomics, families and variants, datasets, MCP and the API" height="2340" loading="lazy" src="./assets/gl1x-research-suite-screenshot.webp" width="2188"/></button><figcaption>The research suite at gl1x.com/bio: every tool is a page, an API route and a tool for agents.</figcaption></figure>

Nothing in the suite is a dead end. Every structure links to its record, the research workbench and its literature. Every list of hits becomes a dataset, every dataset can become an AI model that runs on chain, and every model can be checked against its on-chain bytes. That is what *interoperable* means here: one discovery is the starting point of the next.

## Peptides, longevity and the questions ahead {#peptides-longevity-and-the-questions-ahead}

Some of the most consequential questions in biology today concern peptides and ageing. The archive on GenesisL1 already holds the structures researchers reach for first:

- the GLP-1 receptor bound to **semaglutide** ([7KI0](https://gl1x.com/token/0xd58B01f6C18086e5202cdC5D7Ad3E41790360102/instance/184543), stored entirely on chain) and to **tirzepatide**, in twelve records that include its second target, the GIP receptor;
- **SIRT6**, the sirtuin studied in DNA repair and lifespan, in 64 records — among them SIRT6 [bound to a nucleosome](https://gl1x.com/token/0xd58B01f6C18086e5202cdC5D7Ad3E41790360102/instance/215389);
- **α-Klotho**, the ageing-linked co-receptor, [resolved by cryo-EM](https://gl1x.com/token/0xd58B01f6C18086e5202cdC5D7Ad3E41790360102/instance/222049);
- **telomerase**, in 185 records, and **mTOR**'s rapamycin-binding domain among 103 records on rapamycin.

With GL1X, a researcher — or an agent working for one — can pick up any of these and keep going: compare how two peptide drugs meet the same receptor, find every structure that binds the same cofactor, compute a peptide's mass and fragments, model the receptor's charges at blood pH, gather the papers that matter and build a dataset to train an on-chain model. All of it is computation on public records, open to verification; none of it is medical advice. What it offers is speed, openness and an audit trail — the conditions under which a decentralized research community can do science together.

## One record, ten answers {#one-record-ten-answers}

To show how one answer leads to the next, we followed a single record through the suite on 20 October 2026: human haemoglobin, **4HHB**. Ten steps took nine MCP calls, and each began where the last one ended.

1. **Find it.** The record is stored entirely on chain as [token 93945](https://gl1x.com/token/0xd58B01f6C18086e5202cdC5D7Ad3E41790360102/instance/93945), minted in [block 10,624,642](https://gl1x.com/block/10624642), with a second copy on IPFS.
2. **Prove it.** GL1X derived all four protein chains again from the chain's own state at block 13,869,469 and matched them by SHA-256.
3. **Read its ligands.** Four haem groups, each held by a histidine, and two phosphates in the cleft where 2,3-bisphosphoglycerate binds.
4. **Go archive-wide.** [Haem](https://gl1x.com/bio/ligands/HEM) appears 25,030 times in 11,026 records.
5. **Follow a thread.** In a sample of 5,000 of those records, 565 also hold [tetrahydrobiopterin](https://gl1x.com/bio/ligands/H4B) — haem's partner in the nitric-oxide synthases.
6. **Ask the chemistry.** GL1X found the salt bridge of Perutz's account of the Bohr effect and moved its histidine's pKa the right way, to 6.86 — though not as far as the 8.1 measured by Ohe and Kajita in 1980. The published [pKa benchmark](https://gl1x.com/docs/paper-pka) sets out where the model is strong and where it falls short.
7. **Compare shapes.** The β chain against 1,558,073 protein chains, in about a second.
8. **Compare sequences.** BLAST against 1,288,423 protein sequences, in about a quarter of a second; every hit carries a proof.
9. **Read the literature.** The structure's title found [3,029 PubMed records](https://gl1x.com/bio/pubmed#q=human+deoxyhaemoglobin), among them the 1984 paper that reported it.
10. **Build a dataset.** The BLAST hits became 25 rows of 89 inputs, packed the way an on-chain GL1F model takes them.

<figure class="wide"><button class="hero-button" data-lightbox="./assets/gl1x-discovery-chain-infographic.webp" type="button"><img alt="Infographic: ten connected steps from the on-chain haemoglobin record 4HHB — proof, ligands, haem sites across the archive, tetrahydrobiopterin, pH, structure search, BLAST, PubMed, and a GL1F dataset — with the numbers gl1x.com returned" height="1200" loading="lazy" src="./assets/gl1x-discovery-chain-infographic.webp" width="1600"/></button><figcaption>One record, ten answers from nine MCP calls; every computed number is the explorer's answer on 20 October 2026.</figcaption></figure>

Ten steps, one protocol, nothing copied by hand. A path like this can begin at any of the million records, and an agent can walk it again, record after record.

## Broccoli: the literature as a map {#broccoli-the-literature-as-a-map}

A literature search usually ends in a list: thousands of titles, ranked by an engine that cannot tell you what the field is made of. On GL1X it ends in a map.

**Broccoli** is Decentralized Science Labs' open-source clustering engine, released under the MIT License. On the [PubMed page](https://gl1x.com/bio/pubmed) it takes up to 2,000 records and groups them into named topics in the reader's own browser — there is no clustering server, and GL1X keeps no record of what is searched. Its random steps are seeded, so the same records with the same settings always draw the same map.

It finds topics three ways — **Lingo**, which discovers the main concepts first and then names them; **Suffix Tree Clustering**, which groups records by the phrases they share; and **bisecting k-means** — and draws them four ways: an **organic treemap**, **bubbles**, a **radial** sunburst and **florets**, a head of broccoli seen from above with every paper a bud on a sunflower spiral. Click a topic and it opens into subtopics, six levels deep. Every structure in GL1X links to its papers by PDB ID and by title; for an agent, structure to literature is two calls.

<figure><button class="hero-button" data-lightbox="./assets/gl1x-pubmed-broccoli-screenshot.webp" type="button"><img alt="Screenshot of the PubMed search page of GL1X: a search box with Lingo, STC and k-means, and Broccoli's florets map of example searches" height="1452" loading="lazy" src="./assets/gl1x-pubmed-broccoli-screenshot.webp" width="2188"/></button><figcaption>PubMed search on gl1x.com, with Broccoli's florets map. Every structure in the explorer links here.</figcaption></figure>

<figure class="wide"><button class="hero-button" data-lightbox="./assets/gl1x-broccoli-maps-infographic.webp" type="button"><img alt="Infographic of Broccoli's four maps: organic treemap, bubbles, radial sunburst and florets, with the three clustering algorithms Lingo, STC and bisecting k-means" height="900" loading="lazy" src="./assets/gl1x-broccoli-maps-infographic.webp" width="1600"/></button><figcaption>Broccoli's four ways of drawing a literature. The layouts are illustrative; on gl1x.com every topic is named from its records.</figcaption></figure>

Broccoli is honest about what it is: it groups papers by shared words and phrases, not by meaning, so synonyms that share no word stay apart. In return it is fast, private and reproducible. The design is documented in [Broccoli: topic maps in the browser](https://gl1x.com/docs/broccoli).

## Proof, not trust {#proof-not-trust}

A scientific instrument earns trust through calibration, and GL1X publishes its own. Its BLAST gives the same results as NCBI BLAST+ 2.12.0 across 78 configurations. Its structure aligner agrees with the reference TM-align on 2,260 comparisons, one tie aside. Its secondary-structure assignment matches the reference program on 99.97% of residues, and its peptide masses match the reference library to within 10<sup>−8</sup> daltons. Its pKa model is benchmarked against 365 measured values, with the weak spots published alongside the strengths.

What GL1X shows, it can prove. A [sequence proof](https://gl1x.com/docs/molnft#proofs) derives a record's sequences again from the chain and CID-checked IPFS at a fixed block and lists every call, so anyone can replay it against their own node. GL1F models are rebuilt from their on-chain bytes and checked against the identity they claim. The methods are written up in six [papers](https://gl1x.com/docs/papers). On GenesisL1, nobody has to take anyone's word for it.

## Open source, MIT, built to be shared {#open-source-mit}

GL1X is free software under the **MIT License**, presented by **Decentralized Science Labs LLC**, which builds the explorer, its MCP server and Broccoli, and **Bioinformatics LLC**, which builds its scientific components. Each licenses its parts under the MIT License, so GL1X as a whole is open, at [github.com/GenesisL1/gl1x](https://github.com/GenesisL1/gl1x).

It runs as a single Go program with PostgreSQL, and one installer sets up a complete mirror of the explorer and the laboratory. Universities, institutes, validators and companies can run their own — and every mirror makes GenesisL1's public infrastructure more resilient.

## Where this goes {#where-this-goes}

Our aim is plain: GL1X should serve hundreds of thousands of researchers, students, builders and AI agents every month in the years ahead. The design points that way. Every record, ligand, protein, proposal and validator is a page that search engines can index, and an Atom feed tells them what is new. Nothing requires an account. Agents are first-class visitors. And the surface keeps growing — in recent releases from 57 MCP tools to 87, and from 144 API routes to 186.

The larger idea is GenesisL1's: a public ledger where scientific data, models and rights live together, secured and governed through L1 by the community that uses them. GL1X is how that ledger becomes usable — by a scientist at the bench, by a student with a browser, and by the AI agents that will increasingly do research beside them.

The ledger is now a laboratory. Bring your questions — or your agent.

## Frequently asked questions {#faq}

### What is GL1X?

GL1X is the explorer of the GenesisL1 blockchain and an on-chain bioinformatics laboratory. It shows every block, transaction, account and L1 coin flow of the network, and works on over a million molecular records with sequence and structure search, binding-site and pH analysis, peptide and proteomics tools, families and variants, and PubMed search with Broccoli topic maps — for people in the browser and for AI agents through MCP.

### How is GL1X related to GenesisL1?

GenesisL1 is a sovereign Layer 1 blockchain for decentralized science. GL1X is its instrument: the explorer through which the network's ledger, its molecular records, its on-chain AI models and its applications are read, analysed and verified.

### What is the L1 coin used for?

L1 is the native coin of GenesisL1 and its working resource. It pays for transactions and computation, prices permanent scientific writes, secures the network when validators and delegators bond it, weights governance votes, settles applications and funds public goods through the community pool. GL1X shows all of these flows.

### Can I ask an AI assistant about L1 and GenesisL1?

Yes. Connect Claude, ChatGPT or any assistant that supports remote MCP servers to https://gl1x.com/mcp and ask in plain language — about staking and validators, the community pool, governance, an account or a transaction. The assistant answers from GL1X's index of the chain.

### What makes GL1X different from other blockchain explorers?

Other explorers, Blockscout and Etherscan among them, offer MCP servers for ledger data. GL1X brings three things together: the GenesisL1 ledger with the scientific and molecular records stored on it, a wide range of bioinformatics tools that work on those records, and an MCP server whose 87 read-only tools open all of it to AI agents. To our knowledge, it is the only blockchain explorer that combines the three.

### What is Broccoli?

Broccoli is Decentralized Science Labs' MIT-licensed JavaScript engine that clusters up to 2,000 PubMed records into named topics in the browser, with Lingo, Suffix Tree Clustering or bisecting k-means, and draws them as an organic treemap, bubbles, a radial map or florets.

### Is GL1X open source?

Yes. GL1X is released under the MIT License by Decentralized Science Labs LLC and Bioinformatics LLC, with the source at github.com/GenesisL1/gl1x. Anyone can run a complete mirror.

### Can I verify what GL1X shows?

Yes. Sequence proofs derive a record's sequences again from the chain at a fixed block and from content-checked IPFS data, with every call listed for replay; GL1F models are rebuilt from their on-chain bytes; and the engines that have a reference program are checked against it, with the results published in the documentation.

<hr/>

## Sources {#sources}

1. **GL1X documentation.** [Open the documentation ↗](https://gl1x.com/docs)
2. **MCP: the explorer as tools for agents and LLMs.** [Open the MCP reference ↗](https://gl1x.com/docs/mcp)
3. **GL1X: an MCP-native blockchain explorer for agentic exploration of a scientific Layer-1** (technical report, October 2026). [Open the paper ↗](https://gl1x.com/docs/paper-mcp)
4. **Decentralized bioinformatics over on-chain molecular records** (technical report, October 2026). [Open the paper ↗](https://gl1x.com/docs/paper-bioinformatics)
5. **Broccoli: topic maps in the browser.** [Open the Broccoli documentation ↗](https://gl1x.com/docs/broccoli)
6. **GL1X pKa values against experiment** (technical report, October 2026). [Open the benchmark ↗](https://gl1x.com/docs/paper-pka)
7. **GenesisL1: The DeSci Layer 1 Where Scientific Data, Verifiable AI and Digital Rights Become One System** (GenesisL1 Insights). [Read the article](./genesisl1-desci-blockchain-verifiable-ai-model-nfts.html)
8. **GL1X source code and licence.** [Open the repository ↗](https://github.com/GenesisL1/gl1x)
9. **Fermi G, Perutz MF, Shaanan B, Fourme R. The crystal structure of human deoxyhaemoglobin at 1.74 Å resolution.** J Mol Biol 1984;175:159–174. [Open in PubMed ↗](https://pubmed.ncbi.nlm.nih.gov/6726807/)
10. **Model Context Protocol.** [Open the specification site ↗](https://modelcontextprotocol.io/)
11. **The discovery chain: queries, key results and a capture script.** [Open the evidence repository ↗](https://github.com/GenesisL1/insights)
12. **Blockscout MCP server** (Blockscout documentation). [Open the documentation ↗](https://docs.blockscout.com/devs/mcp-server)
13. **Etherscan MCP** (Etherscan documentation). [Open the documentation ↗](https://docs.etherscan.io/ai/mcp)

This article describes public software and public data. GL1X's scientific outputs are computational — pKa estimates on fixed coordinates, druggability scores that are not probabilities of binding, model predictions — and are not clinical or biomedical claims. L1 is described here by its functions in the GenesisL1 network; nothing in this article is an offer, a solicitation or investment advice.
