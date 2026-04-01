from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import os
import uuid
import json
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)


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
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'mkv', 'webm'])],
        blank=True,
        null=True,
    )
    url_externa = models.URLField(
        max_length=2000,
        blank=True,
        null=True,
        verbose_name='URL externa do vídeo',
        help_text='Link direto para o vídeo (ex: CDN, Instagram CDN) — substitui o upload de arquivo',
    )
    duracao_segundos = models.IntegerField(default=0, help_text='Duração em segundos')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    ORIENTACAO_CHOICES = [
        ('HORIZONTAL', 'Horizontal (16:9 — Paisagem)'),
        ('VERTICAL', 'Vertical (9:16 — Retrato)'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    ativo = models.BooleanField(default=True, db_index=True)
    orientacao = models.CharField(
        max_length=10,
        choices=ORIENTACAO_CHOICES,
        default='HORIZONTAL',
        verbose_name='Orientação',
        help_text='Horizontal (16:9) para vídeos gravados em paisagem; Vertical (9:16) para vídeos gravados em retrato (ex: iPhone na vertical)'
    )

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

    def save(self, *args, **kwargs):
        # Detecta se é upload novo ou troca de arquivo
        is_new = self._state.adding
        arquivo_mudou = False
        if not is_new and self.pk:
            try:
                old = Video.objects.only('arquivo').get(pk=self.pk)
                if old.arquivo.name != self.arquivo.name:
                    arquivo_mudou = True
            except Video.DoesNotExist:
                pass

        # Salva primeiro para ter o arquivo no disco
        super().save(*args, **kwargs)

        # Normaliza apenas quando há arquivo novo ou trocado
        if self.arquivo and (is_new or arquivo_mudou):
            self._normalizar_video()

    @staticmethod
    def _detectar_orientacao_video(caminho):
        """Usa ffprobe para detectar orientação real (considerando rotação do metadado).

        MOVs do iPhone gravam em landscape mas com metadado de rotação.
        ffprobe retorna as dimensões brutas do stream (ex: 3840×2160) e a rotação
        pode estar em dois lugares dependendo da versão do ffprobe e do codec:
          - stream.tags.rotate       (H.264, ffprobe antigo)
          - stream.side_data_list[]  (HEVC/H.265, ffprobe moderno — "Display Matrix")
        Sem tratar isso, detectamos HORIZONTAL por engano e o vídeo sai deitado.
        """
        import shutil
        import json as json_mod
        if not shutil.which('ffprobe'):
            return 'HORIZONTAL', 0, 0
        try:
            r = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_streams',
                 '-of', 'json', caminho],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json_mod.loads(r.stdout)
                stream = data.get('streams', [{}])[0]
                w = int(stream.get('width', 0))
                h = int(stream.get('height', 0))

                rotate = 0

                # 1) tags.rotate — presente em H.264 e alguns MOVs antigos
                try:
                    rotate = int(stream.get('tags', {}).get('rotate', 0))
                except (ValueError, TypeError):
                    rotate = 0

                # 2) side_data_list — usado em HEVC/H.265 (iPhone) com ffprobe moderno
                if rotate == 0:
                    for sd in stream.get('side_data_list', []):
                        if 'rotation' in sd:
                            try:
                                # Display Matrix usa negativo: -90 = 90° horário
                                rotate = abs(int(sd['rotation']))
                            except (ValueError, TypeError):
                                pass
                            break

                if rotate in (90, 270):
                    w, h = h, w  # trocar: dimensão real exibida é a transposta

                orient = 'VERTICAL' if h > w else 'HORIZONTAL'
                return orient, w, h
        except Exception:
            pass
        return 'HORIZONTAL', 0, 0

    @staticmethod
    def _calcular_scale_filter(w, h, orient):
        """1080p FireTV-safe (V6 validado): Main 4.0 + BT.709 + VBV + GOP 60 + mp42.
        scale + setsar=1 elimina anamorfismo; format=yuv420p garante bt.601 correto.
        """
        if orient == 'VERTICAL':
            return 'scale=1080:1920:flags=lanczos,format=yuv420p,setsar=1'
        else:
            return 'scale=1920:1080:flags=lanczos,format=yuv420p,setsar=1'

    def _normalizar_video(self):
        """Pipeline 1080p FireTV-safe (V6 validado em dispositivo real):

        - H.264 Main profile, Level 4.0
        - 1080×1920 (vertical) ou 1920×1080 (horizontal)
        - 5 Mbps VBV, GOP 60, BT.709, brand mp42 / tag avc1
        - map_metadata -1 remove rotate/clap/pasp/display matrix
        - setsar=1 + setdar implícito eliminam anamorfismo

        Compatível com storage local E Cloudflare R2 (S3):
        - Storage local: processa no disco, substitui arquivo in-place.
        - Storage remoto (R2): baixa para /tmp, processa, faz upload de volta.
        """
        import shutil, tempfile
        from django.core.files import File

        if not shutil.which('ffmpeg'):
            logger.warning('ffmpeg não encontrado — vídeo %s não normalizado', self.pk)
            return

        # ── 1. Obter input local (download do R2 se necessário) ──────────────
        tmp_input = None
        is_remote = False
        try:
            input_path = self.arquivo.path  # funciona para storage local
        except NotImplementedError:
            # Storage remoto (R2/S3) — baixar para /tmp
            is_remote = True
            ext = os.path.splitext(self.arquivo.name)[1] or '.mp4'
            fd, tmp_input = tempfile.mkstemp(suffix=ext, dir='/tmp')
            os.close(fd)
            with self.arquivo.open('rb') as src:
                with open(tmp_input, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
            input_path = tmp_input
        except (ValueError, OSError):
            return

        if not os.path.exists(input_path):
            logger.warning('Arquivo de entrada não encontrado para vídeo %s', self.pk)
            return

        # ── 2. Arquivo de output em /tmp ──────────────────────────────────────
        fd, tmp_output = tempfile.mkstemp(suffix='.mp4', dir='/tmp')
        os.close(fd)

        # Detectar orientação e resolução real do vídeo
        orient, orig_w, orig_h = self._detectar_orientacao_video(input_path)
        scale_filter = self._calcular_scale_filter(orig_w, orig_h, orient)

        # Bitrate 1080p — VBV calibrado para Fire TV (V6)
        bitrate = '5M'
        maxrate = '5M'
        bufsize = '10M'

        try:
            resultado = subprocess.run([
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', scale_filter,
                '-map_metadata', '-1',
                '-c:v', 'libx264',
                '-profile:v', 'main',
                '-level', '4.0',
                '-pix_fmt', 'yuv420p',
                '-r', '30',
                '-b:v', bitrate,
                '-maxrate', maxrate,
                '-bufsize', bufsize,
                '-g', '60',
                '-keyint_min', '60',
                '-preset', 'medium',
                '-color_range', 'tv',
                '-colorspace', 'bt709',
                '-color_primaries', 'bt709',
                '-color_trc', 'bt709',
                '-c:a', 'aac',
                '-b:a', '160k',
                '-ar', '44100',
                '-movflags', '+faststart',
                '-brand', 'mp42',
                '-tag:v', 'avc1',
                '-vsync', 'cfr',
                tmp_output
            ], capture_output=True, text=True, timeout=900)

            if resultado.returncode == 0 and os.path.getsize(tmp_output) > 0:
                if is_remote:
                    # ── Upload para R2, mesmo prefixo de path, forçando .mp4 ──
                    storage_name = os.path.splitext(self.arquivo.name)[0] + '.mp4'
                    try:
                        self.arquivo.storage.delete(self.arquivo.name)
                    except Exception:
                        pass
                    with open(tmp_output, 'rb') as f:
                        saved_name = self.arquivo.storage.save(storage_name, File(f))
                    Video.objects.filter(pk=self.pk).update(arquivo=saved_name, orientacao=orient)
                else:
                    # ── Local: substituir arquivo no disco ──
                    base = os.path.splitext(input_path)[0]
                    caminho_final = base + '.mp4'
                    if input_path != caminho_final:
                        try:
                            os.remove(input_path)
                        except OSError:
                            pass
                    os.replace(tmp_output, caminho_final)
                    from django.conf import settings
                    rel = os.path.relpath(caminho_final, settings.MEDIA_ROOT).replace('\\', '/')
                    Video.objects.filter(pk=self.pk).update(arquivo=rel, orientacao=orient)
                logger.info('Vídeo %s normalizado com sucesso (%s)', self.pk, orient)
            else:
                logger.error('ffmpeg falhou para vídeo %s: %s', self.pk, resultado.stderr[:500])

        except subprocess.TimeoutExpired:
            logger.error('ffmpeg timeout para vídeo %s', self.pk)
        except Exception as e:
            logger.error('Erro ao normalizar vídeo %s: %s', self.pk, e)
        finally:
            # Limpar temporários
            if tmp_input and os.path.exists(tmp_input):
                try:
                    os.remove(tmp_input)
                except OSError:
                    pass
            if os.path.exists(tmp_output):
                try:
                    os.remove(tmp_output)
                except OSError:
                    pass

    def get_file_size(self):
        """Retorna o tamanho do arquivo em MB (funciona com local e R2)"""
        if self.arquivo:
            try:
                return round(self.arquivo.size / (1024 * 1024), 2)
            except Exception:
                return 0
        return 0

    @property
    def file_size_bytes(self):
        """Retorna o tamanho do arquivo em bytes, ou 0 se não existir"""
        if self.arquivo:
            try:
                return self.arquivo.size
            except Exception:
                return 0
        return 0

    def arquivo_existe(self):
        """Verifica se o arquivo existe no storage (local ou R2)"""
        if self.url_externa:
            return True
        if not self.arquivo:
            return False
        try:
            # Storage local: usa os.path
            return os.path.exists(self.arquivo.path)
        except NotImplementedError:
            # Storage remoto (R2/S3): usa o método do storage
            try:
                return self.arquivo.storage.exists(self.arquivo.name)
            except Exception:
                return False
        except (ValueError, OSError):
            return False

    @property
    def extensao(self):
        """Retorna a extensão do arquivo (ex: .mp4, .mov, .avi)"""
        if self.arquivo and self.arquivo.name:
            return os.path.splitext(self.arquivo.name)[1].lower()
        return ''

    @property
    def extensao_class(self):
        """Retorna a classe CSS Bootstrap baseada na extensão do arquivo"""
        ext = self.extensao
        if ext == '.mp4':
            return 'success'
        elif ext in ('.mov', '.m4v'):
            return 'warning'
        else:
            return 'danger'

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
    franqueado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'FRANCHISEE'},
        related_name='dispositivos_franqueado',
        help_text='Franqueado responsável por este dispositivo. Permite transferir a gestão da TV ao franqueado sem alterar o município.',
    )
    alerta_desconexao_enviado = models.BooleanField(
        default=False,
        help_text='True quando o alerta de desconexão já foi enviado e o dispositivo continua offline.',
    )
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

    @property
    def esta_online(self):
        """True se o dispositivo enviou heartbeat nos últimos OFFLINE_THRESHOLD_MINUTES."""
        from django.utils import timezone
        from django.conf import settings as _s
        threshold = getattr(_s, 'DEVICE_OFFLINE_THRESHOLD_MINUTES', 10)
        if not self.ultima_sincronizacao:
            return False
        return (timezone.now() - self.ultima_sincronizacao).total_seconds() < threshold * 60

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

    def get_agendamentos_ativos_por_horario(self):
        """Igual a get_playlists_ativas_por_horario() mas retorna os objetos
        AgendamentoExibicao em vez de apenas as playlists, preservando o campo
        percentual para cálculo de composição proporcional.

        Retorna lista de AgendamentoExibicao na mesma ordem de prioridade.
        """
        agendamentos = self.agendamentos.filter(
            ativo=True,
            playlist__ativa=True,
        ).select_related('playlist')

        now = timezone.localtime(timezone.now())
        dia_semana = now.weekday()
        hora_atual = now.time()

        horario = []
        fulltime = []

        for ag in agendamentos:
            if not ag.playlist:
                continue
            dias = ag.dias_efetivos
            if ag.is_fulltime:
                if dia_semana in dias:
                    fulltime.append(ag)
            else:
                if dia_semana in dias and ag.hora_inicio <= hora_atual <= ag.hora_fim:
                    horario.append(ag)

        resultado = []
        if horario:
            resultado.extend(sorted(horario, key=lambda x: x.prioridade, reverse=True))
        if fulltime:
            resultado.extend(sorted(fulltime, key=lambda x: x.prioridade, reverse=True))

        if not resultado:
            # Fallback: playlist_atual sem percentual
            if self.playlist_atual:
                dummy = AgendamentoExibicao.__new__(AgendamentoExibicao)
                dummy.playlist = self.playlist_atual
                dummy.percentual = 100
                return [dummy]
            return []

        return resultado

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
    percentual = models.IntegerField(
        default=100,
        help_text=(
            'Percentual desta playlist na composição total (0-100). '
            'Ex: 80 = 80% dos slots para esta playlist. '
            'Se todos forem 0 ou houver apenas uma playlist, o comportamento é sequencial normal.'
        )
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


class LogExibicaoWebView(models.Model):
    """Log de exibição de conteúdo corporativo (WebView) nas TVs"""
    TIPO_CHOICES = [
        ('PREVISAO_TEMPO', 'Previsão do Tempo'),
        ('COTACOES', 'Cotações'),
        ('NOTICIAS', 'Notícias'),
        ('DESIGN', 'Design/Editor'),
    ]
    dispositivo = models.ForeignKey(DispositivoTV, on_delete=models.CASCADE, related_name='logs_webview')
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='logs_webview', null=True, blank=True)
    conteudo_corporativo = models.ForeignKey(
        'ConteudoCorporativo', on_delete=models.CASCADE,
        related_name='logs_webview', null=True, blank=True
    )
    tipo_conteudo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='DESIGN')
    titulo = models.CharField(max_length=200, default='Conteúdo Corporativo')
    duracao_segundos = models.IntegerField(default=0)
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField(null=True, blank=True)
    completamente_exibido = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log WebView'
        verbose_name_plural = 'Logs WebView'
        ordering = ['-data_hora_inicio']

    def __str__(self):
        return f"{self.titulo} - {self.dispositivo.nome} - {self.data_hora_inicio}"

    def duracao_exibicao_formatada(self):
        if not self.data_hora_fim:
            return "—"
        delta = self.data_hora_fim - self.data_hora_inicio
        segundos = int(delta.total_seconds())
        return f"{segundos // 60}:{segundos % 60:02d}"


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
    force_update = models.BooleanField(default=False, help_text='Forçar atualização — app exibe alerta obrigatório')
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
    franqueado = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'FRANCHISEE'},
        related_name='conteudos_corporativos',
        help_text='Franqueado dono deste conteúdo. Nulo = pertence ao owner. Templates (is_template=True) são visíveis a todos.',
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
    ORIENTACAO_CHOICES = [
        ('HORIZONTAL', 'Horizontal (16:9 — 1920×1080)'),
        ('VERTICAL', 'Vertical (9:16 — 1080×1920)'),
    ]
    orientacao = models.CharField(
        max_length=12,
        choices=ORIENTACAO_CHOICES,
        default='HORIZONTAL',
        help_text='Orientação de exibição na TV'
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


# ─────────────────────────────────────────────────────────────────────────────
#  CAMPANHAS  (cupom de desconto + futuros tipos)
# ─────────────────────────────────────────────────────────────────────────────

class Campanha(models.Model):
    """Campanha de marketing gerada pelo franqueado.

    Cada campanha produz um link/QR Code público. O tipo determina qual
    configuração complementar é necessária (ex: CampanhaCupomConfig).
    """

    TIPO_CHOICES = [
        ('CUPOM', 'Resgate de Cupom de Desconto'),
        ('ROLETA', 'Roleta de Prêmios'),
        ('CARTA', 'Virar a Carta'),
        ('ALERTA', 'Alerta Inteligente'),
        # Adicionar outros tipos aqui conforme necessário:
        # ('SORTEIO', 'Sorteio'),
        # ('PESQUISA', 'Pesquisa de Satisfação'),
    ]

    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('ATIVA', 'Ativa'),
        ('ENCERRADA', 'Encerrada'),
    ]

    franqueado = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='campanhas',
        limit_choices_to={'role': 'FRANCHISEE'},
        verbose_name='Franqueado',
    )
    nome = models.CharField(max_length=200, verbose_name='Nome da Campanha')
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default='CUPOM',
        verbose_name='Tipo de Campanha',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RASCUNHO',
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text='Identificador único da URL pública desta campanha.',
    )
    data_fim = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data/Hora de Encerramento',
        help_text='Deixe em branco para campanha sem prazo definido.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Campanha'
        verbose_name_plural = 'Campanhas'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    @property
    def is_ativa(self):
        if self.status == 'ENCERRADA':
            return False
        if self.data_fim and timezone.now() > self.data_fim:
            return False
        return self.status == 'ATIVA'

    @property
    def expirada(self):
        return bool(self.data_fim and timezone.now() > self.data_fim)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('campanha_landing', kwargs={'token': str(self.token)})


