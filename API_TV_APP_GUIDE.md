# Guia de Integração - MediaExpand TV App

## 📱 Informações Gerais

**Base URL**: `http://seu-dominio.com/api/`

**Documentação Interativa**: 
- Swagger UI: `http://seu-dominio.com/api/swagger/`
- ReDoc: `http://seu-dominio.com/api/redoc/`

**Autenticação**: Não é necessária para os endpoints da TV (usam `identificador_unico`)

---

## 🔧 Endpoints Principais

### 1. 🔐 Autenticação e Sincronização da TV

**POST** `/api/tv/auth/`

Autentica o dispositivo e obtém a playlist atual.

**Request Body:**
```json
{
  "identificador_unico": "uuid-do-dispositivo",
  "versao_app": "1.0.0"  // Opcional
}
```

**Response (Sucesso - 200):**
```json
{
  "dispositivo_id": 1,
  "dispositivo_nome": "TV Shopping Center",
  "municipio": "São Paulo/SP",
  "playlist": {
    "id": 5,
    "nome": "Playlist Principal",
    "descricao": "Playlist com vídeos aprovados",
    "duracao_total_segundos": 300,
    "items": [
      {
        "id": 10,
        "ordem": 1,
        "repeticoes": 1,
        "video": {
          "id": 25,
          "titulo": "Anúncio Supermercado",
          "descricao": "Promoção de fim de semana",
          "arquivo": "http://dominio.com/media/videos/video.mp4",
          "thumbnail": "http://dominio.com/media/thumbnails/thumb.jpg",
          "duracao_segundos": 30,
          "status": "APPROVED",
          "cliente": {
            "id": 3,
            "empresa": "Supermercado Silva"
          }
        }
      }
    ]
  }
}
```

**Response (Sem Playlist - 200):**
```json
{
  "dispositivo_id": 1,
  "dispositivo_nome": "TV Shopping Center",
  "municipio": "São Paulo/SP",
  "playlist": null,
  "message": "Nenhuma playlist ativa configurada"
}
```

**Response (Erro - 404):**
```json
{
  "error": "Dispositivo não encontrado ou inativo"
}
```

**Quando usar**: 
- Ao iniciar o app
- A cada X minutos para verificar atualizações (recomendado: 5-10 minutos)
- Quando o app voltar ao foreground

---

### 2. 📊 Registrar Log de Exibição

**POST** `/api/tv/log-exibicao/`

Registra que um vídeo foi exibido.

**Request Body:**
```json
{
  "dispositivo_id": 1,
  "video_id": 25,
  "playlist_id": 5,
  "data_hora_inicio": "2026-02-07T14:30:00Z",
  "data_hora_fim": "2026-02-07T14:30:30Z",
  "completamente_exibido": true
}
```

**Response (201):**
```json
{
  "id": 1523,
  "dispositivo": 1,
  "video": 25,
  "playlist": 5,
  "data_hora_inicio": "2026-02-07T14:30:00Z",
  "data_hora_fim": "2026-02-07T14:30:30Z",
  "completamente_exibido": true,
  "created_at": "2026-02-07T14:30:35Z"
}
```

**Quando usar**: 
- Após cada vídeo ser exibido completamente
- Ou ao final de um loop completo da playlist

---

### 3. ⏰ Verificar Horário de Exibição

**GET** `/api/tv/check-schedule/{identificador_unico}/`

Verifica se o dispositivo deve estar exibindo conteúdo no momento atual.

**Response (200):**
```json
{
  "should_display": true,
  "current_time": "2026-02-07T14:30:00-03:00",
  "dispositivo_nome": "TV Shopping Center",
  "has_playlist": true,
  "playlist_id": 5,
  "playlist_nome": "Playlist Principal",
  "agendamentos": [
    {
      "nome": "Horário Comercial",
      "dias": "seg,ter,qua,qui,sex",
      "hora_inicio": "08:00:00",
      "hora_fim": "18:00:00"
    }
  ]
}
```

**Quando usar**: 
- A cada minuto para verificar se deve pausar/continuar exibição
- Se `should_display` = `false`, mostrar tela preta ou standby

---

## 📝 Fluxo Recomendado para o App

### Ao Iniciar o App

1. **Obter UUID do dispositivo** (gerar uma vez e salvar localmente)
2. **Chamar** `/api/tv/auth/` com o UUID
3. **Baixar os vídeos** da playlist (se houver)
4. **Iniciar reprodução** em loop

### Durante a Execução

