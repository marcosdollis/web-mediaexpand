# 📂 Estrutura do Projeto MediaExpand

```
web-mediaexpand/
│
├── 📁 mediaexpand/                    # Configuração principal do Django
│   ├── __init__.py
│   ├── settings.py                   # Configurações do projeto
│   ├── urls.py                       # URLs principais
│   ├── wsgi.py                       # WSGI para deploy
│   └── asgi.py                       # ASGI (async)
│
├── 📁 core/                          # App principal da aplicação
│   ├── __init__.py
│   ├── apps.py                       # Configuração do app
│   ├── models.py                     # 🔴 Modelos do banco de dados
│   ├── admin.py                      # Interface administrativa
│   ├── serializers.py                # 🔴 Serializers para API REST
│   ├── views.py                      # 🔴 Views e ViewSets da API
│   ├── urls.py                       # URLs da API
│   ├── permissions.py                # 🔴 Permissões customizadas
│   │
│   └── 📁 management/                # Comandos customizados
│       └── 📁 commands/
│           └── create_owner.py       # Criar usuário OWNER inicial
│
├── 📁 media/                         # 📹 Arquivos de mídia (vídeos, thumbnails)
│   ├── videos/                       # Vídeos dos clientes
│   └── thumbnails/                   # Miniaturas dos vídeos
│
├── 📁 staticfiles/                   # Arquivos estáticos coletados
│
├── 📄 manage.py                      # Script de gerenciamento Django
├── 📄 requirements.txt               # Dependências Python
├── 📄 Procfile                       # Configuração Railway/Heroku
├── 📄 railway.json                   # Configuração Railway
├── 📄 runtime.txt                    # Versão do Python
│
├── 📄 .env                           # ⚙️ Variáveis de ambiente (local)
├── 📄 .env.example                   # Exemplo de variáveis
├── 📄 .gitignore                     # Arquivos ignorados pelo Git
│
├── 📄 setup.bat                      # 🚀 Script setup Windows
├── 📄 setup.sh                       # 🚀 Script setup Linux/Mac
│
└── 📚 Documentação/
    ├── README.md                     # 📖 Documentação principal
    ├── API_TV_GUIDE.md              # 📱 Guia de integração TV App
    ├── EXEMPLOS_USO.md              # 💡 Exemplos práticos
    ├── SECURITY.md                  # 🔒 Segurança e boas práticas
    ├── RAILWAY_DEPLOY.md            # 🚂 Deploy no Railway
    └── instructions.txt              # 📝 Resumo rápido
```

---

## 🗂️ Modelos do Banco de Dados

### 1️⃣ User (Usuário)
- **Campos**: username, email, password, role (OWNER/FRANCHISEE/CLIENT), phone, cpf_cnpj
- **Herda de**: AbstractUser do Django
- **Relações**: 
  - created_by → User (quem criou)
  - cliente_profile → Cliente
  - municipios → Municipio (como franqueado)

### 2️⃣ Municipio
- **Campos**: nome, estado, ativo
- **Relações**:
  - franqueado → User (FRANCHISEE)
  - clientes ← Cliente
  - playlists ← Playlist
  - dispositivos ← DispositivoTV

### 3️⃣ Cliente
- **Campos**: empresa, ativo, observacoes
- **Relações**:
  - user → User (OneToOne)
  - franqueado → User (FRANCHISEE)
  - municipios → Municipio (ManyToMany)
  - videos ← Video

### 4️⃣ Video
- **Campos**: titulo, descricao, arquivo, duracao_segundos, thumbnail, status (PENDING/APPROVED/REJECTED), ativo
- **Relações**:
  - cliente → Cliente
  - playlist_items ← PlaylistItem
  - logs_exibicao ← LogExibicao

### 5️⃣ Playlist
- **Campos**: nome, descricao, ativa, duracao_total_segundos
- **Relações**:
  - municipio → Municipio
  - franqueado → User (FRANCHISEE)
  - items ← PlaylistItem
  - dispositivos ← DispositivoTV

### 6️⃣ PlaylistItem
- **Campos**: ordem, repeticoes, ativo
- **Relações**:
  - playlist → Playlist
  - video → Video

