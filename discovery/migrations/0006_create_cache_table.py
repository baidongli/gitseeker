from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command("createcachetable", "gitseeker_cache")


def drop_cache_table(apps, schema_editor):
    schema_editor.execute("DROP TABLE IF EXISTS gitseeker_cache")


class Migration(migrations.Migration):

    dependencies = [
        ("discovery", "0005_setting"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