1. **A cada 5-10 minutos**: Chamar `/api/tv/auth/` para verificar atualizações
2. **A cada minuto**: Chamar `/api/tv/check-schedule/` para verificar horário
3. **Após cada vídeo**: Chamar `/api/tv/log-exibicao/` para registrar

### Gerenciamento de Vídeos

- **Cache local**: Salvar vídeos baixados para evitar re-download
- **Verificar mudanças**: Comparar `playlist.id` e `items` para detectar atualizações
- **Download assíncrono**: Baixar novos vídeos em background
- **Limpeza**: Remover vídeos que não estão mais na playlist

---

## 🎬 Lógica de Reprodução

### Ordem de Exibição

Os vídeos devem ser reproduzidos na ordem do campo `ordem` de cada `item`.

```javascript
// Exemplo de lógica
playlist.items.sort((a, b) => a.ordem - b.ordem);

for (let item of playlist.items) {
  for (let i = 0; i < item.repeticoes; i++) {
    await playVideo(item.video.arquivo);
    logExibicao(item.video.id);
  }
}
```

### Repetição

- Cada item tem um campo `repeticoes` que indica quantas vezes seguidas deve ser exibido
- Após exibir todos os itens, o loop recomeça

### Tela Preta

Se `should_display` = `false`, o app deve:
- Pausar a reprodução
- Mostrar tela preta ou logotipo
- Continuar verificando a cada minuto

---

## 🔄 Sincronização e Atualizações

### Detectar Mudanças na Playlist

Ao chamar `/api/tv/auth/`, compare:

```javascript
const playlistChanged = 
  currentPlaylist.id !== newPlaylist.id ||
  currentPlaylist.items.length !== newPlaylist.items.length ||
  itemsOrderChanged(currentPlaylist.items, newPlaylist.items);

if (playlistChanged) {
  updatePlaylist(newPlaylist);
  downloadNewVideos();
}
```

### Atualização de Vídeos

- Verifique se há novos vídeos comparando os IDs
- Baixe os novos vídeos antes de aplicar a nova playlist
- Remova vídeos antigos do cache após confirmar que não são mais necessários

---

## 📦 Formato dos Arquivos

### Vídeos
- **Formato**: MP4 (H.264)
- **URL completa** retornada no campo `arquivo`
- **Download**: Use a URL diretamente

### Thumbnails
- **Formato**: JPG/PNG
- **URL completa** retornada no campo `thumbnail`
- **Opcional**: Pode ser usado para preview ou logs

---

## 🚨 Tratamento de Erros

### Dispositivo Não Encontrado (404)
- Verificar se o UUID está correto
- Entrar em contato com o administrador para registrar o dispositivo

### Sem Playlist (200 com playlist: null)
- Mostrar mensagem de aguardo
- Tentar novamente em alguns minutos
- Não considerar como erro

### Erro de Rede
- Usar playlist em cache (se disponível)
- Tentar reconectar automaticamente
- Exibir conteúdo local enquanto offline

---

## 💡 Boas Práticas

1. **Persistência Local**
   - Salvar UUID do dispositivo
   - Cachear playlist e vídeos
   - Manter logs de exibição em fila se offline

2. **Performance**
   - Pre-carregar próximo vídeo
   - Usar compressão para thumbnails
   - Limpar cache de vídeos antigos

3. **Monitoramento**
   - Enviar logs de erros
   - Atualizar `versao_app` regularmente
   - Registrar todas as exibições

4. **Segurança**
   - Não expor o UUID publicamente
   - Validar URLs antes de baixar
   - Verificar integridade dos arquivos

---

## 🧪 Testando a API

### Usando cURL

```bash
# Autenticar dispositivo
curl -X POST http://localhost:8000/api/tv/auth/ \
  -H "Content-Type: application/json" \
  -d '{"identificador_unico": "seu-uuid-aqui"}'

# Verificar horário
curl http://localhost:8000/api/tv/check-schedule/seu-uuid-aqui/

# Registrar log
curl -X POST http://localhost:8000/api/tv/log-exibicao/ \
  -H "Content-Type: application/json" \
  -d '{
    "dispositivo_id": 1,
    "video_id": 25,
    "playlist_id": 5,
    "data_hora_inicio": "2026-02-07T14:30:00Z",
    "data_hora_fim": "2026-02-07T14:30:30Z",
    "completamente_exibido": true
  }'
```

---

## 📞 Suporte

Para dúvidas ou problemas:
- **Documentação Interativa**: http://seu-dominio.com/api/swagger/
- **Contato**: contato@mediaexpand.com

---

## 🔄 Versão

**Versão da API**: v1  
**Última atualização**: Fevereiro 2026
