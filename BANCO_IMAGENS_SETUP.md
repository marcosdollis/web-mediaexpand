# 🖼️ Configuração do Banco de Imagens (Pixabay + Iconify)

## ✅ O que já está implementado

- **Pixabay API**: Fotos, ilustrações e vetores gratuitos
- **Iconify API**: 100k+ ícones de 12+ coleções (sem necessidade de chave API)
- **Fallback automático**: Se não houver chave Pixabay, usa Lorem Picsum
- **Backend proxy**: Rotas `/corporativo/design/search-images/`, `/search-icons/`, `/search-stickers/`
- **UI completa**: 4 abas (Fotos, Ilustrações, Ícones, PNGs) com busca e categorias

## 🔑 Configuração da Chave Pixabay no Railway

### 1. Acesse o Railway Dashboard
```
https://railway.app/
```

### 2. Selecione seu projeto
- Clique no projeto `web-production-1d97f`

### 3. Vá para Variables (variáveis de ambiente)
- Clique na aba **Variables** no menu lateral

### 4. Adicione a variável
Clique em **+ New Variable** e adicione:

```
PIXABAY_API_KEY=54841440-7dfb3a0c6fca6ec2c20c4aae9
```

### 5. Deploy automático
O Railway vai reiniciar automaticamente o serviço após adicionar a variável.

## 🧪 Testar Localmente

### 1. Verificar se .env existe e está configurado
```bash
cat .env
# Deve conter:
# PIXABAY_API_KEY=54841440-7dfb3a0c6fca6ec2c20c4aae9
```

### 2. Ativar ambiente virtual
```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências (se necessário)
```bash
pip install -r requirements.txt
```

### 4. Aplicar migrações
```bash
python manage.py migrate
```

### 5. Iniciar servidor
```bash
python manage.py runserver
```

### 6. Testar banco de imagens
1. Acesse: `http://localhost:8000/corporativo/design/create/`
2. Faça login se necessário
3. No painel esquerdo, clique na aba **"Biblioteca de Mídia"**
4. Teste cada aba:
   - **📷 Fotos**: Busque "nature", "business", "technology"
   - **🎨 Ilustrações**: Busque "cartoon", "vector", "art"
   - **✨ Ícones**: Busque "home", "search", "user" (não precisa de API key)
   - **🖼️ PNGs**: Busque "logo", "emoji", "sticker"

### 7. Verificar logs no console
Se houver problemas, veja as mensagens de debug no terminal:
```
[DEBUG] PIXABAY_API_KEY configured: True/False
[DEBUG] No Pixabay API key found, using fallback
```

## 🐛 Troubleshooting

### "Erro: Unexpected token '<'"
**Causa**: Rota não encontrada ou erro de autenticação  
**Solução**: Verifique se está logado e se as rotas estão em `core/urls_web.py`

### "Erro ao buscar imagens"
**Causa**: Chave API inválida ou limite de requisições excedido  
**Solução**: 
- Verifique se a chave está configurada no Railway
- Se foi usada mais de 5000x no mês (limite gratuito), crie nova chave em https://pixabay.com/api/docs/

### "Cannot find module 'django'"
**Causa**: Ambiente virtual não está ativado  
**Solução**: Execute `.\venv\Scripts\Activate.ps1` (Windows) ou `source venv/bin/activate` (Linux/Mac)

### Fallback (Lorem Picsum) ativa sem querer
**Causa**: Variável de ambiente não foi lida corretamente  
**Solução**:
1. Verifique `.env` local ou variáveis do Railway
2. Reinicie o servidor Django
3. Verifique os logs: `[DEBUG] PIXABAY_API_KEY configured: True`

## 📊 Limites da API Gratuita

### Pixabay
- **5.000 requisições/hora** (limite generoso)
- **Sem necessidade de atribuição** para uso comercial
- **Imagens de alta qualidade** (até 5472x3648px)

### Iconify
- **Sem limite de requisições**
- **100% gratuito**
- **Sem necessidade de API key**

### Lorem Picsum (Fallback)
- **Sem limite**
- **Não pesquisável por palavra-chave** (imagens aleatórias)
- **Uso apenas como backup**

## 🔗 Links Úteis

- **Pixabay API Docs**: https://pixabay.com/api/docs/
- **Iconify Search**: https://icon-sets.iconify.design/
- **Lorem Picsum**: https://picsum.photos/
- **Railway Docs**: https://docs.railway.app/

## ✅ Checklist de Deploy

- [ ] Adicionar `PIXABAY_API_KEY` nas variáveis do Railway
- [ ] Fazer commit das alterações de código
- [ ] Fazer push para repositório Git
- [ ] Aguardar deploy automático do Railway
- [ ] Testar busca de imagens/ícones no editor
- [ ] Verificar preview do design com transições
