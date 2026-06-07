from rest_framework import serializers
from .models import User, HealthData, RiskPrediction, SleepSchedule, HydrationLog, MedicineReminder, Notification, MedicalReport, ChatMessage

class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name', required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'name', 'password', 'age', 'gender', 'height', 'weight')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Default behavior of AbstractUser is to require a username. If not provided, we can use email.
        email = validated_data.get('email', '')
        username = validated_data.get('username', email)
        
        user = User(
            username=username,
            email=email,
            first_name=validated_data.get('first_name', ''),
            age=validated_data.get('age'),
            gender=validated_data.get('gender'),
            height=validated_data.get('height'),
            weight=validated_data.get('weight')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class HealthDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthData
        fields = '__all__'
        read_only_fields = ('user', 'synced_at')

class RiskPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskPrediction
        fields = '__all__'
        read_only_fields = ('user', 'prediction_date')

class SleepScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SleepSchedule
        fields = '__all__'
        read_only_fields = ('user',)

class HydrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HydrationLog
        fields = '__all__'
        read_only_fields = ('user', 'timestamp')

class MedicineReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineReminder
        fields = '__all__'
        read_only_fields = ('user',)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

class MedicalReportSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    extracted_text = serializers.SerializerMethodField()
    extracted_metrics = serializers.SerializerMethodField()
    metrics_table = serializers.SerializerMethodField()

    class Meta:
        model = MedicalReport
        fields = (
            'id', 'user', 'file', 'extracted_text', 'extracted_metrics',
            'metrics_table', 'uploaded_at',
        )
        read_only_fields = ('user', 'uploaded_at')

    def get_file(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def get_extracted_text(self, obj):
        from .report_extraction import display_summary
        return display_summary(obj.extracted_text)

    def get_extracted_metrics(self, obj):
        from .report_extraction import metrics_from_report
        return metrics_from_report(obj)

    def get_metrics_table(self, obj):
        from .report_extraction import metrics_table_rows
        return metrics_table_rows(obj)

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'role', 'content', 'created_at')
