# How MultiDoc Brain works

## The question
Real client files are messy: Word files with tables, spreadsheets, CSVs, scanned PDFs. **How much does the way you read
those files change what a small local model can answer?**

## The corpus (invented, answers known)
8 files for a fictional company, "Cedar & Co. Outfitters":

| File | Type | What is tricky about it |
|---|---|---|
| employee_handbook.docx | Word | key facts live in a **table** |
| meeting_notes_2025-09.docx | Word | plain paragraphs |
| expense_policy.pdf | PDF with text | plain lines |
| price_list.xlsx | Excel, 2 sheets | numbers only make sense next to their **column headers** |
| quarterly_sales.xlsx | Excel | same |
| vendors.csv | CSV | same |
| customer_faq.md | Markdown | plain |
| scanned_safety_notice.pdf | **image only** | no text layer at all |

34 questions: 31 have a known answer in the files, 3 do not (the right reply is `NOT FOUND`).

## The four reading levels
| Level | What changes |
|---|---|
| P0 | Plain text only. Word tables are dropped. Spreadsheet rows are bare values with no headers. Scans are unreadable. |
| P1 | Tables, sheets and CSV rows become `Header: value \| Header: value` lines. |
| P2 | P1 + every chunk starts with `[file \| sheet / page / table caption]`. |
| P3 | P2 + OCR (Tesseract) for pages with no text layer. |

P0 is a deliberately naive baseline that I defined. It is how a quick loader often behaves, not a claim about any one library.

## Pipeline
`parse files -> chunk (about 700 characters) -> BM25 keyword index -> top 4 chunks -> local model -> score`

## Two measurements
1. **Retrieval hit@4** (no model, seconds): is the known answer inside the 4 chunks the model receives?
2. **Model accuracy** (`--answer`, slow): does the model's reply contain the known answer? Scoring is a plain string match
   (numbers normalised, plural allowed). No LLM judge. For the 3 unanswerable questions, correct means the model said `NOT FOUND`.

## Why retrieval and model accuracy can disagree
Look at the spreadsheet row in P0: `RB-310 Ridge Boots 154 8`. The right numbers are retrieved, but with no headers the model must
guess which is the price and which is the stock. Retrieval hit@4 cannot see that problem. Model accuracy can. That gap is the point
of measuring both.

## Limits
Small synthetic corpus. BM25 only (no embeddings). One run per cell on a small model. Treat a one or two question gap as noise.
