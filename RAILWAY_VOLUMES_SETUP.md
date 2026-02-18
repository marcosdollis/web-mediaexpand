# Configuração de Railway Volumes para Armazenamento de Mídia

## 🎯 Solução Simples e Direta

Ao invés de usar serviços externos como Cloudinary, vamos usar o **Railway Volumes** - o sistema de armazenamento persistente nativo do Railway.

**Vantagens:**
- ✅ Já incluído no Railway (sem custos extras até 200GB)
- ✅ Configuração extremamente simples
- ✅ Sem necessidade de contas/credenciais externas
- ✅ Arquivos persistem entre deploys
- ✅ Performance melhor (mesma rede do servidor)

---

## 📋 Passo a Passo

### 1. Criar um Volume no Railway

1. Acesse https://railway.app/
2. Entre no seu projeto **MediaExpand**
3. Clique no serviço (web-production...)
4. Vá na aba **"Variables"** ou **"Settings"**
5. Role até encontrar **"Volumes"**
6. Clique em **"New Volume"**

**Configure o Volume:**
```
Mount Path: /data
```

Isso criará um volume persistente montado em `/data` no container.

### 2. **IMPORTANTE: Configurar DEBUG=False**

⚠️ **Este é o passo mais importante!** ⚠️

No Railway, você **PRECISA** configurar a variável de ambiente `DEBUG=False`:

1. Na mesma aba **"Variables"**
2. Clique em **"New Variable"**
3. Adicione:
   - **Variable:** `DEBUG`
   - **Value:** `False`

**Por quê?**
- Com `DEBUG=True`: arquivos salvos em `/app/media` (temporário, perdidos no deploy)
- Com `DEBUG=False`: arquivos salvos em `/data/media` (persistente, mantidos após deploy)

### 3. Verificar a Configuração

O código já está configurado! Em `settings.py`:

```python
DEBUG = config('DEBUG', default=False, cast=bool)  # Agora default é False

if DEBUG:
    MEDIA_URL = 'media/'
    MEDIA_ROOT = BASE_DIR / 'media'  # Desenvolvimento local
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = '/data/media'  # Produção Railway ✓
```

### 4. Verificar se Está Funcionando

Após criar o volume e configurar `DEBUG=False`:

1. **Faça login como OWNER** na aplicação
2. **Acesse o Dashboard** e clique em **"Diagnóstico"**
3. **Verifique:**
   - ✅ DEBUG deve estar `False` (badge verde)
   - ✅ MEDIA_ROOT deve ser `/data/media` (badge "Volume")
   - ✅ O diretório `/data/media` deve existir e ser gravável

**OU via URL direta:**
```
https://seu-dominio.railway.app/system/diagnostics/
```

### 5. Limpar Vídeos Órfãos (se houver)

Se você fez uploads antes de configurar o volume, os vídeos foram salvos no container temporário e estão órfãos agora:

**Opção 1 - Interface Web:**
1. Faça login como OWNER
2. Vá em **"Vídeos"**
3. Use o filtro **"Arquivos" → "Sem arquivo"**
4. Exclua cada vídeo órfão manualmente

**Opção 2 - Comando:**
```bash
# Ver o que seria removido
railway run python manage.py cleanup_orphaned_files --dry-run

# Remover os vídeos órfãos
railway run python manage.py cleanup_orphaned_files
```

### 6. Re-upload dos Vídeos

Após limpar os órfãos, peça aos clientes para fazer upload dos vídeos novamente. Desta vez eles serão salvos em `/data/media` e **persistirão entre deploys**! ✅

---

## 🔍 Como Funciona

### Estrutura de Diretórios no Railway:

```
/app/                    # Seu código Django
/data/                   # Volume persistente (criado pelo Railway)
  └── media/            # Arquivos de mídia (vídeos, contratos, etc.)
      ├── videos/
      │   ├── cliente_1/
      │   ├── cliente_2/
      │   └── cliente_3/
      ├── contratos/
      ├── thumbnails/
      └── app_versions/
```

### Fluxo de Upload:

1. Cliente faz upload de vídeo
2. Django salva em `MEDIA_ROOT` (`/data/media`)
3. Arquivo é salvo no Volume persistente
4. Em novos deploys, arquivos permanecem
5. URLs dos arquivos: `https://seu-dominio.railway.app/media/videos/...`

---

## ✅ Testar se Está Funcionando

### Teste 1: Upload
1. Acesse sua aplicação no Railway
2. Faça login como cliente
3. Faça upload de um vídeo teste
4. Se aparecer na listagem, funcionou!

### Teste 2: Após Deploy
1. Faça um commit qualquer no código
2. Aguarde o redeploy
3. Acesse a listagem de vídeos
4. Se o vídeo ainda estiver lá, o volume funciona! ✅

