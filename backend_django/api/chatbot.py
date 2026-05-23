"""
chatbot.py — Groq LLM integration for Smart Health AI chatbot.

Responsibilities:
 - Build a rich, personalized system prompt using live user health data from the DB
 - Maintain conversation history (last N messages) for continuity
 - Call the Groq API (llama-3.1-8b-instant) and return the assistant's reply
"""

from groq import Groq
from django.conf import settings


def _calculate_bmi(height_cm, weight_kg):
    """Calculate BMI from height (cm) and weight (kg)."""
    if height_cm and weight_kg and height_cm > 0:
        height_m = height_cm / 100.0
        return round(weight_kg / (height_m ** 2), 1)
    return None


def build_system_prompt(user, health_data, risk_predictions, medicines):
    """
    Build a personalised system prompt containing the user's live health context.
    This is prepended as the 'system' role message on every Groq API call.
    """
    # ── User profile ─────────────────────────────────────────────────────────
    age     = getattr(user, 'age', None) or 'Unknown'
    gender  = getattr(user, 'gender', None) or 'Unknown'
    height  = getattr(user, 'height', None)
    weight  = getattr(user, 'weight', None)
    bmi     = _calculate_bmi(height, weight)

    profile_lines = [
        f"  - Name   : {user.first_name or user.username}",
        f"  - Age    : {age} years",
        f"  - Gender : {gender}",
        f"  - Height : {height} cm" if height else "  - Height : Not provided",
        f"  - Weight : {weight} kg" if weight else "  - Weight : Not provided",
        f"  - BMI    : {bmi}" if bmi else "  - BMI    : Not calculated",
    ]

    # ── Latest vitals ─────────────────────────────────────────────────────────
    if health_data:
        vitals_lines = [
            f"  - Heart Rate       : {health_data.get('heart_rate', 'N/A')} bpm",
            f"  - SpO2             : {health_data.get('spo2', 'N/A')} %",
            f"  - Sleep Duration   : {health_data.get('sleep_hours', 'N/A')} hours",
            f"  - Steps Today      : {health_data.get('steps', 'N/A')}",
            f"  - Calories Burned  : {health_data.get('calories', 'N/A')} kcal",
            f"  - Stress Level     : {health_data.get('stress_level', 'N/A')} / 100",
            f"  - HRV              : {health_data.get('hrv', 'N/A')} ms",
            f"  - Snoring Events   : {health_data.get('snoring_events', 'N/A')}",
            f"  - SpO2 Drops       : {health_data.get('spo2_drops', 'N/A')}",
            f"  - Irregular HR     : {health_data.get('irregular_hr_events', 'N/A')} events",
            f"  - Sitting Time     : {health_data.get('sitting_time', 'N/A')} hours",
        ]
    else:
        vitals_lines = ["  - No health data synced yet."]

    # ── Risk predictions ──────────────────────────────────────────────────────
    if risk_predictions:
        risk_lines = [
            f"  - {r.disease_name}: {r.risk_level} ({round(r.risk_percentage, 1)}%)"
            for r in risk_predictions
        ]
    else:
        risk_lines = ["  - No risk predictions available yet."]

    # ── Active medicines ──────────────────────────────────────────────────────
    if medicines:
        med_lines = [
            f"  - {m.medicine_name} {m.dosage} at {str(m.timing)[:5]}"
            for m in medicines
        ]
    else:
        med_lines = ["  - No medicines recorded."]

    system_prompt = f"""You are an empathetic, knowledgeable, and professional AI health assistant embedded in the Smart Health AI mobile app.

You have access to the following LIVE health data for this specific user. Use it to provide highly personalised advice:

👤 USER PROFILE:
{chr(10).join(profile_lines)}

❤️  LATEST HEALTH VITALS:
{chr(10).join(vitals_lines)}

🏥 RECENT RISK PREDICTIONS (ML Model):
{chr(10).join(risk_lines)}

💊 ACTIVE MEDICINES:
{chr(10).join(med_lines)}

INSTRUCTIONS:
1. Always reference the user's actual health data when giving advice.
2. Provide clear, actionable, evidence-based health recommendations.
3. Be empathetic and supportive — never alarming or dismissive.
4. For serious symptoms or concerns, always recommend consulting a licensed doctor.
5. Keep responses concise (3–5 sentences max unless asked for more detail).
6. Use plain language — no unnecessary medical jargon.
7. You can answer general health questions too, but always relate them back to the user's data if relevant.
8. NEVER diagnose conditions definitively — you can suggest possibilities and recommend professional evaluation.
"""
    return system_prompt


def get_groq_response(system_prompt, message_history, new_user_message):
    """
    Call the Groq API with the full conversation context and return the assistant reply.

    Args:
        system_prompt (str): The health-context system prompt.
        message_history (list): List of dicts with 'role' and 'content' (DB history).
        new_user_message (str): The latest message from the user.

    Returns:
        str: The assistant's response text, or an error message.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    # Build the messages array: system → history → new user message
    messages = [{"role": "system", "content": system_prompt}]

    for msg in message_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": new_user_message})

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=1024,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"I'm having trouble connecting right now. Please try again in a moment. (Error: {str(e)})"
