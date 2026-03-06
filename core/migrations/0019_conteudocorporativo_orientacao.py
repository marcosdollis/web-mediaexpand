from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_conteudocorporativo_cotacoes_commodities_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='conteudocorporativo',
            name='orientacao',
            field=models.CharField(
                choices=[
                    ('HORIZONTAL', 'Horizontal (16:9 — 1920×1080)'),
                    ('VERTICAL', 'Vertical (9:16 — 1080×1920)'),
                ],
                default='HORIZONTAL',
                help_text='Orientação de exibição na TV',
                max_length=12,
            ),
        ),
    ]
