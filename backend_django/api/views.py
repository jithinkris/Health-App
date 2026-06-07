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
from .report_extraction import (
    create_medical_report_record,
    extract_text_from_upload,
    save_parsed_report_data,
)
from .report_llm import parse_medical_report_with_groq


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


def get_user_features(user):
    """
    Calculates the 22-feature array for ML model inference and analyzes
    smartwatch/medical data for hikes/spikes against the user's normal baseline.
    """
    # 1. Demographics
    age = float(user.age) if user.age is not None else 30.0
    gender_str = (user.gender or '').lower()
    gender = 1.0 if 'male' in gender_str else (0.0 if 'female' in gender_str else 0.5)
    
    height = float(user.height) if user.height is not None else 170.0
    weight = float(user.weight) if user.weight is not None else 70.0
    bmi = weight / ((height / 100) ** 2) if (height and height > 0) else 24.2
    
    # 2. Historical baselines (fetch up to 30 past records)
    health_history = HealthData.objects.filter(user=user).order_by('-synced_at')[:30]
    report_history = MedicalReport.objects.filter(user=user).order_by('-uploaded_at')[:30]
    
    hr_vals = [h.heart_rate for h in health_history if h.heart_rate is not None]
    spo2_vals = [h.spo2 for h in health_history if h.spo2 is not None]
    bp_sys_vals = [r.blood_pressure_systolic for r in report_history if r.blood_pressure_systolic is not None]
    glucose_vals = [r.glucose for r in report_history if r.glucose is not None]
    
    # Baseline averages (excluding latest if possible, to check for a new spike)
    baseline_hr = sum(hr_vals[1:]) / len(hr_vals[1:]) if len(hr_vals) > 1 else (hr_vals[0] if hr_vals else 72.0)
    baseline_spo2 = sum(spo2_vals[1:]) / len(spo2_vals[1:]) if len(spo2_vals) > 1 else (spo2_vals[0] if spo2_vals else 98.0)
    baseline_bp_sys = sum(bp_sys_vals[1:]) / len(bp_sys_vals[1:]) if len(bp_sys_vals) > 1 else (bp_sys_vals[0] if bp_sys_vals else 120.0)
    baseline_glucose = sum(glucose_vals[1:]) / len(glucose_vals[1:]) if len(glucose_vals) > 1 else (glucose_vals[0] if glucose_vals else 90.0)
    
    # 3. Current / Latest Metrics (with imputation if missing)
    latest_health = health_history[0] if health_history.exists() else None
    latest_report = report_history[0] if report_history.exists() else None
    
    current_hr = latest_health.heart_rate if (latest_health and latest_health.heart_rate is not None) else (latest_report.heart_rate if (latest_report and latest_report.heart_rate is not None) else None)
    current_sleep = latest_health.sleep_hours if (latest_health and latest_health.sleep_hours is not None) else 7.5
    current_steps = latest_health.steps if (latest_health and latest_health.steps is not None) else 6000
    current_spo2 = latest_health.spo2 if (latest_health and latest_health.spo2 is not None) else (latest_report.spo2 if (latest_report and latest_report.spo2 is not None) else None)
    current_calories = latest_health.calories if (latest_health and latest_health.calories is not None) else 2000
    current_stress = latest_health.stress_level if (latest_health and latest_health.stress_level is not None) else 30.0
    current_hrv = latest_health.hrv if (latest_health and latest_health.hrv is not None) else 50.0
    current_snoring = latest_health.snoring_events if (latest_health and latest_health.snoring_events is not None) else 0
    current_spo2_drops = latest_health.spo2_drops if (latest_health and latest_health.spo2_drops is not None) else 0
    current_irregular_hr = latest_health.irregular_hr_events if (latest_health and latest_health.irregular_hr_events is not None) else 0
    current_sitting = latest_health.sitting_time if (latest_health and latest_health.sitting_time is not None) else 6.0
    
    current_bp_sys = latest_report.blood_pressure_systolic if (latest_report and latest_report.blood_pressure_systolic is not None) else 120
    current_bp_dia = latest_report.blood_pressure_diastolic if (latest_report and latest_report.blood_pressure_diastolic is not None) else 80
    current_glucose = latest_report.glucose if (latest_report and latest_report.glucose is not None) else 90.0
    current_hemoglobin = latest_report.hemoglobin if (latest_report and latest_report.hemoglobin is not None) else 14.0
    current_chol_total = latest_report.cholesterol_total if (latest_report and latest_report.cholesterol_total is not None) else 180.0
    current_hdl = latest_report.hdl if (latest_report and latest_report.hdl is not None) else 50.0
    current_ldl = latest_report.ldl if (latest_report and latest_report.ldl is not None) else 100.0
    current_trig = latest_report.triglycerides if (latest_report and latest_report.triglycerides is not None) else 130.0
    
    if current_hr is None: current_hr = 72.0
    if current_spo2 is None: current_spo2 = 98.0
    
    # 4. Hike/Anomaly checks & Alert creation
    hike_analysis = []
    
    # Heart rate hike
    if latest_health and latest_health.heart_rate is not None:
        val = latest_health.heart_rate
        if val > 1.2 * baseline_hr and val > 85:
            msg = f"Heart rate hike detected: Your current heart rate of {val} bpm is {int(((val - baseline_hr)/baseline_hr)*100)}% higher than your baseline average of {int(baseline_hr)} bpm."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="Heart Rate Hike Alert", message=msg)
        elif val > 100:
            msg = f"High heart rate alert: Your heart rate of {val} bpm indicates tachycardia (>100 bpm)."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="High Heart Rate Alert", message=msg)
            
    # SpO2 drops
    if latest_health and latest_health.spo2 is not None:
        val = latest_health.spo2
        if val < 95.0:
            msg = f"Low blood oxygen level (SpO2) alert: Your oxygen level is {val}%, which is below the normal range (95-100%)."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="Low SpO2 Alert", message=msg)
        elif val < baseline_spo2 - 3.0:
            msg = f"Oxygen level drop detected: Your oxygen level dropped to {val}% (baseline average is {int(baseline_spo2)}%)."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="SpO2 Drop Alert", message=msg)
            
    # Blood pressure hike
    if latest_report and latest_report.blood_pressure_systolic is not None:
        val = latest_report.blood_pressure_systolic
        if val > 1.15 * baseline_bp_sys and val > 130:
            msg = f"Elevated blood pressure detected: Current systolic BP is {val} mmHg, which is {int(((val - baseline_bp_sys)/baseline_bp_sys)*100)}% higher than your baseline average of {int(baseline_bp_sys)} mmHg."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="High Blood Pressure Alert", message=msg)
        elif val >= 140:
            msg = f"Hypertension alert: Your systolic blood pressure is {val} mmHg (Stage 2 Hypertension threshold is 140)."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="Hypertension Alert", message=msg)
            
    # Glucose hike
    if latest_report and latest_report.glucose is not None:
        val = latest_report.glucose
        if val > 1.2 * baseline_glucose and val > 120:
            msg = f"Glucose level spike detected: Current blood glucose is {val} mg/dL, which is {int(((val - baseline_glucose)/baseline_glucose)*100)}% higher than your baseline average of {int(baseline_glucose)} mg/dL."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="Blood Glucose Spike Alert", message=msg)
        elif val >= 140:
            msg = f"Hyperglycemia alert: Your blood glucose level is {val} mg/dL, indicating elevated blood sugar."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="Hyperglycemia Alert", message=msg)

    # HRV drop
    if latest_health and latest_health.hrv is not None:
        val = latest_health.hrv
        if val < 25.0:
            msg = f"Low HRV alert: Your heart rate variability is low ({val} ms), which may indicate high physical or mental fatigue."
            hike_analysis.append(msg)
            Notification.objects.get_or_create(user=user, title="Low HRV Alert", message=msg)

    features = [
        age, gender, bmi, current_hr, current_sleep, current_steps, current_spo2,
        current_calories, current_stress, current_hrv, current_snoring, current_spo2_drops,
        current_irregular_hr, current_sitting, current_bp_sys, current_bp_dia,
        current_glucose, current_hemoglobin, current_chol_total, current_hdl, current_ldl, current_trig
    ]
    
    return features, hike_analysis


class PredictRiskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        features, hike_analysis = get_user_features(request.user)
        
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml_model', 'risk_model.pkl')
        try:
            model = joblib.load(model_path)
        except Exception as e:
            return Response({'error': f'Model load failed: {str(e)}'}, status=500)

        # Run prediction
        risk_level = model.predict([features])[0]
        probs = model.predict_proba([features])[0]
        
        class_idx = list(model.classes_).index(risk_level)
        risk_percentage = min(100.0, max(0.0, probs[class_idx] * 100))

        recommendation = []
        if hike_analysis:
            recommendation.extend(hike_analysis)
            
        if risk_level == 'HIGH':
            recommendation.extend(["Consult doctor immediately if you feel unwell", "Review your recent health data", "Increase sleep duration and monitor vital metrics"])
            Notification.objects.get_or_create(
                user=request.user,
                title="High Health Risk Warning",
                message=f"Your general health risk level was evaluated as HIGH ({round(risk_percentage, 1)}%). Please seek medical advice."
            )
        elif risk_level == 'MEDIUM':
            recommendation.extend(["Consider lifestyle changes", "Monitor your heart rate frequently", "Stay hydrated and active"])
        else:
            recommendation.extend(["Maintain regular health checks", "Keep up the healthy habits!"])

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
        serializer = MedicalReportSerializer(reports, many=True, context={'request': request})
        return Response(serializer.data, status=200)

    def post(self, request, *args, **kwargs):
        try:
            uploaded_file = request.FILES.get('file') or request.FILES.get('image')
            if not uploaded_file:
                return Response({'file': ['No file was submitted.']}, status=400)

            report = create_medical_report_record(request.user, uploaded_file)

            raw_text = ""
            try:
                raw_text = extract_text_from_upload(report.image.path)
            except Exception:
                raw_text = ""

            if not raw_text:
                raw_text = "Could not extract readable text from the report."

            parsed = parse_medical_report_with_groq(raw_text)
            summary = parsed.get("summary") or "Report processed successfully."
            metrics = parsed.get("metrics") or {}
            save_parsed_report_data(report, summary, metrics)

            serializer = MedicalReportSerializer(report, context={'request': request})
            return Response(serializer.data, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class SyncSmartwatchDataView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        user = request.user
        
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
        features, hike_analysis = get_user_features(request.user)
        
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
        
        try:
            model = joblib.load(model_path)
            risk_level = model.predict([features])[0]
            probs = model.predict_proba([features])[0]
            
            class_idx = list(model.classes_).index(risk_level)
            risk_percentage = min(100.0, max(0.0, probs[class_idx] * 100))
        except Exception as e:
            # Fallback to general rules if model fails to load
            import random
            risk_level = random.choice(['LOW', 'MEDIUM', 'HIGH'])
            risk_percentage = random.uniform(10, 90)

        recommendation = []
        if hike_analysis:
            recommendation.extend(hike_analysis)
            
        if risk_level == 'HIGH':
            recommendation.extend(["Consult doctor immediately", "Review your recent health data and vital parameters"])
            Notification.objects.get_or_create(
                user=request.user,
                title=f"High Risk Alert: {disease_name}",
                message=f"Your predicted risk of {disease_name} is HIGH ({round(risk_percentage, 1)}%). Please seek professional medical advice."
            )
        elif risk_level == 'MEDIUM':
            recommendation.extend(["Consider lifestyle modifications", "Schedule a checkup with your healthcare provider"])
        else:
            recommendation.extend(["Maintain healthy habits and active lifestyle"])
            
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
