from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import models
from .models import (
    User, Municipio, Cliente, Video,
    Playlist, PlaylistItem, DispositivoTV, LogExibicao,
    ConteudoCorporativo, ConfiguracaoAPI
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'phone', 'cpf_cnpj', 'is_active_user', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserMinimalSerializer(serializers.ModelSerializer):
    """Serializer mínimo para listagens"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']


class MunicipioSerializer(serializers.ModelSerializer):
    franqueado_nome = serializers.CharField(source='franqueado.get_full_name', read_only=True)
    
    class Meta:
        model = Municipio
        fields = [
            'id', 'nome', 'estado', 'franqueado', 'franqueado_nome',
            'ativo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClienteSerializer(serializers.ModelSerializer):
    user_data = UserMinimalSerializer(source='user', read_only=True)
    franqueado_nome = serializers.CharField(source='franqueado.get_full_name', read_only=True)
    municipios_info = MunicipioSerializer(source='municipios', many=True, read_only=True)
    
    class Meta:
        model = Cliente
        fields = [
            'id', 'user', 'user_data', 'empresa', 'municipios', 'municipios_info',
            'franqueado', 'franqueado_nome', 'ativo', 'observacoes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClienteCreateSerializer(serializers.ModelSerializer):
    """Serializer para criar cliente com usuário junto"""
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Cliente
        fields = [
            'id', 'username', 'password', 'email', 'first_name', 'last_name',
            'empresa', 'municipios', 'franqueado', 'ativo', 'observacoes'
        ]
    
    def create(self, validated_data):
        # Extrai dados do usuário
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        # Cria o usuário
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='CLIENT'
        )
        
        # Cria o cliente
        municipios = validated_data.pop('municipios', [])
        cliente = Cliente.objects.create(user=user, **validated_data)
        cliente.municipios.set(municipios)
        
        return cliente


class VideoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='cliente.empresa', read_only=True)
    tamanho_mb = serializers.SerializerMethodField()
    arquivo_url = serializers.SerializerMethodField()
    qrcode_tracking_url = serializers.SerializerMethodField()
    qrcode_total_clicks = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'cliente', 'cliente_nome', 'titulo', 'descricao', 'arquivo',
            'arquivo_url', 'duracao_segundos', 'thumbnail', 'status', 'ativo',
            'tamanho_mb', 'qrcode_url_destino', 'qrcode_descricao',
            'qrcode_tracking_code', 'qrcode_tracking_url', 'qrcode_total_clicks',
            'texto_tarja',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'qrcode_tracking_code', 'created_at', 'updated_at']
    
    def get_tamanho_mb(self, obj):
        return obj.get_file_size()
    
    def get_arquivo_url(self, obj):
        if obj.arquivo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.arquivo.url)
        return None
    
    def get_qrcode_tracking_url(self, obj):
        """Retorna a URL de rastreamento completa para gerar o QR Code"""
        if obj.qrcode_url_destino:
            request = self.context.get('request')
            if request:
                tracking_url = request.build_absolute_uri(f'/r/{obj.qrcode_tracking_code}/')
                if 'railway.app' in tracking_url:
                    tracking_url = tracking_url.replace('http://', 'https://')
                return tracking_url
        return None
    
    def get_qrcode_total_clicks(self, obj):
        """Retorna o total de cliques no QR Code"""
        return obj.qrcode_clicks.count() if hasattr(obj, 'qrcode_clicks') else 0


class PlaylistItemSerializer(serializers.ModelSerializer):
    video_info = VideoSerializer(source='video', read_only=True)
    
    class Meta:
        model = PlaylistItem
        fields = [
            'id', 'playlist', 'video', 'video_info', 'ordem',
            'repeticoes', 'ativo', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PlaylistSerializer(serializers.ModelSerializer):
    franqueado_nome = serializers.CharField(source='franqueado.get_full_name', read_only=True)
    municipio_info = MunicipioSerializer(source='municipio', read_only=True)
    items_info = PlaylistItemSerializer(source='items', many=True, read_only=True)
    total_videos = serializers.SerializerMethodField()
    
    class Meta:
        model = Playlist
        fields = [
            'id', 'nome', 'descricao', 'municipio', 'municipio_info',
            'franqueado', 'franqueado_nome', 'ativa', 'duracao_total_segundos',
            'items_info', 'total_videos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_videos(self, obj):
        return obj.items.filter(ativo=True).count()


class DispositivoTVSerializer(serializers.ModelSerializer):
    municipio_info = MunicipioSerializer(source='municipio', read_only=True)
    playlist_info = PlaylistSerializer(source='playlist_atual', read_only=True)
    
    class Meta:
        model = DispositivoTV
        fields = [
            'id', 'nome', 'identificador_unico', 'municipio', 'municipio_info',
            'playlist_atual', 'playlist_info', 'localizacao', 'ativo',
            'ultima_sincronizacao', 'versao_app', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ultima_sincronizacao', 'created_at', 'updated_at']


class LogExibicaoSerializer(serializers.ModelSerializer):
    dispositivo_nome = serializers.CharField(source='dispositivo.nome', read_only=True)
    video_titulo = serializers.CharField(source='video.titulo', read_only=True)
    playlist_nome = serializers.CharField(source='playlist.nome', read_only=True)
    
    class Meta:
        model = LogExibicao
        fields = [
            'id', 'dispositivo', 'dispositivo_nome', 'video', 'video_titulo',
            'playlist', 'playlist_nome', 'data_hora_inicio', 'data_hora_fim',
            'completamente_exibido', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Serializers específicos para a API de TV
class PlaylistTVSerializer(serializers.ModelSerializer):
    """Serializer otimizado para o app de TV"""
    videos = serializers.SerializerMethodField()
    
    class Meta:
        model = Playlist
        fields = ['id', 'nome', 'duracao_total_segundos', 'videos']
    
    def _build_url(self, path):
        """Constrói URL absoluta e força HTTPS em produção"""
        url = self.context['request'].build_absolute_uri(path)
        if 'railway.app' in url:
            url = url.replace('http://', 'https://')
        return url

    def get_videos(self, obj):
        from django.urls import reverse

        items = obj.items.filter(ativo=True).select_related('video', 'conteudo_corporativo').order_by('ordem')
        result = []

        for item in items:
            # ── Conteúdo corporativo → HTML via WebView ──
            if item.conteudo_corporativo:
                cc = item.conteudo_corporativo
                if not cc.ativo:
                    continue

                # DESIGN type → renders via Fabric.js static canvas
                if cc.tipo == 'DESIGN':
                    html_path = reverse('design_render_tv', kwargs={'pk': cc.id})
                else:
                    html_path = reverse('tv-corporativo-html', kwargs={
                        'tipo': cc.tipo.lower(),
                        'playlist_id': obj.id,
                    })
                html_url = self._build_url(html_path)

                for _ in range(item.repeticoes):
                    result.append({
                        'id': 900000 + cc.id,
                        'titulo': cc.titulo,
                        'tipo': 'corporativo',
                        'subtipo': cc.tipo,
                        'duracao_segundos': cc.duracao_segundos,
                        'ativo': True,
                        'texto_tarja': None,
                        'qrcode': None,
                        'arquivo_url': html_url,
                    })
                continue

            # ── Vídeo normal ──
            if not item.video:
                continue
            video = item.video
            if not video.arquivo or not video.ativo:
                continue
            # Verificar visibilidade: APPROVED sempre, SCHEDULED se na janela de datas
            if not video.esta_visivel_nas_tvs:
                continue
                
            for _ in range(item.repeticoes):
                arquivo_url = self._build_url(video.arquivo.url)
                
                video_data = {
                    'id': video.id,
                    'tipo': 'video',
                    'titulo': video.titulo,
                    'arquivo_url': arquivo_url,
                    'duracao_segundos': video.duracao_segundos,
                    'ativo': video.ativo,
                    'texto_tarja': video.texto_tarja,
                }
                
                if video.qrcode_url_destino:
                    tracking_url = self._build_url(f'/r/{video.qrcode_tracking_code}/')
                    video_data['qrcode'] = {
                        'tracking_url': tracking_url,
                        'descricao': video.qrcode_descricao or '',
                    }
                else:
                    video_data['qrcode'] = None
                
                result.append(video_data)

        return result


class DispositivoTVAuthSerializer(serializers.Serializer):
    """Serializer para autenticação de dispositivos TV"""
    identificador_unico = serializers.CharField(max_length=100)
    versao_app = serializers.CharField(max_length=20, required=False)
