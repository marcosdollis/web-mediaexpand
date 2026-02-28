# Teste: Múltiplas Playlists 24/7

## 🎯 Objetivo
Validar que dispositivos com 2+ playlists sem horário (24/7) recebem todos os vídeos mesclados.

## 📋 Pré-requisitos

1. **Criar 2 Playlists Ativas** no admin:
   - Playlist A: com 2-3 vídeos
   - Playlist B: com 2-3 vídeos (vídeos DIFERENTES)

2. **Criar/Vincular Playlists ao Dispositivo**:
   - Ir em "Playlists Vinculadas" (ou "Agendamentos")
   - Adicionar: Playlist A
     - hora_inicio: **vazio** (deixar em branco)
     - hora_fim: **vazio** (deixar em branco)
     - dias_semana: todos ou vazio
     - ativo: ✓ marcado
     - prioridade: 10
   
   - Adicionar: Playlist B
     - hora_inicio: **vazio**
     - hora_fim: **vazio**
     - dias_semana: todos ou vazio
     - ativo: ✓ marcado
     - prioridade: 10

## 🧪 Teste 1: Validar Resposta da API

### Endpoint
```
POST https://seu-dominio.com/api/tv/auth/
```

### Request Body
```json
{
  "identificador_unico": "SEU-UUID-DO-DISPOSITIVO",
  "versao_app": "1.0.0"
}
```

### Resposta Esperada
```json
{
  "dispositivo_id": 1,
  "dispositivo_nome": "Nome do Dispositivo",
  "municipio": "Cidade/UF",
  "playlist": {
    "id": 0,  // ← 0 = múltiplas mescladas
    "nome": "Playlist A + Playlist B",  // ← Ambos nomes
    "duracao_total_segundos": 300,
    "playlists_mescladas": [1, 2],  // ← IDs das playlists
    "videos": [
      // Vídeos da Playlist A
      { "id": 10, "titulo": "Video A1", ... },
      { "id": 11, "titulo": "Video A2", ... },
      // Vídeos da Playlist B
      { "id": 20, "titulo": "Video B1", ... },
      { "id": 21, "titulo": "Video B2", ... }
    ]
  }
}
```

### ✅ Validações
- [ ] `playlist.id` = 0 (indica mesclagem)
- [ ] `playlist.nome` contém " + " (ambos nomes)
- [ ] `playlist.playlists_mescladas` é array com 2 IDs
- [ ] `playlist.videos` tem vídeos das 2 playlists
- [ ] Total de vídeos = (vídeos A) + (vídeos B)

## 🧪 Teste 2: Validar no App Android

### Passos
1. **Reiniciar o app** na TV
2. **Observar reprodução**: deve tocar todos os vídeos em sequência
3. **Contar vídeos**: deve ser soma das 2 playlists

### ✅ Validações
- [ ] App baixou todos os vídeos
- [ ] Reprodução toca: A1 → A2 → B1 → B2 → volta para A1
- [ ] Logs mostram total correto de vídeos
- [ ] Não há erro de "playlist não encontrada"

## 🧪 Teste 3: Cenário com Horários Específicos

### Setup
- Manter Playlist A como 24/7
- Mudar Playlist B para ter horário:
  - hora_inicio: 08:00
  - hora_fim: 18:00

### Comportamento Esperado

**Durante 08:00 - 18:00:**
- API retorna: Playlist B (só ela, horário tem prioridade)

**Fora de 08:00 - 18:00:**
- API retorna: Playlist A (só ela, única 24/7)

### ✅ Validações
- [ ] Às 10:00 → API retorna só Playlist B
- [ ] Às 22:00 → API retorna só Playlist A
- [ ] Nunca retorna as duas mescladas (horário específico tem prioridade)

## 🧪 Teste 4: Prioridades Diferentes

### Setup
- Ambas playlists 24/7 (sem horário)
- Playlist A: prioridade = 20
- Playlist B: prioridade = 10

### Comportamento Esperado
- API retorna ambas mescladas
- **Ordem:** Playlist A primeiro, depois Playlist B
- Videos: A1 → A2 → B1 → B2

### ✅ Validações
- [ ] Vídeos de maior prioridade aparecem primeiro
- [ ] `playlists_mescladas`: [ID_A, ID_B] (ordem por prioridade)

## 🐛 Troubleshooting

### Problema: API ainda retorna só uma playlist

**Verificar:**
1. Ambas playlists têm `ativa = True`?
2. Ambos agendamentos têm `ativo = True`?
3. `hora_inicio` e `hora_fim` estão NULL (vazios)?
4. Backend foi reiniciado após mudança no código?

**Comando para reiniciar (Railway):**
```bash
# Fazer commit e push para força rebuild
git add .
git commit -m "fix: api múltiplas playlists"
git push
```

### Problema: App baixa mas não toca todos

**Verificar:**
1. Logs do app: quantos vídeos foram processados?
2. Algum vídeo com URL inválida ou erro 404?
3. Format/codec do vídeo é suportado?

### Problema: Vídeos aparecem duplicados

**Isso é normal se:**
- Você adicionou o mesmo vídeo nas 2 playlists
- O vídeo aparecerá 2 vezes na sequência

**Solução:**
- Remover vídeo duplicado de uma das playlists

## 📊 Comandos Úteis

### Testar API via cURL
```bash
curl -X POST https://seu-dominio.com/api/tv/auth/ \
  -H "Content-Type: application/json" \
  -d '{"identificador_unico":"SEU-UUID"}'
```

### Verificar agendamentos de um dispositivo
```bash
curl https://seu-dominio.com/api/tv/check-schedule/SEU-UUID/
```

### Ver logs do Django (local)
```bash
python manage.py runserver
# Acesse o endpoint e veja logs no terminal
```

### Ver logs Railway (produção)
```bash
railway logs
# ou no dashboard em: railway.app/project/[projeto]/logs
```

## ✅ Checklist Final

- [ ] Teste 1 ✅ API retorna `playlists_mescladas`
- [ ] Teste 2 ✅ App toca todos os vídeos em sequência
- [ ] Teste 3 ✅ Horários específicos funcionam corretamente
- [ ] Teste 4 ✅ Prioridades são respeitadas
- [ ] Documentação atualizada
- [ ] Cliente notificado das mudanças

---

**Data do Teste:** _______________  
**Testado por:** _______________  
**Resultado:** ⬜ Passou | ⬜ Falhou  
**Observações:** _______________________________________________
