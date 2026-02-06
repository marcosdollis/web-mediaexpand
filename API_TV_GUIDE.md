# Guia de Integração - App de TV

## 🔌 Como Integrar o App de TV com a API MediaExpand

Este guia detalha como seu app de TV deve se comunicar com o backend.

## 1️⃣ Autenticação do Dispositivo

### Endpoint: POST /api/tv/auth/

Cada dispositivo TV deve ter um identificador único (UUID). Use este endpoint para autenticar o dispositivo e receber a playlist atual.

**Request:**
```http
POST /api/tv/auth/
Content-Type: application/json

{
  "identificador_unico": "TV-ABC-123-XYZ",
  "versao_app": "1.0.0"
}
```

**Response Success (200):**
```json
{
  "dispositivo_id": 1,
  "dispositivo_nome": "TV Shopping Center - Entrada Principal",
  "municipio": "São Paulo/SP",
  "playlist": {
    "id": 5,
    "nome": "Playlist Manhã - Shopping",
    "duracao_total_segundos": 180,
    "videos": [
      {
        "id": 10,
        "titulo": "Propaganda Loja de Roupas",
        "arquivo_url": "https://seu-dominio.railway.app/media/videos/cliente_5/video1.mp4",
        "duracao_segundos": 30
      },
      {
        "id": 11,
        "titulo": "Propaganda Restaurante",
        "arquivo_url": "https://seu-dominio.railway.app/media/videos/cliente_6/video2.mp4",
        "duracao_segundos": 30
      },
      {
        "id": 12,
        "titulo": "Propaganda Academia",
        "arquivo_url": "https://seu-dominio.railway.app/media/videos/cliente_7/video3.mp4",
        "duracao_segundos": 30
      }
    ]
  }
}
```

**Response sem Playlist (200):**
```json
{
  "dispositivo_id": 1,
  "dispositivo_nome": "TV Shopping Center",
  "municipio": "São Paulo/SP",
  "playlist": null,
  "message": "Nenhuma playlist ativa configurada"
}
```

**Response Error (404):**
```json
{
  "error": "Dispositivo não encontrado ou inativo"
}
```

---

## 2️⃣ Registrar Logs de Exibição

### Endpoint: POST /api/tv/log-exibicao/

Registre cada vez que um vídeo for exibido na TV. Isso permite estatísticas e relatórios.

**Request:**
```http
POST /api/tv/log-exibicao/
Content-Type: application/json

{
  "dispositivo_id": 1,
  "video_id": 10,
  "playlist_id": 5,
  "data_hora_inicio": "2026-02-05T10:30:00Z",
  "data_hora_fim": "2026-02-05T10:30:30Z",
  "completamente_exibido": true
}
```

**Campos:**
- `dispositivo_id`: ID retornado na autenticação
- `video_id`: ID do vídeo que foi exibido
- `playlist_id`: ID da playlist
- `data_hora_inicio`: ISO 8601 timestamp do início
- `data_hora_fim`: ISO 8601 timestamp do fim (ou null se interrompido)
- `completamente_exibido`: `true` se o vídeo foi exibido até o fim, `false` se pulado/interrompido

**Response Success (201):**
```json
{
  "id": 123,
  "dispositivo": 1,
  "dispositivo_nome": "TV Shopping Center",
  "video": 10,
  "video_titulo": "Propaganda Loja de Roupas",
  "playlist": 5,
  "playlist_nome": "Playlist Manhã - Shopping",
  "data_hora_inicio": "2026-02-05T10:30:00Z",
  "data_hora_fim": "2026-02-05T10:30:30Z",
  "completamente_exibido": true,
  "created_at": "2026-02-05T10:30:31.123456Z"
}
```

---

## 3️⃣ Verificar Horário de Exibição

### Endpoint: GET /api/tv/check-schedule/{identificador_unico}/

**NOVO!** Verifica se o dispositivo deve estar exibindo conteúdo no momento atual baseado nos agendamentos configurados.

**Request:**
```http
GET /api/tv/check-schedule/TV-ABC-123-XYZ/
```

**Response - Dentro do Horário (200):**
```json
{
  "should_display": true,
  "current_time": "2026-02-06T14:30:00-03:00",
  "dispositivo_nome": "TV Shopping Center - Entrada Principal",
  "has_playlist": true,
  "playlist_id": 5,
  "playlist_nome": "Playlist Manhã - Shopping",
  "agendamentos": [
    {
      "nome": "Horário Comercial",
      "dias_semana": [0, 1, 2, 3, 4],
      "hora_inicio": "08:00",
      "hora_fim": "18:00"
    }
  ]
}
```

