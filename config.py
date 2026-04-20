"""
Document parsers: raw OCR text → typed Pydantic models.

Three parsers, one per document type:
- parse_bill()             → ParsedBill
- parse_discharge_summary() → ParsedDischargeSummary
- parse_policy()           → ParsedPolicy

All parsers use Claude with strict JSON-only output prompts.
No inference — if a field is absent in the source, it is null/empty.
"""

import json
import logging

import anthropic

from shared.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from shared.models import ParsedBill, ParsedDischargeSummary, ParsedPolicy

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── System prompts ────────────────────────────────────────────────────────────

BILL_EXTRACTION_PROMPT = """
You are a medical billing parser. Extract structured data from the hospital bill text provided.

Return ONLY valid JSON matching this exact schema:
{
  "hospital_name": "string",
  "patient_name": "string",
  "total_billed": float,
  "insurer_approved": float,
  "patient_demand": float,
  "line_items": [
    {
      "description": "string",
      "billed_amount": float,
      "quantity": int
    }
  ]
}

Rules:
- Extract only what is present in the document. Do not infer or guess.
- Set missing numeric fields to 0.0.
- For aggregated line items (e.g. "ICU Consumables - Rs 67,000"), extract them as-is.
  Do NOT attempt to break them down further.
- patient_demand = amount the hospital is asking the patient to pay out-of-pocket.
- Return ONLY the JSON object. No explanation. No markdown code fences.
"""

DISCHARGE_EXTRACTION_PROMPT = """
You are a medical document parser. Extract structured data from the discharge summary provided.

Return ONLY valid JSON matching this exact schema:
{
  "diagnosis": "string",
  "admission_date": "string",
  "discharge_date": "string",
  "icu_days": int,
  "specialists_mentioned": ["list of doctor names or specialties explicitly mentioned"],
  "procedures_listed": ["list of procedures or diagnostic tests performed"],
  "medicines_prescribed": ["list of medicines with dosage if available"]
}

Rules:
- Extract only what is explicitly stated. Do not infer from context.
- If ICU days are not stated, set to 0.
- Return ONLY the JSON object. No explanation. No markdown.
"""

POLICY_EXTRACTION_PROMPT = """
You are an insurance policy parser. Extract structured data from the insurance policy document provided.

Return ONLY valid JSON matching this exact schema:
{
  "insurer_name": "string",
  "policy_number": "string",
  "sum_insured": float,
  "room_rent_limit": float or null,
  "exclusions": ["list of explicitly stated exclusions or non-payable items"]
}

Rules:
- Extract only what is explicitly stated.
- room_rent_limit: the daily room rent cap if stated, else null.
- exclusions: copy the actual exclusion descriptions verbatim, not paraphrased.
- Return ONLY the JSON object. No explanation. No markdown.
"""


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_bill(raw_text: str) -> ParsedBill:
    """Parse hospital bill raw text into a ParsedBill model."""
    logger.info("Parsing hospital bill...")
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=BILL_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
    )
    text = response.content[0].text.strip()
    # Strip accidental markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text)
    data["raw_text"] = raw_text
    for item in data.get("line_items", []):
        item.setdefault("confidence", "unverifiable")
    return ParsedBill(**data)


def parse_discharge_summary(raw_text: str) -> ParsedDischargeSummary:
    """Parse discharge summary raw text into a ParsedDischargeSummary model."""
    logger.info("Parsing discharge summary...")
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=DISCHARGE_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text)
    data["raw_text"] = raw_text
    return ParsedDischargeSummary(**data)


def parse_policy(raw_text: str) -> ParsedPolicy:
    """Parse insurance policy raw text into a ParsedPolicy model."""
    logger.info("Parsing insurance policy...")
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=POLICY_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text)
    data["raw_text"] = raw_text
    return ParsedPolicy(**data)
