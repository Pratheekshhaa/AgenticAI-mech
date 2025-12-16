import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"


def call_llama(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()

    return r.json().get("response", "").strip()


def _safe_json_extract(text: str) -> dict | None:
    """
    Extract JSON object from arbitrary LLM output safely.
    """
    if not text:
        return None

    # Remove code fences if present
    text = text.replace("```json", "").replace("```", "").strip()

    # Try direct load
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try regex extraction
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None

    return None


def analyze_feedback(feedback_text: str) -> dict:
    prompt = f"""
You are an AI system that converts customer feedback into structured data.

Feedback:
\"\"\"{feedback_text}\"\"\"

Return ONLY a JSON object in this exact format:
{{
  "rating": number between 1 and 5,
  "sentiment": "Positive" | "Neutral" | "Negative",
  "service_quality": "Good" | "Average" | "Poor"
}}
"""

    raw = call_llama(prompt)
    parsed = _safe_json_extract(raw)

    # ---------- FALLBACK ----------
    if parsed is None:
        return {
            "rating": 3,
            "sentiment": "Neutral",
            "service_quality": "Average"
        }

    return parsed


def extract_bill_info(bill_text: str) -> dict:
    if not bill_text.strip():
        return {
            "services_done": [],
            "total_cost": 0,
            "service_date": "Unknown"
        }

    prompt = f"""
Extract service details from this text.

Text:
\"\"\"{bill_text}\"\"\"

Return ONLY JSON in this format:
{{
  "services_done": ["list of services"],
  "total_cost": number,
  "service_date": "YYYY-MM-DD or Unknown"
}}
"""

    raw = call_llama(prompt)
    parsed = _safe_json_extract(raw)

    if parsed is None:
        return {
            "services_done": [],
            "total_cost": 0,
            "service_date": "Unknown"
        }

    return parsed
