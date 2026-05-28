from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_chatsession_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicalreport',
            name='extracted_metrics',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
