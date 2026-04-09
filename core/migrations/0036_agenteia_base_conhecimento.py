from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_agente_ia'),
    ]

    operations = [
        migrations.AddField(
            model_name='agenteia',
            name='base_conhecimento',
            field=models.FileField(
                blank=True,
                help_text='Arquivo .txt ou .csv com catálogo de produtos, imóveis, FAQ etc. Máx. 200 KB por envio.',
                null=True,
                upload_to='agentes/conhecimento/',
                verbose_name='Base de Conhecimento (arquivo)',
            ),
        ),
    ]
