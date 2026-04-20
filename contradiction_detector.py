# Contributing to MediSafe

## Setup

```bash
git clone https://github.com/your-org/medisafe.git
cd medisafe
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python scripts/build_knowledge_base.py
```

## Branch naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feature/short-description` | `feature/add-nppa-lookup` |
| Fix | `fix/short-description` | `fix/pdf-parse-crash` |
| Data | `data/short-description` | `data/expand-cghs-rates` |

## Team ownership

| Module | Owner |
|---|---|
| `ingestion/` | Person A |
| `data/` | Person A |
| `reasoning/` | Person B |
| `reasoning/prompts.py` | Person B |
| `output/` | Person C |
| `app.py` | Person C |
| `shared/models.py` | All three — discuss before changing |

## PR rules

- All PRs target `develop`, not `main`
- `main` is merged to only at end of each day after integration test
- Tag your PR with the owner's name if it touches their module
- Every new function needs a docstring

## Running tests

```bash
pytest tests/ -v
```

Tests use mocked Claude responses — no API key needed for unit tests.

## Updating data files

When updating `data/cghs_rates.json` or `data/nppa_caps.json`:
1. Add a comment in the PR describing the data source and date
2. Run `python scripts/build_knowledge_base.py --verify-only` to confirm validity
3. Do not remove existing entries — only add or update

## Commit message format

```
[module] short description

- bullet detail if needed
- another detail
```

Examples:
```
[ingestion] add Hindi text OCR fallback
[reasoning] tighten contradiction detector prompt
[data] add 45 new CGHS procedure rates from 2025 revision
[output] fix PDF font rendering for rupee symbol
```
