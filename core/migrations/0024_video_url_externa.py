import core.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_agendamentoexibicao_percentual'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='url_externa',
            field=models.URLField(
                blank=True,
                null=True,
                max_length=500,
                verbose_name='URL externa do vídeo',
                help_text='Link direto para o vídeo (ex: CDN, Instagram CDN) — substitui o upload de arquivo',
            ),
        ),
        migrations.AlterField(
            model_name='video',
            name='arquivo',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=core.models.video_upload_path,
                validators=[django.core.validators.FileExtensionValidator(
                    allowed_extensions=['mp4', 'avi', 'mov', 'mkv', 'webm']
                )],
            ),
        ),
    ]
