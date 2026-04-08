from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_landing_lead'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campanha',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('CUPOM', 'Resgate de Cupom de Desconto'),
                    ('ROLETA', 'Roleta de Prêmios'),
                    ('CARTA', 'Virar a Carta'),
                    ('ALERTA', 'Alerta Inteligente'),
                    ('SORTEIO', 'Sorteio'),
                ],
                default='CUPOM',
                max_length=30,
                verbose_name='Tipo de Campanha',
            ),
        ),
        migrations.CreateModel(
            name='CampanhaSorteioConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo_pagina', models.CharField(blank=True, max_length=200, verbose_name='Título da Página Pública')),
                ('descricao_pagina', models.TextField(blank=True, verbose_name='Descrição / Instruções')),
                ('mensagem_sucesso', models.CharField(default='Inscrição realizada! Boa sorte no sorteio!', max_length=400, verbose_name='Mensagem de Sucesso')),
                ('foto_item', models.ImageField(blank=True, null=True, upload_to='campanhas/sorteio/', verbose_name='Foto do Item Sorteado')),
                ('capturar_telefone', models.BooleanField(default=True, verbose_name='Capturar Telefone')),
                ('capturar_endereco', models.BooleanField(default=False, verbose_name='Capturar Endereço')),
                ('bloquear_duplicados_cpf', models.BooleanField(default=True, verbose_name='Bloquear CPF duplicado')),
                ('bloquear_duplicados_ip', models.BooleanField(default=False, verbose_name='Bloquear IP duplicado')),
                ('cor_primaria', models.CharField(default='#6366f1', max_length=7, verbose_name='Cor Principal')),
                ('data_sorteio', models.DateTimeField(blank=True, null=True, verbose_name='Data/Hora do Sorteio')),
                ('campanha', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='config_sorteio',
                    to='core.campanha',
                )),
            ],
            options={
                'verbose_name': 'Config. Sorteio',
            },
        ),
        migrations.CreateModel(
            name='CampanhaParticipanteSorteio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('cpf', models.CharField(max_length=14)),
                ('telefone', models.CharField(blank=True, max_length=20)),
                ('endereco', models.CharField(blank=True, max_length=400)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('ativo_sorteio', models.BooleanField(default=True, verbose_name='Participar do Sorteio')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('campanha', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='participantes_sorteio',
                    to='core.campanha',
                )),
            ],
            options={
                'verbose_name': 'Participante de Sorteio',
                'verbose_name_plural': 'Participantes de Sorteio',
                'ordering': ['-criado_em'],
            },
        ),
    ]
