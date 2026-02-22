from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Configuração do Swagger/OpenAPI
schema_view = get_schema_view(
   openapi.Info(
      title="MediaExpand API",
      default_version='v1',
      description="""
# API MediaExpand - Sistema de Gerenciamento de Mídia Indoor

## Autenticação
A API usa autenticação JWT (JSON Web Token). Para obter um token:

1. Faça POST em `/api/token/` com username e password
2. Use o token no header: `Authorization: Bearer {seu_token}`

## Endpoints para TV App

### 1. Autenticação da TV
**POST** `/api/tv/auth/`

Autentica o dispositivo TV e retorna a playlist atual.

**Body:**
```json
{
  "identificador_unico": "uuid-do-dispositivo"
}
```

**Response:**
```json
{
  "dispositivo": {...},
  "playlist": {...},
  "videos": [
    {
      "id": 1,
      "titulo": "Promo Verão",
      "arquivo_url": "https://domain/media/videos/...",
      "duracao_segundos": 30,
      "ativo": true,
      "qrcode": {
        "tracking_url": "https://domain/r/uuid-tracking/",
        "descricao": "Resgate seu desconto!"
      },
      "texto_tarja": "Faça um storie com #media123 e ganhe uma lavagem grátis!"
    }
  ]
}
```

**Campos QR Code nos vídeos:**
- `qrcode`: Objeto com dados do QR Code (ou `null` se não configurado)
  - `tracking_url`: URL de rastreamento para gerar o QR Code na TV
  - `descricao`: Texto para exibir junto ao QR Code (ex: "Acesse nosso site!")

**Campo Tarja Inferior:**
- `texto_tarja`: Texto exibido em tarja na parte inferior da tela durante o vídeo, estilo CNN (ou `null` se não configurado). Máximo 300 caracteres.

**Comportamento:** Se `qrcode` for `null`, o app NÃO exibe QR Code. Se presente, o app deve gerar um QR Code a partir de `tracking_url` e exibi-lo no canto do vídeo com o texto da `descricao`.
Se `texto_tarja` for `null`, o app NÃO exibe tarja. Se presente, exibir o texto em uma barra semi-transparente na parte inferior da tela.

### 2. Registrar Log de Exibição
**POST** `/api/tv/log-exibicao/`

Registra quando um vídeo foi exibido.

**Body:**
```json
{
  "dispositivo_identificador": "uuid-do-dispositivo",
  "video_id": 1,
  "tempo_exibicao_segundos": 30
}
```

### 3. Verificar Horário de Exibição
**GET** `/api/tv/check-schedule/{identificador_unico}/`

Verifica se o dispositivo deve estar exibindo conteúdo no horário atual.

**Response:**
```json
{
  "should_display": true,
  "current_time": "14:30:00",
  "active_schedules": [...]
}
```

## QR Code - Rastreamento de Conversão

### Como funciona:
1. Ao criar um vídeo, opcionalmente configure a **URL de destino** e **descrição** do QR Code
2. O sistema gera automaticamente um código de rastreamento único (UUID)
3. A API de TV envia o QR Code com URL de rastreamento (`/r/{tracking_code}/`) e a descrição
4. O app Android gera o QR Code visual e exibe no canto do vídeo
5. Quando alguém escaneia o QR Code, o sistema registra o acesso (IP, data/hora) e redireciona ao destino

### Endpoint de Redirect:
**GET** `/r/{tracking_code}/`

URL pública que registra o clique e redireciona ao destino configurado.

### Campos no endpoint `/api/videos/`:
- `qrcode_url_destino`: URL de destino (site do cliente, promoção, Instagram)
- `qrcode_descricao`: Texto exibido junto ao QR Code na TV
- `qrcode_tracking_code`: UUID único de rastreamento (read-only)
- `qrcode_tracking_url`: URL completa de rastreamento (read-only, gerada automaticamente)
- `qrcode_total_clicks`: Total de cliques registrados (read-only)
- `texto_tarja`: Texto da tarja inferior estilo CNN (máx. 300 caracteres)

## Endpoints REST

Todos os endpoints REST padrão para gerenciamento de:
- Usuários (`/api/users/`)
- Municípios (`/api/municipios/`)
- Clientes (`/api/clientes/`)
- Vídeos (`/api/videos/`)
- Playlists (`/api/playlists/`)
- Dispositivos (`/api/dispositivos/`)
- Logs de Exibição (`/api/logs-exibicao/`)
      """,
      terms_of_service="",
      contact=openapi.Contact(email="contato@mediaexpand.com"),
      license=openapi.License(name="Proprietary"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

from core.views import qrcode_redirect_view, serve_media_streaming

urlpatterns = [
    path('', include('core.urls_web')),  # Web URLs (templates)
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # QR Code Tracking Redirect
    path('r/<uuid:tracking_code>/', qrcode_redirect_view, name='qrcode_redirect'),
    
    # Swagger/OpenAPI Documentation
    re_path(r'^api/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Customização do Admin
admin.site.site_header = "MediaExpand - Administração"
admin.site.site_title = "MediaExpand Admin"
admin.site.index_title = "Gerenciamento de Mídia Indoor"

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files com streaming e suporte a Range Requests
# Resolve travamento de vídeos grandes (100MB+) permitindo download parcial/progressivo
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media_streaming),
]
