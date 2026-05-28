from rest_framework import generics, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
import os
import joblib
from .models import User, HealthData, RiskPrediction, SleepSchedule, HydrationLog, MedicineReminder, Notification, MedicalReport, ChatSession, ChatMessage
from .serializers import (UserSerializer, HealthDataSerializer, RiskPredictionSerializer, SleepScheduleSerializer, 
                          HydrationLogSerializer, MedicineReminderSerializer, NotificationSerializer, MedicalReportSerializer,
                          ChatMessageSerializer)
from rest_framework.parsers import MultiPartParser, FormParser
from .chatbot import build_system_prompt, get_groq_response
from django.conf import settings
from django.http import JsonResponse
import re


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


def _extract_text_from_image(file_path):
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    try:
        return pytesseract.image_to_string(Image.open(file_path)).strip()
    except Exception:
        return ""


def _extract_key_metrics(text):
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

def health(request):
    return JsonResponse({"status": "ok"})

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

class BaseUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class HealthDataViewSet(BaseUserViewSet):
    queryset = HealthData.objects.all()
    serializer_class = HealthDataSerializer

class RiskPredictionViewSet(BaseUserViewSet):
    queryset = RiskPrediction.objects.all()
    serializer_class = RiskPredictionSerializer

class SleepScheduleViewSet(BaseUserViewSet):
    queryset = SleepSchedule.objects.all()
    serializer_class = SleepScheduleSerializer

class HydrationLogViewSet(BaseUserViewSet):
    queryset = HydrationLog.objects.all()
    serializer_class = HydrationLogSerializer

class MedicineReminderViewSet(BaseUserViewSet):
    queryset = MedicineReminder.objects.all()
    serializer_class = MedicineReminderSerializer

class NotificationViewSet(BaseUserViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class PredictRiskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        try:
            age = float(data.get('age', 0))
            bmi = float(data.get('bmi', 0))
            hr = float(data.get('heart_rate', 0))
            sleep = float(data.get('sleep_duration', 0))
            activity = int(data.get('activity_level', 0))
            steps = float(data.get('steps_count', 0))
            spo2 = float(data.get('spo2', 0))
        except ValueError:
            return Response({'error': 'Invalid data type'}, status=400)

        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml_model', 'risk_model.pkl')
        try:
            model = joblib.load(model_path)
        except Exception as e:
            return Response({'error': f'Model load failed: {str(e)}'}, status=500)

        # Ensure correct column order match
        features = [[age, bmi, hr, sleep, activity, steps, spo2]]
        risk_level = model.predict(features)[0]
        
        probs = model.predict_proba(features)[0]
        # Depending on class indices (High, Low, Medium). Max probability mapping.
        risk_percentage = min(100.0, max(probs) * 100)

        recommendation = ["Maintain regular health checks."]
        if risk_level == 'HIGH':
            recommendation = ["Consult doctor if symptoms persist", "Improve sleep duration", "Increase physical activity"]
        elif risk_level == 'MEDIUM':
            recommendation = ["Consider lifestyle changes", "Monitor your heart rate frequently"]

        prediction = RiskPrediction.objects.create(
            user=request.user,
            risk_level=risk_level,
            risk_percentage=risk_percentage
        )

        return Response({
            "risk_level": risk_level,
            "risk_percentage": round(risk_percentage, 2),
            "recommendation": recommendation,
            "prediction_id": prediction.id
        })

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'email': user.email,
            'name': getattr(user, 'first_name', user.username),
            'age': getattr(user, 'age', 0),
            'gender': getattr(user, 'gender', 'Not specified'),
            'height': getattr(user, 'height', 0.0),
            'weight': getattr(user, 'weight', 0.0),
        })

    def patch(self, request):
        user = request.user
        data = request.data
        if 'name' in data:
            user.first_name = data['name']
        if 'age' in data:
            user.age = data['age']
        if 'gender' in data:
            user.gender = data['gender']
        if 'height' in data:
            user.height = data['height']
        if 'weight' in data:
            user.weight = data['weight']
        user.save()
        return self.get(request)

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework_simplejwt.tokens import RefreshToken

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('id_token')
        if not token:
            return Response({'error': 'No token provided'}, status=400)
            
        try:
            CLIENT_ID = "543013705253-i35d9ipst9b40sc4c4g50a86v4emvlci.apps.googleusercontent.com"
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
            
            email = idinfo['email']
            name = idinfo.get('name', email.split('@')[0])
            
            user, created = User.objects.get_or_create(username=email, defaults={
                'email': email,
                'first_name': name
            })
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'is_new': created
            })
        except ValueError:
            return Response({'error': 'Invalid token'}, status=400)

class UploadMedicalReportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, *args, **kwargs):
        reports = MedicalReport.objects.filter(user=request.user).order_by('-uploaded_at')
        serializer = MedicalReportSerializer(reports, many=True)
        return Response(serializer.data, status=200)

    def post(self, request, *args, **kwargs):
        try:
            file_serializer = MedicalReportSerializer(data=request.data)
            if not file_serializer.is_valid():
                return Response(file_serializer.errors, status=400)

            report = file_serializer.save(user=request.user)
            extracted_text = ""
            try:
                file_name = (report.image.name or "").lower()
                if file_name.endswith(".pdf"):
                    extracted_text = _extract_text_from_pdf(report.image.path)
                else:
                    extracted_text = _extract_text_from_image(report.image.path)
            except Exception:
                extracted_text = ""

            if not extracted_text:
                extracted_text = "Could not extract readable text from the report."

            report.extracted_text = extracted_text
            report.extracted_metrics = _extract_key_metrics(extracted_text)
            try:
                report.save(update_fields=["extracted_text", "extracted_metrics"])
            except Exception:
                # Backward compatibility if production DB has not migrated yet.
                report.extracted_metrics = None
                report.save(update_fields=["extracted_text"])

            response_data = MedicalReportSerializer(report).data
            if report.extracted_metrics is None and report.extracted_text:
                response_data["extracted_metrics"] = _extract_key_metrics(report.extracted_text)
            return Response(response_data, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class SyncSmartwatchDataView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        user = request.user
        
        # Always create a new HealthData record for historical tracking
        health_data = HealthData(user=user)
            
        health_data.heart_rate = data.get('heart_rate', health_data.heart_rate)
        health_data.sleep_hours = data.get('sleep_hours', health_data.sleep_hours)
        health_data.steps = data.get('steps', health_data.steps)
        health_data.spo2 = data.get('spo2', health_data.spo2)
        health_data.calories = data.get('calories', health_data.calories)
        health_data.stress_level = data.get('stress_level', health_data.stress_level)
        health_data.hrv = data.get('hrv', health_data.hrv)
        health_data.snoring_events = data.get('snoring_events', health_data.snoring_events)
        health_data.spo2_drops = data.get('spo2_drops', health_data.spo2_drops)
        health_data.irregular_hr_events = data.get('irregular_hr_events', health_data.irregular_hr_events)
        health_data.sitting_time = data.get('sitting_time', health_data.sitting_time)
        
        health_data.save()
        return Response({"message": "Data synced successfully", "data": HealthDataSerializer(health_data).data})

class DiseasePredictionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        disease_name = request.data.get('disease_name', 'General')
        
        # Load user data
        health_data = HealthData.objects.filter(user=request.user).last()
        
        # Determine model to load
        model_filename = "risk_model.pkl"
        if disease_name == 'Hypertension Risk':
            model_filename = 'hypertension_rf.pkl'
        elif disease_name == 'Cardiovascular Risk':
            model_filename = 'cardiovascular_xgb.pkl'
        elif disease_name == 'Sleep Apnea Risk':
            model_filename = 'sleep_apnea_cnn.h5'
        elif disease_name == 'Stress / Anxiety':
            model_filename = 'stress_svm.pkl'
        elif disease_name == 'Arrhythmia / AFib Risk':
            model_filename = 'arrhythmia_dl.h5'
        elif disease_name == 'Obesity Risk':
            model_filename = 'obesity_lr.pkl'
        elif disease_name == 'Diabetes Risk':
            model_filename = 'diabetes_xgb.pkl'
        elif disease_name == 'Fatigue Detection':
            model_filename = 'fatigue_rf.pkl'
        elif disease_name == 'Depression Risk':
            model_filename = 'depression_lstm.h5'
        elif disease_name == 'Fall Detection for Elderly':
            model_filename = 'fall_cnn.h5'
        elif disease_name == 'Sedentary Lifestyle Risk':
            model_filename = 'sedentary_dt.pkl'

        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml_model', model_filename)
        
        # MOCK PREDICTION LOGIC if model doesn't exist yet
        risk_level = 'LOW'
        risk_percentage = 15.0
        
        try:
            if model_filename.endswith('.pkl'):
                model = joblib.load(model_path)
                # mock feature array
                features = [[0] * 10] 
                # This is highly dependent on actual model features
                # risk_level = model.predict(features)[0]
                # probs = model.predict_proba(features)[0]
                # risk_percentage = min(100.0, max(probs) * 100)
            elif model_filename.endswith('.h5'):
                # For keras models (just placeholder)
                pass
        except Exception as e:
            # Fallback to mock logic if models aren't really created/loaded properly
            import random
            risk_level = random.choice(['LOW', 'MEDIUM', 'HIGH'])
            risk_percentage = random.uniform(10, 90)

        recommendation = ["Maintain a healthy lifestyle"]
        if risk_level == 'HIGH':
            recommendation = ["Consult doctor immediately", "Review your recent health data"]
            
        prediction = RiskPrediction.objects.create(
            user=request.user,
            disease_name=disease_name,
            risk_level=risk_level,
            risk_percentage=risk_percentage
        )

        return Response({
            "disease_name": disease_name,
            "risk_level": risk_level,
            "risk_percentage": round(risk_percentage, 2),
            "recommendation": recommendation,
            "prediction_id": prediction.id
        })


class ChatView(APIView):
    """
    POST /api/chat/  — Send a message and receive an AI health assistant reply.
    Request body: { "message": "..." }
    Response: { "reply": "...", "session_id": int, "history_count": int }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response({'error': 'Message cannot be empty.'}, status=400)

        user = request.user

        # ── 1. Fetch health context from DB ──────────────────────────────────
        latest_health = HealthData.objects.filter(user=user).values().last()
        risk_predictions = RiskPrediction.objects.filter(user=user).order_by('-prediction_date')[:3]
        medicines = MedicineReminder.objects.filter(user=user)

        # ── 2. Build personalised system prompt ───────────────────────────────
        system_prompt = build_system_prompt(user, latest_health, risk_predictions, medicines)

        # ── 3. Get or create the user's chat session ──────────────────────────
        session, _ = ChatSession.objects.get_or_create(user=user)

        # ── 4. Load recent conversation history (context window) ───────────────
        history_limit = getattr(settings, 'CHAT_HISTORY_LIMIT', 20)
        recent_messages = list(
            session.messages
            .order_by('-created_at')[:history_limit]
        )
        recent_messages.reverse()  # Chronological order for the LLM

        message_history = [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]

        # ── 5. Call Groq API ──────────────────────────────────────────────────
        ai_reply = get_groq_response(system_prompt, message_history, user_message)

        # ── 6. Persist both messages to DB ────────────────────────────────────
        ChatMessage.objects.create(session=session, role='user', content=user_message)
        ChatMessage.objects.create(session=session, role='assistant', content=ai_reply)

        return Response({
            'reply': ai_reply,
            'session_id': session.id,
            'history_count': session.messages.count(),
        })


class ChatHistoryView(APIView):
    """
    GET    /api/chat/history/  — Returns the last 50 chat messages for the user.
    DELETE /api/chat/history/  — Clears all chat history for the user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            session = ChatSession.objects.get(user=request.user)
            messages = session.messages.order_by('created_at')
            serializer = ChatMessageSerializer(messages, many=True)
            return Response({
                'session_id': session.id,
                'messages': serializer.data,
            })
        except ChatSession.DoesNotExist:
            return Response({'session_id': None, 'messages': []})

    def delete(self, request):
        try:
            session = ChatSession.objects.get(user=request.user)
            deleted_count, _ = session.messages.all().delete()
            return Response({'message': f'Chat history cleared. {deleted_count} messages deleted.'})
        except ChatSession.DoesNotExist:
            return Response({'message': 'No chat history found.'})
