from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_video_url_externa_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='conteudocorporativo',
            name='franqueado',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Franqueado dono deste conteúdo. Nulo = pertence ao owner. Templates (is_template=True) são visíveis a todos.',
                limit_choices_to={'role': 'FRANCHISEE'},
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='conteudos_corporativos',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Franqueado',
            ),
        ),
    ]