class CampanhaCupomConfig(models.Model):
    """Configuração específica para campanhas do tipo CUPOM."""

    MODO_CHOICES = [
        ('SEM_LEAD', 'Sem captura de dados — exibir código direto'),
        ('CODIGO_UNICO', 'Código único para todos'),
        ('CODIGO_POR_CLIENTE', 'Código individual por cliente (gerado na hora)'),
    ]

    campanha = models.OneToOneField(
        Campanha,
        on_delete=models.CASCADE,
        related_name='config_cupom',
    )

    # ── Código ────────────────────────────────────────────────────────────────
    modo_codigo = models.CharField(
        max_length=25,
        choices=MODO_CHOICES,
        default='CODIGO_UNICO',
        verbose_name='Modo de Código',
    )
    codigo_unico = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Código do Cupom',
        help_text='Código que será exibido a todos os usuários (modo Código Único).',
    )
    prefixo_codigo = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Prefixo dos Códigos',
        help_text='Prefixo para os códigos individuais gerados. Ex: "PROMO" → PROMO-A1B2.',
    )

    # ── Captura de leads ──────────────────────────────────────────────────────
    capturar_nome = models.BooleanField(default=False, verbose_name='Capturar Nome')
    capturar_cpf = models.BooleanField(default=False, verbose_name='Capturar CPF')
    capturar_telefone = models.BooleanField(default=False, verbose_name='Capturar Telefone')
    capturar_endereco = models.BooleanField(default=False, verbose_name='Capturar Endereço')

    # ── Landing page ──────────────────────────────────────────────────────────
    titulo_pagina = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Título da Página',
        help_text='Deixe em branco para usar o nome da campanha.',
    )
    descricao_pagina = models.TextField(
        blank=True,
        verbose_name='Descrição / Instrução',
        help_text='Texto exibido na landing page antes do formulário.',
    )
    cor_primaria = models.CharField(
        max_length=7,
        default='#0d6efd',
        verbose_name='Cor Principal (hex)',
    )

    class Meta:
        verbose_name = 'Configuração de Cupom'

    def __str__(self):
        return f"Config cupom – {self.campanha.nome}"

    @property
    def captura_algum_dado(self):
        return any([self.capturar_nome, self.capturar_cpf,
                    self.capturar_telefone, self.capturar_endereco])


