"""
Knowledge base: CGHS rate card, NPPA drug caps, IRDAI regulatory rules.

Data is loaded once from JSON files in data/ at module import.
Lookup functions use fuzzy matching to handle inconsistent procedure names.

Data sources:
  CGHS rates   → https://cghs.nic.in  (rate schedule PDFs)
  NPPA caps    → https://nppaindia.nic.in  (scheduled drug price list)
  IRDAI rules  → IRDAI circular IRDAI/HLT/REG/CIR/170/06/2025
"""

import json
import logging
from difflib import SequenceMatcher
from pathlib import Path

from shared.config import CGHS_CONFIDENCE_THRESHOLD, DATA_DIR

logger = logging.getLogger(__name__)

# Loaded once at import
CGHS_RATES: dict[str, float] = {}
NPPA_CAPS: dict[str, float] = {}
IRDAI_RULES: list[dict] = []


def _load() -> None:
    global CGHS_RATES, NPPA_CAPS, IRDAI_RULES
    data_dir = Path(DATA_DIR)

    cghs_path = data_dir / "cghs_rates.json"
    if cghs_path.exists():
        with open(cghs_path) as f:
            CGHS_RATES = json.load(f)
        logger.info(f"Loaded {len(CGHS_RATES)} CGHS rate entries")
    else:
        logger.warning("cghs_rates.json not found — benchmark lookup will be unavailable")

    nppa_path = data_dir / "nppa_caps.json"
    if nppa_path.exists():
        with open(nppa_path) as f:
            NPPA_CAPS = json.load(f)
        logger.info(f"Loaded {len(NPPA_CAPS)} NPPA cap entries")
    else:
        logger.warning("nppa_caps.json not found — drug price caps will be unavailable")

    irdai_path = data_dir / "irdai_rules.json"
    if irdai_path.exists():
        with open(irdai_path) as f:
            IRDAI_RULES = json.load(f)
        logger.info(f"Loaded {len(IRDAI_RULES)} IRDAI rule entries")
    else:
        logger.warning("irdai_rules.json not found — regulatory check will be limited")


_load()


def lookup_cghs_rate(procedure_name: str) -> tuple[float | None, str | None]:
    """
    Fuzzy-match a procedure name against the CGHS rate card.

    Returns (rate, matched_key) if confidence >= threshold, else (None, None).
    Tune CGHS_CONFIDENCE_THRESHOLD in .env (default 0.6).
    """
    if not CGHS_RATES:
        return None, None

    best_score = 0.0
    best_key = None

    proc_lower = procedure_name.lower()
    for key in CGHS_RATES:
        score = SequenceMatcher(None, proc_lower, key.lower()).ratio()
        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= CGHS_CONFIDENCE_THRESHOLD and best_key:
        return CGHS_RATES[best_key], best_key

    return None, None


def lookup_nppa_cap(medicine_name: str) -> float | None:
    """
    Substring match a medicine name against NPPA scheduled drug list.
    Returns per-unit ceiling price if found, else None.
    """
    if not NPPA_CAPS:
        return None

    name_lower = medicine_name.lower()
    for key, price in NPPA_CAPS.items():
        if key.lower() in name_lower:
            return price

    return None


def get_irdai_rules() -> list[dict]:
    """Return all loaded IRDAI rules for use in policy checker."""
    return IRDAI_RULES
