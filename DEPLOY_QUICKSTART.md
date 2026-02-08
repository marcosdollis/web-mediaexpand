# 🚀 Deploy Rápido - MediaExpand

## 📋 Pré-requisitos

- Conta no GitHub
- Conta no Railway (usar GitHub para login)
- SECRET_KEY gerada

---

## ⚡ Deploy em 5 Passos

### 1️⃣ Commit e Push para GitHub

```bash
# Commitar alterações
git add .
git commit -m "Sistema MediaExpand completo com gerenciamento de APK"
git push origin main
```

### 2️⃣ Criar Projeto no Railway

1. Acesse: https://railway.app
2. Login com GitHub
3. **New Project** → **Deploy from GitHub repo**
4. Selecione: `web-mediaexpand`
5. Railway detecta Django automaticamente

### 3️⃣ Adicionar PostgreSQL

1. No projeto Railway: **New** → **Database** → **PostgreSQL**
2. Railway conecta automaticamente via `DATABASE_URL`

### 4️⃣ Configurar Variáveis de Ambiente

No Railway: **Service** → **Variables** → **Raw Editor**

```env
DEBUG=False
SECRET_KEY=sua-secret-key-aqui
ALLOWED_HOSTS=*.railway.app
CSRF_TRUSTED_ORIGINS=https://*.railway.app

# Usuário OWNER (criado automaticamente no primeiro deploy)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@mediaexpand.com
DJANGO_SUPERUSER_PASSWORD=SuaSenhaForteAqui123!
DJANGO_SUPERUSER_FIRST_NAME=Administrador
DJANGO_SUPERUSER_LAST_NAME=Sistema
```

**Gerar SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

⚠️ **IMPORTANTE**: O usuário OWNER será criado **automaticamente** no primeiro deploy usando essas variáveis!

### 5️⃣ Deploy Automático

O Railway faz deploy automaticamente e:
1. Instala dependências
2. Executa migrations
3. **Cria usuário OWNER automaticamente** (se não existir)
4. Coleta arquivos estáticos
5. Inicia o servidor

**Não precisa mais executar `create_owner` manualmente!** ✨

**Pronto! 🎉**

---

## 🌐 Acessar Sistema

### URLs Automáticas do Railway:

- **Admin Django**: `https://seu-app.up.railway.app/admin/`
- **Dashboard Web**: `https://seu-app.up.railway.app/dashboard/`
- **API Swagger**: `https://seu-app.up.railway.app/api/swagger/`
- **Download APK**: `https://seu-app.up.railway.app/app/download/`

### Login:
- Usuário: `marcos` (ou o que você criou)
- Senha: (a que você definiu)

---

## 📱 Funcionalidades Disponíveis

✅ **Sistema Web Completo**
- Dashboard para OWNER, FRANCHISEE e CLIENT
- Gestão de municípios, franqueados e clientes
- Upload e aprovação de vídeos
- Criação de playlists
- Gerenciamento de dispositivos TV
- Agendamento de exibições
- Sistema de segmentos/categorias

✅ **API REST Completa**
- Autenticação JWT
- CRUD de todos os recursos
- Documentação Swagger automática
- Endpoints para TV App

✅ **TV App API**
- Autenticação por UUID único
- Download de playlist com vídeos
- Registro de logs de exibição
- Verificação de horários de exibição

✅ **Gerenciamento de APK**
- Upload de versões do app Android
- Download público da versão ativa
- Controle de versões e ativação
- Contador de downloads
- Notas de versão

---

## 🔗 Links Importantes

### Para Desenvolvedores do App:
- **Documentação API**: `https://seu-app.up.railway.app/api/swagger/`
- **Guia TV App**: Ver arquivo `API_TV_APP_GUIDE.md`
- **Download APK**: `https://seu-app.up.railway.app/app/download/`

### Para Gestores:
- **Login Sistema**: `https://seu-app.up.railway.app/login/`
- **Dashboard**: `https://seu-app.up.railway.app/dashboard/`

---

## ⚠️ IMPORTANTE - Armazenamento de Arquivos

O Railway usa **sistema de arquivos efêmero** (arquivos podem ser perdidos em redeploy).

### Soluções para Produção:

#### Opção 1: Railway Volumes (Básico)
```bash
# No Railway: Settings → Volumes → Add Volume
# Mount Path: /data
# Atualizar settings.py: MEDIA_ROOT = '/data/media'
```

#### Opção 2: AWS S3 (Recomendado)
```bash
pip install django-storages boto3
```

```python
# settings.py
if os.environ.get('USE_S3') == 'True':
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
```

#### Opção 3: Cloudinary (Mais Fácil)
```bash
pip install cloudinary django-cloudinary-storage
```

**Sem storage externo, os arquivos (vídeos e APKs) serão perdidos em redeploy!**

---

## 🧪 Testar Deploy

### 1. Testar Admin
```bash
curl https://seu-app.up.railway.app/admin/
# Deve retornar HTML da página de login
```

### 2. Testar API
```bash
curl https://seu-app.up.railway.app/api/swagger/
# Deve retornar página do Swagger
```

### 3. Testar Autenticação
```bash
curl -X POST https://seu-app.up.railway.app/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"marcos","password":"sua_senha"}'
# Deve retornar tokens JWT
```

### 4. Testar Download APK
```bash
curl -I https://seu-app.up.railway.app/app/download/
# Deve retornar 200 OK ou 302 Redirect
```

---

## 🔄 Atualizar Projeto (CI/CD Automático)

O Railway faz deploy automático a cada push:

```bash
# Fazer alterações
git add .
git commit -m "Nova feature XYZ"
git push origin main

# Railway detecta e faz redeploy automaticamente
# Acompanhe em: Railway → Deployments
```

---

## 🐛 Problemas Comuns

### "Application failed to respond"
**Solução**: Verificar logs no Railway → Deployments → View Logs

### Static files não carregam
**Solução**:
```bash
railway run python manage.py collectstatic --noinput
```

### Erro de banco de dados
**Solução**:
```bash
railway run python manage.py migrate
```

### CSRF error
**Solução**: Adicionar em Variables:
```env
CSRF_TRUSTED_ORIGINS=https://seu-app.up.railway.app
```

---

## 💡 Próximos Passos

1. ✅ Deploy concluído
2. 📝 Criar dados de teste (franqueados, clientes, municípios)
3. 🎥 Fazer upload de vídeos de teste
4. 📺 Criar playlists
5. 📱 Fazer upload do APK do app TV
6. 🧪 Testar API com app TV
7. 🔒 Configurar storage externo (S3/Cloudinary)
8. 📊 Configurar monitoramento (Sentry opcional)
9. 🌐 Adicionar domínio customizado (opcional)

---

## 📞 Recursos

- **Documentação Railway**: https://docs.railway.app
- **Documentação Django**: https://docs.djangoproject.com
- **Django REST Framework**: https://www.django-rest-framework.org
- **Swagger/OpenAPI**: https://swagger.io

---

## 📊 Custos Estimados

**Railway - Plano Hobby ($5/mês)**
- Servidor web
- PostgreSQL
- 512MB RAM
- 1GB disco (sem volumes)
- SSL automático
- Deploy contínuo

**+ AWS S3 (Recomendado)**
- ~$1-5/mês para storage de vídeos
- Depende do volume de uploads

**+ Cloudinary (Alternativa)**
- Plano Free: 25GB storage, 25GB bandwidth
- Mais fácil de configurar

**Total: $5-10/mês para começar**

---

**Bom deploy! 🚀**