class CampanhaLead(models.Model):
    """Registro de resgaste/lead gerado por uma campanha."""

    campanha = models.ForeignKey(
        Campanha,
        on_delete=models.CASCADE,
        related_name='leads',
    )
    # Dados do cliente (preenchidos apenas quando captura está ativa)
    nome = models.CharField(max_length=200, blank=True)
    cpf = models.CharField(max_length=14, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField(max_length=400, blank=True)
    # Código entregue ao cliente
    codigo_cupom = models.CharField(max_length=100, blank=True)
    # Metadados
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lead de Campanha'
        verbose_name_plural = 'Leads de Campanha'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Lead #{self.pk} – {self.campanha.nome}"


# ─────────────────────────────────────────────────────────────────────────────
#  ROLETA DE PRÊMIOS
# ─────────────────────────────────────────────────────────────────────────────


class CampanhaRoletaConfig(models.Model):
    """Configurações gerais da Roleta de Prêmios."""

    campanha = models.OneToOneField(
        Campanha, on_delete=models.CASCADE, related_name='config_roleta'
    )
    # ── Controle de jogadas ────────────────────────────────────────────────
    max_jogadas_por_ip_por_dia = models.PositiveIntegerField(
        default=1,
        verbose_name='Máx. jogadas por IP por dia',
        help_text='0 = ilimitado por dia',
    )
    max_jogadas_total_por_ip = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Máx. jogadas total por IP',
        help_text='Deixe em branco para sem limite absoluto.',
    )
    # ── Captura de lead pós-prêmio ────────────────────────────────────────
    capturar_nome     = models.BooleanField(default=True,  verbose_name='Capturar Nome')
    capturar_cpf      = models.BooleanField(default=False, verbose_name='Capturar CPF')
    capturar_telefone = models.BooleanField(default=True,  verbose_name='Capturar Telefone')
    capturar_endereco = models.BooleanField(default=False, verbose_name='Capturar Endereço')
    # ── Aparência ──────────────────────────────────────────────────────────
    titulo_pagina    = models.CharField(max_length=200, blank=True, verbose_name='Título da Página')
    descricao_pagina = models.TextField(blank=True, verbose_name='Instruções para o participante')
    cor_primaria     = models.CharField(max_length=7, default='#e63946', verbose_name='Cor Principal')
    texto_botao_girar = models.CharField(
        max_length=50, default='GIRAR!',
        verbose_name='Texto do botão de girar',
    )
    texto_sem_premio = models.CharField(
        max_length=150, default='Não foi desta vez! Tente novamente.',
        verbose_name='Mensagem de consolação',
        help_text='Exibida quando o participante cai num segmento perdedor.',
    )

    class Meta:
        verbose_name = 'Config. Roleta'

    def __str__(self):
        return f'Config roleta – {self.campanha.nome}'

    @property
    def captura_algum_dado(self):
        return any([self.capturar_nome, self.capturar_cpf,
                    self.capturar_telefone, self.capturar_endereco])


