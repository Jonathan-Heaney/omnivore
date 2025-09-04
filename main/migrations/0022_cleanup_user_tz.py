# main/migrations/0022_cleanup_user_tz.py
from django.db import migrations


def null_out_utc(apps, schema_editor):
    User = apps.get_model("main", "CustomUser")
    User.objects.filter(timezone="UTC").update(timezone=None)
    User.objects.filter(timezone="").update(timezone=None)


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0021_alter_customuser_timezone'),
    ]

    operations = [migrations.RunPython(
        null_out_utc, migrations.RunPython.noop)]
