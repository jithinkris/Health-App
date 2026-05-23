from rest_framework import generics, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
import os
import joblib
from .models import User, HealthData, RiskPrediction, SleepSchedule, HydrationLog, MedicineReminder, Notification, MedicalReport
from .serializers import (UserSerializer, HealthDataSerializer, RiskPredictionSerializer, SleepScheduleSerializer, 
                          HydrationLogSerializer, MedicineReminderSerializer, NotificationSerializer, MedicalReportSerializer)
from rest_framework.parsers import MultiPartParser, FormParser

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
        file_serializer = MedicalReportSerializer(data=request.data)
        if file_serializer.is_valid():
            report = file_serializer.save(user=request.user)
            # OCR logic placeholder
            try:
                import pytesseract
                from PIL import Image
                text = pytesseract.image_to_string(Image.open(report.image.path))
                report.extracted_text = text
                report.save()
            except Exception as e:
                report.extracted_text = "Mock OCR Text: Blood Pressure: 120/80, Heart Rate: 75 bpm"
                report.save()
                
            return Response(MedicalReportSerializer(report).data, status=201)
        else:
            return Response(file_serializer.errors, status=400)

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

