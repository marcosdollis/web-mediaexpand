# Segurança e Boas Práticas - MediaExpand

## 🔒 Configurações de Segurança

### 1. Variáveis de Ambiente em Produção

**Railway Dashboard - Environment Variables:**

```env
DEBUG=False
SECRET_KEY=gere-uma-chave-forte-de-50-caracteres-aleatórios
ALLOWED_HOSTS=*.railway.app,mediaexpand.com.br,www.mediaexpand.com.br
DATABASE_URL=postgresql://... (fornecido automaticamente pelo Railway)
```

**Gerar SECRET_KEY segura:**
```python
# No shell Python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 2. HTTPS em Produção

O Railway força HTTPS automaticamente. Certifique-se de que:
- `SECURE_SSL_REDIRECT = True` (já configurado)
- `SESSION_COOKIE_SECURE = True` (já configurado)
- `CSRF_COOKIE_SECURE = True` (já configurado)

### 3. CORS (Cross-Origin Resource Sharing)

**Desenvolvimento (local):**
```python
CORS_ALLOW_ALL_ORIGINS = True  # Apenas para desenvolvimento
```

**Produção:**
```python
CORS_ALLOWED_ORIGINS = [
    "https://mediaexpand.com.br",
    "https://www.mediaexpand.com.br",
    "https://app.mediaexpand.com.br",
]
```

Atualize em [mediaexpand/settings.py](mediaexpand/settings.py#L161).

### 4. Rate Limiting (Recomendado)

Instale `django-ratelimit`:
```bash
pip install django-ratelimit
```

Adicione ao `requirements.txt`:
```txt
django-ratelimit==4.1.0
```

Use em views críticas:
```python
from ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method='POST')
def sensitive_view(request):
    ...
```

### 5. Validação de Uploads

**Tamanho máximo de arquivos:**

Em `settings.py`, adicione:
```python
# Tamanho máximo de upload: 500MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500MB
```

**Validação de tipos de arquivo:**

Já implementado em `core/models.py` (linha 110):
```python
validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'mkv', 'webm'])]
```

**Escanear vírus (Opcional):**
- Use serviços como ClamAV ou VirusTotal API
- Implemente verificação antes de aprovar vídeos

### 6. Senhas Fortes

**Política já implementada:**
- Mínimo 8 caracteres
- Não pode ser muito similar aos dados do usuário
- Não pode ser senha comum
- Não pode ser totalmente numérica

**Para reforçar:**

Em `settings.py`, adicione validador customizado:
```python
AUTH_PASSWORD_VALIDATORS = [
    # ... validadores existentes ...
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,  # Aumentar para 10
        }
    },
]
```

### 7. Tokens JWT

**Configurações atuais:**
- Access Token: 5 horas
- Refresh Token: 7 dias

**Para mais segurança em produção:**
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # 30 min
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),     # 1 dia
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,  # Ativar blacklist
}
```

**Instalar blacklist:**
```bash
pip install djangorestframework-simplejwt[crypto]
```

Adicione ao `INSTALLED_APPS`:
```python
'rest_framework_simplejwt.token_blacklist',
```

Execute migração:
```bash
python manage.py migrate
```

### 8. Logging em Produção

Adicione ao `settings.py`:
```python
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'WARNING',
                'class': 'logging.FileHandler',
                'filename': BASE_DIR / 'logs/django.log',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': True,
            },
        },
    }
```

### 9. Backup do Banco de Dados

**Railway PostgreSQL:**

```bash
# Backup manual
railway run pg_dump > backup_$(date +%Y%m%d).sql

# Restaurar
railway run psql < backup_20260205.sql
```

**Automatizar com cron (Linux) ou Task Scheduler (Windows).**

### 10. Monitoramento

**Sentry (Recomendado):**

```bash
pip install sentry-sdk
```

Em `settings.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn="https://sua-dsn.sentry.io",
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    )
```

---

## 🛡️ Checklist de Segurança Pré-Deploy

