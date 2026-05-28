from django.db import migrations, models


def _column_exists(schema_editor, table_name, column_name):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({table_name})")
            return column_name in [row[1] for row in cursor.fetchall()]

        if connection.vendor == "postgresql":
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                LIMIT 1
                """,
                [table_name, column_name],
            )
            return cursor.fetchone() is not None

    return False


def add_metric_columns_if_missing(apps, schema_editor):
    table_name = "api_medicalreport"
    columns = {
        "heart_rate": "INTEGER",
        "blood_pressure_systolic": "INTEGER",
        "blood_pressure_diastolic": "INTEGER",
        "spo2": "REAL",
        "hemoglobin": "REAL",
        "glucose": "REAL",
        "cholesterol_total": "REAL",
        "hdl": "REAL",
        "ldl": "REAL",
        "triglycerides": "REAL",
    }

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        for column_name, sql_type in columns.items():
            if _column_exists(schema_editor, table_name, column_name):
                continue
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type} NULL"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_remove_medicalreport_extracted_metrics"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="medicalreport",
                    name="heart_rate",
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="blood_pressure_systolic",
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="blood_pressure_diastolic",
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="spo2",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="hemoglobin",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="glucose",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="cholesterol_total",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="hdl",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="ldl",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="medicalreport",
                    name="triglycerides",
                    field=models.FloatField(blank=True, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_metric_columns_if_missing,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