### Teste 3: App Android
1. Teste autenticação
2. Verifique se as URLs dos vídeos começam com:
   ```
   https://web-production-XXXX.up.railway.app/media/...
   ```
3. Teste reprodução no app

---

## 📊 Limites e Custo

### Railway Volumes:
- **Gratuito:** Não há custo pelo volume em si (incluído no plano)
- **Storage:** 200GB incluídos por projeto
- **Custo adicional:** Só se ultrapassar 200GB (~$0.25/GB/mês)

Para 95% dos casos, 200GB é mais que suficiente.

**Exemplo de uso:**
- Vídeo médio: 10-50 MB
- Com 200GB: ~4000 vídeos de 50MB
- Para ultrapassar: precisaria de centenas de clientes

---

## 🔧 Gestão de Espaço

### Ver Uso Atual:

No Railway, você pode verificar o uso do volume na dashboard do projeto.

### Limpar Arquivos Órfãos:

Use o comando de gerenciamento:

```bash
# Ver registros sem arquivos
python manage.py cleanup_orphaned_files --dry-run

# Remover registros sem arquivos
python manage.py cleanup_orphaned_files
```

### Compressão de Vídeos (Futuro):

Se precisar economizar espaço, pode implementar:
- Compressão automática de vídeos no upload
- Limitação de tamanho/duração de vídeos
- Limpeza automática de vídeos antigos/não usados

---

## 🆚 Railway Volumes vs Cloudinary

| Aspecto | Railway Volumes | Cloudinary |
|---------|----------------|------------|
| Configuração | 2 minutos | 10+ minutos |
| Custo | Incluído (200GB) | Gratuito (25GB) |
| Credenciais | Não precisa | Precisa configurar |
| Performance | Excelente (mesma rede) | Bom (CDN) |
| CDN | Não | Sim |
| Transformações | Não | Sim (otimização) |
| Melhor para | Maioria dos casos | Milhares de usuários |

**Recomendação:** Use Railway Volumes. É mais simples e suficiente para 95% dos casos.

---

## 🚨 Troubleshooting

### Problema: Criei o volume mas os vídeos sumiram após deploy

**Causa Raiz:** A variável de ambiente `DEBUG` não foi configurada como `False` no Railway.

**O que aconteceu:**
1. Você criou o volume em `/data` ✓
2. Mas `DEBUG` estava em `True` (ou não configurado, usando default antigo)
3. Com `DEBUG=True`, o Django salva arquivos em `/app/media` (temporário)
4. Ao fazer deploy, o container foi recriado e `/app/media` foi perdido
5. Os registros no banco permaneceram, mas os arquivos físicos sumiram

**Solução passo a passo:**

1. **Configure DEBUG=False no Railway:**
   ```
   Railway → Variables → New Variable
   Variable: DEBUG
   Value: False
   ```

2. **Verifique via Diagnóstico:**
   - Faça login como OWNER
   - Dashboard → Diagnóstico
   - Confirme: DEBUG = False, MEDIA_ROOT = /data/media

3. **Limpe os vídeos órfãos:**
   - Via web: Vídeos → Filtro "Sem arquivo" → Excluir
   - Via CLI: `railway run python manage.py cleanup_orphaned_files`

4. **Re-upload dos vídeos:**
   - Peça aos clientes para fazer upload novamente
   - Desta vez, arquivos irão para `/data/media` ✓

5. **Teste:**
   - Faça upload de um vídeo teste
   - Faça um commit qualquer e force redeploy
   - Verifique se o vídeo ainda está acessível ✅

### Problema: Vídeos sumiram após deploy

**Causa:** Os vídeos foram salvos no sistema de arquivos temporário do container (em `/app/media`), não no volume persistente (`/data/media`). Quando o Railway fez redeploy, o container foi recriado e os arquivos temporários foram perdidos. Os registros no banco de dados permaneceram, mas os arquivos físicos sumiram.

**Solução:**
1. **Certifique-se que criou o volume no Railway:**
   ```
   Railway Dashboard → Seu serviço → Settings → Volumes → New Volume
   Mount Path: /data
   ```

2. **Verifique se `DEBUG=False` em produção:**
   - No Railway, a variável `DEBUG` deve estar como `False` ou não existir
   - Isso garante que `MEDIA_ROOT = '/data/media'` (não `/app/media`)

3. **Limpar registros órfãos (vídeos sem arquivo):**
   
   **Via Interface Web (recomendado):**
   - Faça login como OWNER
   - Vá em "Vídeos"
   - Use o filtro "Arquivos" → "Sem arquivo"
   - Vídeos órfãos terão um badge vermelho "Arquivo ausente"
   - Clique em "Excluir" em cada vídeo órfão
   
   **Via Comando (Railway CLI):**
   ```bash
   # Ver o que seria removido (sem executar)
   railway run python manage.py cleanup_orphaned_files --dry-run
   
   # Remover os registros órfãos
   railway run python manage.py cleanup_orphaned_files
   ```

