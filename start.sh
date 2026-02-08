#!/bin/bash
# Script de inicialização para Railway

echo "🚀 Iniciando MediaExpand..."

# Aguardar PostgreSQL estar disponível
echo "⏳ Aguardando PostgreSQL..."
python << END
import sys
import time
import psycopg2
from urllib.parse import urlparse
import os

max_retries = 30
retry_count = 0

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL não configurado!")
    sys.exit(1)

result = urlparse(database_url)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        conn.close()
        print("✅ PostgreSQL conectado!")
        break
    except psycopg2.OperationalError:
        retry_count += 1
        print(f"⏳ Tentativa {retry_count}/{max_retries}...")
        time.sleep(1)

if retry_count >= max_retries:
    print("❌ Não foi possível conectar ao PostgreSQL!")
    sys.exit(1)
END

# Executar migrations
echo "📦 Executando migrations..."
python manage.py migrate --noinput

# Coletar arquivos estáticos
echo "📂 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Criar usuário OWNER se não existir
echo "👤 Verificando usuário OWNER..."
python manage.py create_owner --noinput

# Iniciar servidor
echo "✅ Iniciando servidor Gunicorn..."
exec gunicorn mediaexpand.wsgi --log-file - --bind 0.0.0.0:$PORT
