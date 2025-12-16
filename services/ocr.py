"""
OCR module with graceful fallback.
No external OCR dependency required.
"""

def extract_text_from_bill(file_bytes: bytes) -> str:
    """
    Fallback OCR:
    Since OCR library is not installed,
    we return a placeholder text and rely on user feedback.
    """
    return (
        "OCR not available. "
        "Bill text not extracted automatically."
    )
