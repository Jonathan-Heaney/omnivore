from django.db import migrations, models
import uuid


def backfill_public_ids(apps, schema_editor):
    ArtPiece = apps.get_model('main', 'ArtPiece')
    # Only fill rows that are NULL (fresh installs skip quickly)
    for row in ArtPiece.objects.filter(public_id__isnull=True).only('id'):
        row.public_id = uuid.uuid4()
        row.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_welcomegrant'),
    ]

    operations = [
        # 1) Add nullable, non-unique field
        migrations.AddField(
            model_name='artpiece',
            name='public_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        # 2) Backfill UUIDs
        migrations.RunPython(backfill_public_ids, migrations.RunPython.noop),
        # 3) Make it NOT NULL + UNIQUE + indexed
        migrations.AlterField(
            model_name='artpiece',
            name='public_id',
            field=models.UUIDField(
                default=uuid.uuid4, unique=True, editable=False, db_index=True),
        ),
    ]
