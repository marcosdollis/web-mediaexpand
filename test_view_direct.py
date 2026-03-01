#!/usr/bin/env python
"""
Teste direto da view design_search_images_view
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediaexpand.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
    print("✅ Django configurado com sucesso")
except Exception as e:
    print(f"❌ Erro ao configurar Django: {e}")
    sys.exit(1)

# Agora importa depois do setup
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.views import design_search_images_view
from django.conf import settings

print("\n" + "="*60)
print("🧪 TESTE DIRETO DA VIEW design_search_images_view")
print("="*60)

# Verifica se a API key está configurada
api_key = getattr(settings, 'PIXABAY_API_KEY', '')
print(f"\n📋 Configuração:")
print(f"   PIXABAY_API_KEY: {bool(api_key)}")
if api_key:
    print(f"   Valor: {api_key[:10]}...{api_key[-5:]}")

# Cria um usuário fake para o teste
User = get_user_model()
try:
    user = User.objects.first()
    if not user:
        print("\n⚠️ Nenhum usuário encontrado no banco")
        print("   Criando usuário de teste...")
        user = User.objects.create_user(
            username='test',
            email='test@test.com',
            password='test123',
            user_type='OWNER'
        )
        print("   ✅ Usuário criado")
    else:
        print(f"\n✅ Usando usuário: {user.username}")
except Exception as e:
    print(f"\n❌ Erro ao criar/buscar usuário: {e}")
    sys.exit(1)

# Cria uma requisição fake
factory = RequestFactory()
request = factory.get('/corporativo/design/search-images/', {
    'q': 'natureza',
    'page': 1,
    'per_page': 5,
    'image_type': 'photo'
})
request.user = user

print("\n🔍 Executando busca...")
print(f"   Query: natureza")
print(f"   Page: 1")
print(f"   Per page: 5")
print(f"   Type: photo")

try:
    response = design_search_images_view(request)
    
    print(f"\n📊 Resposta:")
    print(f"   Status Code: {response.status_code}")
    
    import json
    data = json.loads(response.content.decode())
    
    print(f"   Success: {data.get('success')}")
    print(f"   Message: {data.get('message', 'N/A')}")
    print(f"   Results: {len(data.get('results', []))} imagens")
    print(f"   Total: {data.get('total', 0)}")
    
    if data.get('results'):
        first = data['results'][0]
        print(f"\n📸 Primeira imagem:")
        print(f"   ID: {first.get('id')}")
        print(f"   Tags: {first.get('tags', 'N/A')[:50]}...")
        print(f"   Source: {first.get('source')}")
        print(f"   Thumbnail: {first.get('thumbnail', 'N/A')[:60]}...")
    
    print("\n" + "="*60)
    if data.get('success'):
        print("🎉 TESTE PASSOU! View funcionando corretamente")
    else:
        print("⚠️ View retornou erro (mas não crashou)")
        print(f"   Mensagem: {data.get('message')}")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERRO ao executar view:")
    print(f"   Tipo: {type(e).__name__}")
    print(f"   Mensagem: {str(e)}")
    
    import traceback
    print(f"\n📋 Traceback completo:")
    traceback.print_exc()
    
    print("\n" + "="*60)
    print("❌ TESTE FALHOU!")
    print("="*60)
    sys.exit(1)