4. **Re-upload dos vídeos:**
   - Após limpar os órfãos, os clientes precisarão fazer upload dos vídeos novamente
   - Desta vez, com o volume configurado, os arquivos serão salvos em `/data/media`
   - Os arquivos persistirão entre deploys ✅

### Problema: 404 nos arquivos após deploy

**Solução:** Certifique-se que criou o volume:
```
1. Railway Dashboard
2. Seu serviço
3. Settings → Volumes → New Volume
4. Mount Path: /data
```

### Problema: Erro de permissão ao salvar arquivo

**Solução:** O Railway já configura permissões automaticamente. Se der erro:
- Verifique se MEDIA_ROOT = '/data/media' (não '/data/' apenas)
- Redeploy após criar o volume

### Problema: Arquivos desaparecem após deploy

**Solução:** O volume não foi criado corretamente:
- Verifique se aparece em "Volumes" no Railway
- Mount Path deve ser exatamente `/data`
- Faça redeploy após criar o volume

---

## 🔐 Servir Arquivos de Mídia

### Desenvolvimento:

Django serve automaticamente (`DEBUG=True`):
```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Produção (Railway):

Django também serve os arquivos, mas você pode otimizar no futuro usando:
- **WhiteNoise** (já configurado para static, pode estender para media)
- **Nginx** (se migrar para outra infraestrutura)
- **CDN** (se crescer muito)

Por enquanto, deixe Django servir - funciona perfeitamente.

---

## 📦 Backup (Opcional)

Se quiser fazer backup dos arquivos do volume:

### Opção 1: Download Manual
- Acesse o Railway CLI
- Use `railway run` para rodar comandos
- Faça backup com `tar` ou `rsync`

### Opção 2: Backup Automático para S3
- Configure um cronjob no Railway
- Use `boto3` para enviar para AWS S3
- Executar diariamente/semanalmente

**Nota:** Para a maioria dos casos, não é necessário. Railway tem alta disponibilidade.

---

## ✅ Checklist de Implementação

- [x] Código configurado para usar `/data/media` em produção
- [ ] Volume criado no Railway com Mount Path `/data`
- [ ] **Variável `DEBUG=False` configurada no Railway** ← CRÍTICO!
- [ ] Diagnóstico verificado (MEDIA_ROOT = /data/media, DEBUG = False)
- [ ] Redeploy feito após criar volume e configurar DEBUG
- [ ] Teste de upload funcionando
- [ ] Arquivos persistem após novo deploy
- [ ] Vídeos órfãos removidos (se houver)
- [ ] App Android consegue reproduzir vídeos
- [ ] URLs dos vídeos são HTTPS

## 🛡️ Como Prevenir Perda de Arquivos

1. **Sempre crie o volume ANTES do primeiro deploy em produção**
2. **Verifique se `DEBUG=False` no Railway**
3. **Teste com um vídeo após o primeiro deploy:**
   - Faça upload de um vídeo teste
   - Force um redeploy (commit qualquer mudança)
   - Verifique se o vídeo ainda está acessível
4. **Monitore vídeos órfãos:**
   - Como OWNER, use o filtro "Arquivos → Sem arquivo" regularmente
   - Se vídeos órfãos aparecerem, investigue o motivo

## 🔍 Como Verificar se o Volume Está Funcionando

### Via Railway Dashboard:
1. Acesse seu projeto
2. Clique no serviço
3. Vá em "Settings" → "Volumes"
4. Deve aparecer um volume montado em `/data`

### Via Comando:
```bash
# Conectar ao container
railway run bash

# Verificar se /data existe
ls -la /data

# Verificar se /data/media existe
ls -la /data/media

# Ver espaço usado
du -sh /data/media
```

### Via Upload Teste:
1. Faça login como cliente
2. Faça upload de um vídeo pequeno
3. Acesse o banco de dados e veja o caminho do arquivo
4. Deve começar com `app_versions/` ou `videos/cliente_X/`
5. Em produção, estará fisicamente em `/data/media/...`

---

## 🎓 Próximos Passos

Depois que estiver funcionando:

1. **Monitorar uso de espaço:** Fique de olho no dashboard do Railway
2. **Limitar uploads:** Configure tamanho máximo de vídeos se necessário
3. **Comprimir vídeos:** Implemente compressão automática se precisar economizar espaço
4. **CDN (futuro):** Se tiver muitos acessos simultâneos, considere CloudFlare na frente

---

**Última atualização:** 16/02/2026

**Simplicidade > Complexidade**

Railway Volumes é a solução mais direta e eficiente para este projeto! 🚀
