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
python manage.py migrate --noinput || {
    echo "❌ Erro ao executar migrations!"
    exit 1
}
echo "✅ Migrations concluídas"

# Coletar arquivos estáticos (IMPORTANTE!)
echo "📂 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear || {
    echo "⚠️ Aviso: Erro ao coletar arquivos estáticos, mas continuando..."
}
echo "✅ Arquivos estáticos coletados"

# Verificar se pasta staticfiles foi criada
if [ -d "/app/staticfiles" ]; then
    echo "✅ Pasta staticfiles encontrada em /app/staticfiles"
    ls -la /app/staticfiles/ | head -10
else
    echo "⚠️ Pasta staticfiles não encontrada!"
fi

# Criar usuário OWNER se não existir
echo "👤 Verificando usuário OWNER..."
python manage.py create_owner --noinput || {
    echo "⚠️ Aviso: Não foi possível criar usuário OWNER automaticamente"
}
echo "✅ Verificação de usuário concluída"

# Iniciar servidor
echo "🌐 Iniciando servidor Gunicorn na porta ${PORT:-8000}..."
exec gunicorn mediaexpand.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
