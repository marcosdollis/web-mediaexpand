from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_conteudocorporativo_orientacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogExibicaoWebView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_conteudo', models.CharField(
                    choices=[
                        ('PREVISAO_TEMPO', 'Previsão do Tempo'),
                        ('COTACOES', 'Cotações'),
                        ('NOTICIAS', 'Notícias'),
                        ('DESIGN', 'Design/Editor'),
                    ],
                    default='DESIGN', max_length=20
                )),
                ('titulo', models.CharField(default='Conteúdo Corporativo', max_length=200)),
                ('duracao_segundos', models.IntegerField(default=0)),
                ('data_hora_inicio', models.DateTimeField()),
                ('data_hora_fim', models.DateTimeField(blank=True, null=True)),
                ('completamente_exibido', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('conteudo_corporativo', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs_webview', to='core.conteudocorporativo'
                )),
                ('dispositivo', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs_webview', to='core.dispositivotv'
                )),
                ('playlist', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs_webview', to='core.playlist'
                )),
            ],
            options={
                'verbose_name': 'Log WebView',
                'verbose_name_plural': 'Logs WebView',
                'ordering': ['-data_hora_inicio'],
            },
        ),
    ]
