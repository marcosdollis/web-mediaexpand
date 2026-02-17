from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
import os


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    ativo = models.BooleanField(default=True)
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
    ativa = models.BooleanField(default=True)
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
        total = sum([item.video.duracao_segundos for item in self.items.all() if item.video.duracao_segundos])
        self.duracao_total_segundos = total
        self.save()
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
    """Item de uma playlist (vínculo entre playlist e vídeo)"""
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='playlist_items')
    ordem = models.IntegerField(default=0)
    repeticoes = models.IntegerField(default=1, help_text='Quantas vezes o vídeo será exibido')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Item da Playlist'
        verbose_name_plural = 'Itens das Playlists'
        ordering = ['playlist', 'ordem']
        unique_together = ['playlist', 'video']
    
    def __str__(self):
        return f"{self.playlist.nome} - {self.video.titulo} (Ordem: {self.ordem})"


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
    ativo = models.BooleanField(default=True)
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
        """Verifica se o dispositivo deve estar exibindo agora baseado nos agendamentos"""
        from django.utils import timezone
        import datetime
        
        # Se não tiver agendamentos, sempre exibe
        agendamentos = self.agendamentos.filter(ativo=True)
        if not agendamentos.exists():
            return True
        
        now = timezone.localtime(timezone.now())
        dia_semana = now.weekday()  # 0=segunda, 6=domingo
        hora_atual = now.time()
        
        # Verificar se algum agendamento permite exibição agora
        for agendamento in agendamentos:
            if dia_semana in agendamento.dias_semana:
                if agendamento.hora_inicio <= hora_atual <= agendamento.hora_fim:
                    return True
        
        return False


class AgendamentoExibicao(models.Model):
    """Agendamento de horários de exibição para dispositivos"""
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
    nome = models.CharField(max_length=200, help_text='Nome descritivo do agendamento')
    dias_semana = models.JSONField(
        default=list,
        help_text='Lista de dias da semana: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom'
    )
    hora_inicio = models.TimeField(help_text='Hora de início da exibição')
    hora_fim = models.TimeField(help_text='Hora de término da exibição')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Agendamento de Exibição'
        verbose_name_plural = 'Agendamentos de Exibição'
        ordering = ['dispositivo', 'hora_inicio']
    
    def __str__(self):
        dias_str = ', '.join([self.DIAS_SEMANA_CHOICES[dia][1][:3] for dia in sorted(self.dias_semana)])
        return f"{self.nome} - {dias_str} ({self.hora_inicio.strftime('%H:%M')} - {self.hora_fim.strftime('%H:%M')})"
    
    def get_dias_display(self):
        """Retorna os dias da semana em formato legível"""
        if not self.dias_semana:
            return "Nenhum dia"
        dias_nomes = [self.DIAS_SEMANA_CHOICES[dia][1] for dia in sorted(self.dias_semana)]
        return ', '.join(dias_nomes)


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