### 7️⃣ DispositivoTV
- **Campos**: nome, identificador_unico, localizacao, ativo, ultima_sincronizacao, versao_app
- **Relações**:
  - municipio → Municipio
  - playlist_atual → Playlist
  - logs_exibicao ← LogExibicao

### 8️⃣ LogExibicao
- **Campos**: data_hora_inicio, data_hora_fim, completamente_exibido
- **Relações**:
  - dispositivo → DispositivoTV
  - video → Video
  - playlist → Playlist

---

## 🔗 Relacionamentos

```
User (OWNER)
  └─► User (FRANCHISEE)
        ├─► Municipio
        │     ├─► Playlist
        │     │     └─► PlaylistItem ◄─┐
        │     │           └─► Video ◄──┼──┐
        │     ├─► DispositivoTV        │  │
        │     └─► Cliente ─────────────┘  │
        │           └─► User (CLIENT)      │
        │                 └─────────────────┘
        └─► Playlist
              └─► PlaylistItem
                    └─► Video
```

---

## 🔐 Hierarquia de Permissões

### OWNER (Dono)
- ✅ Acesso total
- ✅ Vê todos os recursos
- ✅ Cria franqueados
- ✅ Aprova/rejeita vídeos
- ✅ Gerencia qualquer recurso

### FRANCHISEE (Franqueado)
- ✅ Cria municípios
- ✅ Cria clientes
- ✅ Aprova/rejeita vídeos de seus clientes
- ✅ Cria playlists
- ✅ Gerencia dispositivos TV
- ✅ Visualiza logs de seus municípios
- ❌ Não vê dados de outros franqueados

### CLIENT (Cliente)
- ✅ Upload de vídeos
- ✅ Visualiza seus próprios vídeos
- ✅ Atualiza informações pessoais
- ❌ Não cria playlists
- ❌ Não aprova vídeos
- ❌ Não vê dados de outros clientes

---

## 🌐 Endpoints da API REST

### Base URL
- Local: `http://localhost:8000/api/`
- Railway: `https://seu-projeto.up.railway.app/api/`

### Recursos Principais

| Recurso | Endpoint | Métodos | Autenticação |
|---------|----------|---------|--------------|
| **Autenticação** | `/api/token/` | POST | ❌ Público |
| **Refresh Token** | `/api/token/refresh/` | POST | ❌ Público |
| **Usuários** | `/api/users/` | GET, POST, PUT, DELETE | ✅ JWT |
| **Me** | `/api/users/me/` | GET | ✅ JWT |
| **Municípios** | `/api/municipios/` | GET, POST, PUT, DELETE | ✅ Franqueado/Owner |
| **Clientes** | `/api/clientes/` | GET, POST, PUT, DELETE | ✅ Franqueado/Owner |
| **Vídeos** | `/api/videos/` | GET, POST, PUT, DELETE | ✅ JWT |
| **Aprovar Vídeo** | `/api/videos/{id}/approve/` | POST | ✅ Franqueado/Owner |
| **Playlists** | `/api/playlists/` | GET, POST, PUT, DELETE | ✅ Franqueado/Owner |
| **Add Vídeo** | `/api/playlists/{id}/add_video/` | POST | ✅ Franqueado/Owner |
| **Dispositivos** | `/api/dispositivos/` | GET, POST, PUT, DELETE | ✅ Franqueado/Owner |
| **Logs** | `/api/logs-exibicao/` | GET, POST | ✅ Franqueado/Owner |
| **Stats** | `/api/dashboard/stats/` | GET | ✅ JWT |
| **TV Auth** | `/api/tv/auth/` | POST | ❌ Público |
| **TV Log** | `/api/tv/log-exibicao/` | POST | ❌ Público |

---

## 🛠️ Tecnologias Utilizadas

| Categoria | Tecnologia | Versão | Objetivo |
|-----------|-----------|--------|----------|
| **Backend** | Django | 4.2.9 | Framework web |
| **API** | Django REST Framework | 3.14.0 | API RESTful |
| **Autenticação** | djangorestframework-simplejwt | 5.3.1 | JWT tokens |
| **CORS** | django-cors-headers | 4.3.1 | Cross-origin |
| **Imagens** | Pillow | 10.2.0 | Processamento |
| **PostgreSQL** | psycopg2-binary | 2.9.9 | Driver DB |
| **Config** | python-decouple | 3.8 | Env vars |
| **Server** | Gunicorn | 21.2.0 | WSGI server |
| **Static** | WhiteNoise | 6.6.0 | Arquivos estáticos |
| **DB URL** | dj-database-url | 2.1.0 | Parse DATABASE_URL |

