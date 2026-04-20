"""
OCR layer: accepts PDF or image bytes, returns raw extracted text.

Strategy:
- Text PDFs  → PyMuPDF (fast, no API call needed)
- Scanned PDFs → convert to image → Claude vision
- Images (jpg/png/webp) → Claude vision directly
"""

import base64
import logging
from pathlib import Path

import anthropic
import fitz  # PyMuPDF

from shared.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_PDF_TYPE = ".pdf"
MIN_TEXT_LENGTH = 100   # below this, treat PDF as scanned


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Main entry point. Pass raw file bytes and original filename.
    Returns extracted text string.
    Raises ValueError for unsupported file types.
    """
    ext = Path(filename).suffix.lower()

    if ext in SUPPORTED_IMAGE_TYPES:
        logger.info(f"Processing image file: {filename}")
        return _extract_from_image(file_bytes, ext)

    elif ext == SUPPORTED_PDF_TYPE:
        logger.info(f"Processing PDF file: {filename}")
        return _extract_from_pdf(file_bytes)

    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported: {SUPPORTED_IMAGE_TYPES | {SUPPORTED_PDF_TYPE}}"
        )


def _extract_from_pdf(file_bytes: bytes) -> str:
    """Try PyMuPDF text extraction first; fall back to vision if scanned."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()

    if len(text.strip()) >= MIN_TEXT_LENGTH:
        logger.info("PDF text extraction successful (non-scanned)")
        return text

    logger.info("PDF appears scanned — converting to image for vision OCR")
    # Render first page at 200dpi and run vision
    page = doc[0]
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    return _extract_from_image(img_bytes, ".png")


def _extract_from_image(file_bytes: bytes, ext: str) -> str:
    """Send image to Claude vision for text extraction."""
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/png")
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL text from this hospital document exactly as it appears. "
                            "Preserve all numbers, amounts, line items, dates, and medical codes. "
                            "Do not summarize, interpret, or reformat. "
                            "Output the raw extracted text only."
                        ),
                    },
                ],
            }
        ],
    )
    return response.content[0].text