class CampanhaRoletaPremio(models.Model):
    """Um prêmio (segmento) da roleta."""

    campanha = models.ForeignKey(
        Campanha, on_delete=models.CASCADE, related_name='premios_roleta'
    )
    nome = models.CharField(max_length=200, verbose_name='Nome do Prêmio')
    descricao = models.CharField(max_length=400, blank=True, verbose_name='Descrição')
    codigo_resgate = models.CharField(
        max_length=100, blank=True,
        verbose_name='Código de Resgate',
        help_text='Código ou instrução entregue ao ganhador (opcional).',
    )
    peso = models.PositiveIntegerField(
        default=10,
        verbose_name='Peso de Probabilidade',
        help_text='Quanto maior o peso, mais chance de sair.',
    )
    quantidade_maxima = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Qtd. Máxima de Ganhadores',
        help_text='Deixe em branco para ilimitado.',
    )
    cor = models.CharField(max_length=7, default='#f4a261', verbose_name='Cor do Segmento')
    emoji = models.CharField(max_length=10, blank=True, default='🎁', verbose_name='Emoji')
    eh_perdedor = models.BooleanField(
        default=False,
        verbose_name='É Segmento Perdedor?',
        help_text='Se marcado, o participante não ganha prêmio ao cair aqui.',
    )
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0, verbose_name='Ordem na roleta')

    class Meta:
        verbose_name = 'Prêmio da Roleta'
        verbose_name_plural = 'Prêmios da Roleta'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'{self.nome} (peso {self.peso})'

    @property
    def total_ganhos(self):
        return self.jogadas.filter(ganhou=True).count()

    @property
    def esgotado(self):
        if not self.quantidade_maxima:
            return False
        return self.total_ganhos >= self.quantidade_maxima


