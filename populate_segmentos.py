"""
Script para popular segmentos iniciais
Execute: python populate_segmentos.py
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediaexpand.settings')
django.setup()

from core.models import Segmento

# Lista de segmentos padrão
segmentos_data = [
    ('Alimentação', 'Restaurantes, bares, lanchonetes, supermercados'),
    ('Saúde', 'Clínicas, hospitais, farmácias, laboratórios'),
    ('Educação', 'Escolas, cursos, universidades'),
    ('Comércio', 'Lojas, varejo em geral'),
    ('Serviços', 'Prestadores de serviços diversos'),
    ('Indústria', 'Fábricas e indústrias'),
    ('Tecnologia', 'TI, software, eletrônicos'),
    ('Construção', 'Construção civil, materiais'),
    ('Automotivo', 'Concessionárias, oficinas, autopeças'),
    ('Moda e Beleza', 'Salões, boutiques, cosméticos'),
    ('Entretenimento', 'Cinemas, eventos, lazer'),
    ('Financeiro', 'Bancos, financeiras, contabilidade'),
    ('Imobiliário', 'Imobiliárias, corretoras'),
    ('Agronegócio', 'Agricultura, pecuária, agropecuária'),
    ('Outros', 'Segmentos diversos'),
]

# Criar segmentos
criados = 0
existentes = 0

for nome, descricao in segmentos_data:
    segmento, created = Segmento.objects.get_or_create(
        nome=nome,
        defaults={
            'descricao': descricao,
            'ativo': True
        }
    )
    
    if created:
        criados += 1
        print(f'✓ Criado: {nome}')
    else:
        existentes += 1
        print(f'- Já existe: {nome}')

print(f'\n✅ Processo concluído!')
print(f'   Criados: {criados}')
print(f'   Já existentes: {existentes}')
print(f'   Total: {criados + existentes}')