---

## 🚀 Comandos Úteis

### Setup Inicial
```bash
# Windows
setup.bat

# Linux/Mac
chmod +x setup.sh && ./setup.sh
```

### Desenvolvimento
```bash
# Ativar venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Migrações
python manage.py makemigrations
python manage.py migrate

# Criar superusuário OWNER
python manage.py create_owner

# Rodar servidor
python manage.py runserver

# Shell interativo
python manage.py shell

# Coletar estáticos
python manage.py collectstatic
```

### Testes
```bash
python manage.py test
python manage.py check
```

---

## 📊 Fluxo de Dados

### 1. Setup Inicial
```
OWNER cria conta
  └─► OWNER cria FRANCHISEE
        └─► FRANCHISEE cria Município
              └─► FRANCHISEE cria Cliente (USER + Cliente)
```

### 2. Gerenciamento de Vídeos
```
CLIENT faz upload de vídeo (status=PENDING)
  └─► FRANCHISEE/OWNER revisa vídeo
        ├─► Aprovar (status=APPROVED)
        └─► Rejeitar (status=REJECTED)
```

### 3. Criação de Playlist
```
FRANCHISEE cria Playlist para Município
  └─► FRANCHISEE adiciona vídeos APROVADOS
        └─► Sistema calcula duração total
```

### 4. Dispositivo TV
```
FRANCHISEE cadastra DispositivoTV
  └─► Vincula Playlist ao dispositivo
        └─► TV App autentica (POST /api/tv/auth/)
              └─► Recebe playlist com URLs de vídeos
                    └─► TV reproduz vídeos
                          └─► TV envia log (POST /api/tv/log-exibicao/)
```

---

## 📈 Próximas Etapas Sugeridas

1. ✅ **Backend completo** (FEITO)
2. 🔄 **Desenvolver App de TV** (React Native / Flutter / Electron)
3. 🔄 **Desenvolver Frontend Web** (React / Vue / Angular)
4. 🔄 **Adicionar testes unitários**
5. 🔄 **Implementar Swagger/OpenAPI**
6. 🔄 **Adicionar cache (Redis)**
7. 🔄 **Implementar notificações (email/push)**
8. 🔄 **Analytics e relatórios avançados**
9. 🔄 **Armazenamento em nuvem (S3/CloudFront)**
10. 🔄 **Mobile app para clientes (React Native)**

---

## 📞 Arquivos de Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [README.md](README.md) | Documentação principal e guia de instalação |
| [API_TV_GUIDE.md](API_TV_GUIDE.md) | Guia completo de integração do app de TV |
| [EXEMPLOS_USO.md](EXEMPLOS_USO.md) | Exemplos práticos via shell e API |
| [SECURITY.md](SECURITY.md) | Segurança, boas práticas e checklist |
| [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) | Guia passo a passo de deploy no Railway |
| [instructions.txt](instructions.txt) | Resumo rápido do projeto |
| [ESTRUTURA.md](ESTRUTURA.md) | Este arquivo - estrutura do projeto |

---

## 🎯 Funcionalidades Implementadas

- ✅ Sistema de autenticação JWT robusto
- ✅ Hierarquia de 3 níveis de usuários
- ✅ CRUD completo de todos os recursos
- ✅ Permissões granulares por nível
- ✅ Upload e validação de vídeos
- ✅ Sistema de aprovação de vídeos
- ✅ Criação e gerenciamento de playlists
- ✅ Ordenação e repetição de vídeos
- ✅ Cadastro de dispositivos TV
- ✅ API para autenticação de TVs
- ✅ Sistema de logs de exibição
- ✅ Dashboard com estatísticas
- ✅ Admin Django customizado
- ✅ Pronto para SQLite (dev) e PostgreSQL (prod)
- ✅ Configuração completa para Railway
- ✅ Scripts de setup automatizados
- ✅ Documentação completa

---

**MediaExpand v1.0** - Sistema de Gerenciamento de Mídia Indoor
*Desenvolvido com Django + Django REST Framework*
*Fevereiro 2026*