class CampanhaJogada(models.Model):
    """Registro de cada jogada na roleta."""

    campanha = models.ForeignKey(
        Campanha, on_delete=models.CASCADE, related_name='jogadas'
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    premio = models.ForeignKey(
        CampanhaRoletaPremio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='jogadas',
    )
    ganhou = models.BooleanField(default=False)
    # Lead preenchido após ganhar (opcional)
    nome     = models.CharField(max_length=200, blank=True)
    cpf      = models.CharField(max_length=14,  blank=True)
    telefone = models.CharField(max_length=20,  blank=True)
    endereco = models.CharField(max_length=400, blank=True)
    lead_salvo = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Jogada'
        verbose_name_plural = 'Jogadas'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Jogada #{self.pk} – {self.campanha.nome} – {"Ganhou" if self.ganhou else "Não ganhou"}'


# ─────────────────────────────────────────────────────────────────────────────
#  VIRAR A CARTA
# ─────────────────────────────────────────────────────────────────────────────


class CampanhaCartaConfig(models.Model):
    """Configurações da campanha Virar a Carta."""

    campanha = models.OneToOneField(
        Campanha, on_delete=models.CASCADE, related_name='config_carta'
    )
    # ── Controle de jogadas ───────────────────────────────────────────────
    max_jogadas_por_ip_por_dia = models.PositiveIntegerField(
        default=1, verbose_name='Máx. jogadas por IP por dia',
        help_text='0 = ilimitado por dia',
    )
    max_jogadas_total_por_ip = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Máx. jogadas total por IP',
        help_text='Deixe em branco para sem limite absoluto.',
    )
    # ── Captura de lead pós-prêmio ──────────────────────────────────────
    capturar_nome     = models.BooleanField(default=True,  verbose_name='Capturar Nome')
    capturar_cpf      = models.BooleanField(default=False, verbose_name='Capturar CPF')
    capturar_telefone = models.BooleanField(default=True,  verbose_name='Capturar Telefone')
    capturar_endereco = models.BooleanField(default=False, verbose_name='Capturar Endereço')
    # ── Aparência ──────────────────────────────────────────────────────
    titulo_pagina    = models.CharField(max_length=200, blank=True, verbose_name='Título da Página')
    descricao_pagina = models.TextField(blank=True, verbose_name='Instruções')
    cor_primaria     = models.CharField(max_length=7, default='#1a1a2e', verbose_name='Cor de Fundo da Página')
    cor_verso_carta  = models.CharField(max_length=7, default='#16213e', verbose_name='Cor do Verso da Carta')
    cor_frente_carta = models.CharField(max_length=7, default='#e63946', verbose_name='Cor da Frente da Carta')
    texto_verso_carta = models.CharField(
        max_length=100, default='Vire a carta!',
        verbose_name='Texto no verso da carta',
    )
    texto_botao_virar = models.CharField(
        max_length=50, default='Virar a Carta!',
        verbose_name='Texto do botão',
    )
    texto_sem_premio = models.CharField(
        max_length=150, default='Não foi desta vez! Tente novamente.',
        verbose_name='Mensagem de consolação',
    )
    logo = models.ImageField(
        upload_to='campanhas/logos/',
        null=True, blank=True,
        verbose_name='Logo da empresa (verso da carta)',
        help_text='Opcional. Se não informado, exibe padrão de cartas.',
    )

    class Meta:
        verbose_name = 'Config. Carta'

    def __str__(self):
        return f'Config carta – {self.campanha.nome}'

    @property
    def captura_algum_dado(self):
        return any([self.capturar_nome, self.capturar_cpf,
                    self.capturar_telefone, self.capturar_endereco])


