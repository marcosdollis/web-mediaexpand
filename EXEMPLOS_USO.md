# Exemplo de Criação de Dados via Admin ou Shell

Este documento mostra exemplos práticos de como criar dados no sistema.

## Via Django Shell

Abra o shell:
```bash
python manage.py shell
```

### Criar Franqueado

```python
from core.models import User

franqueado = User.objects.create_user(
    username='franqueado_sp',
    email='franqueado@email.com',
    password='senha123',
    first_name='João',
    last_name='Silva',
    role='FRANCHISEE',
    phone='(11) 98765-4321',
    cpf_cnpj='123.456.789-00'
)
```

### Criar Município

```python
from core.models import Municipio, User

franqueado = User.objects.get(username='franqueado_sp')

municipio = Municipio.objects.create(
    nome='São Paulo',
    estado='SP',
    franqueado=franqueado,
    ativo=True
)
```

### Criar Cliente (com usuário)

```python
from core.models import User, Cliente, Municipio

# Criar usuário
user_cliente = User.objects.create_user(
    username='cliente_loja1',
    email='loja1@email.com',
    password='senha123',
    first_name='Maria',
    last_name='Santos',
    role='CLIENT'
)

# Criar perfil de cliente
franqueado = User.objects.get(username='franqueado_sp')
municipio = Municipio.objects.get(nome='São Paulo')

cliente = Cliente.objects.create(
    user=user_cliente,
    empresa='Loja de Roupas Fashion',
    franqueado=franqueado,
    ativo=True
)

cliente.municipios.add(municipio)
```

### Criar Vídeo

```python
from core.models import Video, Cliente
from django.core.files import File

cliente = Cliente.objects.get(empresa='Loja de Roupas Fashion')

# Se você tem um arquivo de vídeo
with open('caminho/do/video.mp4', 'rb') as f:
    video = Video.objects.create(
        cliente=cliente,
        titulo='Promoção de Verão 2026',
        descricao='Promoção imperdível com até 50% de desconto',
        arquivo=File(f, name='promo_verao.mp4'),
        duracao_segundos=30,
        status='PENDING',
        ativo=True
    )

# Aprovar vídeo
video.status = 'APPROVED'
video.save()
```

### Criar Playlist

```python
from core.models import Playlist, Municipio, User

franqueado = User.objects.get(username='franqueado_sp')
municipio = Municipio.objects.get(nome='São Paulo')

playlist = Playlist.objects.create(
    nome='Playlist Manhã - Shopping',
    descricao='Playlist para horário da manhã (9h às 12h)',
    municipio=municipio,
    franqueado=franqueado,
    ativa=True
)
```

### Adicionar Vídeos à Playlist

```python
from core.models import Playlist, Video, PlaylistItem

playlist = Playlist.objects.get(nome='Playlist Manhã - Shopping')
video = Video.objects.get(titulo='Promoção de Verão 2026')

item = PlaylistItem.objects.create(
    playlist=playlist,
    video=video,
    ordem=1,
    repeticoes=2,  # Vídeo será exibido 2 vezes
    ativo=True
)

# Calcular duração total da playlist
playlist.calcular_duracao_total()
```

### Criar Dispositivo TV

```python
from core.models import DispositivoTV, Municipio, Playlist
import uuid

municipio = Municipio.objects.get(nome='São Paulo')
playlist = Playlist.objects.get(nome='Playlist Manhã - Shopping')

dispositivo = DispositivoTV.objects.create(
    nome='TV Shopping Center - Entrada',
    identificador_unico=str(uuid.uuid4()),  # Gera UUID único
    municipio=municipio,
    playlist_atual=playlist,
    localizacao='Shopping Center ABC - Entrada Principal',
    ativo=True
)

print(f"Identificador único: {dispositivo.identificador_unico}")
# Use este identificador no app de TV
```

## Via API REST (com cURL)

### 1. Obter Token JWT

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "seu_usuario_owner",
    "password": "sua_senha"
  }'
```

Salve o `access` token retornado.

### 2. Criar Franqueado

```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -d '{
    "username": "franqueado_rj",
    "email": "franqueado.rj@email.com",
    "password": "senha123",
    "first_name": "Pedro",
    "last_name": "Oliveira",
    "role": "FRANCHISEE",
    "phone": "(21) 98888-7777"
  }'
```

### 3. Criar Município

```bash
curl -X POST http://localhost:8000/api/municipios/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -d '{
    "nome": "Rio de Janeiro",
    "estado": "RJ",
    "franqueado": 2,
    "ativo": true
  }'
```

### 4. Criar Cliente

```bash
curl -X POST http://localhost:8000/api/clientes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -d '{
    "username": "cliente_restaurante",
    "email": "restaurante@email.com",
    "password": "senha123",
    "first_name": "Carlos",
    "last_name": "Mendes",
    "empresa": "Restaurante Sabor da Terra",
    "municipios": [1],
    "franqueado": 2,
    "ativo": true
  }'