- [ ] `DEBUG = False` em produção
- [ ] `SECRET_KEY` forte e única
- [ ] `ALLOWED_HOSTS` configurado corretamente
- [ ] HTTPS habilitado (forçado)
- [ ] CORS configurado com origins específicas
- [ ] Senhas dos usuários iniciais alteradas
- [ ] Banco de dados com senha forte
- [ ] JWT com tempo de expiração adequado
- [ ] Logs configurados
- [ ] Backup do banco configurado
- [ ] Monitoramento (Sentry) configurado
- [ ] Rate limiting em endpoints críticos
- [ ] Validação de uploads robusta
- [ ] Permissões de arquivo corretas no servidor

---

## 🚀 Boas Práticas de Desenvolvimento

### 1. Git e Versionamento

**Nunca commite:**
- `.env` (já no .gitignore)
- `db.sqlite3` (já no .gitignore)
- `media/` com vídeos reais (já no .gitignore)
- Credenciais ou tokens

**Exemplo .gitignore completo:**
```
*.pyc
__pycache__/
db.sqlite3
.env
/media
/staticfiles
venv/
```

### 2. Testes

**Criar testes unitários:**

```python
# core/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Municipio, Cliente

User = get_user_model()

class UserTestCase(TestCase):
    def test_create_owner(self):
        user = User.objects.create_user(
            username='owner_test',
            password='senha123',
            role='OWNER'
        )
        self.assertTrue(user.is_owner())
        self.assertFalse(user.is_franchisee())
```

**Executar testes:**
```bash
python manage.py test
```

### 3. Documentação da API

**Instalar Swagger/OpenAPI:**

```bash
pip install drf-spectacular
```

Em `settings.py`:
```python
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

Em `urls.py`:
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    ...
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

Acesse: `http://localhost:8000/api/docs/`

### 4. Migrations

**Sempre que alterar models:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**Verificar antes de commitar:**
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

### 5. Performance

**Otimizar queries:**
```python
# Ruim
for cliente in Cliente.objects.all():
    print(cliente.user.username)  # N+1 queries

# Bom
clientes = Cliente.objects.select_related('user').all()
for cliente in clientes:
    print(cliente.user.username)  # 1 query
```

**Cache de queries frequentes (opcional):**
```bash
pip install django-redis
```

### 6. Code Quality

**Instalar ferramentas de qualidade:**
```bash
pip install black flake8 pylint isort
```

**Formatar código:**
```bash
black .
isort .
flake8 .
```

---

## 📊 Monitoramento de Desempenho

### Métricas Importantes:

1. **Tempo de resposta da API**
2. **Taxa de upload de vídeos**
3. **Logs de exibição por hora/dia**
4. **Dispositivos ativos**
5. **Erros HTTP (4xx, 5xx)**

### Ferramentas Recomendadas:

- **Sentry**: Erros e exceções
- **Railway Metrics**: CPU, memória, banda
- **Google Analytics**: (opcional) para tracking de clientes
- **Grafana + Prometheus**: (avançado) métricas customizadas

---

## 🆘 Troubleshooting em Produção

### Erro 500 - Internal Server Error

1. Verifique logs do Railway
2. Verifique `DEBUG=False` não expõe detalhes
3. Configure Sentry para capturar exceções
4. Verifique migrations estão atualizadas

### Problema de Upload de Vídeos

1. Verifique limites de tamanho
2. Verifique permissões da pasta `media/`
3. Verifique espaço em disco no Railway
4. Considere usar S3/CloudFront para armazenamento

### Banco de Dados Lento

1. Adicione índices em campos frequentemente consultados
2. Use `select_related` e `prefetch_related`
3. Considere paginação mais agressiva
4. Limpe logs antigos periodicamente

### Dispositivo TV Não Sincroniza

1. Verifique `identificador_unico` correto
2. Verifique dispositivo está `ativo=True`
3. Verifique playlist está `ativa=True`
4. Verifique conexão de internet da TV

---

## 📧 Contato e Suporte

Para dúvidas ou problemas, consulte:
1. [README.md](README.md) - Documentação principal
2. [API_TV_GUIDE.md](API_TV_GUIDE.md) - Guia de integração TV
3. [EXEMPLOS_USO.md](EXEMPLOS_USO.md) - Exemplos práticos

---

**MediaExpand - Sistema de Gerenciamento de Mídia Indoor**
*Versão 1.0 - Fevereiro 2026*
