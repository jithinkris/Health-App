import json
import re

METRICS_MARKER = "\n__EXTRACTED_METRICS__\n"

METRIC_FIELDS = (
    "heart_rate",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "spo2",
    "hemoglobin",
    "glucose",
    "cholesterol_total",
    "hdl",
    "ldl",
    "triglycerides",
)


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
        "hdl": r"(?:hdl)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)",
        "ldl": r"(?:ldl)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)",
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


def metrics_from_report(report):
    metrics = {}
    for field in METRIC_FIELDS:
        value = getattr(report, field, None)
        if value is not None:
            metrics[field] = value

    if metrics:
        return metrics

    stored_text = getattr(report, "extracted_text", None)
    if stored_text and METRICS_MARKER in stored_text:
        _, metrics_json = stored_text.split(METRICS_MARKER, 1)
        try:
            parsed = json.loads(metrics_json.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return extract_key_metrics(stored_text or "")


def apply_metrics_to_report(report, metrics):
    for field in METRIC_FIELDS:
        setattr(report, field, metrics.get(field))


def report_update_fields():
    return ["extracted_text", *METRIC_FIELDS]
