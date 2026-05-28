from django.db import migrations


class Migration(migrations.Migration):
    """
    Intentionally no-op: production DB keeps the `image` column.
    The API accepts multipart field `file` via serializer source mapping.
    """

    dependencies = [
        ("api", "0005_medicalreport_extracted_metrics"),
    ]

    operations = []
