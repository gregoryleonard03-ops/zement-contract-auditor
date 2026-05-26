# Zement Contract Auditor

AI-powered risk analysis for vendor contracts. Upload a PDF or DOCX → get a reliability score (0–100) + list of red flags with dollar impact.

## Local Setup

```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

## Generate Demo Contracts

```bash
python3 tests/generate_test_contracts.py
```

Creates 3 sample contracts in `tests/sample_contracts/`:
- `contract_a_clean.txt` — clean contract, should score 85+
- `contract_b_medium.txt` — medium risk, 2-3 yellow flags
- `contract_c_toxic.txt` — high risk, includes $1500/transaction hidden fee

## Deploy to Streamlit Cloud

1. Push this folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select repo → branch `main` → file `app.py`
4. Add secret: `ANTHROPIC_API_KEY = "sk-ant-..."`
5. Deploy

## Architecture

```
app.py          — Streamlit UI (upload, cards, CSS)
analyzer.py     — Text extraction (PDF/DOCX), Claude API calls, scoring
prompts.py      — System prompt and templates
requirements.txt
.streamlit/config.toml
tests/
  generate_test_contracts.py
  sample_contracts/
```
