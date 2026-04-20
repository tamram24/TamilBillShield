# MediSafe — Hospital Bill Analyzer

> **Know what you're paying for. Challenge what's wrong. Get your money back.**

MediSafe is an AI-powered document intelligence tool that helps Indian patients understand and contest hospital bills, insurance rejections, and billing overcharges — in under 10 minutes, right at the billing counter.

Built with Python, Streamlit, and the Anthropic Claude API.

---

## The Problem

When a family member is admitted to a private hospital, patients face a three-sided information asymmetry:

- The **hospital** knows what it charged, what it should have charged, and what it can get away with
- The **insurer** knows the policy terms, exclusion clauses, and regulatory requirements it may be violating
- The **patient** knows nothing — and cannot leave until the bill is paid

MediSafe closes this gap.

---

## What It Does

| Module | What it checks |
|---|---|
| **Bill Auditor** | Compares each line item against CGHS benchmark rates and NPPA drug price caps |
| **Policy Checker** | Detects wrongful insurance rejections that violate IRDAI 2025 guidelines |
| **Contradiction Detector** | Finds mismatches between discharge summary and hospital bill |
| **Letter Generator** | Produces a hospital dispute letter and insurer escalation notice with legal citations |

**Output:** Three targeted documents — a patient summary, a hospital dispute letter, and an insurer escalation notice — generated in under 10 minutes.

---

## Team & 7-Day Build Plan

| Person | Owns | Days |
|---|---|---|
| Person A | Ingestion layer (OCR, parsers, knowledge base, vector store) | 1–4 |
| Person B | Reasoning core (bill auditor, policy checker, contradiction detector) | 2–5 |
| Person C | Output layer (letter generator, Streamlit UI, PDF export) | 3–7 |

Integration and end-to-end testing: Days 6–7 (all three)

---

## Architecture

```
User uploads (bill + discharge summary + insurance policy)
        │
        ▼
┌─────────────────────────────────────┐
│         Ingestion Layer             │
│  OCR → Typed JSON per document      │
└─────────────────┬───────────────────┘
                  │
        ┌─────────▼──────────┐
        │   Knowledge Base   │
        │ CGHS · NPPA · IRDAI│
        │   ChromaDB (policy)│
        └─────────┬──────────┘
                  │
┌─────────────────▼───────────────────┐
│           Reasoning Core            │
│  Bill Auditor · Policy Checker      │
│  Contradiction Detector             │
│  (Claude claude-sonnet-4-20250514)  │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│           Output Layer              │
│  Patient summary · Hospital letter  │
│  Insurer escalation notice          │
└─────────────────────────────────────┘
```

---

## Project Structure

```
medisafe/
├── app.py                        # Streamlit entry point
├── requirements.txt
├── .env.example
├── README.md
│
├── shared/
│   ├── __init__.py
│   ├── models.py                 # Pydantic schemas (source of truth)
│   └── config.py                 # API keys, constants, thresholds
│
├── ingestion/
│   ├── __init__.py
│   ├── ocr.py                    # PDF/image → raw text (Claude vision + PyMuPDF)
│   ├── parsers.py                # Raw text → typed Pydantic models
│   ├── knowledge_base.py         # CGHS/NPPA/IRDAI lookup functions
│   └── vector_store.py           # ChromaDB: policy chunk embedding + retrieval
│
├── reasoning/
│   ├── __init__.py
│   ├── bill_auditor.py           # Line-item vs benchmark analysis
│   ├── policy_checker.py         # Rejection vs IRDAI rules analysis
│   ├── contradiction_detector.py # Bill vs discharge summary comparison
│   └── prompts.py                # All Claude system prompts (single source)
│
├── output/
│   ├── __init__.py
│   ├── letter_generator.py       # Hospital + insurer letter generation
│   └── pdf_export.py             # fpdf2-based PDF download
│
├── data/
│   ├── cghs_rates.json           # CGHS procedure benchmark rates
│   ├── nppa_caps.json            # NPPA scheduled drug ceiling prices
│   └── irdai_rules.json          # Key IRDAI 2025 circular rules
│
└── tests/
    ├── sample_bill.txt           # Redacted test bill
    ├── sample_discharge.txt      # Redacted test discharge summary
    └── test_parsers.py           # Basic parser unit tests
```

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/your-org/medisafe.git
cd medisafe
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Build the knowledge base (critical — do this first)

