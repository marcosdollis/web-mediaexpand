from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
import os
import uuid
import json


class User(AbstractUser):
    """
    Modelo customizado de usuário com hierarquia:
    - OWNER (Dono): Acesso total
    - FRANCHISEE (Franqueado): Gerencia municípios e clientes
    - CLIENT (Cliente): Upload de vídeos e visualização
    """
    ROLE_CHOICES = [
        ('OWNER', 'Dono'),
        ('FRANCHISEE', 'Franqueado'),
        ('CLIENT', 'Cliente'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CLIENT')
    phone = models.CharField(max_length=20, blank=True, null=True)
    cpf_cnpj = models.CharField(max_length=18, blank=True, null=True, unique=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )
    is_active_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def is_owner(self):
        return self.role == 'OWNER'
    
    def is_franchisee(self):
        return self.role == 'FRANCHISEE'
    
    def is_client(self):
        return self.role == 'CLIENT'


class Municipio(models.Model):
    """Município onde o franqueado opera"""
    nome = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    franqueado = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'FRANCHISEE'},
        related_name='municipios'
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text='Latitude do município (ex: -23.550520)'
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text='Longitude do município (ex: -46.633308)'
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'
        ordering = ['estado', 'nome']
        unique_together = ['nome', 'estado', 'franqueado']
    
    def __str__(self):
        return f"{self.nome}/{self.estado}"


class Segmento(models.Model):
    """Segmento de negócio do cliente"""
    nome = models.CharField(max_length=100, unique=True, verbose_name='Nome do Segmento')
    descricao = models.TextField(blank=True, null=True, verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Segmento'
        verbose_name_plural = 'Segmentos'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Cliente(models.Model):
    """Cliente que terá vídeos exibidos"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente_profile')
    empresa = models.CharField(max_length=200)
    segmento = models.ForeignKey(Segmento, on_delete=models.PROTECT, related_name='clientes', verbose_name='Segmento')
    municipios = models.ManyToManyField(Municipio, related_name='clientes')
    franqueado = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'FRANCHISEE'},
        related_name='clientes_franqueado',
        null=True,
        blank=True
    )
    contrato = models.FileField(upload_to='contratos/', null=True, blank=True, verbose_name='Contrato')
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']
        # Garante que só pode haver uma empresa por segmento por município
        # Esta constraint será adicionada via código na view
    
    def __str__(self):
        return f"{self.empresa} - {self.segmento.nome}"
    
    @property
    def contrato_size_bytes(self):
        """Retorna o tamanho do contrato em bytes, ou 0 se não existir"""
        if self.contrato and os.path.exists(self.contrato.path):
            try:
                return self.contrato.size
            except (OSError, ValueError):
                return 0
        return 0


def video_upload_path(instance, filename):
    """Organiza uploads de vídeo por cliente"""
    return f'videos/cliente_{instance.cliente.id}/{filename}'


class Video(models.Model):
    """Vídeos de propaganda dos clientes"""
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('APPROVED', 'Aprovado'),
        ('REJECTED', 'Rejeitado'),
        ('SCHEDULED', 'Agendado'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='videos')
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    arquivo = models.FileField(
        upload_to=video_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'mkv', 'webm'])]
    )
    duracao_segundos = models.IntegerField(default=0, help_text='Duração em segundos')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    ativo = models.BooleanField(default=True, db_index=True)
    
    # Campos de agendamento de publicação
    data_publicacao = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Data de publicação',
        help_text='Quando status=Agendado, o vídeo só aparece nas TVs a partir desta data/hora'
    )
    data_expiracao = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Data de expiração',
        help_text='O vídeo deixa de aparecer nas TVs após esta data/hora (vazio = sem expiração)'
    )
    
    # QR Code para rastreamento de conversão
    qrcode_url_destino = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL de destino do QR Code',
        help_text='Link para onde o QR Code redirecionará (ex: site do cliente, Instagram, promoção)'
    )
    qrcode_descricao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Descrição do QR Code',
        help_text='Texto exibido junto ao QR Code (ex: "Resgate seu desconto!", "Acesse nosso site")'
    )
    qrcode_tracking_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name='Código de rastreamento',
        help_text='Código único para rastrear acessos via QR Code'
    )
    
    # Tarja inferior estilo CNN
    texto_tarja = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name='Texto da Tarja Inferior',
        help_text='Texto exibido em tarja na parte inferior da tela durante o vídeo (estilo CNN). Ex: "Faça um storie com #media123 e ganhe um desconto!"'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Vídeo'
        verbose_name_plural = 'Vídeos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.titulo} - {self.cliente.empresa}"
    
    def get_file_size(self):
        """Retorna o tamanho do arquivo em MB"""
        if self.arquivo and os.path.exists(self.arquivo.path):
            try:
                return round(self.arquivo.size / (1024 * 1024), 2)
            except (OSError, ValueError):
                return 0
        return 0
    
    @property
    def file_size_bytes(self):
        """Retorna o tamanho do arquivo em bytes, ou 0 se não existir"""
        if self.arquivo and os.path.exists(self.arquivo.path):
            try:
                return self.arquivo.size
            except (OSError, ValueError):
                return 0
        return 0
    
    def arquivo_existe(self):
        """Verifica se o arquivo físico existe no sistema de arquivos"""
        if not self.arquivo:
            return False
        try:
            return os.path.exists(self.arquivo.path)
        except (ValueError, OSError):
            return False

    @property
    def esta_visivel_nas_tvs(self):
        """
        Retorna True se o vídeo deve aparecer nas TVs agora.
        - APPROVED: sempre visível (se ativo)
        - SCHEDULED: visível somente se data_publicacao <= now <= data_expiracao
        - PENDING/REJECTED: nunca visível
        """
        if not self.ativo:
            return False
        if self.status == 'APPROVED':
            return True
        if self.status == 'SCHEDULED':
            from django.utils import timezone
            now = timezone.now()
            if self.data_publicacao and now < self.data_publicacao:
                return False
            if self.data_expiracao and now > self.data_expiracao:
                return False
            # Se tem data_publicacao e já passou, está visível
            if self.data_publicacao:
                return True
        return False

    @property
    def status_publicacao_display(self):
        """Status legível para agendamento de publicação"""
        if self.status != 'SCHEDULED':
            return self.get_status_display()
        from django.utils import timezone
        now = timezone.now()
        if self.data_publicacao and now < self.data_publicacao:
            return 'Agendado'
        if self.data_expiracao and now > self.data_expiracao:
            return 'Expirado'
        return 'Em exibição'

    @property
    def status_publicacao_badge(self):
        """Classe CSS do badge para agendamento"""
        s = self.status_publicacao_display
        return {
            'Agendado': 'info',
            'Em exibição': 'success',
            'Expirado': 'secondary',
            'Pendente': 'warning',
            'Aprovado': 'success',
            'Rejeitado': 'danger',
        }.get(s, 'secondary')


class Playlist(models.Model):
    """Playlist de vídeos para exibição nos municípios"""
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name='playlists')
    franqueado = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'FRANCHISEE'},
        related_name='playlists',
        null=True,
        blank=True
    )
    ativa = models.BooleanField(default=True, db_index=True)
    duracao_total_segundos = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Playlist'
        verbose_name_plural = 'Playlists'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nome} - {self.municipio}"
    
    def calcular_duracao_total(self):
        """Calcula a duração total da playlist"""
        total = self.items.filter(ativo=True).aggregate(
            total=models.Sum('video__duracao_segundos')
        )['total'] or 0
        self.duracao_total_segundos = total
        self.save(update_fields=['duracao_total_segundos'])
        return total
    
    @property
    def duracao_total_formatada(self):
        """Retorna a duração total formatada em MM:SS"""
        if not self.duracao_total_segundos:
            return "0:00"
        minutos = int(self.duracao_total_segundos // 60)
        segundos = int(self.duracao_total_segundos % 60)
        return f"{minutos}:{segundos:02d}"
    
    @property
    def total_videos(self):
        """Retorna o total de vídeos na playlist"""
        return self.items.count()
    
    @property
    def total_dispositivos(self):
        """Retorna o total de dispositivos usando esta playlist"""
        return self.dispositivos.count()


class PlaylistItem(models.Model):
    """Item de uma playlist (vínculo entre playlist e vídeo OU conteúdo corporativo)"""
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='playlist_items', null=True, blank=True)
    conteudo_corporativo = models.ForeignKey(
        'ConteudoCorporativo', on_delete=models.CASCADE,
        related_name='playlist_items', null=True, blank=True
    )
    ordem = models.IntegerField(default=0)
    repeticoes = models.IntegerField(default=1, help_text='Quantas vezes o item será exibido')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Item da Playlist'
        verbose_name_plural = 'Itens das Playlists'
        ordering = ['playlist', 'ordem']
    
    def __str__(self):
        label = self.video.titulo if self.video else (self.conteudo_corporativo.titulo if self.conteudo_corporativo else '?')
        return f"{self.playlist.nome} - {label} (Ordem: {self.ordem})"

    @property
    def is_corporativo(self):
        return self.conteudo_corporativo_id is not None

    @property
    def titulo_display(self):
        if self.video:
            return self.video.titulo
        if self.conteudo_corporativo:
            return self.conteudo_corporativo.titulo
        return '—'

    @property
    def duracao_display(self):
        if self.video:
            return self.video.duracao_segundos
        if self.conteudo_corporativo:
            return self.conteudo_corporativo.duracao_segundos
        return 0


class DispositivoTV(models.Model):
    """Dispositivos de TV que executarão as playlists"""
    nome = models.CharField(max_length=200)
    identificador_unico = models.CharField(max_length=100, unique=True, help_text='UUID ou código único da TV')
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name='dispositivos')
    playlist_atual = models.ForeignKey(
        Playlist,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispositivos'
    )
    localizacao = models.CharField(max_length=300, blank=True, null=True, help_text='Endereço ou local da TV')
    publico_estimado_mes = models.IntegerField(
        default=0,
        help_text='Estimativa de pessoas que visualizarão os anúncios por mês'
    )
    ativo = models.BooleanField(default=True, db_index=True)
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    versao_app = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Dispositivo TV'
        verbose_name_plural = 'Dispositivos TV'
        ordering = ['municipio', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {self.municipio}"
    
    def esta_no_horario_exibicao(self):
        """
        Verifica se o dispositivo deve estar ligado agora baseado nos
        HorarioFuncionamento cadastrados. Se não há nenhum, está sempre ligado.
        """
        from django.utils import timezone

        horarios = self.horarios_funcionamento.filter(ativo=True)
        if not horarios.exists():
            return True  # sem horário de funcionamento = 24/7

        now = timezone.localtime(timezone.now())
        dia_semana = now.weekday()
        hora_atual = now.time()

        for h in horarios:
            dias = h.dias_semana if h.dias_semana else list(range(7))
            if dia_semana in dias and h.hora_inicio <= hora_atual <= h.hora_fim:
                return True

        return False

    @property
    def tem_horario_funcionamento(self):
        """Retorna True se o dispositivo tem horários de funcionamento definidos"""
        return self.horarios_funcionamento.filter(ativo=True).exists()

    def get_playlists_ativas_por_horario(self):
        """
        Retorna TODAS as playlists que devem ser exibidas agora.
        Lógica:
        - Playlists 24/7 estão SEMPRE no merge (base contínua)
        - Playlists com horário específico são ADICIONADAS quando dentro do horário
        
        Exemplo:
        - Playlist A: 24/7
        - Playlist B: 24/7
        - Playlist C: 12:30-13:30
        
        Resultado:
        - Fora de 12:30-13:30: [A, B]
        - Durante 12:30-13:30: [C, A, B] (horário específico + 24/7)
        """
        from django.utils import timezone

        agendamentos = self.agendamentos.filter(ativo=True).select_related('playlist')
        if not agendamentos.exists():
            return [self.playlist_atual] if self.playlist_atual else []

        now = timezone.localtime(timezone.now())
        dia_semana = now.weekday()
        hora_atual = now.time()

        agendamentos_horario = []
        agendamentos_fulltime = []

        for ag in agendamentos:
            if not ag.playlist or not ag.playlist.ativa:
                continue

            dias = ag.dias_efetivos

            if ag.is_fulltime:
                # Playlist 24/7 - sempre incluída
                if dia_semana in dias:
                    agendamentos_fulltime.append(ag)
            else:
                # Playlist com horário específico - só incluída se bater o horário
                if dia_semana in dias and ag.hora_inicio <= hora_atual <= ag.hora_fim:
                    agendamentos_horario.append(ag)

        # Monta lista de playlists ativas
        playlists_ativas = []

        # 1. Adiciona playlists de horário específico (se houver e estiver no horário)
        if agendamentos_horario:
            agendamentos_horario.sort(key=lambda x: x.prioridade, reverse=True)
            playlists_ativas.extend([ag.playlist for ag in agendamentos_horario])

        # 2. SEMPRE adiciona as playlists 24/7 (base contínua)
        if agendamentos_fulltime:
            agendamentos_fulltime.sort(key=lambda x: x.prioridade, reverse=True)
            playlists_ativas.extend([ag.playlist for ag in agendamentos_fulltime])

        # 3. Fallback: se não tem nenhuma, usa playlist_atual
        if not playlists_ativas:
            return [self.playlist_atual] if self.playlist_atual else []

        return playlists_ativas

    def get_playlist_atual_por_horario(self):
        """
        Retorna a playlist que deve ser exibida agora (apenas uma).
        Mantido por compatibilidade. Use get_playlists_ativas_por_horario() para múltiplas.
        """
        playlists = self.get_playlists_ativas_por_horario()
        return playlists[0] if playlists else None

    def status_conexao(self):
        """
        Retorna o status real de conexão baseado no consumo da API:
          - 'transmitindo': app consumiu a API nos últimos 10 min e está no horário de exibição
          - 'fora_horario': app consumiu a API recentemente mas fora do horário agendado
          - 'desconectado': nenhum consumo de API nos últimos 10 min (ou nunca)
        """
        from django.utils import timezone
        import datetime

        if not self.ultima_sincronizacao:
            return 'desconectado'

        delta = timezone.now() - self.ultima_sincronizacao
        if delta.total_seconds() > 600:  # 10 minutos sem consumo
            return 'desconectado'

        # App está ativo — verificar se está no horário de exibição
        if self.esta_no_horario_exibicao():
            return 'transmitindo'
        return 'fora_horario'

    def status_conexao_display(self):
        """Retorna rótulo legível para o status de conexão"""
        labels = {
            'transmitindo': 'Transmitindo',
            'fora_horario': 'Fora do Horário',
            'desconectado': 'Desconectado',
        }
        return labels.get(self.status_conexao(), 'Desconectado')


class AgendamentoExibicao(models.Model):
    """
    Vinculação Dispositivo → Playlist com agendamento opcional.
    Se hora_inicio/hora_fim forem nulos, a playlist roda 24/7.
    Permite N playlists por dispositivo, cada uma com horário próprio.
    """
    DIAS_SEMANA_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    dispositivo = models.ForeignKey(DispositivoTV, on_delete=models.CASCADE, related_name='agendamentos')
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE,
        null=True, related_name='agendamentos',
        help_text='Playlist a ser exibida neste dispositivo'
    )
    nome = models.CharField(
        max_length=200, blank=True,
        help_text='Nome descritivo (opcional — gerado automaticamente se vazio)'
    )
    dias_semana = models.JSONField(
        default=list,
        help_text='Dias da semana: 0=Seg..6=Dom. Vazio = todos os dias.'
    )
    hora_inicio = models.TimeField(
        null=True, blank=True,
        help_text='Hora de início (vazio = 24h)'
    )
    hora_fim = models.TimeField(
        null=True, blank=True,
        help_text='Hora de término (vazio = 24h)'
    )
    prioridade = models.IntegerField(
        default=0,
        help_text='Prioridade (maior = maior prioridade). Usado para resolver conflitos.'
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Playlist Vinculada'
        verbose_name_plural = 'Playlists Vinculadas'
        ordering = ['dispositivo', '-prioridade', 'hora_inicio']
    
    def __str__(self):
        nome = self.nome or self.playlist.nome
        if self.hora_inicio and self.hora_fim:
            return f"{nome} ({self.hora_inicio.strftime('%H:%M')}-{self.hora_fim.strftime('%H:%M')})"
        return f"{nome} (24/7)"

    def save(self, *args, **kwargs):
        if not self.nome:
            self.nome = self.playlist.nome if self.playlist else ''
        super().save(*args, **kwargs)

    @property
    def is_fulltime(self):
        """Retorna True se roda 24/7 (sem horário definido)"""
        return not self.hora_inicio and not self.hora_fim

    @property
    def dias_efetivos(self):
        """Retorna dias_semana ou todos os dias se vazio"""
        return self.dias_semana if self.dias_semana else list(range(7))
    
    def get_dias_display(self):
        """Retorna os dias da semana em formato legível"""
        dias = self.dias_efetivos
        if len(dias) == 7:
            return "Todos os dias"
        if not dias:
            return "Todos os dias"
        dias_nomes = [self.DIAS_SEMANA_CHOICES[dia][1] for dia in sorted(dias)]
        return ', '.join(dias_nomes)

    def get_horario_display(self):
        """Retorna o horário em formato legível"""
        if self.is_fulltime:
            return "24 horas"
        return f"{self.hora_inicio.strftime('%H:%M')} até {self.hora_fim.strftime('%H:%M')}"


class HorarioFuncionamento(models.Model):
    """
    Horários de funcionamento (ligar/desligar) de um dispositivo TV.
    Permite N faixas de horário por dispositivo.
    Ex: Seg-Sex 08:00-17:00, Sáb 09:00-13:00
    Fora dos horários cadastrados, a TV simula estar desligada (tela preta).
    Se nenhum horário for cadastrado, a TV fica ligada 24h.
    """
    DIAS_SEMANA_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    dispositivo = models.ForeignKey(
        DispositivoTV, on_delete=models.CASCADE,
        related_name='horarios_funcionamento'
    )
    nome = models.CharField(
        max_length=200, blank=True,
        help_text='Nome descritivo (ex: Horário Comercial, Sábado)'
    )
    dias_semana = models.JSONField(
        default=list,
        help_text='Dias da semana: 0=Seg..6=Dom. Vazio = todos os dias.'
    )
    hora_inicio = models.TimeField(help_text='Hora que a TV liga')
    hora_fim = models.TimeField(help_text='Hora que a TV desliga')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Horário de Funcionamento'
        verbose_name_plural = 'Horários de Funcionamento'
        ordering = ['dispositivo', 'hora_inicio']

    def __str__(self):
        return f"{self.nome or 'Horário'} ({self.hora_inicio.strftime('%H:%M')}-{self.hora_fim.strftime('%H:%M')})"

    def save(self, *args, **kwargs):
        if not self.nome:
            self.nome = f"{self.hora_inicio.strftime('%H:%M')}-{self.hora_fim.strftime('%H:%M')}"
        super().save(*args, **kwargs)

    def get_dias_display(self):
        dias = self.dias_semana if self.dias_semana else list(range(7))
        if len(dias) == 7 or not dias:
            return "Todos os dias"
        nomes = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        return ', '.join(nomes[d] for d in sorted(dias))

    def get_horario_display(self):
        return f"{self.hora_inicio.strftime('%H:%M')} até {self.hora_fim.strftime('%H:%M')}"


class LogExibicao(models.Model):
    """Log de exibições de vídeos nas TVs"""
    dispositivo = models.ForeignKey(DispositivoTV, on_delete=models.CASCADE, related_name='logs_exibicao')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='logs_exibicao')
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='logs_exibicao')
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField(null=True, blank=True)
    completamente_exibido = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Exibição'
        verbose_name_plural = 'Logs de Exibição'
        ordering = ['-data_hora_inicio']
    
    def __str__(self):
        return f"{self.video.titulo} - {self.dispositivo.nome} - {self.data_hora_inicio}"
    
    def duracao_exibicao_segundos(self):
        """Retorna a duração da exibição em segundos"""
        if not self.data_hora_fim:
            return 0
        delta = self.data_hora_fim - self.data_hora_inicio
        return int(delta.total_seconds())
    
    def duracao_exibicao_formatada(self):
        """Retorna a duração formatada em MM:SS"""
        segundos = self.duracao_exibicao_segundos()
        if segundos == 0:
            return "0:00"
        minutos = segundos // 60
        segs = segundos % 60
        return f"{minutos}:{segs:02d}"


class AppVersion(models.Model):
    """Versões do aplicativo Android para download"""
    versao = models.CharField(max_length=20, unique=True, help_text='Ex: 1.0.0, 1.2.5')
    arquivo_apk = models.FileField(
        upload_to='app_versions/',
        validators=[FileExtensionValidator(allowed_extensions=['apk'])],
        help_text='Arquivo APK do aplicativo'
    )
    tamanho = models.BigIntegerField(help_text='Tamanho do arquivo em bytes', editable=False)
    notas_versao = models.TextField(blank=True, help_text='Descrição das mudanças nesta versão')
    ativo = models.BooleanField(default=True, help_text='Versão disponível para download')
    downloads = models.IntegerField(default=0, editable=False, help_text='Número de downloads')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='app_versions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Versão do App'
        verbose_name_plural = 'Versões do App'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"MediaExpand TV v{self.versao}"
    
    def save(self, *args, **kwargs):
        # Obter tamanho do arquivo antes de salvar
        if self.arquivo_apk:
            try:
                # Durante upload, arquivo_apk.size está disponível
                self.tamanho = self.arquivo_apk.size
            except (OSError, ValueError, AttributeError):
                self.tamanho = 0
        super().save(*args, **kwargs)
    
    def get_tamanho_formatado(self):
        """Retorna o tamanho formatado em MB"""
        return f"{self.tamanho / (1024 * 1024):.2f} MB"
    
    @classmethod
    def get_versao_ativa(cls):
        """Retorna a versão ativa mais recente"""
        return cls.objects.filter(ativo=True).first()


class QRCodeClick(models.Model):
    """Registro de cliques/acessos via QR Code para rastreamento de conversão"""
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='qrcode_clicks')
    tracking_code = models.UUIDField(db_index=True, help_text='Código de rastreamento do vídeo')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    referer = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Clique QR Code'
        verbose_name_plural = 'Cliques QR Code'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Click em {self.video.titulo} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class ConteudoCorporativo(models.Model):
    """
    Conteúdo estilo TV corporativa que pode ser adicionado a playlists.
    Funciona como um 'vídeo virtual' — o app renderiza o conteúdo em vez de reproduzir um arquivo.
    """
    TIPO_CHOICES = [
        ('PREVISAO_TEMPO', 'Previsão do Tempo'),
        ('COTACOES', 'Cotações (Moedas, Cripto, Commodities)'),
        ('NOTICIAS', 'Notícias'),
        ('DESIGN', 'Design Personalizado'),
    ]

    titulo = models.CharField(max_length=200, help_text='Nome de exibição do conteúdo')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    duracao_segundos = models.IntegerField(
        default=15,
        help_text='Tempo de exibição na tela (segundos)'
    )
    # Campos para Design Personalizado (Fabric.js)
    design_json = models.JSONField(
        null=True, blank=True,
        help_text='JSON do canvas Fabric.js com todos os elementos do design'
    )
    design_thumbnail = models.ImageField(
        upload_to='designs/thumbnails/',
        null=True, blank=True,
        help_text='Thumbnail PNG gerada pelo editor'
    )
    design_largura = models.IntegerField(
        default=1920,
        help_text='Largura do design em pixels'
    )
    design_altura = models.IntegerField(
        default=1080,
        help_text='Altura do design em pixels'
    )
    is_template = models.BooleanField(
        default=False,
        help_text='Se marcado, aparece na galeria de modelos para reutilização'
    )
    
    # Configurações de Cotações (quais exibir)
    cotacoes_moedas = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos de moedas para exibir (ex: ["USD", "EUR", "GBP"])'
    )
    cotacoes_cripto = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos de criptomoedas para exibir (ex: ["BTC", "ETH"])'
    )
    cotacoes_commodities = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos de commodities para exibir (ex: ["gold", "oil"])'
    )
    template_categoria = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Categoria do template (ex: Promoção, Institucional, Menu...)'
    )
    ativo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conteúdo Corporativo'
        verbose_name_plural = 'Conteúdos Corporativos'
        ordering = ['tipo', 'titulo']

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"

    def get_icone(self):
        icones = {
            'PREVISAO_TEMPO': 'fas fa-cloud-sun',
            'COTACOES': 'fas fa-chart-line',
            'NOTICIAS': 'fas fa-newspaper',
            'DESIGN': 'fas fa-palette',
        }
        return icones.get(self.tipo, 'fas fa-tv')

    def get_cor_badge(self):
        cores = {
            'PREVISAO_TEMPO': 'info',
            'COTACOES': 'success',
            'NOTICIAS': 'warning',
            'DESIGN': 'purple',
        }
        return cores.get(self.tipo, 'secondary')


class ConfiguracaoAPI(models.Model):
    """
    Configurações globais para as APIs externas (singleton).
    Controla chaves de API e limites de requisições por dia.
    """
    # Previsão do tempo - Open-Meteo (grátis, sem chave)
    weather_max_requests_dia = models.IntegerField(
        default=100,
        help_text='Máximo de requisições/dia para API de previsão do tempo (Open-Meteo, grátis)'
    )
    weather_requests_hoje = models.IntegerField(default=0)
    weather_ultimo_reset = models.DateField(auto_now_add=True)

    # Cotações - AwesomeAPI (grátis, sem chave)
    cotacoes_max_requests_dia = models.IntegerField(
        default=100,
        help_text='Máximo de requisições/dia para API de cotações (AwesomeAPI, grátis)'
    )
    cotacoes_requests_hoje = models.IntegerField(default=0)
    cotacoes_ultimo_reset = models.DateField(auto_now_add=True)

    # Notícias - NewsAPI
    noticias_api_key = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Chave da API NewsAPI.org (grátis até 100 req/dia)'
    )
    noticias_max_requests_dia = models.IntegerField(
        default=50,
        help_text='Máximo de requisições/dia para API de notícias'
    )
    noticias_requests_hoje = models.IntegerField(default=0)
    noticias_ultimo_reset = models.DateField(auto_now_add=True)

    # Cache (minutos)
    cache_weather_minutos = models.IntegerField(
        default=30,
        help_text='Tempo de cache para previsão do tempo (minutos)'
    )
    cache_cotacoes_minutos = models.IntegerField(
        default=15,
        help_text='Tempo de cache para cotações (minutos)'
    )
    cache_noticias_minutos = models.IntegerField(
        default=60,
        help_text='Tempo de cache para notícias (minutos)'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de API'
        verbose_name_plural = 'Configurações de API'

    def __str__(self):
        return 'Configurações de APIs Externas'

    def save(self, *args, **kwargs):
        # Singleton – força pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def resetar_contadores_se_necessario(self):
        """Reseta contadores diários se o dia mudou"""
        from django.utils import timezone
        hoje = timezone.localdate()
        changed = False
        if self.weather_ultimo_reset != hoje:
            self.weather_requests_hoje = 0
            self.weather_ultimo_reset = hoje
            changed = True
        if self.cotacoes_ultimo_reset != hoje:
            self.cotacoes_requests_hoje = 0
            self.cotacoes_ultimo_reset = hoje
            changed = True
        if self.noticias_ultimo_reset != hoje:
            self.noticias_requests_hoje = 0
            self.noticias_ultimo_reset = hoje
            changed = True
        if changed:
            self.save()

    def pode_requisitar(self, tipo):
        """Verifica se ainda pode fazer requisição para o tipo dado"""
        self.resetar_contadores_se_necessario()
        if tipo == 'PREVISAO_TEMPO':
            return self.weather_requests_hoje < self.weather_max_requests_dia
        elif tipo == 'COTACOES':
            return self.cotacoes_requests_hoje < self.cotacoes_max_requests_dia
        elif tipo == 'NOTICIAS':
            return self.noticias_requests_hoje < self.noticias_max_requests_dia
        return False

    def registrar_requisicao(self, tipo):
        """Incrementa o contador de requisições"""
        if tipo == 'PREVISAO_TEMPO':
            self.weather_requests_hoje += 1
        elif tipo == 'COTACOES':
            self.cotacoes_requests_hoje += 1
        elif tipo == 'NOTICIAS':
            self.noticias_requests_hoje += 1
        self.save(update_fields=[self._get_counter_field(tipo), 'updated_at'])

    def _get_counter_field(self, tipo):
        fields = {
            'PREVISAO_TEMPO': 'weather_requests_hoje',
            'COTACOES': 'cotacoes_requests_hoje',
            'NOTICIAS': 'noticias_requests_hoje',
        }
        return fields.get(tipo, 'weather_requests_hoje')
