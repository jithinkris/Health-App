from django.db import migrations


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


def ensure_metric_columns(apps, schema_editor):
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
        ("api", "0010_alter_medicalreport_image"),
    ]

    operations = [
        migrations.RunPython(ensure_metric_columns, migrations.RunPython.noop),
    ]
