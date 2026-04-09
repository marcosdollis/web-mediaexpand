import uuid
from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    AgenteIA = apps.get_model('core', 'AgenteIA')
    for agente in AgenteIA.objects.filter(public_id__isnull=True):
        agente.public_id = uuid.uuid4()
        agente.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_agenteia_base_conhecimento'),
    ]

    operations = [
        # Passo 1: adiciona como nullable sem unique
        migrations.AddField(
            model_name='agenteia',
            name='public_id',
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                help_text='Identificador público permanente da URL do chat — não muda se o nome mudar',
            ),
        ),
        # Passo 2: popula um UUID único para cada linha existente
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        # Passo 3: adiciona constraint unique e remove null
        migrations.AlterField(
            model_name='agenteia',
            name='public_id',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                help_text='Identificador público permanente da URL do chat — não muda se o nome mudar',
            ),
        ),
    ]
