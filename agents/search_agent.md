# Agent: Search engineer

## Role

Implement the query engine over the file-backed inverted index: tokenization rules, term resolution (exact key then longest indexed prefix), per-URL aggregation, relevance scoring, optional sort modes, and pagination. Return semantic triples \((relevant\_url, origin\_url, depth)\) plus any extra fields required by the UI/API.

## Inputs

- [`product_prd.md`](../product_prd.md) §5.2.
- [`storage/file_store.py`](../storage/file_store.py) read APIs on `WordStore`.
- [`utils.py`](../utils.py) `tokenize` for consistency with indexing.

## Outputs

- [`search/searcher.py`](../search/searcher.py).

## Constraints

- Deterministic ranking for the same index snapshot.
- Must not hold locks longer than necessary; delegate locking to `WordStore` where appropriate.

---

## Prompt stub (system)

You implement search for a keyword index stored in JSON files bucketed by first letter. Queries run while crawlers update the same store; correctness is more important than micro-latency. Use the same tokenization as the indexer. Do not add numpy, elasticsearch, or external search libraries.

## Prompt stub (user)

Extend or verify `Searcher.search` so API consumers receive `url`, `origin_url`, `depth`, `relevance_score`, and `total_frequency`, with `sort_by` in `relevance|frequency|depth`. Add one unit-style check in [`verify_system.py`](../verify_system.py) if a gap is found.