# ─────────────────────────────────────────────────────────────────────────────
#  ALERTA INTELIGENTE
# ─────────────────────────────────────────────────────────────────────────────


class CampanhaAlertaConfig(models.Model):
    """É a configuração-header da campanha Alerta Inteligente.

    Permite que o franqueado (ex: imobiliária) personalize
    título, instruções e aparência da página pública.
    Os campos dinâmicos ficam em CampanhaAlertaCampo.
    """

    campanha = models.OneToOneField(
        Campanha, on_delete=models.CASCADE, related_name='config_alerta'
    )
    titulo_pagina = models.CharField(
        max_length=200, blank=True,
        verbose_name='Título da Página Pública',
        help_text='Deixe em branco para usar o nome da campanha.',
    )
    subtitulo_pagina = models.CharField(
        max_length=300, blank=True,
        verbose_name='Subtítulo / Texto de Conversão',
        help_text='Frase que motiva o visitante a preencher o formulário.',
    )
    descricao_pagina = models.TextField(
        blank=True,
        verbose_name='Descrição / Instruções',
        help_text='Texto exibido abaixo do título antes do formulário.',
    )
    mensagem_sucesso = models.CharField(
        max_length=400,
        default='Seu alerta foi cadastrado! Entraremos em contato assim que encontrarmos o que você procura.',
        verbose_name='Mensagem de Sucesso',
    )
    # Contato da empresa
    whatsapp_contato = models.CharField(
        max_length=20, blank=True,
        verbose_name='WhatsApp para Contato',
        help_text='Número no formato 5511999990000. Exibido após o envio.',
    )
    # Aparência
    cor_primaria = models.CharField(
        max_length=7, default='#1a1a2e',
        verbose_name='Cor Principal (hex)',
    )
    cor_destaque = models.CharField(
        max_length=7, default='#e63946',
        verbose_name='Cor de Destaque (hex)',
    )
    logo = models.ImageField(
        upload_to='campanhas/logos/', null=True, blank=True,
        verbose_name='Logo da empresa',
    )
    # Campos sempre fixos de contato
    capturar_nome     = models.BooleanField(default=True,  verbose_name='Capturar Nome')
    capturar_telefone = models.BooleanField(default=True,  verbose_name='Capturar Telefone')
    capturar_email    = models.BooleanField(default=False, verbose_name='Capturar E-mail')

    class Meta:
        verbose_name = 'Config. Alerta Inteligente'

    def __str__(self):
        return f'Config alerta – {self.campanha.nome}'


