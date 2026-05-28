from django.db import migrations


class Migration(migrations.Migration):
    """
    Keep DB compatibility on free Render instances where extracted_metrics
    column was never created. Metrics are stored inside extracted_text.
    """

    dependencies = [
        ("api", "0007_ensure_extracted_metrics_column"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="medicalreport",
                    name="extracted_metrics",
                ),
            ],
            database_operations=[],
        ),
    ]
