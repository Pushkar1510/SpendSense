# SpendSense

Local-first personal finance toolkit: ingest bank statements, categorize transactions, and ask spend questions with **SQL-backed answers and citations**.

No cloud. No paid APIs. Your data stays on your machine.

## Features

- **CSV + PDF ingest** — flexible column mapping; text PDFs via pdfplumber
- **Optional local OCR** — scanned PDFs via **Tesseract** (no cloud OCR)
- **Deduped storage** — SQLite with hash-based re-upload protection
- **Rule + optional LLM categorization** — keyword rules first; Ollama only if running locally
- **Grounded Q&A** — money totals always come from SQL tools; the LLM never invents amounts
- **Citations** — every answer can show the supporting transactions
- **FastAPI + Streamlit** — thin UI over a clean HTTP API

## Privacy model

| Principle | Detail |
|-----------|--------|
| Local-first | SQLite under `data/` (gitignored) |
| $0 stack | No paid cloud OCR/LLMs; optional local Tesseract + Ollama |
| Optional AI | Ollama on `127.0.0.1:11434` only |
| Safe defaults | Never commit real bank statements |

## Stack

Python 3.11+ · FastAPI · SQLite · pandas · pdfplumber · PyMuPDF · pytesseract · Streamlit · pytest · (optional) Ollama / Tesseract

## Setup

```bash
git clone https://github.com/Pushkar1510/SpendSense.git
cd SpendSense

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Optional: local OCR for scanned PDFs

```bash
# Ubuntu / Debian
sudo apt install tesseract-ocr

# verify
tesseract --version
```

Without Tesseract, text-based PDFs still work; scanned/image PDFs should be exported as CSV.

### Optional: local LLM

```bash
ollama pull llama3.2
```

## Run

**Terminal 1 — API**

```bash
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — UI**

```bash
PYTHONPATH=. streamlit run ui/streamlit_app.py
```

### Quick API smoke test

```bash
curl -s http://127.0.0.1:8000/health
curl -F "file=@tests/fixtures/sample_statement.csv" http://127.0.0.1:8000/upload
curl -X POST http://127.0.0.1:8000/categorize \
  -H 'Content-Type: application/json' \
  -d '{"use_llm":false}'
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"How much on food in August 2024?"}'
```

Expected: answer contains **830** with citations.

## Sample questions

- How much on food in August 2024?
- How much on transport in August 2024?
- What was my income in August 2024?
- Show a breakdown by category
- List my transactions

## Architecture

```
Streamlit UI  ──HTTP──►  FastAPI
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Ingest     Categorize       Ask
        CSV/PDF(+OCR) rules→Ollama   intent→SQL tools
              │            │            │
              └────────────┴────────────┘
                           ▼
                        SQLite
```

Amounts use a signed convention: **expenses negative**, **income positive** (default currency: INR).

PDF flow: pdfplumber text extract → if empty/unparseable → optional **Tesseract OCR** → same line parser. CSV remains the most reliable path.

## Tests

```bash
PYTHONPATH=. pytest -v
```

Unit tests mock Ollama and Tesseract — no live model/OCR required.

## Project layout

```
app/
  api/          # FastAPI routes + schemas
  db/           # schema, connection, repository
  rules/        # category keyword rules (YAML)
  services/     # ingest, categorize, tools, ask
ui/
  streamlit_app.py
tests/
  fixtures/     # anonymized sample statements
```

## Resume bullets

- Built a local-first personal finance app (FastAPI + SQLite + Streamlit) for statement ingest, categorization, and grounded spend Q&A
- Implemented CSV/PDF parsing with optional on-device Tesseract OCR, signed amounts, dedupe hashing, and deterministic SQL tools
- Designed a rule-first categorization pipeline with optional local Ollama fallback; money math never depends on the LLM
- Exposed upload / categorize / ask APIs with citation-backed answers and pytest coverage including golden ask evals

## License

Use freely for learning and portfolio. Do not commit real bank data.
