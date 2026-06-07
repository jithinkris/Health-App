import base64
import json
import mimetypes
import os
import re

from django.conf import settings

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

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
PDF_EXTENSIONS = {".pdf"}


def _extract_text_from_pdf(file_path):
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(file_path)
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks).strip()
    except Exception:
        return ""


def _extract_text_from_image_ocr(file_path):
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    try:
        return pytesseract.image_to_string(Image.open(file_path)).strip()
    except Exception:
        return ""


def _extract_text_from_image_groq(file_path):
    if not settings.GROQ_API_KEY:
        return ""

    mime_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"
    try:
        with open(file_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return ""

    try:
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=getattr(settings, "GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract all readable text from this medical report image. "
                                "Return plain text only, preserving values and labels."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception:
        return ""


def extract_text_from_upload(file_path):
    extension = os.path.splitext(file_path)[1].lower()

    if extension in PDF_EXTENSIONS:
        return _extract_text_from_pdf(file_path)

    if extension in IMAGE_EXTENSIONS:
        text = _extract_text_from_image_ocr(file_path)
        if text:
            return text
        return _extract_text_from_image_groq(file_path)

    return ""


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

    return {}


def apply_metrics_to_report(report, metrics):
    for field in METRIC_FIELDS:
        value = metrics.get(field) if metrics else None
        setattr(report, field, value)


def report_update_fields():
    return ["extracted_text", *METRIC_FIELDS]


METRIC_DISPLAY = {
    "heart_rate": ("Heart Rate", "bpm"),
    "blood_pressure": ("Blood Pressure", "mmHg"),
    "spo2": ("SpO2", "%"),
    "hemoglobin": ("Hemoglobin", "g/dL"),
    "glucose": ("Glucose", "mg/dL"),
    "cholesterol_total": ("Total Cholesterol", "mg/dL"),
    "hdl": ("HDL", "mg/dL"),
    "ldl": ("LDL", "mg/dL"),
    "triglycerides": ("Triglycerides", "mg/dL"),
}


def metrics_table_rows(report):
    metrics = metrics_from_report(report)
    if not metrics:
        return []

    rows = []
    systolic = metrics.get("blood_pressure_systolic")
    diastolic = metrics.get("blood_pressure_diastolic")
    if systolic is not None or diastolic is not None:
        label, unit = METRIC_DISPLAY["blood_pressure"]
        value = f"{systolic or '--'}/{diastolic or '--'}"
        rows.append({"metric": label, "value": value, "unit": unit})

    for field in METRIC_FIELDS:
        if field in ("blood_pressure_systolic", "blood_pressure_diastolic"):
            continue
        value = metrics.get(field)
        if value is None:
            continue
        label, unit = METRIC_DISPLAY.get(field, (field.replace("_", " ").title(), ""))
        rows.append({"metric": label, "value": value, "unit": unit})

    return rows
