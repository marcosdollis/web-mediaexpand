#!/bin/bash
# Script de inicialização para Railway

set -e  # Para na primeira falha

echo "🚀 Iniciando MediaExpand..."

# Verificar se DATABASE_URL existe
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Erro: DATABASE_URL não configurado!"
    exit 1
fi

echo "✅ DATABASE_URL configurado"

# Executar migrations
echo "📦 Executando migrations..."
python manage.py migrate --noinput
echo "✅ Migrations concluídas"

# Criar tabela de cache no banco (idempotente)
echo "📦 Criando tabela de cache..."
python manage.py createcachetable
echo "✅ Cache configurado"

# IMPORTANTE: Coletar arquivos estáticos COM verbose para debug
echo "📂 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear -v 2
echo "✅ Arquivos estáticos coletados"

# Verificar arquivos coletados
echo "📋 Verificando arquivos em staticfiles:"
if [ -d "/app/staticfiles" ]; then
    echo "Pasta staticfiles existe"
    echo "Arquivos CSS:"
    ls -la /app/staticfiles/css/ || echo "Pasta css não encontrada"
    echo "Arquivos JS:"
    ls -la /app/staticfiles/js/ || echo "Pasta js não encontrada"
    echo "Total de arquivos:"
    find /app/staticfiles -type f | wc -l
else
    echo "⚠️ Pasta staticfiles NÃO EXISTE!"
fi

# Criar usuário OWNER se não existir
echo "👤 Verificando usuário OWNER..."
python manage.py create_owner --noinput
echo "✅ Verificação de usuário concluída"

# Iniciar servidor
echo "🌐 Iniciando servidor Gunicorn na porta ${PORT:-8000}..."
exec gunicorn mediaexpand.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 900 \
    --keep-alive 75 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