class CampanhaAlertaCampo(models.Model):
    """Campo dinâmico criado pelo franqueado para coletar informações
    específicas do impu00f3vel ou interesse do potencial cliente.
    """

    TIPO_CHOICES = [
        ('TEXTO',       'Texto livre'),
        ('NUMERO',      'Número inteiro'),
        ('MOEDA',       'Valor monetário (R$)'),
        ('SELECT',      'Seleção única (lista)'),
        ('MULTISELECT', 'Seleção múltipla'),
        ('BOOLEAN',     'Pergunta Sim/Não'),
    ]

    campanha = models.ForeignKey(
        Campanha, on_delete=models.CASCADE, related_name='campos_alerta',
    )
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default='TEXTO')
    rotulo = models.CharField(
        max_length=200, verbose_name='Rótulo do Campo',
        help_text='Pergunta exibida ao visitante. Ex: “Qual tipo de imóvel você procura?”',
    )
    placeholder = models.CharField(
        max_length=200, blank=True, verbose_name='Placeholder / Dica',
        help_text='Texto de dica dentro do campo (opcional).',
    )
    opcoes = models.TextField(
        blank=True, verbose_name='Opções (uma por linha)',
        help_text='Para tipo SELECT ou MULTISELECT: coloque uma opção por linha.',
    )
    obrigatorio = models.BooleanField(default=False, verbose_name='Obrigatório?')
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0, verbose_name='Ordem de Exibição')

    class Meta:
        verbose_name = 'Campo do Alerta'
        verbose_name_plural = 'Campos do Alerta'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.rotulo}'

    def get_opcoes_list(self):
        """Retorna as opções como lista limpa."""
        return [o.strip() for o in self.opcoes.splitlines() if o.strip()]


class CampanhaAlertaLead(models.Model):
    """Lead capturado por uma campanha do tipo Alerta Inteligente.
    Os dados dinâmicos ficam no JSONField `respostas`.
    """

    campanha = models.ForeignKey(
        Campanha, on_delete=models.CASCADE, related_name='leads_alerta',
    )
    # Dados de contato fixos
    nome     = models.CharField(max_length=200, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email    = models.EmailField(blank=True)
    # Respostas dinâmicas: {"campo_id": "valor", ...}
    respostas = models.JSONField(default=dict, blank=True)
    # Metadados
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lead de Alerta'
        verbose_name_plural = 'Leads de Alerta'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Lead Alerta #{self.pk} – {self.nome or self.telefone} – {self.campanha.nome}'

    def get_respostas_display(self, campos_qs=None):
        """Retorna lista de (rótulo, valor) para exibição."""
        resultado = []
        campos = campos_qs or self.campanha.campos_alerta.filter(ativo=True)
        for campo in campos:
            valor = self.respostas.get(str(campo.pk), '')
            if isinstance(valor, list):
                valor = ', '.join(valor)
            resultado.append((campo.rotulo, valor))
        return resultado
