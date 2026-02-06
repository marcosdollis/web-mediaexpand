# MediaExpand - Sistema de Gerenciamento de Mídia Indoor

Sistema completo para gerenciamento de franquias de mídia indoor, desenvolvido com Django e Django REST Framework.

## 🚀 Características

- **Autenticação Robusta**: JWT + Session Authentication
- **Hierarquia de Usuários**:
  - **OWNER (Dono)**: Acesso total ao sistema
  - **FRANCHISEE (Franqueado)**: Gerencia municípios e clientes
  - **CLIENT (Cliente)**: Upload e gerenciamento de vídeos próprios
- **Gestão Completa**:
  - Municípios por franqueado
  - Clientes vinculados a municípios
  - Upload e aprovação de vídeos
  - Criação de playlists
  - Gerenciamento de dispositivos TV
  - Logs de exibição
- **API REST Completa**: Pronta para integração com app de TV
- **Deploy-Ready**: Configurado para Railway com PostgreSQL

## 📋 Pré-requisitos

- Python 3.11+
- pip
- virtualenv (recomendado)

## 🔧 Instalação Local

### 1. Clone ou navegue até o diretório do projeto

```bash
cd c:\Users\marcos_dollis\Documents\web-mediaexpand
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

O arquivo `.env` já está criado com configurações de desenvolvimento. Para produção, copie `.env.example` e ajuste.

### 5. Execute as migrações

```bash
python manage.py migrate
```

### 6. Crie o usuário OWNER (Dono)

```bash
python manage.py create_owner
```

Siga as instruções e forneça:
- Username
- Email
- Nome e Sobrenome
- Senha

### 7. Colete arquivos estáticos (opcional para desenvolvimento)

```bash
python manage.py collectstatic --noinput
```

### 8. Inicie o servidor de desenvolvimento

```bash
python manage.py runserver
```

O sistema estará disponível em: `http://127.0.0.1:8000`

## 🔐 Acesso Inicial

### Admin Django
- URL: `http://127.0.0.1:8000/admin/`
- Login: Use as credenciais do OWNER criado

### API
- Base URL: `http://127.0.0.1:8000/api/`
- Autenticação: JWT Token

## 📡 Endpoints da API

### Autenticação

```
POST /api/token/
Body: {"username": "seu_usuario", "password": "sua_senha"}
Retorna: {"access": "token_jwt", "refresh": "refresh_token"}

POST /api/token/refresh/
Body: {"refresh": "refresh_token"}
Retorna: {"access": "novo_token_jwt"}
```

### Usuários

```
GET    /api/users/                    # Lista usuários (filtrado por permissão)
GET    /api/users/me/                 # Dados do usuário logado
GET    /api/users/{id}/               # Detalhes de um usuário
POST   /api/users/                    # Criar usuário
PUT    /api/users/{id}/               # Atualizar usuário
DELETE /api/users/{id}/               # Deletar usuário
GET    /api/users/franchisees/        # Lista franqueados (OWNER apenas)
```

### Municípios

```
GET    /api/municipios/               # Lista municípios
POST   /api/municipios/               # Criar município
GET    /api/municipios/{id}/          # Detalhes
PUT    /api/municipios/{id}/          # Atualizar
DELETE /api/municipios/{id}/          # Deletar
```

### Clientes

```
GET    /api/clientes/                 # Lista clientes
POST   /api/clientes/                 # Criar cliente (cria usuário junto)
GET    /api/clientes/{id}/            # Detalhes
PUT    /api/clientes/{id}/            # Atualizar
DELETE /api/clientes/{id}/            # Deletar
GET    /api/clientes/{id}/videos/     # Vídeos do cliente
```

### Vídeos

```
GET    /api/videos/                   # Lista vídeos
POST   /api/videos/                   # Upload de vídeo
GET    /api/videos/{id}/              # Detalhes
PUT    /api/videos/{id}/              # Atualizar
DELETE /api/videos/{id}/              # Deletar
POST   /api/videos/{id}/approve/      # Aprovar vídeo (Franqueado/Owner)
POST   /api/videos/{id}/reject/       # Rejeitar vídeo (Franqueado/Owner)
```

### Playlists

```
GET    /api/playlists/                # Lista playlists
POST   /api/playlists/                # Criar playlist
GET    /api/playlists/{id}/           # Detalhes
PUT    /api/playlists/{id}/           # Atualizar
DELETE /api/playlists/{id}/           # Deletar
POST   /api/playlists/{id}/add_video/ # Adicionar vídeo à playlist
DELETE /api/playlists/{id}/remove_video/ # Remover vídeo
POST   /api/playlists/{id}/reorder/   # Reordenar items
```

### Dispositivos TV

```
GET    /api/dispositivos/             # Lista dispositivos
POST   /api/dispositivos/             # Cadastrar dispositivo
GET    /api/dispositivos/{id}/        # Detalhes
PUT    /api/dispositivos/{id}/        # Atualizar
DELETE /api/dispositivos/{id}/        # Deletar
```

### API para TV App

```
POST   /api/tv/auth/
Body: {
  "identificador_unico": "UUID_DA_TV",
  "versao_app": "1.0.0"
}
Retorna: Playlist atual com URLs dos vídeos

POST   /api/tv/log-exibicao/
Body: {
  "dispositivo_id": 1,
  "video_id": 5,
  "playlist_id": 2,
  "data_hora_inicio": "2026-02-05T10:30:00Z",
  "data_hora_fim": "2026-02-05T10:30:30Z",
  "completamente_exibido": true
}
```

