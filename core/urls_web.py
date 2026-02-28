from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home_view, name='home'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/metricas/', views.cliente_metricas_view, name='cliente_metricas'),

    # Users
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/update/', views.user_update_view, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete_view, name='user_delete'),

    # Municipios
    path('municipios/', views.municipio_list_view, name='municipio_list'),
    path('municipios/create/', views.municipio_create_view, name='municipio_create'),
    path('municipios/<int:pk>/update/', views.municipio_update_view, name='municipio_update'),
    path('municipios/<int:pk>/delete/', views.municipio_delete_view, name='municipio_delete'),

    # Segmentos
    path('segmentos/', views.segmento_list_view, name='segmento_list'),
    path('segmentos/create/', views.segmento_create_view, name='segmento_create'),
    path('segmentos/<int:pk>/update/', views.segmento_update_view, name='segmento_update'),
    path('segmentos/<int:pk>/delete/', views.segmento_delete_view, name='segmento_delete'),

    # Clientes
    path('clientes/', views.cliente_list_view, name='cliente_list'),
    path('clientes/create/', views.cliente_create_view, name='cliente_create'),
    path('clientes/<int:pk>/update/', views.cliente_update_view, name='cliente_update'),
    path('clientes/<int:pk>/delete/', views.cliente_delete_view, name='cliente_delete'),

    # Videos
    path('videos/', views.video_list_view, name='video_list'),
    path('videos/create/', views.video_create_view, name='video_create'),
    path('videos/<int:pk>/update/', views.video_update_view, name='video_update'),
    path('videos/<int:pk>/approve/', views.video_approve_view, name='video_approve'),
    path('videos/<int:pk>/reject/', views.video_reject_view, name='video_reject'),
    path('videos/<int:pk>/delete/', views.video_delete_view, name='video_delete'),
    path('videos/<int:pk>/qrcode-metricas/', views.video_qrcode_metricas_view, name='video_qrcode_metricas'),

    # Playlists
    path('playlists/', views.playlist_list_view, name='playlist_list'),
    path('playlists/create/', views.playlist_create_view, name='playlist_create'),
    path('playlists/<int:pk>/', views.playlist_detail_view, name='playlist_detail'),
    path('playlists/<int:pk>/update/', views.playlist_update_view, name='playlist_update'),
    path('playlists/<int:pk>/delete/', views.playlist_delete_view, name='playlist_delete'),

    # Dispositivos
    path('dispositivos/', views.dispositivo_list_view, name='dispositivo_list'),
    path('dispositivos/create/', views.dispositivo_create_view, name='dispositivo_create'),
    path('dispositivos/<int:pk>/', views.dispositivo_detail_view, name='dispositivo_detail'),
    path('dispositivos/<int:pk>/update/', views.dispositivo_update_view, name='dispositivo_update'),
    path('dispositivos/<int:pk>/delete/', views.dispositivo_delete_view, name='dispositivo_delete'),
    
    # Agendamentos de Exibição (vinculação playlist → dispositivo)
    path('dispositivos/<int:dispositivo_pk>/agendamentos/create/', views.agendamento_create_view, name='agendamento_create'),
    path('dispositivos/<int:dispositivo_pk>/agendamentos/<int:pk>/update/', views.agendamento_update_view, name='agendamento_update'),
    path('dispositivos/<int:dispositivo_pk>/agendamentos/<int:pk>/delete/', views.agendamento_delete_view, name='agendamento_delete'),
    
    # Horários de Funcionamento (ligar/desligar do dispositivo)
    path('dispositivos/<int:dispositivo_pk>/horarios/create/', views.horario_create_view, name='horario_create'),
    path('dispositivos/<int:dispositivo_pk>/horarios/<int:pk>/update/', views.horario_update_view, name='horario_update'),
    path('dispositivos/<int:dispositivo_pk>/horarios/<int:pk>/delete/', views.horario_delete_view, name='horario_delete'),
    
    # App Management (OWNER ONLY)
    path('app/upload/', views.app_upload_view, name='app_upload'),
    path('app/version/<int:pk>/toggle/', views.app_version_toggle_view, name='app_version_toggle'),
    path('app/version/<int:pk>/delete/', views.app_version_delete_view, name='app_version_delete'),
    path('app/download/', views.app_download_view, name='app_download'),

    # Conteúdos Corporativos
    path('corporativo/', views.conteudo_corporativo_list_view, name='conteudo_corporativo_list'),
    path('corporativo/create/', views.conteudo_corporativo_create_view, name='conteudo_corporativo_create'),
    path('corporativo/<int:pk>/update/', views.conteudo_corporativo_update_view, name='conteudo_corporativo_update'),
    path('corporativo/<int:pk>/delete/', views.conteudo_corporativo_delete_view, name='conteudo_corporativo_delete'),
    path('corporativo/<int:pk>/preview/', views.conteudo_corporativo_preview_view, name='conteudo_corporativo_preview'),
    path('corporativo/configuracao/', views.configuracao_api_view, name='configuracao_api'),

    # Design Editor (Corporativo)
    path('corporativo/designs/', views.design_list_view, name='design_list'),
    path('corporativo/design/create/', views.design_editor_view, name='design_editor_create'),
    path('corporativo/design/<int:pk>/edit/', views.design_editor_view, name='design_editor_edit'),
    path('corporativo/design/save/', views.design_save_api, name='design_save_new'),
    path('corporativo/design/<int:pk>/save/', views.design_save_api, name='design_save'),
    path('corporativo/design/<int:pk>/duplicate/', views.design_duplicate_view, name='design_duplicate'),
    path('corporativo/design/<int:pk>/delete/', views.design_delete_view, name='design_delete'),
    path('corporativo/design/templates/', views.design_template_gallery_view, name='design_template_gallery'),
    path('corporativo/design/<int:pk>/render/', views.design_render_tv_view, name='design_render_tv'),
    path('corporativo/design/import-pptx/', views.design_import_pptx_view, name='design_import_pptx'),
    path('corporativo/design/upload-audio/', views.design_audio_upload_view, name='design_audio_upload'),
]