# Configuração do Cloudinary para Armazenamento de Mídia

## 🚨 Problema

O Railway (e outras plataformas de deploy) usa um sistema de arquivos efêmero. Isso significa que:
- Arquivos enviados pelos usuários (vídeos, contratos, etc.) são perdidos quando há um novo deploy
- Os arquivos não persistem entre reinicializações
- Não é possível compartilhar arquivos entre múltiplas instâncias

## ✅ Solução: Cloudinary

O Cloudinary é um serviço de armazenamento de mídia na nuvem com:
- Plano gratuito generoso (25 GB de armazenamento, 25 GB de banda mensal)
- CDN global para entrega rápida de conteúdo
- Otimização automática de imagens e vídeos
- API completa para upload e gerenciamento

---

## 📋 Passo a Passo

### 1. Criar Conta no Cloudinary

1. Acesse https://cloudinary.com/
2. Clique em "Sign Up for Free"
3. Preencha o formulário ou use login social (GitHub, Google, etc.)
4. Confirme seu email

### 2. Obter Credenciais

1. Após fazer login, você verá o **Dashboard**
2. Copie as seguintes informações:
   - **Cloud name** (exemplo: `dkj4x7abc`)
   - **API Key** (exemplo: `123456789012345`)
   - **API Secret** (clique em "Reveal" para ver, exemplo: `abcdefghijklmnopqrstu`)

### 3. Configurar Variáveis de Ambiente no Railway

1. Acesse https://railway.app/
2. Entre no seu projeto MediaExpand
3. Clique na aba **Variables**
4. Adicione as seguintes variáveis:

```
CLOUDINARY_CLOUD_NAME=seu_cloud_name_aqui
CLOUDINARY_API_KEY=sua_api_key_aqui
CLOUDINARY_API_SECRET=seu_api_secret_aqui
```

**IMPORTANTE:** Cole exatamente os valores que você copiou do Cloudinary, sem aspas ou espaços extras.

### 4. Redeploy no Railway

Após adicionar as variáveis, o Railway vai automaticamente fazer um novo deploy.

Se não acontecer automaticamente:
1. Clique na aba **Deployments**
2. Clique nos 3 pontinhos do último deploy
3. Clique em "Redeploy"

---

## 🔍 Como Verificar se Está Funcionando

### Teste 1: Upload de Vídeo
1. Acesse sua aplicação no Railway
2. Faça login como cliente
3. Tente fazer upload de um novo vídeo
4. Se o upload funcionar, está configurado!

### Teste 2: Verificar URL do Vídeo
1. No Cloudinary Dashboard, vá em **Media Library**
2. Você deve ver os arquivos enviados
3. As URLs dos vídeos devem começar com:
   ```
   https://res.cloudinary.com/seu_cloud_name/...
   ```

### Teste 3: App Android
1. O app Android deve conseguir fazer download e reproduzir os vídeos
2. As URLs retornadas pela API serão URLs do Cloudinary (HTTPS)

---

## 📦 O Que Foi Alterado no Código

### 1. `requirements.txt`
Adicionadas as bibliotecas:
- `cloudinary==1.41.0`
- `django-cloudinary-storage==0.3.0`

### 2. `mediaexpand/settings.py`
- Adicionado `cloudinary_storage` e `cloudinary` ao `INSTALLED_APPS`
- Configuradas credenciais via variáveis de ambiente
- Em **produção** (DEBUG=False): usa Cloudinary
- Em **desenvolvimento** (DEBUG=True): usa sistema de arquivos local

### 3. Upload de Arquivos
Agora quando um usuário faz upload:
- **Desenvolvimento local:** Salvo em `media/` (como antes)
- **Produção (Railway):** Enviado automaticamente para o Cloudinary

---

## 🆓 Limites do Plano Gratuito

| Recurso | Limite Gratuito |
|---------|-----------------|
| Armazenamento | 25 GB |
| Banda (downloads) | 25 GB/mês |
| Transformações | 25 créditos/mês |
| Vídeos | Até 1 GB/vídeo, 10 min/vídeo |

Para a maioria dos casos, isso é suficiente. Se precisar de mais:
- Cloudinary tem planos pagos acessíveis
- Alternativa: usar AWS S3 (também tem plano gratuito)

---

## 🔧 Migração de Arquivos Existentes

Se você já tem vídeos/arquivos no Railway (que serão perdidos), você precisa:

### Opção 1: Re-upload Manual (Recomendado)
1. Peça aos clientes para fazer re-upload dos vídeos
2. Os novos uploads irão automaticamente para o Cloudinary

### Opção 2: Backup e Upload Programático
Se você tiver muitos arquivos, pode criar um script para:
1. Fazer backup dos arquivos atuais
2. Fazer upload em lote para o Cloudinary
3. Atualizar os caminhos no banco de dados

**Nota:** Como o sistema de arquivos do Railway é efêmero, você precisaria fazer isso antes de um novo deploy, mas isso não é prático. É melhor re-upload manual.

### Opção 3: Limpar Registros Órfãos
Use o comando de gerenciamento criado:

```bash
python manage.py cleanup_orphaned_files --dry-run  # Ver o que será removido
python manage.py cleanup_orphaned_files            # Remover registros sem arquivos
```

---

## ⚙️ Alternativas ao Cloudinary

Se preferir outras soluções:

### AWS S3
- Mais controle e opções
- Plano gratuito: 5GB por 12 meses
- Requer configuração mais complexa
- Biblioteca: `django-storages` + `boto3`

### Railway Volumes
- Persistência de arquivos no Railway
- Pago: ~$0.25/GB/mês
- Arquivos ficam no Railway (não usa CDN)
- Configuração: https://docs.railway.app/reference/volumes

### Backblaze B2
- Muito barato (0.005/GB/mês de storage)
- 10GB gratuitos
- Compatível com S3

---

## 📞 Suporte

Se tiver problemas:

1. **Erro de credenciais inválidas:**
   - Verifique se copiou corretamente as credenciais do Cloudinary
   - Verifique se não há espaços extras nas variáveis de ambiente

2. **Upload não funciona:**
   - Verifique os logs no Railway
   - Teste localmente primeiro (deve salvar em `media/`)

3. **Vídeos antigos dão 404:**
   - Normal, use o comando `cleanup_orphaned_files` para limpar
   - Ou peça re-upload dos vídeos

---

## ✅ Checklist Final

- [ ] Conta criada no Cloudinary
- [ ] Credenciais copiadas (Cloud Name, API Key, API Secret)
- [ ] Variáveis adicionadas no Railway
- [ ] Código atualizado (via git push)
- [ ] Deploy realizado com sucesso
- [ ] Teste de upload funcionando
- [ ] URLs dos vídeos começam com `res.cloudinary.com`
- [ ] App Android consegue reproduzir vídeos

---

**Última atualização:** 16/02/2026
