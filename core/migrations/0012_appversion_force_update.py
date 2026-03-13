from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_video_texto_tarja'),
    ]

    operations = [
        migrations.AddField(
            model_name='appversion',
            name='force_update',
            field=models.BooleanField(
                default=False,
                help_text='Forçar atualização — app exibe alerta obrigatório'
            ),
        ),
    ]
