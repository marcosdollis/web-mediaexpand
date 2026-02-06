# Deploy no Railway - Guia Passo a Passo

## 🚂 Preparação para Deploy

### 1. Configurar Git (se ainda não configurou)

```bash
git init
git add .
git commit -m "Initial commit - MediaExpand"
```

### 2. Criar repositório no GitHub

1. Acesse [github.com](https://github.com)
2. Clique em "New repository"
3. Nome: `mediaexpand-backend`
4. Descrição: "Sistema de Gerenciamento de Mídia Indoor"
5. Privado ou Público (sua escolha)
6. **NÃO** inicialize com README (já temos)
7. Clique em "Create repository"

### 3. Enviar código para GitHub

```bash
git remote add origin https://github.com/seu-usuario/mediaexpand-backend.git
git branch -M main
git push -u origin main
```

---

## 🚀 Deploy no Railway

### Passo 1: Criar Conta no Railway

1. Acesse [railway.app](https://railway.app)
2. Clique em "Login" ou "Start a New Project"
3. Faça login com GitHub
4. Autorize o Railway a acessar seus repositórios

### Passo 2: Criar Novo Projeto

1. No dashboard do Railway, clique em **"New Project"**
2. Selecione **"Deploy from GitHub repo"**
3. Procure e selecione `mediaexpand-backend`
4. O Railway detecta automaticamente que é um projeto Django

### Passo 3: Adicionar PostgreSQL

1. No projeto criado, clique em **"New"**
2. Selecione **"Database"**
3. Escolha **"Add PostgreSQL"**
4. O Railway cria automaticamente e configura `DATABASE_URL`

### Passo 4: Configurar Variáveis de Ambiente

1. Clique no serviço do seu app (não no PostgreSQL)
2. Vá para aba **"Variables"**
3. Clique em **"Raw Editor"**
4. Cole e ajuste:

```env
DEBUG=False
SECRET_KEY=cole-aqui-uma-chave-segura-gerada
ALLOWED_HOSTS=*.railway.app
```

**Para gerar SECRET_KEY segura:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Passo 5: Configurar Domínio (Opcional)

1. Na aba **"Settings"** do serviço
2. Role até **"Domains"**
3. Clique em **"Generate Domain"**
4. Railway gera um domínio como: `mediaexpand-production.up.railway.app`
5. **OU** adicione seu domínio customizado: `api.mediaexpand.com.br`

**Se usar domínio customizado:**
- Adicione registro DNS CNAME: `api.mediaexpand.com.br` → `seu-projeto.up.railway.app`
- Atualize `ALLOWED_HOSTS`: `ALLOWED_HOSTS=*.railway.app,api.mediaexpand.com.br,mediaexpand.com.br`

### Passo 6: Deploy Automático

O Railway faz deploy automaticamente:
1. Detecta `requirements.txt`
2. Instala dependências
3. Executa `Procfile`:
   - `release: python manage.py migrate --noinput`
   - `web: gunicorn mediaexpand.wsgi --log-file -`
4. Inicia o servidor

### Passo 7: Executar Comando Create Owner

1. No dashboard do Railway, clique no seu serviço
2. Vá para a aba **"Deployments"**
3. Clique nos "..." do deploy ativo
4. Selecione **"View Logs"**
5. Abra uma **"Shell"** (ícone de terminal no canto)
6. Execute:

```bash
python manage.py create_owner
```

7. Preencha os dados do usuário OWNER

---

## 🔧 Comandos Úteis Railway

### Via Railway CLI (opcional)

**Instalar CLI:**
```bash
npm install -g @railway/cli
# ou
brew install railway
```

**Login:**
```bash
railway login
```

**Vincular projeto:**
```bash
railway link
```

**Executar comandos:**
```bash
railway run python manage.py migrate
railway run python manage.py create_owner
railway run python manage.py createsuperuser
railway run python manage.py shell
```

**Ver logs:**
```bash
railway logs
```

---

## 📊 Verificar Deploy

### 1. Verificar Logs

No Railway Dashboard:
- Clique no serviço
- Aba "Deployments"
- Veja logs de build e runtime

**Busque por:**
- ✅ "Starting gunicorn"
- ✅ "Booting worker"
- ❌ Erros ou exceções

### 2. Testar API

```bash
# Substitua pela sua URL do Railway
curl https://seu-projeto.up.railway.app/api/

# Ou no navegador
https://seu-projeto.up.railway.app/admin/
```

### 3. Testar Autenticação

```bash
curl -X POST https://seu-projeto.up.railway.app/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "seu_owner_username",
    "password": "sua_senha"
  }'
```

**Deve retornar:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## 🐛 Troubleshooting no Railway

### Erro: "Application failed to respond"

**Solução:**
1. Verifique logs de erro
2. Confirme que `gunicorn` está instalado
3. Verifique `Procfile` está correto
4. Confirme `mediaexpand.wsgi` existe

### Erro: "Static files not loading"

**Solução:**
```bash
# No Railway shell
railway run python manage.py collectstatic --noinput
```

### Erro: "Database connection failed"

**Solução:**
1. Verifique PostgreSQL está rodando
2. Confirme `DATABASE_URL` existe nas variáveis
3. Rode migrations:
```bash
railway run python manage.py migrate
```

### Erro: "ALLOWED_HOSTS invalid"

**Solução:**
- Adicione o domínio Railway às variáveis:
```env
ALLOWED_HOSTS=*.railway.app,seu-dominio.up.railway.app
```

---

## 📈 Monitoramento no Railway

### Métricas Disponíveis

1. **CPU Usage**: Uso de processador
2. **Memory**: Uso de RAM
3. **Network**: Tráfego de entrada/saída
4. **Disk**: Uso de disco

### Alertas

Configure alertas para:
- Uso de CPU > 80%
- Uso de memória > 90%
- Erros HTTP 5xx

---

## 💰 Custos do Railway

### Plano Gratuito (Starter)
- $5 de crédito mensal
- Inclui:
  - 512MB RAM
  - 1GB disco
  - PostgreSQL incluído
- **Suficiente para projetos pequenos/testes**

### Plano Hobby ($5/mês)
- $5 de crédito mensal
- Melhor para produção inicial

### Plano Pro ($20/mês)
- $20 de crédito mensal
- Para produção com mais recursos

**Dica**: Comece com Hobby e escale conforme necessário.

---

## 🔄 Deploy Contínuo (CI/CD)

O Railway já faz deploy automático a cada push no GitHub:

```bash
# Faça alterações no código
git add .
git commit -m "Adiciona nova feature"
git push origin main

# Railway detecta e faz deploy automaticamente
```

---

## 🔐 Segurança Pós-Deploy

### Checklist:

- [ ] `DEBUG=False` confirmado
- [ ] `SECRET_KEY` forte e única
- [ ] `ALLOWED_HOSTS` correto
- [ ] HTTPS funcionando (Railway fornece automaticamente)
- [ ] Usuário OWNER criado e senha forte
- [ ] Backup do banco configurado
- [ ] Monitoramento configurado (Sentry, Railway Metrics)

---

## 📱 Configurar Domínio Customizado

### No seu provedor de DNS (ex: GoDaddy, Registro.br):

1. Adicione registro **CNAME**:
   - Nome: `api` (ou `@` para domínio raiz)
   - Valor: `seu-projeto.up.railway.app`
   - TTL: 3600

2. No Railway:
   - Settings → Domains
   - Add Domain: `api.mediaexpand.com.br`
   - Railway configura SSL automaticamente

3. Aguarde propagação DNS (até 24h, geralmente minutos)

4. Teste:
```bash
curl https://api.mediaexpand.com.br/api/
```

---

## 📦 Backup do Banco de Dados

### Backup Manual:

```bash
railway run pg_dump > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Backup Automático (Cron Job):

**Linux/Mac `backup.sh`:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
railway run pg_dump > backups/backup_$DATE.sql
# Upload para S3/Google Drive/Dropbox
```

**Agendar com cron:**
```bash
crontab -e

# Backup diário às 3h da manhã
0 3 * * * /caminho/para/backup.sh
```

---

## 🚀 Próximos Passos Após Deploy

1. ✅ Deploy no Railway concluído
2. ➡️ Criar dados de teste (franqueados, clientes, vídeos)
3. ➡️ Testar todos os endpoints da API
4. ➡️ Desenvolver frontend/app de TV
5. ➡️ Configurar monitoramento (Sentry)
6. ➡️ Configurar backups automáticos
7. ➡️ Adicionar documentação Swagger
8. ➡️ Implementar testes automatizados

---

## 📞 Suporte

**Railway:**
- Documentação: https://docs.railway.app
- Discord: https://discord.gg/railway
- Twitter: @Railway

**Django:**
- Documentação: https://docs.djangoproject.com
- Fórum: https://forum.djangoproject.com

---

**Boa sorte com o deploy! 🎉**

*Em caso de dúvidas, consulte a documentação ou entre em contato.*
