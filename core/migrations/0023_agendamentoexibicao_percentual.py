from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_merge_appversion_force_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamentoexibicao',
            name='percentual',
            field=models.IntegerField(
                default=100,
                help_text=(
                    'Percentual desta playlist na composição total (0-100). '
                    'Ex: 80 = 80% dos slots para esta playlist. '
                    'Se todos forem 0 ou houver apenas uma playlist, o comportamento é sequencial normal.'
                ),
            ),
        ),
    ]
