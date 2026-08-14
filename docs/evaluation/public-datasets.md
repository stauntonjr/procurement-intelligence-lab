# Public dataset catalog

This catalog identifies public datasets that can support development and
modeling across the procurement-intelligence pipeline. It starts with BOM and
assembly-adjacent sources, then lists labeled proxy datasets for document
structure, extraction, entity resolution, retrieval, numerical reasoning,
anomaly detection, and forecasting.

## Scope and decision

This search did not identify a public, labeled corpus that combines data-center
BOMs, vendor quotes, purchase orders, revisions, deliveries, prices, and
claim-level provenance. That gap is material. The project should therefore use
a versioned synthetic procurement corpus as its domain-specific gold set, while
using the public datasets below to develop adapters, baselines, and transferable
components.

No dataset should be downloaded into the public repository by default. Record
the source URL, version or retrieval date, license/terms, checksum, schema
adapter, and any transformations in an evaluation manifest before use.

## 1. BOM, assembly, and procurement-adjacent sources

| Dataset or source | Labels / supervision | Use in this project | Access and caveats |
| --- | --- | --- | --- |
| [PNNL DATA-ME](https://data.pnnl.gov/group/nodes/dataset/34891) | Structured Excel template for mechanical/electrical building inventory, including materials, manufacturing origin, costs, and transportation fields; not a supervised extraction gold set | Closest public domain-shaped schema for data-center mechanical/electrical inventory and BOM-to-input/output conversion | PNNL Datahub source; verify dataset and derivative-use terms before redistribution |
| [Autodesk Fusion 360 Gallery Assembly Dataset](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/assembly.md) | Assembly/component relationships, UUIDs, geometry, materials, physical properties, and user-selected category/industry tags; not procurement labels | Assembly hierarchy, component identity, structural relationships, and source-location modeling | CAD data is not a procurement corpus; follow the repository and source-design terms |
| [Public CAD Assembly Repository](https://3dassemblyrepository.ge.imati.cnr.it/) | 137 STEP assemblies, 12,783 parts, 11 assembly classes; class labels but no SKU, price, vendor, or delivery labels | Assembly decomposition and graph/relationship experiments | Research-oriented CAD repository; verify download and reuse conditions |
| [Microchip public BOM example](https://www.microchip.com/en-us/development-tool/DM240001) | A public multi-page BOM document with part number, revision, type, manufacturer, vendor/part number, description, and quantity fields | Manual extraction smoke test and field-schema inspiration; not a dataset | Treat as a document example, not as training data; verify document terms |
| [Open Contracting Data Registry](https://data.open-contracting.org/) | OCDS procurement lifecycle records with unique contracting IDs, parties, stages, values, and sometimes linked documents; structured labels rather than document-extraction labels | Procurement lifecycle, vendor, award, value, and temporal-state adapter tests | Registry covers 100+ publishers and supports bulk JSON/Excel/CSV; each publisher has its own quality and terms |
| [USAspending API](https://api.usaspending.gov/) and [endpoint documentation](https://api.usaspending.gov/docs/endpoints) | Federal award transactions, recipients, locations, amounts, NAICS, and Product/Service Codes; no BOM line-item or document labels | Public procurement context, vendor/award normalization, cost and geography-shaped queries | Government structured spending data, not data-center BOM truth; respect API and source terms |
| [Consip MEPA direct-order dataset](https://dati.consip.it/dataset/dataset-ordini-diretti-di-acquisto-sul-mepa) | Aggregated public purchases by year, tender/category, administration, geography, supplier region, goods/service category, and value | Aggregate procurement and category-normalization experiments | Italian public data; aggregated rather than line-level BOM/PO data |

### BOM conclusion

The first domain fixture should remain synthetic. Public BOM/CAD sources can
inform field names, hierarchy, units, and document layouts, but they do not
provide the required labeled chain from source artifact through assertion,
entity resolution, reconciliation, and operational state.

## 2. Document layout, tables, and line-item extraction

| Dataset | Labels / supervision | Use in this project | Access and caveats |
| --- | --- | --- | --- |
| [DocILE](https://github.com/rossumai/docile) | Key Information Localization and Extraction plus Line Item Recognition; field type, page, bounding box, text, and line-item grouping; includes fields such as description, quantity, and price | Highest-priority public proxy for invoice/PO-like field and line-item extraction, localization, and abstention evaluation | Dataset download requires a token; follow the benchmark’s current terms and do not assume the public code license covers all data |
| [PubTables-1M](https://github.com/microsoft/table-transformer) | Table detection and structure annotations with cell topology, content, location, and row/column structure | Table reconstruction, cell localization, row grouping, and source evidence coordinates | Scientific-document tables are not BOMs; use for structure, not procurement semantics |
| [DocLayNet](https://github.com/DS4SD/DocLayNet) | 80,863 human-annotated pages with 11 layout classes, bounding boxes/polygons, and optional text-cell coordinates | Document structure detection and layout uncertainty estimation, including table/list/text regions | Broad public-document sources; verify the dataset license and source-document conditions |
| [PubLayNet / PubTabNet](https://github.com/ibm-aur-nlp/PubLayNet) | Automatically aligned document-layout labels; PubTabNet provides table images with HTML structure | Large-scale layout/table baselines and pretraining comparisons | Automatically generated scientific-document labels may not match noisy procurement documents |
| [FUNSD](https://github.com/crcresearch/FUNSD) and [RFUND](https://github.com/SCUT-DLVCLab/RFUND) | Form entities labeled as question/answer/header/other, word boxes, and entity links; RFUND adds more realistic line-level annotations | Key-value extraction, evidence linking, and review/error analysis | FUNSD is small; original-use terms are research/education oriented, so verify before any public derivative |
| [CORD](https://github.com/clovaai/cord) | Receipt OCR/post-OCR parsing annotations for semantic fields and line items | Receipt-like extraction, key/value parsing, and post-OCR normalization | Repository identifies a CC BY 4.0 license; confirm that license applies to the intended data artifacts |
| [SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE) | 1,000 receipt images with text boxes/transcripts and key fields such as company, address, date, and total | OCR localization, noisy text normalization, and field extraction smoke tests | The repository is an implementation/repackaging; verify original ICDAR dataset terms separately |
| [MAVE](https://github.com/google-research-datasets/mave) | 3M attribute-value annotations over 2.2M cleaned product profiles; character spans, attribute keys, positive/negative evidence, and 1,257 categories | Product description attribute extraction, evidence-span handling, and negative/no-evidence cases | Full reconstruction requires the Amazon Review Data 2018 metadata; review both datasets’ terms and do not redistribute source metadata |

## 3. Entity resolution, product matching, and catalog identity

| Dataset | Labels / supervision | Use in this project | Access and caveats |
| --- | --- | --- | --- |
| [WDC Training Set and Gold Standard](https://webdatacommons.org/largescaleproductcorpus/) | More than 26M offers grouped into product clusters; identifiers and schema.org properties; manually verified match/non-match pairs | Candidate generation, identifier-first matching, blocking, and large-scale product identity | Large download; Common Crawl-derived data and terms must be reviewed |
| [WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/index.html) | 11,715 offers describing 2,162 products, with pairwise and multi-class matching variants and controlled corner cases | Reproducible ER benchmark with unseen entities and difficult cases | Consumer-product domain; use as a method benchmark, not a domain validation set |
| [Supervised Matching datasets](https://zenodo.org/records/7252010) | 13 established matching datasets plus additional benchmark variants, including Abt-Buy, Amazon-Google, Walmart-Amazon, and iTunes-Amazon | Baselines for deterministic matching, blocking, thresholding, abstention, and review-load analysis | Dataset bundle has heterogeneous sources and licenses; record per-dataset provenance |
| [Amazon ESCI](https://github.com/amazon-science/esci-data) | Query-product judgments labeled Exact, Substitute, Complement, or Irrelevant; product title, description, brand, color, locale, and split fields | Retrieval relevance, substitute-vs-identity distinctions, and fine-grained product relationship modeling | E-commerce search is not procurement ER; use the labels as a proxy and retain the distinction between match and substitute |
| [MAVE](https://github.com/google-research-datasets/mave) | Product IDs, categories, attribute names, evidence spans, and negative product-attribute pairs | Attribute normalization and evidence-backed catalog enrichment before ER | See extraction section for source and terms caveats |

The ER benchmark must preserve the project rule that false merges cost more than
unresolved identities. Public matching labels do not remove the need for a
synthetic benchmark containing ambiguous part numbers, manufacturer aliases,
substitutions, revisions, and intentional non-merges.

## 4. Retrieval, evidence-grounded QA, and numerical reasoning

| Dataset | Labels / supervision | Use in this project | Access and caveats |
| --- | --- | --- | --- |
| [BEIR](https://huggingface.co/datasets/BeIR/fiqa-qrels) | Heterogeneous corpora, queries, and query-document relevance judgments (`qrels`) across 18 datasets and multiple retrieval tasks | BM25/vector/reranker harnesses, recall, nDCG, and query-type routing | Domain-general retrieval benchmark; it does not test procurement evidence or claim correctness |
| [DocVQA](https://site.docvqa.org/datasets/docvqa) | 50K questions over 12K document images with manually annotated answers; OCR text and bounding boxes are available | Source-viewer grounding, answer-span localization, document QA, and unanswerable/ambiguity UX | Download requires challenge-portal access and terms review; source documents are not procurement-specific |
| [FinQA](https://github.com/czyssrs/FinQA) | Questions over tables and surrounding text with supporting facts, arithmetic reasoning programs, and executable answers | Deterministic arithmetic boundary, evidence selection, and numerical QA evaluation | Financial reports are a proxy; arithmetic programs should not be treated as procurement policy |
| [TAT-QA](https://arxiv.org/abs/2105.07624) | Hybrid table/text questions requiring numerical reasoning, with supporting evidence and operation types | Multi-source table/text retrieval and grounded calculation tests | Financial-domain proxy; use its reasoning format, not its domain assumptions |

These datasets test components of the evidence-first experience. The project’s
own golden queries must additionally require a complete trace from answer claim
to original BOM/quote/PO location.

## 5. Forecasting and anomaly-detection proxies

| Dataset | Labels / supervision | Use in this project | Access and caveats |
| --- | --- | --- | --- |
| [M5 Walmart forecasting data](https://krzjoa.github.io/m5/) | Hierarchical SKU/store unit-sales history, calendar events, and sell prices with held-out forecasting targets | SKU-level demand forecasting, hierarchical aggregation, price features, and baseline comparison | Retail sales are not procurement lead times or construction schedules; use only for method development |
| [Monash Time Series Forecasting Archive](https://forecastingdata.org/) | Public time-series collections with standard train/test conventions and baseline models | Forecasting protocol, reproducible splits, baseline comparisons, and horizon handling | Broad multi-domain archive; most series have no procurement semantics or anomaly labels |
| [Numenta Anomaly Benchmark](https://github.com/numenta/NAB) | 58 labeled real-time series files with anomaly windows and a scoring method that rewards early detection and penalizes false alarms | Streaming anomaly metrics, alert timing, false-alarm analysis, and threshold evaluation | IT/industrial/social metrics are proxies; synthetic procurement anomalies remain necessary |

## Recommended acquisition order

1. Create the project-specific synthetic BOM/quote/PO/revision/delivery corpus
   and gold evidence manifest first.
2. Use PNNL DATA-ME, public BOM documents, and OCDS/USAspending fields to shape
   the synthetic schema without copying proprietary or sensitive data.
3. Start extraction benchmarks with DocILE, PubTables-1M, and DocLayNet.
4. Start identity benchmarks with WDC Products, WDC gold pairs, ESCI, and the
   supervised-matching bundle.
5. Add DocVQA, FinQA, and BEIR for evidence retrieval and numerical reasoning.
6. Add M5, Monash, and NAB only when the corresponding forecasting/anomaly
   interfaces exist; do not let proxy scores imply procurement performance.

Every imported dataset requires a manifest entry containing source URL,
retrieval date, version, license/terms decision, checksum, adapter version,
split policy, labels used, known limitations, and whether the data may be
redistributed or only fetched during evaluation.
