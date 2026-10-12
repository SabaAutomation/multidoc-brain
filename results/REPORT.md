# MultiDoc Brain results

## 1. Retrieval: was the answer inside the chunks the model received?

Deterministic (no LLM). Higher is better.

| File type | P0 plain text only | P1 + table-aware rows | P2 + source labels | P3 + OCR for scans |
|---|---|---|---|---|
| Prose (pdf/docx/md) | 15/15 | 15/15 | 15/15 | 15/15 |
| Table in a docx | 0/3 | 3/3 | 3/3 | 3/3 |
| Spreadsheet (xlsx) | 7/7 | 7/7 | 7/7 | 7/7 |
| CSV | 3/3 | 3/3 | 3/3 | 3/3 |
| Scanned PDF | 0/3 | 0/3 | 0/3 | 3/3 |
| **All answerable** | **25/31** | **28/31** | **28/31** | **31/31** |

## 2. Model answers (qwen2.5-coder:7b)

Answer correct = known answer string present in the reply.

| File type | P0 plain text only | P1 + table-aware rows | P2 + source labels | P3 + OCR for scans |
|---|---|---|---|---|
| Prose (pdf/docx/md) | 15/15 | 15/15 | 15/15 | 15/15 |
| Table in a docx | 0/3 | 3/3 | 3/3 | 3/3 |
| Spreadsheet (xlsx) | 5/7 | 5/7 | 7/7 | 7/7 |
| CSV | 3/3 | 3/3 | 3/3 | 3/3 |
| Scanned PDF | 0/3 | 0/3 | 0/3 | 3/3 |
| **All answerable** | **23/31** | **26/31** | **28/31** | **31/31** |

**Questions whose answer is NOT in the documents** (correct = the model said NOT FOUND instead of guessing):

| Level | Correctly refused |
|---|---|
| P0 plain text only | 3/3 |
| P1 + table-aware rows | 3/3 |
| P2 + source labels | 3/3 |
| P3 + OCR for scans | 3/3 |

## What this does and does not show

- It compares ways of *reading* messy files, on a small synthetic corpus (8 files, 34 questions) with known answers.
- Retrieval is plain BM25 keyword search. Results may differ with embeddings or other retrievers.
- Model answers come from a small local model on a CPU, usually 1 run per cell. Small differences can be noise; repeat before you trust them.
- The corpus is invented and clean compared with real client files.
