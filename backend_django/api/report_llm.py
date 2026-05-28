import json
from groq import Groq
from django.conf import settings
from .report_extraction import METRIC_FIELDS, extract_key_metrics


def _fallback_parse(raw_text):
    metrics = extract_key_metrics(raw_text)
    if metrics:
        summary_lines = ["Key values identified from the report:"]
        for key, value in metrics.items():
            summary_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        summary = "\n".join(summary_lines)
    else:
        summary = "Report uploaded. No clear lab values were detected automatically."
    return {"summary": summary, "metrics": metrics}


def _normalize_metrics(metrics):
    if not isinstance(metrics, dict):
        return {}

    normalized = {}
    for field in METRIC_FIELDS:
        value = metrics.get(field)
        if value is None or value == "":
            continue
        try:
            if field == "heart_rate" or field.endswith("_systolic") or field.endswith("_diastolic"):
                normalized[field] = int(float(value))
            else:
                normalized[field] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def parse_medical_report_with_groq(raw_text):
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return _fallback_parse(raw_text)

    if not settings.GROQ_API_KEY:
        return _fallback_parse(raw_text)

    prompt = f"""You are a medical lab report parser.
Read the OCR text and extract only values that are clearly present.

Return ONLY valid JSON in this exact shape:
{{
  "summary": "4-8 line patient-friendly summary of important findings",
  "metrics": {{
    "heart_rate": null,
    "blood_pressure_systolic": null,
    "blood_pressure_diastolic": null,
    "spo2": null,
    "hemoglobin": null,
    "glucose": null,
    "cholesterol_total": null,
    "hdl": null,
    "ldl": null,
    "triglycerides": null
  }}
}}

Rules:
- Use null when a metric is missing or unclear.
- Never invent values.
- summary must be concise and readable (not raw OCR dump).
- metrics values must be numbers only (no units in JSON values).

OCR TEXT:
{raw_text[:12000]}
"""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured health metrics from medical reports.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content.strip()
        parsed = json.loads(content)
        summary = (parsed.get("summary") or "").strip()
        metrics = _normalize_metrics(parsed.get("metrics"))
        if not summary:
            summary = _fallback_parse(raw_text)["summary"]
        return {"summary": summary, "metrics": metrics}
    except Exception:
        return _fallback_parse(raw_text)
