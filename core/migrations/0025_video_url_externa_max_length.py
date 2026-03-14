from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_video_url_externa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='url_externa',
            field=models.URLField(
                blank=True,
                null=True,
                max_length=2000,
                verbose_name='URL externa do vídeo',
                help_text='Link direto para o vídeo (ex: CDN, Instagram CDN) — substitui o upload de arquivo',
            ),
        ),
    ]
