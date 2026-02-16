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

### 2. Verificar a Configuração

O código já está configurado! Em `settings.py`:

```python
if DEBUG:
    MEDIA_URL = 'media/'
    MEDIA_ROOT = BASE_DIR / 'media'  # Desenvolvimento local
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = '/data/media'  # Produção Railway
```

### 3. Redeploy

Após criar o volume:
1. Railway detectará a mudança
2. Fará redeploy automático
3. Os uploads serão salvos em `/data/media`

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

- [ ] Volume criado no Railway (`/data`)
- [ ] Código já está configurado (não precisa mudar nada!)
- [ ] Redeploy feito automaticamente
- [ ] Teste de upload funcionando
- [ ] Arquivos persistem após novo deploy
- [ ] App Android consegue reproduzir vídeos
- [ ] URLs dos vídeos são HTTPS

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
