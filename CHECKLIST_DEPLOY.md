# ✅ Checklist Pré-Deploy - MediaExpand

## 📦 Arquivos de Configuração

- [x] `Procfile` - Configurado com gunicorn e migrate
- [x] `runtime.txt` - Python 3.11.7
- [x] `requirements.txt` - Todas as dependências
- [x] `railway.json` - Configuração Railway
- [x] `.gitignore` - Ignorando venv, db.sqlite3, media, etc.

## 🔧 Configurações Django

- [x] `settings.py` configurado para produção
- [x] `ALLOWED_HOSTS` aceita Railway
- [x] `DATABASES` usa DATABASE_URL (Railway PostgreSQL)
- [x] `STATIC_ROOT` e `MEDIA_ROOT` configurados
- [x] `CORS` habilitado
- [x] `JWT` autenticação configurada

## 📱 Funcionalidades Implementadas

### Sistema Web
- [x] Dashboard para OWNER, FRANCHISEE, CLIENT
- [x] Gestão de usuários e permissões
- [x] Municípios e franqueados
- [x] Clientes e segmentos
- [x] Upload e aprovação de vídeos
- [x] Criação de playlists
- [x] Dispositivos TV
- [x] Agendamentos de exibição
- [x] Sistema de APK (upload e download)

### API REST
- [x] Autenticação JWT
- [x] CRUD completo de recursos
- [x] Serializers e ViewSets
- [x] Permissões por role
- [x] Documentação Swagger/OpenAPI

### TV App API
- [x] Autenticação por UUID (`/api/tv/auth/`)
- [x] Download de playlist (`PlaylistTVSerializer`)
- [x] Log de exibições (`/api/tv/log-exibicao/`)
- [x] Verificação de horário (`/api/tv/check-schedule/`)

### Sistema de APK
- [x] Modelo `AppVersion` criado
- [x] Upload de APK (max 100MB)
- [x] Validação de versão e arquivo
- [x] Download público (`/app/download/`)
- [x] Controle de versões ativas
- [x] Contador de downloads
- [x] Interface de gerenciamento

## 📊 Banco de Dados

- [x] Migrations aplicadas localmente
- [x] Comando `create_owner` funcionando
- [x] 8 migrations criadas:
  - 0001_initial
  - 0002_cliente_contrato
  - 0003_alter_playlist_franqueado
  - 0004_agendamentoexibicao
  - 0005_segmento
  - 0006_cliente_segmento
  - 0007_dispositivotv_publico_estimado_mes
  - 0008_appversion

## 📚 Documentação

- [x] `README.md` - Descrição do projeto
- [x] `ESTRUTURA.md` - Estrutura de arquivos
- [x] `API_TV_GUIDE.md` - API para TVs
- [x] `API_TV_APP_GUIDE.md` - Guia completo para dev do app
- [x] `RAILWAY_DEPLOY.md` - Deploy detalhado Railway
- [x] `DEPLOY_QUICKSTART.md` - Deploy rápido (novo)
- [x] `SECURITY.md` - Segurança
- [x] `AGENDAMENTO_GUIDE.md` - Sistema de agendamentos
- [x] `EXEMPLOS_USO.md` - Exemplos de uso

## 🔐 Segurança

- [x] SECRET_KEY em variável de ambiente
- [x] DEBUG=False em produção
- [x] ALLOWED_HOSTS configurado
- [x] CSRF_TRUSTED_ORIGINS configurado
- [x] Senhas hasheadas (Django padrão)
- [x] JWT tokens com expiração
- [x] Permissões por role (OWNER, FRANCHISEE, CLIENT)

## 🌐 Deploy

- [x] Git inicializado
- [x] Repositório no GitHub (aguardando push)
- [x] Configuração Railway pronta
- [x] PostgreSQL será adicionado
- [x] Variáveis de ambiente documentadas

## ⚠️ Avisos Importantes

### 🚨 ARMAZENAMENTO DE ARQUIVOS
O Railway usa sistema de arquivos **efêmero**. Arquivos de mídia (vídeos e APKs) podem ser perdidos em redeploy.

**Soluções:**
1. **Railway Volumes** - Para testes/início
2. **AWS S3** - Recomendado para produção
3. **Cloudinary** - Mais fácil de configurar

### 📝 Tarefas Pós-Deploy

1. Executar `python manage.py create_owner` no Railway
2. Configurar storage externo (S3/Cloudinary)
3. Testar upload de vídeos
4. Fazer upload do primeiro APK
5. Testar API com Swagger
6. Criar dados de teste

## 🚀 Comandos para Commitar

```bash
# Verificar status
git status

# Adicionar todos os arquivos
git add .

# Commitar
git commit -m "Sistema MediaExpand completo - API + Web + Gerenciamento de APK"

# Push para GitHub (criar repo antes)
git push origin main
```

## 📦 Criar Repositório GitHub

```bash
# Se ainda não criou:
# 1. Ir para github.com
# 2. New Repository
# 3. Nome: web-mediaexpand ou mediaexpand-backend
# 4. Descrição: Sistema de Gerenciamento de Mídia Indoor
# 5. Público ou Privado
# 6. NÃO inicializar com README

# Conectar repositório local
git remote add origin https://github.com/seu-usuario/web-mediaexpand.git
git branch -M main
git push -u origin main
```

## 🎯 Deploy Railway

Após push para GitHub:

1. **Railway.app** → Login com GitHub
2. **New Project** → Deploy from GitHub repo
3. Selecionar **web-mediaexpand**
4. **New** → **Database** → **PostgreSQL**
5. **Variables** → Adicionar SECRET_KEY, DEBUG=False, etc.
6. **Shell** → `python manage.py create_owner`
7. **Pronto!** 🎉

---

**Última verificação:** {{ now|date:"d/m/Y H:i" }}

**Status:** ✅ PRONTO PARA DEPLOY

---

## 📞 Links Úteis Pós-Deploy

- Railway Dashboard: https://railway.app/dashboard
- Swagger Docs: https://seu-app.up.railway.app/api/swagger/
- Admin Django: https://seu-app.up.railway.app/admin/
- Download APK: https://seu-app.up.railway.app/app/download/
