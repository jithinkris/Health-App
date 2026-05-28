from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_medicalreport_extracted_metrics"),
    ]

    operations = [
        migrations.RenameField(
            model_name="medicalreport",
            old_name="image",
            new_name="file",
        ),
    ]
