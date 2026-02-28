# Correção: Múltiplas Playlists com Mesclagem Inteligente

**Data:** 28/02/2026  
**Status:** ✅ RESOLVIDO NO BACKEND (v2)  
**Impacto:** Playlists 24/7 + horários específicos agora funcionam corretamente

---

## 🐛 Problema Reportado (v2)

Cliente reportou após primeira correção:
> "Fiz um agendamento de 12:30-13:30 e só tocou essa playlist naquele horário, mas tem que incluir as que estão como 24h também. Se tem playlist com horário específico, ela só vai pro merge no horário cadastrado, as outras 24h ficam no merge sempre."

### Comportamento v1 (INCORRETO)
- Playlist A: 24/7
- Playlist B: 24/7  
- Playlist C: 12:30-13:30

**Durante 12:30-13:30:** API retornava SOMENTE C ❌  
**Fora do horário:** API retornava A + B ✓

### Comportamento v2 (CORRETO)
**Durante 12:30-13:30:** API retorna C + A + B ✅  
**Fora do horário:** API retorna A + B ✓

---

## ✅ Solução Implementada (v2)

### Mudança na Lógica

**Arquivo:** [`core/models.py`](core/models.py) - Método `get_playlists_ativas_por_horario()`

**Lógica Anterior (v1 - incorreta):**
```python
if agendamentos_horario:
    return [ag.playlist for ag in agendamentos_horario]  # Retorna SOMENTE horário
if agendamentos_fulltime:
    return [ag.playlist for ag in agendamentos_fulltime]  # Retorna SOMENTE 24/7
```

**Lógica Nova (v2 - correta):**
```python
playlists_ativas = []

# 1. Adiciona playlists de horário específico (se dentro do horário)
if agendamentos_horario:
    playlists_ativas.extend([ag.playlist for ag in agendamentos_horario])

# 2. SEMPRE adiciona playlists 24/7 (base contínua)
if agendamentos_fulltime:
    playlists_ativas.extend([ag.playlist for ag in agendamentos_fulltime])

return playlists_ativas
```

---

## 📊 Impacto (Atualizado)

### Cenários Suportados

#### Cenário 1: Apenas Playlists 24/7 ✅
```
Playlist A: 24/7
Playlist B: 24/7

Resultado: SEMPRE toca A + B mescladas
```

#### Cenário 2: Playlists 24/7 + Horário Específico ✅ (CORRIGIDO v2)
```
Playlist A: 24/7
Playlist B: 24/7
Playlist C: 12:30-13:30

Durante 12:30-13:30: toca C + A + B (horário + base)
Fora do horário: toca A + B (apenas base)
```

#### Cenário 3: Múltiplos Horários Específicos ✅
```
Playlist A: 24/7 (base)
Playlist B: 08:00-12:00
Playlist C: 12:00-18:00
Playlist D: 18:00-22:00

08:00-12:00: B + A
12:00-18:00: C + A
18:00-22:00: D + A
Outros horários: apenas A
```

#### Cenário 4: Horários Sobrepostos ✅
```
Playlist A: 24/7
Playlist B: 12:00-14:00
Playlist C: 13:00-15:00

12:00-13:00: B + A
13:00-14:00: B + C + A (ambos horários + base)
14:00-15:00: C + A
Outros: apenas A
```

---

## 📋 Regras de Mesclagem (Final)

1. **Playlists 24/7:** Base contínua, SEMPRE no merge
2. **Playlists com horário:** Adicionadas quando dentro do horário
3. **Ordem no merge:** Horário específico (por prioridade) → 24/7 (por prioridade)
4. **Sobreposição:** Múltiplos horários ativos simultaneamente são todos incluídos

---

## 🧪 Testes Realizados

- [x] `python manage.py check` → 0 issues
- [x] Syntax validation → OK
- [x] Método `get_playlists_ativas_por_horario()` implementado
- [x] API `/tv/auth/` retornando múltiplas playlists mescladas
- [x] API `/tv/check-schedule/` retornando info de múltiplas
- [ ] Teste manual com dispositivo real (pendente)

---

## 📋 Próximos Passos

### Para o Cliente Testar

1. **Reiniciar o app Android** na TV (forçar nova sincronização)
2. **Verificar que ambas playlists estão ativas** no admin web
3. **Confirmar que agendamentos NÃO têm horário** (hora_inicio/hora_fim vazios)
4. **Observar reprodução:** deve tocar TODOS os vídeos em sequência

### Validação da API

Testar endpoint manualmente:
```bash
POST https://web-production-1d97f.up.railway.app/api/tv/auth/
Body: {"identificador_unico": "UUID-DO-DISPOSITIVO"}

Verificar resposta contém:
- playlist.playlists_mescladas: [ID1, ID2]
- playlist.videos: array com vídeos de ambas
```

### Se Não Funcionar

Consultar documento de troubleshooting: [`TESTE_MULTIPLAS_PLAYLISTS.md`](TESTE_MULTIPLAS_PLAYLISTS.md)

---

## 📁 Arquivos Modificados

| Arquivo | Mudança | Linhas |
|---------|---------|--------|
| [`core/models.py`](core/models.py) | Novo método `get_playlists_ativas_por_horario()` | ~461-514 |
| [`core/views.py`](core/views.py) | API mesclando múltiplas playlists | ~361-404 |
| [`core/views.py`](core/views.py) | Endpoint check-schedule atualizado | ~505-515 |

## 📚 Documentação Criada

| Arquivo | Propósito |
|---------|-----------|
| [`ANDROID_MULTIPLAS_PLAYLISTS_FIX.txt`](ANDROID_MULTIPLAS_PLAYLISTS_FIX.txt) | Guia completo da mudança |
| [`TESTE_MULTIPLAS_PLAYLISTS.md`](TESTE_MULTIPLAS_PLAYLISTS.md) | Roteiro de testes |
| `CORRECAO_MULTIPLAS_PLAYLISTS.md` | Este resumo executivo |

---

## 🎯 Conclusão

✅ **Problema resolvido no backend**  
✅ **API agora retorna múltiplas playlists mescladas automaticamente**  
✅ **App Android não precisa de mudanças**  
✅ **Backward compatible com configurações existentes**  

O cliente pode testar imediatamente reiniciando o aplicativo Android.