```

### 5. Upload de Vídeo (Como Cliente)

```bash
# Primeiro, faça login como cliente
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "cliente_restaurante",
    "password": "senha123"
  }'

# Depois, faça upload do vídeo
curl -X POST http://localhost:8000/api/videos/ \
  -H "Authorization: Bearer TOKEN_DO_CLIENTE" \
  -F "titulo=Promoção Almoço Executivo" \
  -F "descricao=Almoço executivo por apenas R$ 25,00" \
  -F "arquivo=@caminho/do/video.mp4" \
  -F "duracao_segundos=30"
```

### 6. Aprovar Vídeo (Como Franqueado)

```bash
curl -X POST http://localhost:8000/api/videos/1/approve/ \
  -H "Authorization: Bearer TOKEN_DO_FRANQUEADO"
```

### 7. Criar Playlist

```bash
curl -X POST http://localhost:8000/api/playlists/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_DO_FRANQUEADO" \
  -d '{
    "nome": "Playlist Tarde - Centro",
    "descricao": "Playlist para horário da tarde",
    "municipio": 1,
    "ativa": true
  }'
```

### 8. Adicionar Vídeo à Playlist

```bash
curl -X POST http://localhost:8000/api/playlists/1/add_video/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_DO_FRANQUEADO" \
  -d '{
    "video_id": 1,
    "ordem": 1,
    "repeticoes": 2
  }'
```

## Via Admin Django

1. Acesse `http://localhost:8000/admin/`
2. Faça login com o usuário OWNER
3. Navegue pelos modelos e crie dados manualmente

### Ordem Recomendada:

1. **Usuários** → Criar Franqueados primeiro
2. **Municípios** → Criar municípios para cada franqueado
3. **Clientes** → Criar usuários CLIENT e seus perfis
4. **Vídeos** → Fazer upload e aprovar vídeos
5. **Playlists** → Criar playlists para os municípios
6. **Playlist Items** → Vincular vídeos às playlists
7. **Dispositivos TV** → Cadastrar TVs e associar playlists
8. **Logs de Exibição** → Serão criados automaticamente pelo app de TV

## Script Completo de Dados de Teste

Salve como `populate_test_data.py` na raiz do projeto:

```python
from django.contrib.auth import get_user_model
from core.models import *
import uuid

User = get_user_model()

def populate():
    # OWNER (já deve existir)
    owner = User.objects.filter(role='OWNER').first()
    
    # Franqueado
    franqueado, _ = User.objects.get_or_create(
        username='franqueado_sp',
        defaults={
            'email': 'franqueado.sp@mediaexpand.com',
            'first_name': 'João',
            'last_name': 'Silva',
            'role': 'FRANCHISEE',
            'phone': '(11) 98765-4321',
        }
    )
    franqueado.set_password('senha123')
    franqueado.save()
    
    # Município
    municipio, _ = Municipio.objects.get_or_create(
        nome='São Paulo',
        estado='SP',
        franqueado=franqueado
    )
    
    # Cliente
    user_cliente, _ = User.objects.get_or_create(
        username='cliente_loja1',
        defaults={
            'email': 'loja1@email.com',
            'first_name': 'Maria',
            'last_name': 'Santos',
            'role': 'CLIENT',
        }
    )
    user_cliente.set_password('senha123')
    user_cliente.save()
    
    cliente, _ = Cliente.objects.get_or_create(
        user=user_cliente,
        defaults={
            'empresa': 'Loja Fashion Center',
            'franqueado': franqueado,
        }
    )
    cliente.municipios.add(municipio)
    
    # Playlist
    playlist, _ = Playlist.objects.get_or_create(
        nome='Playlist Principal',
        defaults={
            'municipio': municipio,
            'franqueado': franqueado,
            'descricao': 'Playlist de testes',
        }
    )
    
    # Dispositivo
    dispositivo, _ = DispositivoTV.objects.get_or_create(
        identificador_unico='TV-TEST-001',
        defaults={
            'nome': 'TV Teste',
            'municipio': municipio,
            'playlist_atual': playlist,
            'localizacao': 'Local de teste',
        }
    )
    
    print("✅ Dados de teste criados com sucesso!")
    print(f"Franqueado: {franqueado.username} / senha123")
    print(f"Cliente: {user_cliente.username} / senha123")
    print(f"Dispositivo UUID: {dispositivo.identificador_unico}")

if __name__ == '__main__':
    populate()
```

Execute:
```bash
python manage.py shell < populate_test_data.py
```

Ou no shell:
```bash
python manage.py shell
>>> exec(open('populate_test_data.py').read())
```
