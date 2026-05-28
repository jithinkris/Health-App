from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    height = models.FloatField(null=True, blank=True) # in cm
    weight = models.FloatField(null=True, blank=True) # in kg

class HealthData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_data')
    heart_rate = models.IntegerField(null=True, blank=True)
    sleep_hours = models.FloatField(null=True, blank=True)
    steps = models.IntegerField(null=True, blank=True)
    spo2 = models.FloatField(null=True, blank=True)
    calories = models.IntegerField(null=True, blank=True)
    stress_level = models.FloatField(null=True, blank=True) # e.g., 0-100
    hrv = models.FloatField(null=True, blank=True) # Heart Rate Variability in ms
    snoring_events = models.IntegerField(null=True, blank=True)
    spo2_drops = models.IntegerField(null=True, blank=True)
    irregular_hr_events = models.IntegerField(null=True, blank=True)
    sitting_time = models.FloatField(null=True, blank=True) # in hours
    synced_at = models.DateTimeField(auto_now_add=True)

class RiskPrediction(models.Model):
    RISK_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    disease_name = models.CharField(max_length=100, default="General")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS)
    risk_percentage = models.FloatField()
    prediction_date = models.DateTimeField(auto_now_add=True)

class SleepSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sleep_schedule')
    bedtime = models.TimeField()
    wakeup_time = models.TimeField()

class HydrationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hydration_logs')
    water_amount = models.IntegerField() # in ml
    timestamp = models.DateTimeField(auto_now_add=True)

class MedicineReminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicines')
    medicine_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    timing = models.TimeField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.BooleanField(default=False) # True if taken

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class MedicalReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_reports')
    image = models.FileField(upload_to='medical_reports/')
    extracted_text = models.TextField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    spo2 = models.FloatField(null=True, blank=True)
    hemoglobin = models.FloatField(null=True, blank=True)
    glucose = models.FloatField(null=True, blank=True)
    cholesterol_total = models.FloatField(null=True, blank=True)
    hdl = models.FloatField(null=True, blank=True)
    ldl = models.FloatField(null=True, blank=True)
    triglycerides = models.FloatField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ChatSession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_session')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ChatSession({self.user.username})"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
