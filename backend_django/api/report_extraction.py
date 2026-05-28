import json
import re

METRICS_MARKER = "\n__EXTRACTED_METRICS__\n"


def extract_key_metrics(text):
    if not text:
        return {}

    patterns = {
        "heart_rate": r"(?:heart\s*rate|hr)\s*[:\-]?\s*(\d{2,3})\s*(?:bpm)?",
        "spo2": r"(?:spo2|oxygen\s*saturation|o2\s*sat)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*%?",
        "hemoglobin": r"(?:hemoglobin|hb)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)",
        "glucose": r"(?:glucose|blood\s*sugar|fbs|rbs)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)",
        "cholesterol_total": r"(?:total\s*cholesterol|cholesterol)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)",
        "triglycerides": r"(?:triglycerides)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)",
    }

    metrics = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1)
            try:
                metrics[key] = float(value) if "." in value else int(value)
            except Exception:
                metrics[key] = value

    bp_match = re.search(
        r"(?:blood\s*pressure|bp)\s*[:\-]?\s*(\d{2,3})\s*/\s*(\d{2,3})",
        text,
        flags=re.IGNORECASE,
    )
    if bp_match:
        metrics["blood_pressure_systolic"] = int(bp_match.group(1))
        metrics["blood_pressure_diastolic"] = int(bp_match.group(2))

    return metrics


def display_text(stored_text):
    if not stored_text:
        return ""
    if METRICS_MARKER in stored_text:
        return stored_text.split(METRICS_MARKER, 1)[0].strip()
    return stored_text


def metrics_from_stored_text(stored_text):
    if not stored_text:
        return {}

    if METRICS_MARKER in stored_text:
        _, metrics_json = stored_text.split(METRICS_MARKER, 1)
        try:
            parsed = json.loads(metrics_json.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return extract_key_metrics(display_text(stored_text))


def build_stored_text(extracted_text, metrics):
    text = (extracted_text or "").strip()
    if metrics:
        return text + METRICS_MARKER + json.dumps(metrics)
    return text
