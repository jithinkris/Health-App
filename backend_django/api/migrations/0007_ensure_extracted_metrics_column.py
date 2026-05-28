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


def add_extracted_metrics_if_missing(apps, schema_editor):
    table_name = "api_medicalreport"
    column_name = "extracted_metrics"

    if _column_exists(schema_editor, table_name, column_name):
        return

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT NULL"
            )
        elif connection.vendor == "postgresql":
            cursor.execute(
                f'ALTER TABLE {table_name} ADD COLUMN {column_name} JSONB NULL'
            )
        else:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} JSON NULL"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_rename_medicalreport_image_to_file"),
    ]

    operations = [
        migrations.RunPython(
            add_extracted_metrics_if_missing,
            migrations.RunPython.noop,
        ),
    ]
