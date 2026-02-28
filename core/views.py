from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.db import models
from .models import (
    User, Municipio, Cliente, Video,
    Playlist, PlaylistItem, DispositivoTV, LogExibicao, Segmento, AppVersion,
    QRCodeClick, AgendamentoExibicao, ConteudoCorporativo, ConfiguracaoAPI,
    HorarioFuncionamento
)
from .serializers import (
    UserSerializer, UserMinimalSerializer, MunicipioSerializer,
    ClienteSerializer, ClienteCreateSerializer, VideoSerializer,
    PlaylistSerializer, PlaylistItemSerializer, DispositivoTVSerializer,
    LogExibicaoSerializer, PlaylistTVSerializer, DispositivoTVAuthSerializer
)
from .permissions import (
    IsOwner, IsFranchiseeOrOwner, IsClientOrAbove,
    IsOwnerOfObject, CanManageClients, CanManagePlaylists, CanManageVideos
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar usuários
    - OWNER: vê todos
    - FRANCHISEE: vê seus clientes
    - CLIENT: vê apenas a si mesmo
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        qs = User.objects.all()
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(
                Q(id=user.id) | Q(created_by=user) | Q(cliente_profile__franqueado=user)
            ).distinct()
        else:
            return qs.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Retorna dados do usuário logado"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsFranchiseeOrOwner])
    def franchisees(self, request):
        """Lista todos os franqueados (apenas para OWNER)"""
        franchisees = User.objects.filter(role='FRANCHISEE')
        serializer = UserMinimalSerializer(franchisees, many=True)
        return Response(serializer.data)


class MunicipioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar municípios
    Apenas franqueados e dono podem gerenciar
    """
    queryset = Municipio.objects.select_related('franqueado').all()
    serializer_class = MunicipioSerializer
    permission_classes = [IsFranchiseeOrOwner]
    
    def get_queryset(self):
        user = self.request.user
        qs = Municipio.objects.select_related('franqueado')
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(franqueado=user)
        return Municipio.objects.none()
    
    def perform_create(self, serializer):
        """Ao criar, define o franqueado automaticamente se não for owner"""
        if self.request.user.is_franchisee():
            serializer.save(franqueado=self.request.user)
        else:
            serializer.save()


class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar clientes
    """
    queryset = Cliente.objects.select_related('user', 'franqueado', 'segmento').all()
    permission_classes = [CanManageClients]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ClienteCreateSerializer
        return ClienteSerializer
    
    def get_queryset(self):
        user = self.request.user
        qs = Cliente.objects.select_related('user', 'franqueado', 'segmento').prefetch_related('municipios')
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(franqueado=user)
        return Cliente.objects.none()
    
    def perform_create(self, serializer):
        """Ao criar, define o franqueado automaticamente se não for owner"""
        if self.request.user.is_franchisee():
            serializer.save(franqueado=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['get'])
    def videos(self, request, pk=None):
        """Lista vídeos de um cliente específico"""
        cliente = self.get_object()
        videos = Video.objects.filter(cliente=cliente)
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)


class VideoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar vídeos
    """
    queryset = Video.objects.select_related('cliente', 'cliente__user').all()
    serializer_class = VideoSerializer
    permission_classes = [CanManageVideos, IsOwnerOfObject]
    
    def get_queryset(self):
        user = self.request.user
        qs = Video.objects.select_related('cliente', 'cliente__user', 'cliente__segmento')
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(cliente__franqueado=user)
        elif user.is_client():
            try:
                cliente = user.cliente_profile
                return qs.filter(cliente=cliente)
            except Cliente.DoesNotExist:
                return Video.objects.none()
        return Video.objects.none()
    
    def perform_create(self, serializer):
        """Cliente cria vídeo para si mesmo"""
        user = self.request.user
        if user.is_client():
            try:
                cliente = user.cliente_profile
                serializer.save(cliente=cliente)
            except Cliente.DoesNotExist:
                raise serializers.ValidationError("Usuário não possui perfil de cliente")
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsFranchiseeOrOwner])
    def approve(self, request, pk=None):
        """Aprova um vídeo"""
        video = self.get_object()
        video.status = 'APPROVED'
        video.save()
        return Response({'status': 'vídeo aprovado'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsFranchiseeOrOwner])
    def reject(self, request, pk=None):
        """Rejeita um vídeo"""
        video = self.get_object()
        video.status = 'REJECTED'
        video.save()
        return Response({'status': 'vídeo rejeitado'})


class PlaylistViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar playlists
    """
    queryset = Playlist.objects.select_related('municipio', 'franqueado').all()
    serializer_class = PlaylistSerializer
    permission_classes = [CanManagePlaylists, IsOwnerOfObject]
    
    def get_queryset(self):
        user = self.request.user
        qs = Playlist.objects.select_related('municipio', 'franqueado').prefetch_related(
            'items__video'
        )
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(franqueado=user)
        return Playlist.objects.none()
    
    def perform_create(self, serializer):
        """Ao criar, define o franqueado automaticamente se não for owner"""
        if self.request.user.is_franchisee():
            serializer.save(franqueado=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def add_video(self, request, pk=None):
        """Adiciona um vídeo à playlist"""
        playlist = self.get_object()
        video_id = request.data.get('video_id')
        ordem = request.data.get('ordem', 0)
        repeticoes = request.data.get('repeticoes', 1)
        
        try:
            video = Video.objects.get(id=video_id, status='APPROVED')
        except Video.DoesNotExist:
            return Response(
                {'error': 'Vídeo não encontrado ou não aprovado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        item, created = PlaylistItem.objects.get_or_create(
            playlist=playlist,
            video=video,
            defaults={'ordem': ordem, 'repeticoes': repeticoes}
        )
        
        if not created:
            item.ordem = ordem
            item.repeticoes = repeticoes
            item.save()
        
        playlist.calcular_duracao_total()
        
        serializer = PlaylistItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_video(self, request, pk=None):
        """Remove um vídeo da playlist"""
        playlist = self.get_object()
        video_id = request.data.get('video_id')
        
        try:
            item = PlaylistItem.objects.get(playlist=playlist, video_id=video_id)
            item.delete()
            playlist.calcular_duracao_total()
            return Response({'status': 'vídeo removido da playlist'})
        except PlaylistItem.DoesNotExist:
            return Response(
                {'error': 'Vídeo não encontrado na playlist'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Reordena itens da playlist"""
        playlist = self.get_object()
        items_order = request.data.get('items', [])  # Lista de {id, ordem}
        
        for item_data in items_order:
            try:
                item = PlaylistItem.objects.get(id=item_data['id'], playlist=playlist)
                item.ordem = item_data['ordem']
                item.save()
            except PlaylistItem.DoesNotExist:
                continue
        
        return Response({'status': 'playlist reordenada'})


class PlaylistItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar itens de playlist
    """
    queryset = PlaylistItem.objects.select_related('playlist', 'video').all()
    serializer_class = PlaylistItemSerializer
    permission_classes = [CanManagePlaylists]
    
    def get_queryset(self):
        user = self.request.user
        qs = PlaylistItem.objects.select_related('playlist', 'video', 'video__cliente')
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(playlist__franqueado=user)
        return PlaylistItem.objects.none()


class DispositivoTVViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar dispositivos de TV
    """
    queryset = DispositivoTV.objects.select_related('municipio', 'playlist_atual').all()
    serializer_class = DispositivoTVSerializer
    permission_classes = [IsFranchiseeOrOwner]
    
    def get_queryset(self):
        user = self.request.user
        qs = DispositivoTV.objects.select_related('municipio', 'municipio__franqueado', 'playlist_atual')
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(municipio__franqueado=user)
        return DispositivoTV.objects.none()


class LogExibicaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para logs de exibição (somente leitura para usuários)
    """
    queryset = LogExibicao.objects.select_related('dispositivo', 'video', 'playlist').all()
    serializer_class = LogExibicaoSerializer
    permission_classes = [IsFranchiseeOrOwner]
    http_method_names = ['get', 'post']  # Apenas leitura e criação
    
    def get_queryset(self):
        user = self.request.user
        qs = LogExibicao.objects.select_related('dispositivo', 'video', 'playlist')
        if user.is_owner():
            return qs
        elif user.is_franchisee():
            return qs.filter(dispositivo__municipio__franqueado=user)
        return LogExibicao.objects.none()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estatísticas de exibição"""
        queryset = self.get_queryset()
        stats = {
            'total_exibicoes': queryset.count(),
            'exibicoes_completas': queryset.filter(completamente_exibido=True).count(),
            'videos_mais_exibidos': queryset.values('video__titulo').annotate(
                total=Count('id')
            ).order_by('-total')[:10]
        }
        return Response(stats)


# API específica para o App de TV
class TVAPIView(APIView):
    """
    API para o app de TV se autenticar e buscar playlist
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Autenticação de dispositivo e retorno da playlist"""
        serializer = DispositivoTVAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        identificador = serializer.validated_data['identificador_unico']
        versao_app = serializer.validated_data.get('versao_app', '')
        
        try:
            dispositivo = DispositivoTV.objects.get(
                identificador_unico=identificador,
                ativo=True
            )
            
            # Atualiza última sincronização
            dispositivo.ultima_sincronizacao = timezone.now()
            if versao_app:
                dispositivo.versao_app = versao_app
            dispositivo.save()
            
            # Retorna TODAS as playlists ativas no horário atual mescladas
            playlists_ativas = dispositivo.get_playlists_ativas_por_horario()
            
            if playlists_ativas:
                # Mescla todos os vídeos de todas as playlists em uma única lista
                all_videos = []
                playlist_ids = []
                playlist_names = []
                
                for playlist in playlists_ativas:
                    if not playlist.ativa:
                        continue
                    playlist_ids.append(playlist.id)
                    playlist_names.append(playlist.nome)
                    
                    # Serializa os vídeos desta playlist
                    serializer = PlaylistTVSerializer(
                        playlist,
                        context={'request': request}
                    )
                    videos = serializer.data.get('videos', [])
                    all_videos.extend(videos)
                
                # Retorna uma "mega-playlist" com todos os vídeos em sequência
                return Response({
                    'dispositivo_id': dispositivo.id,
                    'dispositivo_nome': dispositivo.nome,
                    'municipio': str(dispositivo.municipio),
                    'playlist': {
                        'id': playlist_ids[0] if len(playlist_ids) == 1 else 0,  # 0 = múltiplas playlists mescladas
                        'nome': ' + '.join(playlist_names),  # "Playlist A + Playlist B"
                        'duracao_total_segundos': sum(v.get('duracao_segundos', 0) for v in all_videos),
                        'videos': all_videos,
                        'playlists_mescladas': playlist_ids,  # IDs das playlists que foram mescladas
                    }
                })
            else:
                return Response({
                    'dispositivo_id': dispositivo.id,
                    'dispositivo_nome': dispositivo.nome,
                    'municipio': str(dispositivo.municipio),
                    'playlist': None,
                    'message': 'Nenhuma playlist ativa configurada'
                })
        
        except DispositivoTV.DoesNotExist:
            return Response(
                {'error': 'Dispositivo não encontrado ou inativo'},
                status=status.HTTP_404_NOT_FOUND
            )


class TVLogExibicaoView(APIView):
    """
    API para o app de TV registrar logs de exibição
    Formato esperado: {dispositivo_id, video_id, tempo_exibicao_segundos}
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Registra log de exibição"""
        dispositivo_id = request.data.get('dispositivo_id')
        video_id = request.data.get('video_id')
        tempo_exibicao_segundos = request.data.get('tempo_exibicao_segundos', 0)
        
        # Valida campos obrigatórios
        if not dispositivo_id or not video_id:
            return Response(
                {'error': 'dispositivo_id e video_id são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            dispositivo = DispositivoTV.objects.get(id=dispositivo_id)
            video = Video.objects.get(id=video_id)
            
            # Usa a playlist atual do dispositivo
            if not dispositivo.playlist_atual:
                return Response(
                    {'error': 'Dispositivo não possui playlist configurada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calcula horários automaticamente
            data_hora_fim = timezone.now()
            data_hora_inicio = data_hora_fim - timezone.timedelta(seconds=tempo_exibicao_segundos)
            
            # Verifica se foi completamente exibido (pelo menos 90% do tempo)
            completamente_exibido = False
            if video.duracao_segundos > 0:
                porcentagem_exibida = (tempo_exibicao_segundos / video.duracao_segundos) * 100
                completamente_exibido = porcentagem_exibida >= 90
            
            log = LogExibicao.objects.create(
                dispositivo=dispositivo,
                video=video,
                playlist=dispositivo.playlist_atual,
                data_hora_inicio=data_hora_inicio,
                data_hora_fim=data_hora_fim,
                completamente_exibido=completamente_exibido
            )
            
            return Response(
                {'success': True, 'message': 'Log registrado com sucesso'},
                status=status.HTTP_201_CREATED
            )
        
        except DispositivoTV.DoesNotExist:
            return Response(
                {'error': 'Dispositivo não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Video.DoesNotExist:
            return Response(
                {'error': 'Vídeo não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )


class TVCheckScheduleView(APIView):
    """
    API para o app de TV verificar se deve exibir conteúdo no momento atual
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, identificador_unico):
        """Verifica se o dispositivo deve estar exibindo conteúdo agora"""
        try:
            dispositivo = DispositivoTV.objects.get(
                identificador_unico=identificador_unico,
                ativo=True
            )
            
            # Verifica se está no horário de exibição
            should_display = dispositivo.esta_no_horario_exibicao()
            
            # Atualiza última sincronização
            dispositivo.ultima_sincronizacao = timezone.now()
            dispositivo.save(update_fields=['ultima_sincronizacao'])
            
            response_data = {
                'should_display': should_display,
                'current_time': timezone.localtime(timezone.now()).isoformat(),
                'dispositivo_nome': dispositivo.nome,
                'has_playlist': dispositivo.playlist_atual is not None,
                'horarios_funcionamento': [
                    {
                        'nome': h.nome,
                        'hora_inicio': h.hora_inicio.strftime('%H:%M'),
                        'hora_fim': h.hora_fim.strftime('%H:%M'),
                        'dias_semana': h.dias_semana or [],
                        'ativo': h.ativo,
                    }
                    for h in dispositivo.horarios_funcionamento.filter(ativo=True)
                ],
            }
            
            # Playlists ativas pelo horário (pode ser diferente da padrão)
            playlists_ativas = dispositivo.get_playlists_ativas_por_horario()
            if should_display and playlists_ativas:
                if len(playlists_ativas) == 1:
                    response_data['playlist_id'] = playlists_ativas[0].id
                    response_data['playlist_nome'] = playlists_ativas[0].nome
                else:
                    # Múltiplas playlists mescladas
                    response_data['playlist_id'] = 0  # 0 = múltiplas mescladas
                    response_data['playlist_nome'] = ' + '.join([p.nome for p in playlists_ativas])
                    response_data['playlists_mescladas'] = [p.id for p in playlists_ativas]
            
            # Retorna info dos agendamentos ativos com playlist vinculada
            agendamentos = dispositivo.agendamentos.filter(ativo=True).select_related('playlist')
            if agendamentos.exists():
                response_data['agendamentos'] = [
                    {
                        'nome': ag.nome,
                        'dias_semana': ag.dias_semana,
                        'hora_inicio': ag.hora_inicio.strftime('%H:%M') if ag.hora_inicio else None,
                        'hora_fim': ag.hora_fim.strftime('%H:%M') if ag.hora_fim else None,
                        'playlist_id': ag.playlist_id,
                        'playlist_nome': ag.playlist.nome if ag.playlist else None,
                        'prioridade': ag.prioridade,
                    }
                    for ag in agendamentos
                ]
            else:
                response_data['agendamentos'] = []
                response_data['message'] = 'Sem agendamentos: exibição 24/7'
            
            return Response(response_data)
        
        except DispositivoTV.DoesNotExist:
            return Response(
                {'error': 'Dispositivo não encontrado ou inativo'},
                status=status.HTTP_404_NOT_FOUND
            )


class TVCorporativoHTMLView(APIView):
    """
    Retorna a página HTML completa de conteúdo corporativo para o app de TV.
    O Android WebView carrega esta URL e exibe por duracao_segundos.
    
    URL: /api/tv/corporativo/<tipo>/<playlist_id>/
    tipo: previsao_tempo | cotacoes | noticias
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, tipo, playlist_id):
        from django.shortcuts import render as django_render
        from .services import buscar_dados_corporativos

        tipo_upper = tipo.upper()
        valid = ['PREVISAO_TEMPO', 'COTACOES', 'NOTICIAS']
        if tipo_upper not in valid:
            return Response({'error': f'Tipo inválido. Válidos: {valid}'}, status=400)

        # Buscar município da playlist para previsão do tempo
        municipio = None
        try:
            playlist = Playlist.objects.select_related('municipio').get(pk=playlist_id)
            municipio = playlist.municipio
        except Playlist.DoesNotExist:
            pass

        dados = buscar_dados_corporativos(tipo_upper, municipio=municipio)

        context = {
            'conteudo_tipo': tipo_upper,
            'dados': dados,
        }
        return django_render(request, 'corporativo/conteudo_tv.html', context)


class DashboardStatsView(APIView):
    """
    View para estatísticas do dashboard
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.is_owner():
            stats = {
                'total_franqueados': User.objects.filter(role='FRANCHISEE').count(),
                'total_clientes': Cliente.objects.count(),
                'total_municipios': Municipio.objects.count(),
                'total_videos': Video.objects.count(),
                'videos_pendentes': Video.objects.filter(status='PENDING').count(),
                'total_playlists': Playlist.objects.count(),
                'total_dispositivos': DispositivoTV.objects.count(),
                'dispositivos_ativos': DispositivoTV.objects.filter(ativo=True).count(),
            }
        elif user.is_franchisee():
            stats = {
                'total_clientes': Cliente.objects.filter(franqueado=user).count(),
                'total_municipios': Municipio.objects.filter(franqueado=user).count(),
                'total_videos': Video.objects.filter(cliente__franqueado=user).count(),
                'videos_pendentes': Video.objects.filter(
                    cliente__franqueado=user,
                    status='PENDING'
                ).count(),
                'total_playlists': Playlist.objects.filter(franqueado=user).count(),
                'total_dispositivos': DispositivoTV.objects.filter(
                    municipio__franqueado=user
                ).count(),
            }
        elif user.is_client():
            try:
                cliente = user.cliente_profile
                stats = {
                    'total_videos': Video.objects.filter(cliente=cliente).count(),
                    'videos_pendentes': Video.objects.filter(
                        cliente=cliente,
                        status='PENDING'
                    ).count(),
                    'videos_aprovados': Video.objects.filter(
                        cliente=cliente,
                        status='APPROVED'
                    ).count(),
                    'videos_rejeitados': Video.objects.filter(
                        cliente=cliente,
                        status='REJECTED'
                    ).count(),
                }
            except Cliente.DoesNotExist:
                stats = {}
        else:
            stats = {}
        
        return Response(stats)


# Web Views (Django Templates)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.db.models import Count, Sum, Q, Avg, Prefetch
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from datetime import timedelta, datetime, time
import calendar
import os
from .forms import VideoForm, PlaylistForm, DispositivoTVForm, SegmentoForm, AppVersionForm, ConteudoCorporativoForm, ConfiguracaoAPIForm, HorarioFuncionamentoForm


def home_view(request):
    """Página inicial - redireciona para dashboard se logado, senão para login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def login_view(request):
    """View de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Usuário ou senha inválidos.')
        else:
            messages.error(request, 'Dados inválidos.')
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """View de logout"""
    logout(request)
    messages.info(request, 'Você foi desconectado com sucesso.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Dashboard principal"""
    user = request.user
    context = {
        'now': timezone.now(),
        'video_stats': {'approved': 0, 'pending': 0, 'rejected': 0},  # Inicializar sempre
    }

    if user.is_owner():
        # Estatísticas para proprietário - consultas otimizadas
        context.update({
            'total_franchisees': User.objects.filter(role='FRANCHISEE').count(),
            'total_municipios': Municipio.objects.count(),
            'total_clients': Cliente.objects.count(),
            'total_devices': DispositivoTV.objects.count(),
        })
        
        # Pré-carregar dados dos municípios com anotações (evita N+1)
        municipios_annotated = Municipio.objects.select_related('franqueado').annotate(
            publico_total=Sum('dispositivos__publico_estimado_mes'),
            dispositivos_count=Count('dispositivos')
        ).order_by('nome')
        
        # Indexar por franqueado_id
        municipios_by_franqueado = {}
        for mun in municipios_annotated:
            municipios_by_franqueado.setdefault(mun.franqueado_id, []).append({
                'municipio': mun,
                'publico_total': mun.publico_total or 0,
                'dispositivos_count': mun.dispositivos_count or 0,
            })
        
        # Pré-carregar clientes por franqueado
        all_clientes = Cliente.objects.select_related('user', 'segmento').order_by('empresa')
        clientes_by_franqueado = {}
        for cli in all_clientes:
            clientes_by_franqueado.setdefault(cli.franqueado_id, []).append(cli)
        
        # Pré-carregar playlists por franqueado
        all_playlists = Playlist.objects.select_related('municipio').order_by('nome')
        playlists_by_franqueado = {}
        for pl in all_playlists:
            playlists_by_franqueado.setdefault(pl.franqueado_id, []).append(pl)
        
        # Pré-carregar contagens de dispositivos por franqueado
        dispositivos_por_franqueado = dict(
            DispositivoTV.objects.values_list('municipio__franqueado').annotate(
                total=Count('id')
            ).values_list('municipio__franqueado', 'total')
        )
        
        # Pré-carregar público total por franqueado
        publico_por_franqueado = dict(
            DispositivoTV.objects.values('municipio__franqueado').annotate(
                total=Sum('publico_estimado_mes')
            ).values_list('municipio__franqueado', 'total')
        )
        
        # Montar visão hierárquica sem queries adicionais
        franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
        franqueados_data = []
        
        for franqueado in franqueados:
            fid = franqueado.id
            muns = municipios_by_franqueado.get(fid, [])
            clis = clientes_by_franqueado.get(fid, [])
            pls = playlists_by_franqueado.get(fid, [])
            
            franqueados_data.append({
                'franqueado': franqueado,
                'municipios': muns,
                'clientes': clis,
                'playlists': pls,
                'stats': {
                    'total_municipios': len(muns),
                    'total_clientes': len(clis),
                    'total_playlists': len(pls),
                    'total_dispositivos': dispositivos_por_franqueado.get(fid, 0),
                    'publico_total': publico_por_franqueado.get(fid, 0) or 0,
                }
            })
        
        context['franqueados_data'] = franqueados_data
        
    elif user.is_franchisee():
        # Estatísticas para franqueado
        municipios = Municipio.objects.filter(franqueado=user)
        clientes = Cliente.objects.filter(franqueado=user)
        dispositivos = DispositivoTV.objects.filter(municipio__franqueado=user)

        context.update({
            'total_municipios': municipios.count(),
            'total_clients': clientes.count(),
            'total_devices': dispositivos.count(),
        })
    else:
        # Estatísticas para cliente
        try:
            cliente = user.cliente_profile
            videos = Video.objects.filter(cliente=cliente)
            
            # Informações do franqueado
            franqueado = cliente.franqueado
            
            # Municípios do franqueado com público - query otimizada com anotações
            municipios = Municipio.objects.filter(franqueado=franqueado).annotate(
                publico_total=Sum('dispositivos__publico_estimado_mes'),
                dispositivos_count=Count('dispositivos')
            ).order_by('nome')
            
            municipios_com_publico = [{
                'municipio': m,
                'publico_total': m.publico_total or 0,
                'dispositivos_count': m.dispositivos_count or 0,
            } for m in municipios]
            
            # Público total do franqueado
            publico_total_franqueado = sum(m['publico_total'] for m in municipios_com_publico)
            
            context.update({
                'total_videos': videos.count(),
                'approved_videos': videos.filter(status='APPROVED').count(),
                'cliente': cliente,
                'franqueado': franqueado,
                'municipios_franqueado': municipios_com_publico,
                'publico_total_franqueado': publico_total_franqueado,
            })
        except Cliente.DoesNotExist:
            context.update({
                'total_videos': 0,
                'approved_videos': 0,
            })

    # Atividades recentes (últimos 10 dias)
    recent_activities = []
    cutoff_date = timezone.now() - timedelta(days=10)

    if user.is_owner():
        # Atividades de todos
        recent_videos = Video.objects.filter(
            created_at__gte=cutoff_date
        ).select_related('cliente').order_by('-created_at')[:5]
        for video in recent_videos:
            recent_activities.append({
                'description': f'Novo vídeo "{video.titulo}" enviado por {video.cliente.empresa}',
                'timestamp': video.created_at
            })
    elif user.is_franchisee():
        # Atividades dos clientes do franqueado
        recent_videos = Video.objects.filter(
            cliente__franqueado=user,
            created_at__gte=cutoff_date
        ).select_related('cliente').order_by('-created_at')[:5]
        for video in recent_videos:
            recent_activities.append({
                'description': f'Novo vídeo "{video.titulo}" enviado por {video.cliente.empresa}',
                'timestamp': video.created_at
            })
    else:
        # Atividades do próprio cliente
        try:
            cliente = user.cliente_profile
            recent_videos = Video.objects.filter(
                cliente=cliente,
                created_at__gte=cutoff_date
            ).order_by('-created_at')[:5]
            for video in recent_videos:
                status_text = {
                    'PENDING': 'pendente',
                    'APPROVED': 'aprovado',
                    'REJECTED': 'rejeitado'
                }.get(video.status, video.status)
                recent_activities.append({
                    'description': f'Vídeo "{video.titulo}" está {status_text}',
                    'timestamp': video.created_at
                })
        except Cliente.DoesNotExist:
            pass

    context['recent_activities'] = sorted(recent_activities, key=lambda x: x['timestamp'], reverse=True)[:5]

    # Estatísticas do gráfico de pizza (para clientes)
    if not user.is_owner() and not user.is_franchisee():
        try:
            cliente = user.cliente_profile
            videos = Video.objects.filter(cliente=cliente)
            context['video_stats'] = {
                'approved': videos.filter(status='APPROVED').count(),
                'pending': videos.filter(status='PENDING').count(),
                'rejected': videos.filter(status='REJECTED').count(),
            }
        except Cliente.DoesNotExist:
            context['video_stats'] = {'approved': 0, 'pending': 0, 'rejected': 0}

    return render(request, 'dashboard/dashboard.html', context)


@login_required
def cliente_metricas_view(request):
    """Dashboard de métricas de visibilidade para clientes"""
    user = request.user
    
    # Verificar se é cliente
    if not user.is_client():
        messages.error(request, 'Esta página é exclusiva para clientes.')
        return redirect('dashboard')
    
    try:
        cliente = user.cliente_profile
    except Cliente.DoesNotExist:
        messages.error(request, 'Perfil de cliente não encontrado.')
        return redirect('dashboard')
    
    # Obter vídeos aprovados do cliente
    videos_cliente = Video.objects.filter(cliente=cliente, status='APPROVED', ativo=True)
    
    # Encontrar playlists que contêm vídeos do cliente
    playlist_ids = PlaylistItem.objects.filter(
        video__in=videos_cliente, 
        ativo=True
    ).values_list('playlist_id', flat=True).distinct()
    
    playlists = Playlist.objects.filter(id__in=playlist_ids, ativa=True)
    
    # Dispositivos que usam essas playlists - prefetch agendamentos para evitar N+1
    dispositivos = DispositivoTV.objects.filter(
        playlist_atual__in=playlists,
        ativo=True
    ).select_related('municipio').prefetch_related(
        Prefetch('agendamentos', queryset=AgendamentoExibicao.objects.filter(ativo=True))
    ).distinct()
    
    # Métricas básicas
    telas_ativas = dispositivos.count()
    
    # Público impactado (soma do público estimado de todos os dispositivos)
    publico_impactado = dispositivos.aggregate(
        total=Sum('publico_estimado_mes')
    )['total'] or 0
    
    # Calcular tempo total de exibição baseado nos agendamentos
    tempo_total_segundos = 0
    dispositivos_detalhes = []
    
    # Dias úteis no mês atual
    now = timezone.now()
    _, dias_no_mes = calendar.monthrange(now.year, now.month)
    
    for dispositivo in dispositivos:
        agendamentos = dispositivo.agendamentos.all()  # já prefetched
        
        horas_dia = 0
        if agendamentos.exists():
            # Calcular horas por semana baseado nos agendamentos
            for agendamento in agendamentos:
                hora_inicio = agendamento.hora_inicio
                hora_fim = agendamento.hora_fim
                
                # Calcular duração em horas
                inicio_segundos = hora_inicio.hour * 3600 + hora_inicio.minute * 60 + hora_inicio.second
                fim_segundos = hora_fim.hour * 3600 + hora_fim.minute * 60 + hora_fim.second
                duracao_segundos = fim_segundos - inicio_segundos
                
                if duracao_segundos > 0:
                    horas_diarias = duracao_segundos / 3600
                    dias_ativos = len(agendamento.dias_semana) if agendamento.dias_semana else 0
                    # Média de dias por mês (considerando semanas)
                    dias_mes = (dias_ativos / 7) * dias_no_mes
                    horas_dia += horas_diarias * dias_mes
        else:
            # Sem agendamento = 12h por dia, todos os dias
            horas_dia = 12 * dias_no_mes
        
        tempo_total_segundos += horas_dia * 3600
        
        dispositivos_detalhes.append({
            'dispositivo': dispositivo,
            'horas_mes': round(horas_dia, 1),
            'localizacao': dispositivo.localizacao or dispositivo.municipio.nome
        })
    
    tempo_total_horas = tempo_total_segundos / 3600
    
    # Duração média dos vídeos do cliente (em segundos)
    duracao_media_video = videos_cliente.aggregate(
        media=Avg('duracao_segundos')
    )['media'] or 15  # Default 15 segundos
    
    # Total de vídeos em todas as playlists relevantes
    total_videos_playlists = PlaylistItem.objects.filter(
        playlist__in=playlists,
        ativo=True
    ).count()
    
    # Proporção de vídeos do cliente nas playlists
    videos_cliente_em_playlists = PlaylistItem.objects.filter(
        playlist__in=playlists,
        video__in=videos_cliente,
        ativo=True
    ).count()
    
    # Evitar divisão por zero
    proporcao_cliente = videos_cliente_em_playlists / max(total_videos_playlists, 1)
    
    # Inserções totais: tempo_total (em segundos) / duração média do vídeo * proporção de vídeos do cliente
    insercoes_totais = int((tempo_total_segundos / max(duracao_media_video, 1)) * proporcao_cliente)
    
    # Anunciantes ativos (clientes únicos com vídeos nas mesmas playlists)
    anunciantes_ids = PlaylistItem.objects.filter(
        playlist__in=playlists,
        ativo=True
    ).values_list('video__cliente_id', flat=True).distinct()
    anunciantes_ativos = len(set(anunciantes_ids))
    
    # Tempo por anúncio (duração média dos vídeos do cliente)
    tempo_por_anuncio = duracao_media_video
    
    # Inserções por anunciante
    insercoes_por_anunciante = int(insercoes_totais / max(anunciantes_ativos, 1)) if anunciantes_ativos > 0 else insercoes_totais
    
    # Tempo corrido da marca (inserções * duração média)
    tempo_corrido_segundos = insercoes_totais * duracao_media_video
    tempo_corrido_horas = tempo_corrido_segundos / 3600
    
    # Dados do mês anterior para comparação (usando logs reais se disponíveis)
    mes_anterior = now.replace(day=1) - timedelta(days=1)
    logs_mes_anterior = LogExibicao.objects.filter(
        video__cliente=cliente,
        data_hora_inicio__year=mes_anterior.year,
        data_hora_inicio__month=mes_anterior.month
    ).count()
    
    logs_mes_atual = LogExibicao.objects.filter(
        video__cliente=cliente,
        data_hora_inicio__year=now.year,
        data_hora_inicio__month=now.month
    ).count()
    
    # Calcular variação percentual
    if logs_mes_anterior > 0:
        variacao_percentual = ((logs_mes_atual - logs_mes_anterior) / logs_mes_anterior) * 100
    else:
        variacao_percentual = 100 if logs_mes_atual > 0 else 0
    
    # Função auxiliar para formatar números grandes
    def formatar_numero(n):
        if n >= 1000000:
            return f"{n / 1000000:.1f}M"
        elif n >= 1000:
            return f"{n / 1000:.1f}K"
        return str(int(n))
    
    context = {
        'now': now,
        'cliente': cliente,
        'telas_ativas': telas_ativas,
        'publico_impactado': publico_impactado,
        'publico_impactado_formatado': formatar_numero(publico_impactado),
        'tempo_total_horas': round(tempo_total_horas, 1),
        'insercoes_totais': insercoes_totais,
        'insercoes_totais_formatado': formatar_numero(insercoes_totais),
        'anunciantes_ativos': anunciantes_ativos,
        'tempo_por_anuncio': round(tempo_por_anuncio, 0),
        'insercoes_por_anunciante': insercoes_por_anunciante,
        'insercoes_por_anunciante_formatado': formatar_numero(insercoes_por_anunciante),
        'tempo_corrido_horas': round(tempo_corrido_horas, 1),
        'variacao_percentual': round(variacao_percentual, 0),
        'dispositivos_detalhes': dispositivos_detalhes,
        'videos_cliente': videos_cliente,
        'playlists': playlists,
        'duracao_media_video': round(duracao_media_video, 0),
        'proporcao_cliente': round(proporcao_cliente * 100, 1),
        'logs_mes_atual': logs_mes_atual,
    }
    
    return render(request, 'dashboard/cliente_metricas.html', context)


# Video Views
@login_required
def video_list_view(request):
    """Lista de vídeos"""
    user = request.user
    videos = Video.objects.select_related(
        'cliente', 'cliente__user', 'cliente__segmento'
    ).annotate(
        qrcode_clicks_count=Count('qrcode_clicks')
    )

    # Filtros
    search = request.GET.get('search', '')
    cliente_filter = request.GET.get('cliente', '')
    status_filter = request.GET.get('status', '')
    orphaned_filter = request.GET.get('orphaned', '')

    if search:
        videos = videos.filter(Q(titulo__icontains=search) | Q(descricao__icontains=search))

    if cliente_filter:
        videos = videos.filter(cliente_id=cliente_filter)

    if status_filter:
        videos = videos.filter(status=status_filter.upper())
    
    # Filtro para arquivos órfãos (apenas para OWNER)
    if orphaned_filter == 'true' and user.is_owner():
        orphaned_ids = []
        for video in videos.only('id', 'arquivo'):
            if not video.arquivo_existe():
                orphaned_ids.append(video.id)
        videos = videos.filter(id__in=orphaned_ids)

    # Controle de permissões
    if user.is_franchisee():
        clientes_ids = Cliente.objects.filter(franqueado=user).values_list('id', flat=True)
        videos = videos.filter(cliente_id__in=clientes_ids)
    elif not user.is_owner():
        try:
            cliente = user.cliente_profile
            videos = videos.filter(cliente=cliente)
        except Cliente.DoesNotExist:
            videos = Video.objects.none()

    # Paginação
    paginator = Paginator(videos.order_by('-created_at'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Clientes para filtro (se aplicável)
    clientes = Cliente.objects.only('id', 'empresa')
    if user.is_franchisee():
        clientes = clientes.filter(franqueado=user)

    context = {
        'videos': page_obj,
        'clientes': clientes,
    }

    return render(request, 'videos/video_list.html', context)


@login_required
def video_create_view(request):
    """Criar novo vídeo"""
    user = request.user
    
    # Verificar se é cliente e buscar perfil
    if user.is_client():
        try:
            cliente = user.cliente_profile
        except Cliente.DoesNotExist:
            messages.error(request, 'Perfil de cliente não encontrado.')
            return redirect('video_list')
        
        if request.method == 'POST':
            form = VideoForm(request.POST, request.FILES, user=user)
            if form.is_valid():
                video = form.save(commit=False)
                video.cliente = cliente
                video.save()
                messages.success(request, 'Vídeo enviado com sucesso! Aguarde aprovação.')
                return redirect('video_list')
        else:
            form = VideoForm(user=user)
        
        return render(request, 'videos/video_form.html', {'form': form})
    
    # Owner e Franqueado podem fazer upload para qualquer cliente
    elif user.is_owner() or user.is_franchisee():
        # Filtrar clientes disponíveis
        if user.is_owner():
            clientes = Cliente.objects.filter(ativo=True).select_related('user').order_by('empresa')
        else:
            clientes = Cliente.objects.filter(franqueado=user, ativo=True).select_related('user').order_by('empresa')
        
        if request.method == 'POST':
            cliente_id = request.POST.get('cliente')
            titulo = request.POST.get('titulo')
            descricao = request.POST.get('descricao')
            arquivo = request.FILES.get('arquivo')
            qrcode_url_destino = request.POST.get('qrcode_url_destino', '').strip() or None
            qrcode_descricao = request.POST.get('qrcode_descricao', '').strip() or None
            texto_tarja = request.POST.get('texto_tarja', '').strip() or None
            
            if not cliente_id or not titulo or not arquivo:
                messages.error(request, 'Cliente, título e arquivo de vídeo são obrigatórios.')
            else:
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                    
                    # Verificar se franqueado tem permissão
                    if user.is_franchisee() and cliente.franqueado != user:
                        messages.error(request, 'Você não tem permissão para enviar vídeos para este cliente.')
                        return redirect('video_list')
                    
                    video = Video.objects.create(
                        cliente=cliente,
                        titulo=titulo,
                        descricao=descricao,
                        arquivo=arquivo,
                        qrcode_url_destino=qrcode_url_destino,
                        qrcode_descricao=qrcode_descricao,
                        texto_tarja=texto_tarja,
                        status='PENDING'
                    )
                    messages.success(request, f'Vídeo enviado com sucesso para {cliente.empresa}!')
                    return redirect('video_list')
                except Cliente.DoesNotExist:
                    messages.error(request, 'Cliente não encontrado.')
        
        return render(request, 'videos/video_form.html', {'clientes': clientes})
    
    else:
        messages.error(request, 'Você não tem permissão para enviar vídeos.')
        return redirect('video_list')


@login_required
def video_update_view(request, pk):
    """Atualizar vídeo"""
    user = request.user
    video = get_object_or_404(Video, pk=pk)

    # Verificar permissões
    if not user.is_owner():
        if user.is_franchisee():
            if video.cliente.franqueado != user:
                messages.error(request, 'Você não tem permissão para editar este vídeo.')
                return redirect('video_list')
        elif not user.is_client() or video.cliente.user != user:
            messages.error(request, 'Você não tem permissão para editar este vídeo.')
            return redirect('video_list')

    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES, instance=video, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vídeo atualizado com sucesso!')
            return redirect('video_list')
    else:
        form = VideoForm(instance=video, user=user)

    return render(request, 'videos/video_form.html', {'form': form, 'video': video})


@login_required
def video_approve_view(request, pk):
    """Aprovar vídeo"""
    user = request.user
    
    print(f"DEBUG: Tentando aprovar vídeo {pk} por usuário {user.username}")
    
    # Apenas owners e franqueados podem aprovar
    if not user.is_owner() and not user.is_franchisee():
        print(f"DEBUG: Usuário {user.username} não tem permissão (role: {user.role})")
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    video = get_object_or_404(Video, pk=pk)
    print(f"DEBUG: Video encontrado: {video.titulo}, Status atual: {video.status}")
    
    # Franqueados só podem aprovar vídeos de seus clientes
    if user.is_franchisee() and video.cliente.franqueado != user:
        print(f"DEBUG: Franqueado não gerencia este cliente")
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    video.status = 'APPROVED'
    video.save()
    print(f"DEBUG: Video {video.titulo} aprovado! Novo status: {video.status}")
    
    messages.success(request, f'Vídeo "{video.titulo}" aprovado com sucesso!')
    return JsonResponse({'success': True})


@login_required
def video_reject_view(request, pk):
    """Rejeitar vídeo"""
    user = request.user
    
    # Apenas owners e franqueados podem rejeitar
    if not user.is_owner() and not user.is_franchisee():
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    video = get_object_or_404(Video, pk=pk)
    
    # Franqueados só podem rejeitar vídeos de seus clientes
    if user.is_franchisee() and video.cliente.franqueado != user:
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    video.status = 'REJECTED'
    video.save()
    
    messages.success(request, f'Vídeo "{video.titulo}" rejeitado.')
    return JsonResponse({'success': True})


@login_required
def video_delete_view(request, pk):
    """Deletar vídeo"""
    import os
    user = request.user
    video = get_object_or_404(Video, pk=pk)
    
    # Verificar permissões
    if not user.is_owner():
        if user.is_franchisee():
            if video.cliente.franqueado != user:
                return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
        elif not user.is_client() or video.cliente.user != user:
            return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    titulo = video.titulo
    arquivo_existe = video.arquivo and os.path.exists(video.arquivo.path)
    
    # Deleta o registro (e o arquivo se existir)
    video.delete()
    
    if arquivo_existe:
        messages.success(request, f'Vídeo "{titulo}" excluído com sucesso!')
    else:
        messages.success(request, f'Registro do vídeo "{titulo}" excluído (arquivo já não existia no servidor)')
    
    return JsonResponse({'success': True})


@login_required
def video_qrcode_metricas_view(request, pk):
    """Métricas de cliques do QR Code de um vídeo"""
    user = request.user
    video = get_object_or_404(Video, pk=pk)
    
    # Verificar permissões
    if not user.is_owner():
        if user.is_franchisee():
            if video.cliente.franqueado != user:
                messages.error(request, 'Você não tem permissão para ver estas métricas.')
                return redirect('video_list')
        elif video.cliente.user != user:
            messages.error(request, 'Você não tem permissão para ver estas métricas.')
            return redirect('video_list')
    
    # Buscar cliques
    clicks = video.qrcode_clicks.all().order_by('-created_at')
    
    # Estatísticas
    total_clicks = clicks.count()
    
    # Cliques por dia (últimos 30 dias)
    hoje = timezone.now().date()
    inicio_periodo = hoje - timedelta(days=30)
    
    clicks_por_dia = (
        clicks.filter(created_at__date__gte=inicio_periodo)
        .annotate(data=TruncDate('created_at'))
        .values('data')
        .annotate(count=Count('id'))
        .order_by('data')
    )
    
    # Preparar dados para o gráfico
    dias_labels = []
    dias_valores = []
    clicks_dict = {item['data']: item['count'] for item in clicks_por_dia}
    
    for i in range(31):  # 31 dias para incluir hoje
        dia = inicio_periodo + timedelta(days=i)
        dias_labels.append(dia.strftime('%d/%m'))
        dias_valores.append(clicks_dict.get(dia, 0))
    
    # Top IPs (para detectar possível fraude)
    top_ips = (
        clicks.exclude(ip_address__isnull=True)
        .values('ip_address')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    
    # Paginação dos cliques
    paginator = Paginator(clicks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Converter listas para JSON para o gráfico (JavaScript precisa de JSON válido)
    import json
    
    context = {
        'video': video,
        'clicks': page_obj,
        'total_clicks': total_clicks,
        'dias_labels': json.dumps(dias_labels),
        'dias_valores': json.dumps(dias_valores),
        'top_ips': top_ips,
    }
    
    return render(request, 'videos/video_qrcode_metricas.html', context)


# Playlist Views
@login_required
def playlist_list_view(request):
    """Lista de playlists"""
    user = request.user
    playlists = Playlist.objects.select_related(
        'municipio', 'franqueado'
    ).prefetch_related(
        Prefetch('items', queryset=PlaylistItem.objects.filter(ativo=True).select_related('video').only(
            'id', 'playlist_id', 'video_id', 'ativo', 'video__titulo'
        )),
        'dispositivos'
    )

    # Controle de permissões
    if user.is_franchisee():
        playlists = playlists.filter(franqueado=user)
    elif not user.is_owner():
        messages.error(request, 'Você não tem permissão para ver playlists.')
        return redirect('dashboard')

    # Paginação
    paginator = Paginator(playlists.order_by('-created_at'), 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'playlists': page_obj,
    }

    return render(request, 'playlists/playlist_list.html', context)


@login_required
def playlist_create_view(request):
    """Criar nova playlist"""
    user = request.user

    # Verificar permissões
    if not user.is_franchisee() and not user.is_owner():
        messages.error(request, 'Apenas franqueados podem criar playlists.')
        return redirect('playlist_list')

    # Obter vídeos disponíveis
    available_videos = Video.objects.filter(status='APPROVED')
    if user.is_franchisee():
        clientes_ids = Cliente.objects.filter(franqueado=user).values_list('id', flat=True)
        available_videos = available_videos.filter(cliente_id__in=clientes_ids)

    # Conteúdos corporativos disponíveis
    conteudos_corporativos = ConteudoCorporativo.objects.filter(ativo=True)

    if request.method == 'POST':
        form = PlaylistForm(request.POST, user=user)
        selected_videos = request.POST.getlist('selected_videos')
        # Filtrar valores vazios
        selected_videos = [v for v in selected_videos if v and v.strip()]

        if form.is_valid():
            playlist = form.save(commit=False)
            # Definir franqueado baseado no município selecionado ou no usuário
            if user.is_franchisee():
                playlist.franqueado = user
            elif playlist.municipio:
                playlist.franqueado = playlist.municipio.franqueado
            playlist.save()

            # Adicionar itens selecionados (vídeos + corporativos)
            if selected_videos:
                for order, item_id in enumerate(selected_videos, 1):
                    if item_id.startswith('corp_'):
                        corp_id = int(item_id.replace('corp_', ''))
                        PlaylistItem.objects.create(
                            playlist=playlist,
                            conteudo_corporativo_id=corp_id,
                            ordem=order
                        )
                    else:
                        PlaylistItem.objects.create(
                            playlist=playlist,
                            video_id=int(item_id),
                            ordem=order
                        )
                messages.success(request, f'Playlist criada com sucesso com {len(selected_videos)} item(ns)!')
            else:
                messages.success(request, 'Playlist criada com sucesso! Você pode adicionar itens depois.')

            return redirect('playlist_list')
    else:
        form = PlaylistForm(user=user)

    context = {
        'form': form,
        'available_videos': available_videos,
        'conteudos_corporativos': conteudos_corporativos,
    }

    return render(request, 'playlists/playlist_form.html', context)


@login_required
def playlist_detail_view(request, pk):
    """Detalhes da playlist"""
    playlist = get_object_or_404(Playlist, pk=pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and playlist.franqueado != user:
        messages.error(request, 'Você não tem permissão para ver esta playlist.')
        return redirect('playlist_list')
    
    # Obter itens da playlist ordenados
    items = playlist.items.all().select_related('video', 'video__cliente', 'conteudo_corporativo').order_by('ordem')
    
    context = {
        'playlist': playlist,
        'items': items,
    }
    
    return render(request, 'playlists/playlist_detail.html', context)


@login_required
def playlist_update_view(request, pk):
    """Editar playlist"""
    playlist = get_object_or_404(Playlist, pk=pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and playlist.franqueado != user:
        messages.error(request, 'Você não tem permissão para editar esta playlist.')
        return redirect('playlist_list')
    
    # Obter vídeos disponíveis
    available_videos = Video.objects.filter(status='APPROVED')
    if user.is_franchisee():
        clientes_ids = Cliente.objects.filter(franqueado=user).values_list('id', flat=True)
        available_videos = available_videos.filter(cliente_id__in=clientes_ids)

    # Conteúdos corporativos disponíveis
    conteudos_corporativos = ConteudoCorporativo.objects.filter(ativo=True)
    
    if request.method == 'POST':
        form = PlaylistForm(request.POST, instance=playlist, user=user)
        selected_videos = request.POST.getlist('selected_videos')
        # Filtrar valores vazios
        selected_videos = [v for v in selected_videos if v and v.strip()]
        
        if form.is_valid():
            playlist = form.save(commit=False)
            # Definir franqueado baseado no município selecionado ou no usuário
            if user.is_franchisee():
                playlist.franqueado = user
            elif playlist.municipio:
                playlist.franqueado = playlist.municipio.franqueado
            playlist.save()
            
            # Remover itens antigos
            playlist.items.all().delete()
            
            # Adicionar itens selecionados (vídeos + corporativos)
            if selected_videos:
                for order, item_id in enumerate(selected_videos, 1):
                    if item_id.startswith('corp_'):
                        corp_id = int(item_id.replace('corp_', ''))
                        PlaylistItem.objects.create(
                            playlist=playlist,
                            conteudo_corporativo_id=corp_id,
                            ordem=order
                        )
                    else:
                        PlaylistItem.objects.create(
                            playlist=playlist,
                            video_id=int(item_id),
                            ordem=order
                        )
                messages.success(request, f'Playlist atualizada com sucesso com {len(selected_videos)} item(ns)!')
            else:
                messages.success(request, 'Playlist atualizada com sucesso!')
            
            return redirect('playlist_detail', pk=playlist.pk)
    else:
        form = PlaylistForm(instance=playlist, user=user)
    
    # Obter itens atuais da playlist
    current_items = playlist.items.all().select_related('video', 'conteudo_corporativo').order_by('ordem')
    
    context = {
        'form': form,
        'playlist': playlist,
        'available_videos': available_videos,
        'conteudos_corporativos': conteudos_corporativos,
        'current_items': current_items,
    }
    
    return render(request, 'playlists/playlist_form.html', context)


@login_required
def playlist_delete_view(request, pk):
    """Deletar playlist"""
    playlist = get_object_or_404(Playlist, pk=pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and playlist.franqueado != user:
        messages.error(request, 'Você não tem permissão para deletar esta playlist.')
        return redirect('playlist_list')
    
    if request.method == 'POST':
        playlist_nome = playlist.nome
        playlist.delete()
        messages.success(request, f'Playlist "{playlist_nome}" deletada com sucesso!')
        return redirect('playlist_list')
    
    context = {
        'playlist': playlist,
    }
    
    return render(request, 'playlists/playlist_confirm_delete.html', context)


# Dispositivo Views
@login_required
def dispositivo_list_view(request):
    """Lista de dispositivos TV"""
    user = request.user
    dispositivos = DispositivoTV.objects.select_related(
        'municipio', 'municipio__franqueado', 'playlist_atual'
    ).annotate(
        total_exibicoes=Count('logs_exibicao')
    )

    # Filtros
    search = request.GET.get('search', '')
    municipio_filter = request.GET.get('municipio', '')
    status_filter = request.GET.get('status', '')
    playlist_filter = request.GET.get('playlist', '')

    if search:
        dispositivos = dispositivos.filter(
            Q(nome__icontains=search) | Q(localizacao__icontains=search)
        )

    if municipio_filter:
        dispositivos = dispositivos.filter(municipio_id=municipio_filter)

    if status_filter:
        dispositivos = dispositivos.filter(ativo=(status_filter == 'ativo'))

    if playlist_filter:
        dispositivos = dispositivos.filter(playlist_atual_id=playlist_filter)

    # Controle de permissões
    if user.is_franchisee():
        dispositivos = dispositivos.filter(municipio__franqueado=user)
    elif not user.is_owner():
        messages.error(request, 'Você não tem permissão para ver dispositivos.')
        return redirect('dashboard')

    # Estatísticas - baseadas no queryset filtrado
    # Total de exibições: contar logs dos dispositivos filtrados
    total_exibicoes = LogExibicao.objects.filter(
        dispositivo__in=dispositivos
    ).count()

    # Status real de conexão (requer avaliação Python por dispositivo)
    all_dispositivos_list = list(dispositivos.prefetch_related('agendamentos'))
    count_transmitindo = 0
    count_fora_horario = 0
    count_desconectado = 0
    for _d in all_dispositivos_list:
        _st = _d.status_conexao()
        if _st == 'transmitindo':
            count_transmitindo += 1
        elif _st == 'fora_horario':
            count_fora_horario += 1
        else:
            count_desconectado += 1

    context = {
        'dispositivos_ativos': dispositivos.filter(ativo=True).count(),
        'dispositivos_inativos': dispositivos.filter(ativo=False).count(),
        'total_exibicoes': total_exibicoes,
        'tempo_total_exibicao': '0h',
        'count_transmitindo': count_transmitindo,
        'count_fora_horario': count_fora_horario,
        'count_desconectado': count_desconectado,
    }

    # Paginação
    paginator = Paginator(dispositivos.order_by('-created_at'), 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Municipios e playlists para filtro (scoped)
    if user.is_owner():
        filter_municipios = Municipio.objects.only('id', 'nome', 'estado')
    else:
        filter_municipios = Municipio.objects.filter(franqueado=user).only('id', 'nome', 'estado')
    
    context.update({
        'dispositivos': page_obj,
        'municipios': filter_municipios,
        'playlists': Playlist.objects.filter(ativa=True).only('id', 'nome'),
    })

    return render(request, 'dispositivos/dispositivo_list.html', context)


@login_required
def dispositivo_create_view(request):
    """Criar novo dispositivo TV"""
    user = request.user

    # Verificar permissões
    if not user.is_franchisee() and not user.is_owner():
        messages.error(request, 'Apenas franqueados podem cadastrar dispositivos.')
        return redirect('dispositivo_list')

    if request.method == 'POST':
        form = DispositivoTVForm(request.POST)
        if form.is_valid():
            dispositivo = form.save(commit=False)
            # Gerar identificador único se não existir
            if not dispositivo.identificador_unico:
                import uuid
                dispositivo.identificador_unico = str(uuid.uuid4())
            dispositivo.save()
            messages.success(request, 'Dispositivo cadastrado com sucesso!')
            return redirect('dispositivo_list')
    else:
        form = DispositivoTVForm()

    return render(request, 'dispositivos/dispositivo_form.html', {'form': form})


@login_required
def dispositivo_detail_view(request, pk):
    """Detalhes do dispositivo TV"""
    dispositivo = get_object_or_404(DispositivoTV, pk=pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para ver este dispositivo.')
        return redirect('dispositivo_list')
    
    # Contar agendamentos ativos
    agendamentos_ativos = dispositivo.agendamentos.filter(ativo=True).select_related('playlist')
    agendamentos_ativos_count = agendamentos_ativos.count()
    
    # Horário de funcionamento do dispositivo
    no_horario = dispositivo.esta_no_horario_exibicao()
    horarios_funcionamento = dispositivo.horarios_funcionamento.all()
    
    # Buscar logs recentes com vídeo e thumbnail
    logs_recentes = dispositivo.logs_exibicao.select_related(
        'video', 'video__cliente', 'playlist'
    ).order_by('-data_hora_inicio')[:15]
    
    context = {
        'dispositivo': dispositivo,
        'agendamentos_ativos_count': agendamentos_ativos_count,
        'no_horario': no_horario,
        'horarios_funcionamento': horarios_funcionamento,
        'logs_recentes': logs_recentes,
    }
    
    return render(request, 'dispositivos/dispositivo_detail.html', context)


@login_required
def dispositivo_update_view(request, pk):
    """Editar dispositivo TV"""
    dispositivo = get_object_or_404(DispositivoTV, pk=pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para editar este dispositivo.')
        return redirect('dispositivo_list')
    
    if request.method == 'POST':
        form = DispositivoTVForm(request.POST, instance=dispositivo)
        if form.is_valid():
            dispositivo = form.save()
            messages.success(request, 'Dispositivo atualizado com sucesso!')
            return redirect('dispositivo_detail', pk=dispositivo.pk)
    else:
        form = DispositivoTVForm(instance=dispositivo)
    
    context = {
        'form': form,
        'dispositivo': dispositivo,
    }
    
    return render(request, 'dispositivos/dispositivo_form.html', context)


@login_required
def dispositivo_delete_view(request, pk):
    """Deletar dispositivo TV"""
    dispositivo = get_object_or_404(DispositivoTV, pk=pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para deletar este dispositivo.')
        return redirect('dispositivo_list')
    
    if request.method == 'POST':
        dispositivo_nome = dispositivo.nome
        dispositivo.delete()
        messages.success(request, f'Dispositivo "{dispositivo_nome}" deletado com sucesso!')
        return redirect('dispositivo_list')
    
    context = {
        'dispositivo': dispositivo,
    }
    
    return render(request, 'dispositivos/dispositivo_confirm_delete.html', context)


# Agendamento Views
@login_required
def agendamento_create_view(request, dispositivo_pk):
    """Criar novo agendamento de exibição"""
    from .forms import AgendamentoExibicaoForm
    from .models import AgendamentoExibicao
    
    dispositivo = get_object_or_404(DispositivoTV, pk=dispositivo_pk)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para criar agendamentos para este dispositivo.')
        return redirect('dispositivo_detail', pk=dispositivo_pk)
    
    if request.method == 'POST':
        form = AgendamentoExibicaoForm(request.POST)
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.dispositivo = dispositivo
            agendamento.save()
            messages.success(request, 'Agendamento criado com sucesso!')
            return redirect('dispositivo_detail', pk=dispositivo_pk)
    else:
        form = AgendamentoExibicaoForm()
    
    context = {
        'form': form,
        'dispositivo': dispositivo,
        'title': 'Vincular Playlist',
        'button_text': 'Vincular',
    }
    
    return render(request, 'agendamentos/agendamento_form.html', context)


@login_required
def agendamento_update_view(request, dispositivo_pk, pk):
    """Atualizar vínculo playlist-dispositivo"""
    from .forms import AgendamentoExibicaoForm
    from .models import AgendamentoExibicao
    
    dispositivo = get_object_or_404(DispositivoTV, pk=dispositivo_pk)
    agendamento = get_object_or_404(AgendamentoExibicao, pk=pk, dispositivo=dispositivo)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para editar este agendamento.')
        return redirect('dispositivo_detail', pk=dispositivo_pk)
    
    if request.method == 'POST':
        form = AgendamentoExibicaoForm(request.POST, instance=agendamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Playlist atualizada com sucesso!')
            return redirect('dispositivo_detail', pk=dispositivo_pk)
    else:
        form = AgendamentoExibicaoForm(instance=agendamento)
    
    context = {
        'form': form,
        'dispositivo': dispositivo,
        'agendamento': agendamento,
        'title': 'Editar Playlist Vinculada',
        'button_text': 'Salvar Alterações',
    }
    
    return render(request, 'agendamentos/agendamento_form.html', context)


@login_required
def agendamento_delete_view(request, dispositivo_pk, pk):
    """Deletar agendamento de exibição"""
    from .models import AgendamentoExibicao
    
    dispositivo = get_object_or_404(DispositivoTV, pk=dispositivo_pk)
    agendamento = get_object_or_404(AgendamentoExibicao, pk=pk, dispositivo=dispositivo)
    user = request.user
    
    # Verificar permissões
    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para deletar este agendamento.')
        return redirect('dispositivo_detail', pk=dispositivo_pk)
    
    if request.method == 'POST':
        playlist_nome = agendamento.playlist.nome if agendamento.playlist else agendamento.nome
        agendamento.delete()
        messages.success(request, f'Playlist "{playlist_nome}" desvinculada com sucesso!')
        return redirect('dispositivo_detail', pk=dispositivo_pk)
    
    context = {
        'agendamento': agendamento,
        'dispositivo': dispositivo,
    }
    
    return render(request, 'agendamentos/agendamento_confirm_delete.html', context)


# ===== Horário de Funcionamento CRUD =====

@login_required
def horario_create_view(request, dispositivo_pk):
    """Criar horário de funcionamento para um dispositivo"""
    dispositivo = get_object_or_404(DispositivoTV, pk=dispositivo_pk)
    user = request.user

    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para este dispositivo.')
        return redirect('dispositivo_detail', pk=dispositivo_pk)

    if request.method == 'POST':
        form = HorarioFuncionamentoForm(request.POST)
        if form.is_valid():
            horario = form.save(commit=False)
            horario.dispositivo = dispositivo
            horario.save()
            messages.success(request, f'Horário "{horario.nome}" criado com sucesso!')
            return redirect('dispositivo_detail', pk=dispositivo_pk)
    else:
        form = HorarioFuncionamentoForm()

    context = {
        'form': form,
        'dispositivo': dispositivo,
    }
    return render(request, 'horarios/horario_form.html', context)


@login_required
def horario_update_view(request, dispositivo_pk, pk):
    """Editar horário de funcionamento"""
    dispositivo = get_object_or_404(DispositivoTV, pk=dispositivo_pk)
    horario = get_object_or_404(HorarioFuncionamento, pk=pk, dispositivo=dispositivo)
    user = request.user

    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para este dispositivo.')
        return redirect('dispositivo_detail', pk=dispositivo_pk)

    if request.method == 'POST':
        form = HorarioFuncionamentoForm(request.POST, instance=horario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Horário "{horario.nome}" atualizado com sucesso!')
            return redirect('dispositivo_detail', pk=dispositivo_pk)
    else:
        form = HorarioFuncionamentoForm(instance=horario)

    context = {
        'form': form,
        'dispositivo': dispositivo,
        'horario': horario,
    }
    return render(request, 'horarios/horario_form.html', context)


@login_required
def horario_delete_view(request, dispositivo_pk, pk):
    """Deletar horário de funcionamento"""
    dispositivo = get_object_or_404(DispositivoTV, pk=dispositivo_pk)
    horario = get_object_or_404(HorarioFuncionamento, pk=pk, dispositivo=dispositivo)
    user = request.user

    if user.is_franchisee() and dispositivo.municipio.franqueado != user:
        messages.error(request, 'Você não tem permissão para este dispositivo.')
        return redirect('dispositivo_detail', pk=dispositivo_pk)

    if request.method == 'POST':
        nome = horario.nome
        horario.delete()
        messages.success(request, f'Horário "{nome}" excluído com sucesso!')
        return redirect('dispositivo_detail', pk=dispositivo_pk)

    context = {
        'horario': horario,
        'dispositivo': dispositivo,
    }
    return render(request, 'horarios/horario_confirm_delete.html', context)


# User/Franchisee Views
@login_required
def user_list_view(request):
    """Lista de usuários"""
    user = request.user
    
    # Apenas proprietários podem ver a lista de usuários
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    users = User.objects.all().order_by('-created_at')
    
    # Filtros
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    context = {
        'users': users,
        'search': search,
        'role_filter': role_filter,
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'users/user_list.html', context)


@login_required
def user_create_view(request):
    """Criar novo usuário"""
    user = request.user
    
    # Apenas proprietários podem criar usuários
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        
        # Validações
        if not username or not password:
            messages.error(request, 'Username e senha são obrigatórios.')
        elif password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Este username já está em uso.')
        elif email and User.objects.filter(email=email).exists():
            messages.error(request, 'Este email já está em uso.')
        else:
            # Criar usuário
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            messages.success(request, f'Usuário {username} criado com sucesso!')
            return redirect('user_list')
    
    context = {
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'users/user_form.html', context)


@login_required
def user_update_view(request, pk):
    """Editar usuário existente"""
    user = request.user
    
    # Apenas proprietários podem editar usuários
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    edit_user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validações
        if email and User.objects.filter(email=email).exclude(pk=pk).exists():
            messages.error(request, 'Este email já está em uso.')
        elif password and password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
        else:
            # Atualizar usuário
            edit_user.email = email
            edit_user.first_name = first_name
            edit_user.last_name = last_name
            edit_user.role = role
            edit_user.is_active = is_active
            
            if password:
                edit_user.set_password(password)
            
            edit_user.save()
            messages.success(request, f'Usuário {edit_user.username} atualizado com sucesso!')
            return redirect('user_list')
    
    context = {
        'edit_user': edit_user,
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'users/user_form.html', context)


@login_required
def user_delete_view(request, pk):
    """Deletar usuário"""
    user = request.user
    
    # Apenas proprietários podem deletar usuários
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    delete_user = get_object_or_404(User, pk=pk)
    
    # Não pode deletar a si mesmo
    if delete_user == user:
        messages.error(request, 'Você não pode deletar sua própria conta.')
        return redirect('user_list')
    
    if request.method == 'POST':
        username = delete_user.username
        delete_user.delete()
        messages.success(request, f'Usuário {username} deletado com sucesso!')
        return redirect('user_list')
    
    context = {
        'delete_user': delete_user,
    }
    
    return render(request, 'users/user_confirm_delete.html', context)


# Municipio Views
@login_required
def municipio_list_view(request):
    """Lista de municípios"""
    user = request.user
    
    # Apenas proprietários e franqueados podem ver municípios
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    municipios = Municipio.objects.all().select_related('franqueado').order_by('nome')
    
    # Franqueados veem apenas seus municípios
    if user.is_franchisee():
        municipios = municipios.filter(franqueado=user)
    
    # Filtros
    search = request.GET.get('search', '')
    franqueado_filter = request.GET.get('franqueado', '')
    
    if search:
        municipios = municipios.filter(
            Q(nome__icontains=search) |
            Q(estado__icontains=search)
        )
    
    if franqueado_filter and user.is_owner():
        municipios = municipios.filter(franqueado_id=franqueado_filter)
    
    # Lista de franqueados para filtro (apenas para owner)
    franqueados = User.objects.filter(role='FRANCHISEE').order_by('username') if user.is_owner() else []
    
    context = {
        'municipios': municipios,
        'search': search,
        'franqueado_filter': franqueado_filter,
        'franqueados': franqueados,
    }
    
    return render(request, 'municipios/municipio_list.html', context)


def _parse_coord(value):
    """Converte texto de coordenada (latitude/longitude) para Decimal com 6 casas.
    Suporta valores com muitas casas decimais vindos do Google Maps."""
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    if not value or not str(value).strip():
        return None
    try:
        # Converte via float para lidar com notação científica, depois quantiza
        d = Decimal(str(round(float(value), 6)))
        return d.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    except (ValueError, InvalidOperation):
        return None


@login_required
def municipio_create_view(request):
    """Criar novo município"""
    user = request.user
    
    # Apenas proprietários podem criar municípios
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        estado = request.POST.get('estado')
        franqueado_id = request.POST.get('franqueado')
        latitude = _parse_coord(request.POST.get('latitude'))
        longitude = _parse_coord(request.POST.get('longitude'))
        
        # Validações
        if not nome or not estado:
            messages.error(request, 'Nome e Estado são obrigatórios.')
        elif not franqueado_id:
            messages.error(request, 'Franqueado é obrigatório.')
        else:
            # Criar município
            municipio = Municipio.objects.create(
                nome=nome,
                estado=estado,
                franqueado_id=franqueado_id,
                latitude=latitude,
                longitude=longitude,
            )
            messages.success(request, f'Município {nome}/{estado} criado com sucesso!')
            return redirect('municipio_list')
    
    # Lista de franqueados para atribuição
    franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
    
    # Lista de UFs brasileiras
    ufs = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    context = {
        'franqueados': franqueados,
        'ufs': ufs,
    }
    
    return render(request, 'municipios/municipio_form.html', context)


@login_required
def municipio_update_view(request, pk):
    """Editar município existente"""
    user = request.user
    
    # Apenas proprietários podem editar municípios
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    municipio = get_object_or_404(Municipio, pk=pk)
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        estado = request.POST.get('estado')
        franqueado_id = request.POST.get('franqueado')
        latitude = _parse_coord(request.POST.get('latitude'))
        longitude = _parse_coord(request.POST.get('longitude'))
        
        # Validações
        if not nome or not estado:
            messages.error(request, 'Nome e Estado são obrigatórios.')
        elif not franqueado_id:
            messages.error(request, 'Franqueado é obrigatório.')
        else:
            # Atualizar município
            municipio.nome = nome
            municipio.estado = estado
            municipio.franqueado_id = franqueado_id
            municipio.latitude = latitude
            municipio.longitude = longitude
            municipio.save()
            messages.success(request, f'Município {nome}/{estado} atualizado com sucesso!')
            return redirect('municipio_list')
    
    # Lista de franqueados para atribuição
    franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
    
    # Lista de UFs brasileiras
    ufs = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    context = {
        'municipio': municipio,
        'franqueados': franqueados,
        'ufs': ufs,
    }
    
    return render(request, 'municipios/municipio_form.html', context)


@login_required
def municipio_delete_view(request, pk):
    """Deletar município"""
    user = request.user
    
    # Apenas proprietários podem deletar municípios
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    municipio = get_object_or_404(Municipio, pk=pk)
    
    if request.method == 'POST':
        nome = municipio.nome
        estado = municipio.estado
        municipio.delete()
        messages.success(request, f'Município {nome}/{estado} deletado com sucesso!')
        return redirect('municipio_list')
    
    # Contar clientes e dispositivos relacionados
    total_clientes = municipio.clientes.count()
    total_dispositivos = municipio.dispositivos.count()
    
    context = {
        'municipio': municipio,
        'total_clientes': total_clientes,
        'total_dispositivos': total_dispositivos,
    }
    
    return render(request, 'municipios/municipio_confirm_delete.html', context)


# Segmento Views
@login_required
def segmento_list_view(request):
    """Lista de segmentos"""
    user = request.user
    
    # Apenas proprietários e franqueados podem ver segmentos
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    segmentos = Segmento.objects.all().order_by('nome')
    
    # Filtro de busca
    search = request.GET.get('search', '')
    if search:
        segmentos = segmentos.filter(nome__icontains=search)
    
    # Filtro ativo/inativo
    status_filter = request.GET.get('status', '')
    if status_filter == 'ativo':
        segmentos = segmentos.filter(ativo=True)
    elif status_filter == 'inativo':
        segmentos = segmentos.filter(ativo=False)
    
    # Paginação
    paginator = Paginator(segmentos, 15)
    page_number = request.GET.get('page')
    segmentos_page = paginator.get_page(page_number)
    
    context = {
        'segmentos': segmentos_page,
        'total_segmentos': segmentos.count(),
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'segmentos/segmento_list.html', context)


@login_required
def segmento_create_view(request):
    """Criar novo segmento"""
    user = request.user
    
    print(f"DEBUG: segmento_create_view chamada. Método: {request.method}, User: {user.username}")
    
    # Proprietários e franqueados podem criar segmentos
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        print(f"DEBUG: POST data: {request.POST}")
        print(f"DEBUG: Is AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
        
        form = SegmentoForm(request.POST)
        if form.is_valid():
            segmento = form.save()
            print(f"DEBUG: Segmento criado com sucesso: ID={segmento.id}, Nome={segmento.nome}")
            messages.success(request, f'Segmento {segmento.nome} criado com sucesso!')
            
            # Se for AJAX, retornar JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({
                    'success': True,
                    'segmento': {
                        'id': segmento.id,
                        'nome': segmento.nome
                    }
                })
            
            return redirect('segmento_list')
        else:
            print(f"DEBUG: Formulário inválido. Erros: {form.errors}")
            
            # Se for AJAX, retornar erros
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Erro ao criar segmento. Verifique os dados.')
    else:
        form = SegmentoForm()
    
    context = {
        'form': form,
        'title': 'Novo Segmento',
        'button_text': 'Criar Segmento'
    }
    
    return render(request, 'segmentos/segmento_form.html', context)


@login_required
def segmento_update_view(request, pk):
    """Editar segmento"""
    user = request.user
    
    # Apenas proprietários podem editar segmentos
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    segmento = get_object_or_404(Segmento, pk=pk)
    
    if request.method == 'POST':
        form = SegmentoForm(request.POST, instance=segmento)
        if form.is_valid():
            segmento = form.save()
            messages.success(request, f'Segmento {segmento.nome} atualizado com sucesso!')
            return redirect('segmento_list')
        else:
            messages.error(request, 'Erro ao atualizar segmento. Verifique os dados.')
    else:
        form = SegmentoForm(instance=segmento)
    
    context = {
        'form': form,
        'segmento': segmento,
        'title': f'Editar Segmento: {segmento.nome}',
        'button_text': 'Salvar Alterações'
    }
    
    return render(request, 'segmentos/segmento_form.html', context)


@login_required
def segmento_delete_view(request, pk):
    """Deletar segmento"""
    user = request.user
    
    # Apenas proprietários podem deletar segmentos
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    segmento = get_object_or_404(Segmento, pk=pk)
    
    if request.method == 'POST':
        nome = segmento.nome
        
        # Verificar se há clientes usando este segmento
        total_clientes = segmento.clientes.count()
        if total_clientes > 0:
            messages.error(request, f'Não é possível deletar o segmento {nome} pois existem {total_clientes} cliente(s) vinculado(s).')
            return redirect('segmento_list')
        
        segmento.delete()
        messages.success(request, f'Segmento {nome} deletado com sucesso!')
        return redirect('segmento_list')
    
    # Contar clientes relacionados
    total_clientes = segmento.clientes.count()
    
    context = {
        'segmento': segmento,
        'total_clientes': total_clientes,
    }
    
    return render(request, 'segmentos/segmento_confirm_delete.html', context)


# Cliente Views
@login_required
def cliente_list_view(request):
    """Lista de clientes"""
    user = request.user
    
    # Apenas proprietários e franqueados podem ver clientes
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    clientes = Cliente.objects.select_related(
        'user', 'franqueado', 'segmento'
    ).prefetch_related('municipios').order_by('-created_at')
    
    # Franqueados veem apenas seus clientes
    if user.is_franchisee():
        clientes = clientes.filter(franqueado=user)
    
    # Filtros
    search = request.GET.get('search', '')
    franqueado_filter = request.GET.get('franqueado', '')
    municipio_filter = request.GET.get('municipio', '')
    
    if search:
        clientes = clientes.filter(
            Q(empresa__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    if franqueado_filter and user.is_owner():
        clientes = clientes.filter(franqueado_id=franqueado_filter)
    
    if municipio_filter:
        clientes = clientes.filter(municipios__id=municipio_filter).distinct()
    
    # Lista de franqueados e municípios para filtros
    franqueados = User.objects.filter(role='FRANCHISEE').order_by('username') if user.is_owner() else []
    
    if user.is_owner():
        municipios_filter = Municipio.objects.all().order_by('nome')
    else:
        municipios_filter = Municipio.objects.filter(franqueado=user).order_by('nome')
    
    context = {
        'clientes': clientes,
        'search': search,
        'franqueado_filter': franqueado_filter,
        'municipio_filter': municipio_filter,
        'franqueados': franqueados,
        'municipios_filter': municipios_filter,
    }
    
    return render(request, 'clientes/cliente_list.html', context)


@login_required
def cliente_create_view(request):
    """Criar novo cliente"""
    user = request.user
    
    # Apenas proprietários e franqueados podem criar clientes
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Dados do usuário
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Dados do cliente
        empresa = request.POST.get('empresa')
        segmento_id = request.POST.get('segmento')
        franqueado_id = request.POST.get('franqueado') if user.is_owner() else user.id
        municipios_ids = request.POST.getlist('municipios')
        observacoes = request.POST.get('observacoes', '')
        contrato = request.FILES.get('contrato')
        
        # Validações
        if not username or not password or not empresa or not segmento_id:
            messages.error(request, 'Username, senha, nome da empresa e segmento são obrigatórios.')
        elif password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Este username já está em uso.')
        elif email and User.objects.filter(email=email).exists():
            messages.error(request, 'Este email já está em uso.')
        elif not municipios_ids:
            messages.error(request, 'Selecione pelo menos um município.')
        else:
            # Validar regra: uma marca por segmento por cidade
            for municipio_id in municipios_ids:
                existe = Cliente.objects.filter(
                    segmento_id=segmento_id,
                    municipios__id=municipio_id
                )
                if existe.exists():
                    cliente_existente = existe.first()
                    municipio = Municipio.objects.get(id=municipio_id)
                    messages.error(request, 
                        f'Já existe o cliente "{cliente_existente.empresa}" '
                        f'no segmento "{cliente_existente.segmento.nome}" '
                        f'no município {municipio.nome}/{municipio.estado}. '
                        'Apenas uma marca por segmento por cidade é permitida.'
                    )
                    # Buscar segmentos para renderizar novamente
                    segmentos = Segmento.objects.filter(ativo=True).order_by('nome')
                    
                    if user.is_owner():
                        franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
                        municipios = Municipio.objects.all().select_related('franqueado').order_by('estado', 'nome')
                    else:
                        franqueados = []
                        municipios = Municipio.objects.filter(franqueado=user).order_by('estado', 'nome')
                    
                    return render(request, 'clientes/cliente_form.html', {
                        'franqueados': franqueados,
                        'municipios': municipios,
                        'segmentos': segmentos,
                    })
            
            # Criar usuário
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='CLIENT'
            )
            
            # Criar cliente
            cliente = Cliente.objects.create(
                user=new_user,
                empresa=empresa,
                segmento_id=segmento_id,
                franqueado_id=franqueado_id,
                observacoes=observacoes,
                contrato=contrato
            )
            
            # Vincular municípios
            cliente.municipios.set(municipios_ids)
            
            messages.success(request, f'Cliente {empresa} criado com sucesso!')
            return redirect('cliente_list')
    
    # Lista de franqueados e municípios para seleção
    if user.is_owner():
        franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
        municipios = Municipio.objects.all().select_related('franqueado').order_by('estado', 'nome')
    else:
        franqueados = []
        municipios = Municipio.objects.filter(franqueado=user).order_by('estado', 'nome')
    
    # Buscar segmentos ativos
    segmentos = Segmento.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'franqueados': franqueados,
        'municipios': municipios,
        'segmentos': segmentos,
    }
    
    return render(request, 'clientes/cliente_form.html', context)


@login_required
def cliente_update_view(request, pk):
    """Editar cliente existente"""
    user = request.user
    
    # Apenas proprietários e franqueados podem editar clientes
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    cliente = get_object_or_404(Cliente, pk=pk)
    
    # Franqueados só podem editar seus próprios clientes
    if user.is_franchisee() and cliente.franqueado != user:
        messages.error(request, 'Acesso negado.')
        return redirect('cliente_list')
    
    if request.method == 'POST':
        # Dados do usuário
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Dados do cliente
        empresa = request.POST.get('empresa')
        segmento_id = request.POST.get('segmento')
        franqueado_id = request.POST.get('franqueado') if user.is_owner() else cliente.franqueado_id
        municipios_ids = request.POST.getlist('municipios')
        observacoes = request.POST.get('observacoes', '')
        is_active = request.POST.get('is_active') == 'on'
        contrato = request.FILES.get('contrato')
        remover_contrato = request.POST.get('remover_contrato') == 'on'
        
        # Validações
        if not empresa or not segmento_id:
            messages.error(request, 'Nome da empresa e segmento são obrigatórios.')
        elif email and User.objects.filter(email=email).exclude(pk=cliente.user.pk).exists():
            messages.error(request, 'Este email já está em uso.')
        elif password and password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
        elif not municipios_ids:
            messages.error(request, 'Selecione pelo menos um município.')
        else:
            # Validar regra: uma marca por segmento por cidade
            for municipio_id in municipios_ids:
                existe = Cliente.objects.filter(
                    segmento_id=segmento_id,
                    municipios__id=municipio_id
                ).exclude(pk=cliente.pk)
                
                if existe.exists():
                    cliente_existente = existe.first()
                    municipio = Municipio.objects.get(id=municipio_id)
                    messages.error(request, 
                        f'Já existe o cliente "{cliente_existente.empresa}" '
                        f'no segmento "{cliente_existente.segmento.nome}" '
                        f'no município {municipio.nome}/{municipio.estado}. '
                        'Apenas uma marca por segmento por cidade é permitida.'
                    )
                    # Buscar segmentos para renderizar novamente
                    segmentos = Segmento.objects.filter(ativo=True).order_by('nome')
                    
                    if user.is_owner():
                        franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
                        municipios = Municipio.objects.all().select_related('franqueado').order_by('estado', 'nome')
                    else:
                        franqueados = []
                        municipios = Municipio.objects.filter(franqueado=user).order_by('estado', 'nome')
                    
                    return render(request, 'clientes/cliente_form.html', {
                        'cliente': cliente,
                        'franqueados': franqueados,
                        'municipios': municipios,
                        'segmentos': segmentos,
                    })
            
            # Atualizar usuário
            cliente.user.email = email
            cliente.user.first_name = first_name
            cliente.user.last_name = last_name
            cliente.user.is_active = is_active
            
            if password:
                cliente.user.set_password(password)
            
            cliente.user.save()
            
            # Atualizar cliente
            cliente.empresa = empresa
            cliente.segmento_id = segmento_id
            cliente.franqueado_id = franqueado_id
            cliente.observacoes = observacoes
            cliente.ativo = is_active
            
            # Atualizar contrato
            if remover_contrato:
                if cliente.contrato:
                    cliente.contrato.delete()
                cliente.contrato = None
            elif contrato:
                # Deletar contrato antigo se existir
                if cliente.contrato:
                    cliente.contrato.delete()
                cliente.contrato = contrato
            
            cliente.save()
            
            # Atualizar municípios
            cliente.municipios.set(municipios_ids)
            
            messages.success(request, f'Cliente {empresa} atualizado com sucesso!')
            return redirect('cliente_list')
    
    # Lista de franqueados e municípios para seleção
    if user.is_owner():
        franqueados = User.objects.filter(role='FRANCHISEE').order_by('username')
        municipios = Municipio.objects.all().select_related('franqueado').order_by('estado', 'nome')
    else:
        franqueados = []
        municipios = Municipio.objects.filter(franqueado=user).order_by('estado', 'nome')
    
    # Buscar segmentos ativos
    segmentos = Segmento.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'cliente': cliente,
        'franqueados': franqueados,
        'municipios': municipios,
        'segmentos': segmentos,
    }
    
    return render(request, 'clientes/cliente_form.html', context)


@login_required
def cliente_delete_view(request, pk):
    """Deletar cliente"""
    user = request.user
    
    # Apenas proprietários e franqueados podem deletar clientes
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    cliente = get_object_or_404(Cliente, pk=pk)
    
    # Franqueados só podem deletar seus próprios clientes
    if user.is_franchisee() and cliente.franqueado != user:
        messages.error(request, 'Acesso negado.')
        return redirect('cliente_list')
    
    if request.method == 'POST':
        empresa = cliente.empresa
        username = cliente.user.username
        
        # Deletar usuário e cliente (CASCADE)
        cliente.user.delete()
        
        messages.success(request, f'Cliente {empresa} ({username}) deletado com sucesso!')
        return redirect('cliente_list')
    
    # Contar vídeos relacionados
    total_videos = cliente.videos.count()
    
    context = {
        'cliente': cliente,
        'total_videos': total_videos,
    }
    
    return render(request, 'clientes/cliente_confirm_delete.html', context)


# =====================================
# APP MANAGEMENT VIEWS (OWNER ONLY)
# =====================================

@login_required
def app_upload_view(request):
    """Upload e gerenciamento de versões do aplicativo (OWNER ONLY)"""
    user = request.user
    
    # Apenas proprietários podem fazer upload
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AppVersionForm(request.POST, request.FILES)
        if form.is_valid():
            app_version = form.save(commit=False)
            app_version.uploaded_by = user
            app_version.save()
            messages.success(request, f'Versão {app_version.versao} enviada com sucesso!')
            return redirect('app_upload')
    else:
        form = AppVersionForm()
    
    # Listar todas as versões
    versions = AppVersion.objects.all()
    
    context = {
        'form': form,
        'versions': versions,
    }
    
    return render(request, 'app/app_upload.html', context)


@login_required
def app_version_toggle_view(request, pk):
    """Ativar/desativar uma versão do app (OWNER ONLY)"""
    user = request.user
    
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    app_version = get_object_or_404(AppVersion, pk=pk)
    app_version.ativo = not app_version.ativo
    app_version.save()
    
    status = 'ativada' if app_version.ativo else 'desativada'
    messages.success(request, f'Versão {app_version.versao} {status} com sucesso!')
    
    return redirect('app_upload')


@login_required
def app_version_delete_view(request, pk):
    """Deletar uma versão do app (OWNER ONLY)"""
    user = request.user
    
    if not user.is_owner():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    app_version = get_object_or_404(AppVersion, pk=pk)
    
    if request.method == 'POST':
        versao = app_version.versao
        # Deletar arquivo do storage
        if app_version.arquivo_apk:
            app_version.arquivo_apk.delete()
        app_version.delete()
        messages.success(request, f'Versão {versao} deletada com sucesso!')
        return redirect('app_upload')
    
    return redirect('app_upload')


def app_download_view(request):
    """Download público da versão ativa do aplicativo"""
    from django.http import FileResponse, Http404
    import os
    
    # Buscar versão ativa mais recente
    app_version = AppVersion.get_versao_ativa()
    
    if not app_version:
        messages.error(request, 'Nenhuma versão disponível para download no momento.')
        return redirect('login')
    
    # Incrementar contador de downloads
    app_version.downloads += 1
    app_version.save(update_fields=['downloads'])
    
    # Verificar se arquivo existe
    if not app_version.arquivo_apk or not os.path.exists(app_version.arquivo_apk.path):
        raise Http404("Arquivo não encontrado")
    
    # Retornar arquivo para download
    response = FileResponse(
        open(app_version.arquivo_apk.path, 'rb'),
        content_type='application/vnd.android.package-archive'
    )
    response['Content-Disposition'] = f'attachment; filename="MediaExpandTV-v{app_version.versao}.apk"'
    
    return response


# ============================================================
# QR CODE TRACKING
# ============================================================

def qrcode_redirect_view(request, tracking_code):
    """
    View pública que rastreia cliques no QR Code e redireciona ao destino.
    URL: /r/<tracking_code>/
    """
    from django.shortcuts import redirect as django_redirect
    
    try:
        video = Video.objects.get(qrcode_tracking_code=tracking_code)
    except Video.DoesNotExist:
        raise Http404("Link não encontrado")
    
    if not video.qrcode_url_destino:
        raise Http404("Link de destino não configurado")
    
    # Registrar o clique
    QRCodeClick.objects.create(
        video=video,
        tracking_code=tracking_code,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        referer=request.META.get('HTTP_REFERER', '')[:500] or None,
    )
    
    # Redirecionar ao destino do cliente
    return django_redirect(video.qrcode_url_destino)


def get_client_ip(request):
    """Obtém o IP real do cliente, considerando proxies"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ============================================================
# STREAMING DE MÍDIA COM SUPORTE A RANGE REQUESTS
# ============================================================

def serve_media_streaming(request, path):
    """
    Serve arquivos de mídia com suporte a HTTP Range Requests (RFC 7233).
    Permite streaming progressivo de vídeos grandes sem carregar tudo na memória.
    
    - Suporta Range requests (HTTP 206 Partial Content)
    - Streaming em chunks de 8MB para não sobrecarregar memória
    - Headers corretos para players de vídeo (Accept-Ranges, Content-Range)
    - Serve o range COMPLETO solicitado pelo player (não limita a 8MB)
    - Fallback para resposta completa com streaming quando Range não é solicitado
    """
    import os
    import mimetypes
    from django.http import StreamingHttpResponse, HttpResponse, Http404
    from django.conf import settings
    
    # Construir caminho completo e validar contra path traversal
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    full_path = os.path.normpath(full_path)
    media_root = os.path.normpath(str(settings.MEDIA_ROOT))
    
    if not full_path.startswith(media_root):
        raise Http404("Acesso negado")
    
    if not os.path.isfile(full_path):
        raise Http404("Arquivo não encontrado")
    
    # Detectar content type
    content_type, _ = mimetypes.guess_type(full_path)
    if not content_type:
        content_type = 'application/octet-stream'
    
    file_size = os.path.getsize(full_path)
    
    # Iterator que lê o arquivo em chunks de 8MB (não carrega tudo na memória)
    def file_iterator(file_path, start, end, chunk_size=8 * 1024 * 1024):
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data
    
    # Verificar se é um Range request
    range_header = request.META.get('HTTP_RANGE', '').strip()
    
    if range_header.startswith('bytes='):
        range_val = range_header[6:].split('-')
        start = int(range_val[0]) if range_val[0] else 0
        end = int(range_val[1]) if range_val[1] else file_size - 1
        end = min(end, file_size - 1)
        
        # Validar range
        if start >= file_size:
            response = HttpResponse(status=416)  # Range Not Satisfiable
            response['Content-Range'] = f'bytes */{file_size}'
            return response
        
        content_length = end - start + 1
        
        response = StreamingHttpResponse(
            file_iterator(full_path, start, end),
            status=206,
            content_type=content_type,
        )
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Content-Length'] = content_length
    else:
        # Sem Range header - resposta completa com streaming
        response = StreamingHttpResponse(
            file_iterator(full_path, 0, file_size - 1),
            content_type=content_type,
        )
        response['Content-Length'] = file_size
    
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = 'public, max-age=86400'
    return response


# ══════════════════════════════════════════════════════════
#  VIEWS: Conteúdo Corporativo & Configuração de API
# ══════════════════════════════════════════════════════════

@login_required
def conteudo_corporativo_list_view(request):
    """Lista de conteúdos corporativos"""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('dashboard')

    conteudos = ConteudoCorporativo.objects.all()
    search = request.GET.get('search', '')
    tipo_filter = request.GET.get('tipo', '')
    if search:
        conteudos = conteudos.filter(titulo__icontains=search)
    if tipo_filter:
        conteudos = conteudos.filter(tipo=tipo_filter)

    context = {
        'conteudos': conteudos,
        'tipos': ConteudoCorporativo.TIPO_CHOICES,
    }
    return render(request, 'corporativo/conteudo_list.html', context)


@login_required
def conteudo_corporativo_create_view(request):
    """Criar novo conteúdo corporativo"""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Você não tem permissão para criar conteúdo corporativo.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ConteudoCorporativoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conteúdo corporativo criado com sucesso!')
            return redirect('conteudo_corporativo_list')
    else:
        form = ConteudoCorporativoForm()

    return render(request, 'corporativo/conteudo_form.html', {'form': form})


@login_required
def conteudo_corporativo_update_view(request, pk):
    """Editar conteúdo corporativo"""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    conteudo = get_object_or_404(ConteudoCorporativo, pk=pk)
    if request.method == 'POST':
        form = ConteudoCorporativoForm(request.POST, instance=conteudo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conteúdo corporativo atualizado!')
            return redirect('conteudo_corporativo_list')
    else:
        form = ConteudoCorporativoForm(instance=conteudo)

    return render(request, 'corporativo/conteudo_form.html', {'form': form, 'conteudo': conteudo})


@login_required
def conteudo_corporativo_delete_view(request, pk):
    """Deletar conteúdo corporativo"""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    conteudo = get_object_or_404(ConteudoCorporativo, pk=pk)
    if request.method == 'POST':
        conteudo.delete()
        messages.success(request, 'Conteúdo corporativo deletado!')
        return redirect('conteudo_corporativo_list')

    return render(request, 'corporativo/conteudo_confirm_delete.html', {'conteudo': conteudo})


@login_required
def conteudo_corporativo_preview_view(request, pk):
    """Preview de dados ao vivo de um conteúdo corporativo.
    Para previsão do tempo, o município é o da playlist vinculada — igual ao que
    o app Android recebe. O usuário pode escolher qual playlist simular.
    """
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    conteudo = get_object_or_404(ConteudoCorporativo, pk=pk)
    from .services import buscar_dados_corporativos

    # Playlists que contêm este conteúdo
    playlists_qs = Playlist.objects.filter(
        items__conteudo_corporativo=conteudo
    ).select_related('municipio').distinct()
    if user.is_franchisee():
        playlists_qs = playlists_qs.filter(franqueado=user)

    municipio = None
    playlist_selecionada = None
    if conteudo.tipo == 'PREVISAO_TEMPO':
        playlist_id = request.GET.get('playlist_id')
        if playlist_id:
            playlist_selecionada = playlists_qs.filter(pk=playlist_id).first()
        if not playlist_selecionada:
            # Preferir playlist com município com coordenadas
            playlist_selecionada = (
                playlists_qs.exclude(municipio__latitude=None).first()
                or playlists_qs.first()
            )
        if playlist_selecionada:
            municipio = playlist_selecionada.municipio

    dados = buscar_dados_corporativos(conteudo.tipo, municipio=municipio)
    config = ConfiguracaoAPI.get_config()

    context = {
        'conteudo': conteudo,
        'dados': dados,
        'config': config,
        'municipio': municipio,
        'playlists': playlists_qs if conteudo.tipo == 'PREVISAO_TEMPO' else [],
        'playlist_selecionada': playlist_selecionada,
    }
    return render(request, 'corporativo/conteudo_preview.html', context)


@login_required
def configuracao_api_view(request):
    """Configuração das APIs externas (apenas OWNER)"""
    user = request.user
    if not user.is_owner():
        messages.error(request, 'Apenas o administrador pode configurar as APIs.')
        return redirect('dashboard')

    config = ConfiguracaoAPI.get_config()
    config.resetar_contadores_se_necessario()

    if request.method == 'POST':
        form = ConfiguracaoAPIForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações de API atualizadas!')
            return redirect('configuracao_api')
    else:
        form = ConfiguracaoAPIForm(instance=config)

    context = {
        'form': form,
        'config': config,
    }
    return render(request, 'corporativo/configuracao_api.html', context)


# ═══════════════════════════════════════════════════════════
#  DESIGN EDITOR — Editor Canva/PPT dentro do Corporativo
# ═══════════════════════════════════════════════════════════

@login_required
def design_editor_view(request, pk=None):
    """
    Editor visual (Fabric.js) para criar ou editar um design corporativo.
    Se pk=None → novo design. Se pk → editar existente.
    """
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    conteudo = None
    if pk:
        conteudo = get_object_or_404(ConteudoCorporativo, pk=pk, tipo='DESIGN')

    # Categorias de template para seletor
    categorias = (
        ConteudoCorporativo.objects
        .filter(tipo='DESIGN', is_template=True, template_categoria__gt='')
        .values_list('template_categoria', flat=True)
        .distinct()
        .order_by('template_categoria')
    )

    context = {
        'conteudo': conteudo,
        'categorias': list(categorias),
    }
    return render(request, 'corporativo/design_editor.html', context)


@login_required
def design_save_api(request, pk=None):
    """
    AJAX POST → salva ou atualiza design (JSON canvas + thumbnail base64).
    Retorna JSON {success, id, message}.
    """
    import json, base64, uuid
    from django.core.files.base import ContentFile
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)

    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        return JsonResponse({'success': False, 'message': 'Sem permissão'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido'}, status=400)

    titulo = data.get('titulo', '').strip()
    design_json = data.get('design_json')
    thumbnail_b64 = data.get('thumbnail')  # data:image/png;base64,...
    largura = int(data.get('largura', 1920))
    altura = int(data.get('altura', 1080))
    duracao = int(data.get('duracao_segundos', 15))
    is_template = bool(data.get('is_template', False))
    template_cat = data.get('template_categoria', '')

    if not titulo:
        return JsonResponse({'success': False, 'message': 'Título é obrigatório'}, status=400)
    if not design_json:
        return JsonResponse({'success': False, 'message': 'Design vazio'}, status=400)

    if pk:
        conteudo = get_object_or_404(ConteudoCorporativo, pk=pk, tipo='DESIGN')
    else:
        conteudo = ConteudoCorporativo(tipo='DESIGN')

    conteudo.titulo = titulo
    conteudo.design_json = design_json
    conteudo.design_largura = largura
    conteudo.design_altura = altura
    conteudo.duracao_segundos = duracao
    conteudo.is_template = is_template
    conteudo.template_categoria = template_cat

    # Salvar thumbnail PNG
    if thumbnail_b64 and ',' in thumbnail_b64:
        fmt, imgstr = thumbnail_b64.split(',', 1)
        ext = 'png'
        filename = f'design_{uuid.uuid4().hex[:8]}.{ext}'
        conteudo.design_thumbnail.save(filename, ContentFile(base64.b64decode(imgstr)), save=False)

    conteudo.save()

    return JsonResponse({
        'success': True,
        'id': conteudo.pk,
        'message': 'Design salvo com sucesso!',
    })


@login_required
def design_list_view(request):
    """Lista de designs criados (não-templates) com grid de thumbnails."""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    designs = ConteudoCorporativo.objects.filter(tipo='DESIGN', is_template=False).order_by('-updated_at')

    search = request.GET.get('search', '')
    if search:
        designs = designs.filter(titulo__icontains=search)

    context = {
        'designs': designs,
        'search': search,
    }
    return render(request, 'corporativo/design_list.html', context)


@login_required
def design_template_gallery_view(request):
    """Galeria de modelos (templates reutilizáveis)."""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    templates = ConteudoCorporativo.objects.filter(tipo='DESIGN', is_template=True, ativo=True).order_by('template_categoria', 'titulo')

    categoria = request.GET.get('categoria', '')
    search = request.GET.get('search', '')
    if categoria:
        templates = templates.filter(template_categoria=categoria)
    if search:
        templates = templates.filter(titulo__icontains=search)

    categorias = (
        ConteudoCorporativo.objects
        .filter(tipo='DESIGN', is_template=True, template_categoria__gt='')
        .values_list('template_categoria', flat=True)
        .distinct()
        .order_by('template_categoria')
    )

    context = {
        'templates': templates,
        'categorias': list(categorias),
        'categoria_selecionada': categoria,
        'search': search,
    }
    return render(request, 'corporativo/design_template_gallery.html', context)


@login_required
def design_duplicate_view(request, pk):
    """Duplica um design existente (ou template) como novo design pessoal."""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    original = get_object_or_404(ConteudoCorporativo, pk=pk, tipo='DESIGN')

    novo = ConteudoCorporativo(
        titulo=f'{original.titulo} (Cópia)',
        tipo='DESIGN',
        duracao_segundos=original.duracao_segundos,
        design_json=original.design_json,
        design_largura=original.design_largura,
        design_altura=original.design_altura,
        is_template=False,
        template_categoria='',
        ativo=True,
    )
    # Copiar thumbnail
    if original.design_thumbnail:
        from django.core.files.base import ContentFile
        import uuid
        novo.design_thumbnail.save(
            f'design_{uuid.uuid4().hex[:8]}.png',
            ContentFile(original.design_thumbnail.read()),
            save=False,
        )
    novo.save()
    messages.success(request, f'Design duplicado! Editando "{novo.titulo}".')
    return redirect('design_editor_edit', pk=novo.pk)


@login_required
def design_delete_view(request, pk):
    """Deletar design."""
    user = request.user
    if not user.is_owner() and not user.is_franchisee():
        messages.error(request, 'Sem permissão.')
        return redirect('dashboard')

    conteudo = get_object_or_404(ConteudoCorporativo, pk=pk, tipo='DESIGN')

    if request.method == 'POST':
        titulo = conteudo.titulo
        conteudo.delete()
        messages.success(request, f'Design "{titulo}" removido.')
        return redirect('design_list')

    return render(request, 'corporativo/design_confirm_delete.html', {'conteudo': conteudo})


def design_render_tv_view(request, pk):
    """
    Renderiza o design como HTML/SVG estático para o app de TV (WebView).
    Usa Fabric.js para gerar canvas a partir do JSON salvo.
    """
    conteudo = get_object_or_404(ConteudoCorporativo, pk=pk, tipo='DESIGN')
    import json
    context = {
        'conteudo': conteudo,
        'design_json': json.dumps(conteudo.design_json) if conteudo.design_json else '{}',
    }
    return render(request, 'corporativo/design_tv_render.html', context)

