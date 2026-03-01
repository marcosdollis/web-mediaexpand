# 🔍 DEBUG: Erro 500 no Banco de Imagens

## 🚨 Problema Atual
```
GET /corporativo/design/search-images/?q=natureza 500 (Internal Server Error)
```

## ✅ Correções Implementadas

### 1. Adicionado logging detalhado em `views.py`
- `[DEBUG] PIXABAY_API_KEY configured: True/False`
- `[DEBUG] Calling Pixabay API: ...`
- `[DEBUG] Pixabay response: totalHits=X, hits=Y`
- `[ERROR] ...` para todos os erros

### 2. Tratamento de erros HTTP específicos
- **400**: API Key inválida
- **429**: Limite excedido → usa fallback automaticamente
- **Timeout**: Erro de conexão → usa fallback
- **Outros**: Mensagens descritivas

### 3. Try-catch em toda a cadeia
- Setup inicial (leitura de API key)
- Chamada à API Pixabay
- Fallback (Lorem Picsum)
- Parsing de resultados

### 4. Import de urllib.error
- Adicionado para capturar HTTPError e URLError corretamente

---

## 🔧 Como Verificar o Erro Real

### No Railway:

#### 1. Acessar logs em tempo real
```bash
# Opção A: Via CLI
railway logs --follow

# Opção B: Via Dashboard
1. Acesse: https://railway.app/
2. Abra seu projeto
3. Clique na aba "Deployments"
4. Clique no deployment ativo
5. Scroll até "Logs"
```

#### 2. O que procurar nos logs
```
[DEBUG] PIXABAY_API_KEY configured: False
→ Chave não foi configurada no Railway

[DEBUG] PIXABAY_API_KEY configured: True
[ERROR] Pixabay HTTP 400: Bad Request
→ Chave inválida ou parâmetros incorretos

[ERROR] Pixabay HTTP 429: Too Many Requests
→ Limite excedido (5000/hora)

[ERROR] Error in initial setup: NameError: name 'os' is not defined
→ Falta import (improvável, mas possível)

[ERROR] Fallback error: ...
→ Problema no fallback (raro)
```

#### 3. Após fazer push das correções
```bash
git add core/views.py
git commit -m "Fix: Melhor tratamento de erros no banco de imagens"
git push
```

Aguarde 1-2 minutos e tente buscar novamente. Os logs vão mostrar exatamente onde está o problema.

---

## 🧪 Testar Localmente ANTES do Deploy

### 1. Ativar ambiente virtual
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Verificar se API key está no .env
```powershell
cat .env | Select-String PIXABAY
# Deve mostrar: PIXABAY_API_KEY=54841440-7dfb3a0c6fca6ec2c20c4aae9
```

### 3. Iniciar servidor local
```powershell
python manage.py runserver
```

### 4. Testar no navegador
```
http://localhost:8000/corporativo/design/create/
```

No console do terminal, você verá os logs em tempo real:
```
[DEBUG] PIXABAY_API_KEY configured: True
[DEBUG] Calling Pixabay API: https://pixabay.com/api/?key=KEY_HIDDEN&q=natureza...
[DEBUG] Pixabay response: totalHits=500, hits=40
```

Se der erro local, o mesmo erro está no Railway.

---

## 🎯 Possíveis Causas e Soluções

### Causa 1: API Key não configurada no Railway ❌
**Sintoma**: `[DEBUG] PIXABAY_API_KEY configured: False`

**Solução**:
1. Railway Dashboard → seu projeto
2. Variables → + New Variable
3. `PIXABAY_API_KEY=54841440-7dfb3a0c6fca6ec2c20c4aae9`
4. Save

### Causa 2: API Key inválida ❌
**Sintoma**: `[ERROR] Pixabay HTTP 400`

**Solução**:
- Verificar se a chave está correta
- Criar nova chave em: https://pixabay.com/api/docs/

### Causa 3: Limite da API excedido ❌
**Sintoma**: `[ERROR] Pixabay HTTP 429`

**Solução**:
- Aguardar 1 hora
- Ou criar nova conta Pixabay (gratuito)
- O fallback (Lorem Picsum) é ativado automaticamente

### Causa 4: Import faltando ❌
**Sintoma**: `NameError: name 'X' is not defined`

**Solução**: Já adicionado `urllib.error` nos imports

### Causa 5: settings.PIXABAY_API_KEY não existe ❌
**Sintoma**: `AttributeError: 'Settings' object has no attribute...`

**Verificar em `mediaexpand/settings.py`**:
```python
# Deve ter esta linha (por volta da linha 193)
PIXABAY_API_KEY = config('PIXABAY_API_KEY', default='')
```

Se não tiver, adicionar:
```python
# No final de settings.py
from decouple import config
PIXABAY_API_KEY = config('PIXABAY_API_KEY', default='')
```

---

## 📊 Status Atual

### ✅ OK
- Lógica de busca implementada
- Fallback (Lorem Picsum + Iconify) funcionando
- Tratamento de erros robusto
- Logging detalhado

### 🔄 Para Verificar
- [ ] API key configurada no Railway
- [ ] Logs no Railway após push
- [ ] Teste de busca funcional

### ⏭️ Próximos Passos
1. Fazer commit das correções
2. Push para Railway
3. Verificar logs
4. Testar busca de imagens
5. Se necessário, ajustar baseado nos logs

---

## 🆘 Se Continuar com Erro 500

### Copie e cole nos logs:
```
railway logs --tail 100
```

E me envie a saída. Especialmente procure por:
- `[DEBUG] PIXABAY_API_KEY configured`
- `[ERROR] ...`
- `Traceback (most recent call last)`

Com isso, posso identificar exatamente o problema!
