#!/bin/bash

echo "========================================"
echo "MediaExpand - Inicialização Rápida"
echo "========================================"
echo ""

echo "[1/6] Criando ambiente virtual..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao criar ambiente virtual"
    exit 1
fi

echo "[2/6] Ativando ambiente virtual..."
source venv/bin/activate

echo "[3/6] Instalando dependências..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao instalar dependências"
    exit 1
fi

echo "[4/6] Executando migrações..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "ERRO: Falha nas migrações"
    exit 1
fi

echo "[5/6] Criando usuário OWNER..."
python manage.py create_owner

echo "[6/6] Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo ""
echo "========================================"
echo "Instalação concluída com sucesso!"
echo "========================================"
echo ""
echo "Para iniciar o servidor:"
echo "  python manage.py runserver"
echo ""
echo "Admin: http://127.0.0.1:8000/admin/"
echo "API: http://127.0.0.1:8000/api/"
echo ""