### Dashboard

```
GET    /api/dashboard/stats/          # Estatísticas do dashboard
```

## 📱 Integração com App de TV

O app de TV deve:

1. **Autenticar** fazendo POST em `/api/tv/auth/` com seu `identificador_unico`
2. **Receber** a playlist atual com todos os vídeos e URLs
3. **Reproduzir** os vídeos na ordem especificada
4. **Registrar** logs de exibição em `/api/tv/log-exibicao/`

### Exemplo de Resposta da API de TV:

```json
{
  "dispositivo_id": 1,
  "dispositivo_nome": "TV Shopping Center",
  "municipio": "São Paulo/SP",
  "playlist": {
    "id": 5,
    "nome": "Playlist Manhã",
    "duracao_total_segundos": 180,
    "videos": [
      {
        "id": 10,
        "titulo": "Propaganda Loja A",
        "arquivo_url": "http://localhost:8000/media/videos/cliente_5/video.mp4",
        "duracao_segundos": 30
      },
      {
        "id": 11,
        "titulo": "Propaganda Loja B",
        "arquivo_url": "http://localhost:8000/media/videos/cliente_6/video2.mp4",
        "duracao_segundos": 30
      }
    ]
  }
}
```

## 🚀 Deploy no Railway

### 1. Crie uma conta no Railway

Acesse [railway.app](https://railway.app) e faça login.

### 2. Crie um novo projeto

- Clique em "New Project"
- Selecione "Deploy from GitHub repo"
- Conecte seu repositório

### 3. Configure as variáveis de ambiente no Railway

No dashboard do Railway, adicione:

```
DEBUG=False
SECRET_KEY=sua-chave-secreta-super-forte-aqui
ALLOWED_HOSTS=*.railway.app,seu-dominio.com
```

O Railway automaticamente provê `DATABASE_URL` com PostgreSQL.

### 4. Adicione PostgreSQL

- No projeto Railway, clique em "New"
- Selecione "Database" > "Add PostgreSQL"
- O Railway conecta automaticamente

### 5. Deploy

O Railway detecta automaticamente o `Procfile` e faz o deploy.

### 6. Execute migrações (primeira vez)

No Railway CLI ou pela interface:

```bash
railway run python manage.py migrate
railway run python manage.py create_owner
```

## 📊 Estrutura do Banco de Dados

### Models Principais:

- **User**: Usuários do sistema (OWNER, FRANCHISEE, CLIENT)
- **Municipio**: Municípios gerenciados por franqueados
- **Cliente**: Perfil de cliente vinculado a usuário
- **Video**: Vídeos de propaganda dos clientes
- **Playlist**: Playlists de vídeos por município
- **PlaylistItem**: Vínculo entre playlist e vídeos
- **DispositivoTV**: Dispositivos onde as playlists são exibidas
- **LogExibicao**: Logs de reprodução dos vídeos

## 🔒 Segurança

- Senhas hasheadas com PBKDF2
- JWT para autenticação de API
- CORS configurável
- HTTPS forçado em produção
- Validação de uploads de arquivo
- Permissões granulares por nível de usuário

## 🛠️ Tecnologias Utilizadas

- **Framework**: Django 4.2.9
- **API**: Django REST Framework 3.14.0
- **Autenticação**: djangorestframework-simplejwt 5.3.1
- **CORS**: django-cors-headers 4.3.1
- **Banco Local**: SQLite3
- **Banco Produção**: PostgreSQL (via psycopg2-binary)
- **Servidor**: Gunicorn
- **Arquivos Estáticos**: WhiteNoise
- **Deploy**: Railway

## 📝 Fluxo de Trabalho

### Como OWNER:
1. Login no admin ou API
2. Criar franqueados (usuários com role=FRANCHISEE)
3. Visualizar todos os dados do sistema
4. Aprovar/rejeitar vídeos
5. Gerenciar qualquer recurso

### Como FRANCHISEE:
1. Login no sistema
2. Criar municípios sob sua responsabilidade
3. Criar clientes (cria usuário CLIENT automaticamente)
4. Vincular clientes a municípios
5. Aprovar/rejeitar vídeos dos clientes
6. Criar playlists para os municípios
7. Adicionar vídeos aprovados às playlists
8. Gerenciar dispositivos TV
9. Visualizar logs de exibição

### Como CLIENT:
1. Login no sistema
2. Upload de vídeos (ficam com status PENDING)
3. Aguardar aprovação do franqueado
4. Visualizar status dos vídeos
5. Ver estatísticas de exibição (quando implementado)

## 🐛 Troubleshooting

### Erro de migração
```bash
python manage.py migrate --run-syncdb
```

### Resetar banco de dados local
```bash
# Windows
del db.sqlite3
python manage.py migrate
python manage.py create_owner
```

### Problema com arquivos estáticos
```bash
python manage.py collectstatic --clear --noinput
```

## 📧 Suporte

Para problemas ou dúvidas sobre o sistema, entre em contato com o desenvolvedor.

## 📄 Licença

Projeto proprietário - Todos os direitos reservados.

---

**Desenvolvido para MediaExpand** - Sistema de Gerenciamento de Mídia Indoor