**Response - Fora do Horário (200):**
```json
{
  "should_display": false,
  "current_time": "2026-02-06T22:30:00-03:00",
  "dispositivo_nome": "TV Shopping Center - Entrada Principal",
  "has_playlist": true,
  "agendamentos": [
    {
      "nome": "Horário Comercial",
      "dias_semana": [0, 1, 2, 3, 4],
      "hora_inicio": "08:00",
      "hora_fim": "18:00"
    }
  ]
}
```

**Response - Sem Agendamentos (200):**
```json
{
  "should_display": true,
  "current_time": "2026-02-06T14:30:00-03:00",
  "dispositivo_nome": "TV Shopping Center",
  "has_playlist": true,
  "playlist_id": 5,
  "playlist_nome": "Playlist Manhã - Shopping",
  "agendamentos": [],
  "message": "Sem agendamentos: exibição 24/7"
}
```

**Response Error (404):**
```json
{
  "error": "Dispositivo não encontrado ou inativo"
}
```

**Campos:**
- `should_display`: `true` se deve exibir conteúdo, `false` se deve mostrar tela preta
- `current_time`: Data/hora atual do servidor (ISO 8601)
- `dias_semana`: Array com dias (0=Segunda, 1=Terça, ..., 6=Domingo)
- `hora_inicio` / `hora_fim`: Horários no formato HH:MM

**Como usar:**
1. Faça esta requisição a cada 1-5 minutos
2. Se `should_display: false`, exiba tela preta
3. Se `should_display: true`, exiba a playlist normalmente
4. Sem agendamentos = sempre exibe (24/7)

---

## 4️⃣ Fluxo de Funcionamento do App de TV

### Inicialização
1. App inicia na TV
2. Faz POST em `/api/tv/auth/` com seu identificador único
3. Recebe a playlist atual com lista de vídeos
4. Baixa/cacheia os vídeos (opcional, recomendado)
5. Verifica horário: GET `/api/tv/check-schedule/{uuid}/`

### Loop de Reprodução (com Verificação de Horário)
```
A cada X minutos (ex: 1-5 minutos):
  1. Verificar horário: GET /api/tv/check-schedule/{uuid}/
  2. Se should_display = false:
     - Exibir tela preta
     - Pausar reprodução
  3. Se should_display = true:
     - Retomar/iniciar reprodução da playlist

Para cada vídeo na playlist (quando should_display = true):
  1. Reproduzir vídeo
  2. Ao iniciar reprodução:
     - Armazenar data_hora_inicio
  3. Ao terminar reprodução:
     - Armazenar data_hora_fim
     - Registrar log: POST /api/tv/log-exibicao/
  4. Próximo vídeo

Ao terminar todos os vídeos:
  - Reiniciar do primeiro vídeo (loop infinito)
```

### Sincronização Periódica
```
A cada X minutos (ex: 5 minutos):
  1. Fazer novo POST em /api/tv/auth/
  2. Verificar se playlist mudou (comparar IDs)
  3. Se mudou:
     - Parar reprodução atual
     - Baixar/cachear novos vídeos
     - Reiniciar reprodução com nova playlist
```

---

## 5️⃣ Exemplo de Implementação (Pseudocódigo)

