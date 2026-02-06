@echo off
echo ========================================
echo MediaExpand - Inicializacao Rapida
echo ========================================
echo.

echo [1/6] Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo ERRO: Falha ao criar ambiente virtual
    pause
    exit /b 1
)

echo [2/6] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo [3/6] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias
    pause
    exit /b 1
)

echo [4/6] Executando migracoes...
python manage.py migrate
if errorlevel 1 (
    echo ERRO: Falha nas migracoes
    pause
    exit /b 1
)

echo [5/6] Criando usuario OWNER...
python manage.py create_owner

echo [6/6] Coletando arquivos estaticos...
python manage.py collectstatic --noinput

echo.
echo ========================================
echo Instalacao concluida com sucesso!
echo ========================================
echo.
echo Para iniciar o servidor:
echo   python manage.py runserver
echo.
echo Admin: http://127.0.0.1:8000/admin/
echo API: http://127.0.0.1:8000/api/
echo.
pause
