from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (RegisterView, HealthDataViewSet, RiskPredictionViewSet, SleepScheduleViewSet, HydrationLogViewSet, MedicineReminderViewSet, NotificationViewSet, PredictRiskView, CurrentUserView, GoogleLoginView, UploadMedicalReportView, SyncSmartwatchDataView, DiseasePredictionView, ChatView, ChatHistoryView, OverallAnalyticsView)

router = DefaultRouter()
router.register(r'health', HealthDataViewSet, basename='health')
router.register(r'predict-risk', RiskPredictionViewSet, basename='predict-risk')
router.register(r'sleep', SleepScheduleViewSet, basename='sleep')
router.register(r'hydration', HydrationLogViewSet, basename='hydration')
router.register(r'medicine', MedicineReminderViewSet, basename='medicine')
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('predict-risk-ml/', PredictRiskView.as_view(), name='predict-risk-ml'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('upload-report/', UploadMedicalReportView.as_view(), name='upload_report'),
    path('sync-smartwatch/', SyncSmartwatchDataView.as_view(), name='sync_smartwatch'),
    path('predict-disease/', DiseasePredictionView.as_view(), name='predict_disease'),
    path('overall-analytics/', OverallAnalyticsView.as_view(), name='overall_analytics'),
    # Chatbot endpoints
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/history/', ChatHistoryView.as_view(), name='chat_history'),
    path('', include(router.urls)),
]