```bash
python scripts/build_knowledge_base.py
```

This downloads and parses:
- CGHS rate card → `data/cghs_rates.json`
- NPPA ceiling prices → `data/nppa_caps.json`
- IRDAI 2025 rules → `data/irdai_rules.json`

See [Data Sources](#data-sources) below for manual alternatives.

### 4. Run

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501`

---

## Usage

1. Upload your **hospital bill** (PDF or photo)
2. Upload the **discharge summary** (PDF or photo)
3. Upload your **insurance policy** (PDF)
4. Paste the **insurer's rejection reasons** from their letter
5. Click **Analyze**

You'll get:
- A plain-language summary of overcharges found
- A color-coded line-item breakdown (verified / suspected / unverifiable)
- A list of wrongful insurance rejections with IRDAI citations
- Two ready-to-use letters you can download and hand over

---

## Confidence Levels

Every flagged line item is tagged with a confidence level:

| Tag | Meaning |
|---|---|
| 🔴 Verified overcharge | CGHS/NPPA benchmark exists AND bill exceeds it by >30% |
| 🟡 Suspected overcharge | No benchmark found but item is vague or amount is anomalous |
| 🟢 Appears fair | Billed amount is at or below benchmark |
| ⚪ Unverifiable | No benchmark available — flagged for manual review |

The system will never fabricate benchmark data. If a rate is unknown, it says so.

---

## Data Sources

| Dataset | Source | Format |
|---|---|---|
| CGHS procedure rates | [cghs.nic.in](https://cghs.nic.in) | PDF → JSON |
| NPPA drug ceiling prices | [nppaindia.nic.in](https://nppaindia.nic.in) | Spreadsheet → JSON |
| IRDAI 2025 health claim rules | IRDAI circular IRDAI/HLT/REG/CIR/170/06/2025 | Manual → JSON |

The `data/` folder ships with a curated starter set. Rates should be refreshed every 6 months as CGHS revises its schedule.

---

## Environment Variables

```
ANTHROPIC_API_KEY=          # Required. Get from console.anthropic.com
CGHS_CONFIDENCE_THRESHOLD=0.6   # Fuzzy match threshold for procedure lookup
LOG_LEVEL=INFO
```

---

## Key Design Decisions

**Why three separate Claude calls per analysis?**
Each reasoning module has a tightly scoped system prompt. Combining them into one call degrades output quality and makes debugging harder. The latency cost (~15–20s total) is acceptable for the use case.

**Why not extrapolate from unverifiable items?**
If 60% of verifiable line items are inflated, the system does NOT infer the remaining 40% are also inflated. Extrapolation without evidence undermines credibility at the billing counter. The system is designed to be right, not comprehensive.

**Why fuzzy match for CGHS lookup?**
Hospital billing systems use inconsistent procedure names ("CT Chest", "CECT Thorax", "CT Scan - Chest with contrast"). A 0.6 similarity threshold balances recall against false positives. Tune `CGHS_CONFIDENCE_THRESHOLD` in `.env` if you get too many mismatches.

**Tone calibration in letters**
The hospital dispute letter is deliberately non-aggressive. Too aggressive → hospital retaliates with delays. Too passive → they ignore it. The letter cites specific amounts and ends with a concrete, time-bound ask.

---

## Limitations & Disclaimers

- Analysis is based on publicly available CGHS rates and IRDAI guidelines. Rates may lag by 6–18 months.
- This tool is **not a substitute for legal advice**. For formal consumer court proceedings, consult a lawyer.
- Differential pricing (insured vs cash patients) is documented but difficult to quantify without a cash-pay invoice for comparison.
- Documents in regional languages will partially parse — OCR quality degrades for non-Latin scripts.

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/add-nppa-lookup`)
3. Commit with clear messages (`git commit -m "Add NPPA cap lookup for scheduled drugs"`)
4. Open a pull request against `main`

Priority contributions needed:
- Expanded CGHS rate card coverage (current: ~200 procedures)
- Regional language OCR support (Hindi discharge summaries)
- IRDAI circular parser for automated rule updates

---

## License

MIT License. See `LICENSE`.

---

## Acknowledgements

Built as a capstone project. Inspired by the 73,000+ health insurance complaints filed on IRDAI's Bima Bharosa portal in FY 2025-26, and every family that paid a bill they didn't understand because their loved one was behind a door they couldn't open.
