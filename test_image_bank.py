#!/usr/bin/env python
"""
Script de teste para verificar configuração do banco de imagens.
Execute: python test_image_bank.py
"""

import os
import sys
import urllib.request
import urllib.parse
import json

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediaexpand.settings')
import django
django.setup()

from django.conf import settings

def test_pixabay():
    """Testa conexão com Pixabay API"""
    print("\n🔍 Testando Pixabay API...")
    
    api_key = getattr(settings, 'PIXABAY_API_KEY', '') or os.environ.get('PIXABAY_API_KEY', '')
    
    if not api_key:
        print("❌ PIXABAY_API_KEY não encontrada!")
        print("   Configure no .env: PIXABAY_API_KEY=sua-chave-aqui")
        print("   Ou adicione nas variáveis de ambiente do Railway")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:10]}...{api_key[-5:]}")
    
    # Teste de busca
    params = {
        'key': api_key,
        'q': 'nature',
        'per_page': 3,
        'lang': 'pt',
    }
    
    url = 'https://pixabay.com/api/?' + urllib.parse.urlencode(params)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MediaExpand/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        
        total = data.get('totalHits', 0)
        hits = len(data.get('hits', []))
        
        print(f"✅ Pixabay funcionando! Total de resultados: {total}")
        print(f"   Recebeu {hits} imagens na resposta")
        
        if hits > 0:
            first = data['hits'][0]
            print(f"   Primeira imagem: {first.get('tags', 'N/A')}")
        
        return True
        
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.reason}")
        if e.code == 403:
            print("   → API Key inválida ou limite excedido")
        return False
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


def test_iconify():
    """Testa conexão com Iconify API (sem necessidade de chave)"""
    print("\n🎨 Testando Iconify API...")
    
    params = {
        'query': 'home',
        'limit': 3,
    }
    
    url = 'https://api.iconify.design/search?' + urllib.parse.urlencode(params)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MediaExpand/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        
        total = data.get('total', 0)
        icons = data.get('icons', [])
        
        print(f"✅ Iconify funcionando! Total de ícones: {total}")
        print(f"   Recebeu {len(icons)} ícones na resposta")
        
        if icons:
            print(f"   Primeiro ícone: {icons[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


def test_picsum():
    """Testa conexão com Lorem Picsum (fallback)"""
    print("\n🖼️ Testando Lorem Picsum (fallback)...")
    
    url = 'https://picsum.photos/v2/list?page=1&limit=3'
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MediaExpand/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        
        print(f"✅ Lorem Picsum funcionando! Recebeu {len(data)} imagens")
        
        if data:
            first = data[0]
            print(f"   Primeira imagem: ID {first.get('id')} por {first.get('author')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


def main():
    print("=" * 60)
    print("🧪 TESTE DE CONFIGURAÇÃO DO BANCO DE IMAGENS")
    print("=" * 60)
    
    results = {
        'pixabay': test_pixabay(),
        'iconify': test_iconify(),
        'picsum': test_picsum(),
    }
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for service, success in results.items():
        status = "✅ OK" if success else "❌ FALHOU"
        print(f"{service.upper():.<20} {status}")
    
    print("\n" + "=" * 60)
    
    if all(results.values()):
        print("🎉 Tudo funcionando perfeitamente!")
    elif results['iconify'] and results['picsum']:
        print("⚠️ Pixabay não configurado, mas fallback (Picsum + Iconify) funcionando")
    else:
        print("❌ Alguns serviços não estão funcionando. Verifique a conexão com a internet.")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
