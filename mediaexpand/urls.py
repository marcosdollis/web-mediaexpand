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
  "videos": [...]
}
```

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

urlpatterns = [
    path('', include('core.urls_web')),  # Web URLs (templates)
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Swagger/OpenAPI Documentation
    re_path(r'^api/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Customização do Admin
admin.site.site_header = "MediaExpand - Administração"
admin.site.site_title = "MediaExpand Admin"
admin.site.index_title = "Gerenciamento de Mídia Indoor"

from django.views.static import serve as static_serve

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files (both development and production)
# Em produção (Railway), Django serve os arquivos de mídia do volume /data/media
# django.conf.urls.static.static() não funciona com DEBUG=False, então usamos re_path direto
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', static_serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