```python
import requests
from datetime import datetime

class TVApp:
    def __init__(self, device_uuid, api_base_url):
        self.device_uuid = device_uuid
        self.api_base_url = api_base_url
        self.device_id = None
        self.playlist = None
        
    def authenticate(self):
        """Autentica o dispositivo e pega a playlist"""
        url = f"{self.api_base_url}/api/tv/auth/"
        payload = {
            "identificador_unico": self.device_uuid,
            "versao_app": "1.0.0"
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.device_id = data['dispositivo_id']
            self.playlist = data.get('playlist')
            return True
        return False
    
    def log_playback(self, video_id, playlist_id, start_time, end_time, completed):
        """Registra log de exibição"""
        url = f"{self.api_base_url}/api/tv/log-exibicao/"
        payload = {
            "dispositivo_id": self.device_id,
            "video_id": video_id,
            "playlist_id": playlist_id,
            "data_hora_inicio": start_time.isoformat(),
            "data_hora_fim": end_time.isoformat(),
            "completamente_exibido": completed
        }
        
        requests.post(url, json=payload)
    
    def check_schedule(self):
        """Verifica se deve exibir conteúdo agora"""
        url = f"{self.api_base_url}/api/tv/check-schedule/{self.device_uuid}/"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('should_display', True)
        except Exception as e:
            print(f"Erro ao verificar horário: {e}")
            # Em caso de erro, continua exibindo
            return True
        
        return True
    
    def play_video(self, video):
        """Reproduz um vídeo e registra log"""
        start_time = datetime.now()
        
        # Sua lógica de reprodução aqui
        # player.play(video['arquivo_url'])
        
        end_time = datetime.now()
        
        # Registra log
        self.log_playback(
            video_id=video['id'],
            playlist_id=self.playlist['id'],
            start_time=start_time,
            end_time=end_time,
            completed=True
        )
    
    def run(self):
        """Loop principal do app"""
        import time
        
        # Autentica
        if not self.authenticate():
            print("Falha na autenticação")
            return
        
        if not self.playlist:
            print("Nenhuma playlist configurada")
            return
        
        last_schedule_check = time.time()
        is_displaying = True
        
        # Loop infinito de reprodução
        while True:
            # Verifica horário a cada 5 minutos
            if time.time() - last_schedule_check > 300:  # 5 minutos
                should_display = self.check_schedule()
                last_schedule_check = time.time()
                
                if should_display != is_displaying:
                    is_displaying = should_display
                    if not is_displaying:
                        print("Fora do horário de exibição - Tela preta")
                        # Mostrar tela preta
                        continue
            
            # Se não deve exibir, aguarda e verifica novamente
            if not is_displaying:
                time.sleep(60)  # Aguarda 1 minuto
                continue
            
            # Exibe playlist normalmente
            for video in self.playlist['videos']:
                # Verifica horário antes de cada vídeo
                if not self.check_schedule():
                    is_displaying = False
                    break
                    
                self.play_video(video)
                
            # Re-autentica a cada ciclo completo
            self.authenticate()


# Uso
app = TVApp(
    device_uuid="TV-ABC-123-XYZ",
    api_base_url="https://mediaexpand.railway.app"
)
app.run()
```

---

## 5️⃣ Recomendações Técnicas

### Cache de Vídeos
- Baixe e armazene vídeos localmente
- Evita buffering durante reprodução
- Atualiza cache quando playlist muda

### Gerenciamento de Erros
- Implemente retry logic para chamadas de API
- Se falhar ao registrar log, armazene localmente e tente depois
- Se perder conexão, continue reproduzindo playlist em cache

### Performance
- Use requests assíncronos para não bloquear reprodução
- Pré-carregue próximo vídeo enquanto atual está tocando
- Comprima/otimize vídeos no backend antes do upload

### Segurança
- Use HTTPS em produção
- Valide certificados SSL
- Não exponha identificadores sensíveis nos logs

### Monitoramento
- Registre todos os erros localmente
- Envie heartbeat periódico (atualização de última_sincronizacao)
- Monitore uso de banda e armazenamento

---

## 6️⃣ Testando a API

### Usando cURL

**Autenticação:**
```bash
curl -X POST http://localhost:8000/api/tv/auth/ \
  -H "Content-Type: application/json" \
  -d '{
    "identificador_unico": "TV-TEST-001",
    "versao_app": "1.0.0"
  }'
```

**Registrar Log:**
```bash
curl -X POST http://localhost:8000/api/tv/log-exibicao/ \
  -H "Content-Type: application/json" \
  -d '{
    "dispositivo_id": 1,
    "video_id": 10,
    "playlist_id": 5,
    "data_hora_inicio": "2026-02-05T10:30:00Z",
    "data_hora_fim": "2026-02-05T10:30:30Z",
    "completamente_exibido": true
  }'
```

### Usando Postman/Insomnia

1. Importe a URL base: `http://localhost:8000` (dev) ou `https://seu-app.railway.app` (prod)
2. Crie uma collection com os endpoints acima
3. Teste cada endpoint individualmente

---

## 7️⃣ Próximos Passos

1. ✅ Backend pronto
2. 🔄 Desenvolver App de TV
3. 🔄 Implementar cache de vídeos
4. 🔄 Adicionar estatísticas de visualização no dashboard
5. 🔄 Implementar notificações para clientes (quando vídeo é aprovado)

---

**Documentação MediaExpand API v1.0**
