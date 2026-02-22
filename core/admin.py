from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, Municipio, Cliente, Video, 
    Playlist, PlaylistItem, DispositivoTV, AgendamentoExibicao, LogExibicao, AppVersion,
    QRCodeClick
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_active_user', 'created_at')
    list_filter = ('role', 'is_active_user', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'cpf_cnpj')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('role', 'phone', 'cpf_cnpj', 'created_by', 'is_active_user')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informações Adicionais', {
            'fields': ('role', 'phone', 'cpf_cnpj', 'email', 'first_name', 'last_name')
        }),
    )


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'estado', 'franqueado', 'ativo', 'created_at')
    list_filter = ('estado', 'ativo', 'franqueado')
    search_fields = ('nome', 'estado', 'franqueado__username')
    ordering = ('estado', 'nome')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'user', 'franqueado', 'ativo', 'created_at')
    list_filter = ('ativo', 'franqueado')
    search_fields = ('empresa', 'user__username', 'user__email')
    filter_horizontal = ('municipios',)
    ordering = ('-created_at',)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'cliente', 'status', 'duracao_segundos', 'get_file_size_display', 'has_qrcode', 'get_qrcode_clicks', 'ativo', 'created_at')
    list_filter = ('status', 'ativo', 'cliente__franqueado')
    search_fields = ('titulo', 'descricao', 'cliente__empresa')
    readonly_fields = ('created_at', 'updated_at', 'get_thumbnail_preview', 'qrcode_tracking_code')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': ('cliente', 'titulo', 'descricao', 'arquivo', 'duracao_segundos', 'thumbnail', 'status', 'ativo')
        }),
        ('QR Code', {
            'fields': ('qrcode_url_destino', 'qrcode_descricao', 'qrcode_tracking_code'),
            'classes': ('collapse',),
            'description': 'Configure um QR Code interativo para exibir junto ao vídeo na TV.'
        }),
        ('Tarja Inferior', {
            'fields': ('texto_tarja',),
            'classes': ('collapse',),
            'description': 'Texto exibido em tarja na parte inferior da TV durante o vídeo (estilo CNN).'
        }),
        ('Informações', {
            'fields': ('created_at', 'updated_at', 'get_thumbnail_preview'),
        }),
    )
    
    def get_file_size_display(self, obj):
        return f"{obj.get_file_size()} MB"
    get_file_size_display.short_description = 'Tamanho'
    
    def get_thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="300" />', obj.thumbnail.url)
        return "Sem thumbnail"
    get_thumbnail_preview.short_description = 'Preview'
    
    def has_qrcode(self, obj):
        if obj.qrcode_url_destino:
            return format_html('<span style="color: green;">\u2713</span>')
        return format_html('<span style="color: gray;">\u2014</span>')
    has_qrcode.short_description = 'QR Code'
    
    def get_qrcode_clicks(self, obj):
        count = obj.qrcode_clicks.count()
        if count > 0:
            return format_html('<strong>{}</strong>', count)
        return '0'
    get_qrcode_clicks.short_description = 'Clicks QR'


class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 1
    fields = ('video', 'ordem', 'repeticoes', 'ativo')
    ordering = ('ordem',)


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('nome', 'municipio', 'franqueado', 'get_total_videos', 'duracao_total_segundos', 'ativa', 'created_at')
    list_filter = ('ativa', 'franqueado', 'municipio__estado')
    search_fields = ('nome', 'descricao', 'municipio__nome')
    inlines = [PlaylistItemInline]
    ordering = ('-created_at',)
    
    def get_total_videos(self, obj):
        return obj.items.count()
    get_total_videos.short_description = 'Total de Vídeos'


@admin.register(PlaylistItem)
class PlaylistItemAdmin(admin.ModelAdmin):
    list_display = ('playlist', 'video', 'ordem', 'repeticoes', 'ativo', 'created_at')
    list_filter = ('ativo', 'playlist')
    search_fields = ('playlist__nome', 'video__titulo')
    ordering = ('playlist', 'ordem')


@admin.register(DispositivoTV)
class DispositivoTVAdmin(admin.ModelAdmin):
    list_display = ('nome', 'identificador_unico', 'municipio', 'playlist_atual', 'ativo', 'ultima_sincronizacao')
    list_filter = ('ativo', 'municipio__estado', 'municipio')
    search_fields = ('nome', 'identificador_unico', 'localizacao')
    readonly_fields = ('ultima_sincronizacao', 'created_at', 'updated_at')
    ordering = ('municipio', 'nome')


@admin.register(AgendamentoExibicao)
class AgendamentoExibicaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'dispositivo', 'get_dias_semana', 'hora_inicio', 'hora_fim', 'ativo', 'created_at')
    list_filter = ('ativo', 'dispositivo__municipio')
    search_fields = ('nome', 'dispositivo__nome')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('dispositivo', 'hora_inicio')
    
    def get_dias_semana(self, obj):
        return obj.get_dias_display()
    get_dias_semana.short_description = 'Dias da Semana'


@admin.register(LogExibicao)
class LogExibicaoAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'video', 'playlist', 'data_hora_inicio', 'data_hora_fim', 'completamente_exibido')
    list_filter = ('completamente_exibido', 'dispositivo__municipio', 'data_hora_inicio')
    search_fields = ('dispositivo__nome', 'video__titulo', 'playlist__nome')
    readonly_fields = ('created_at',)
    ordering = ('-data_hora_inicio',)
    date_hierarchy = 'data_hora_inicio'


@admin.register(AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    list_display = ('versao', 'ativo', 'tamanho_formatado', 'downloads', 'uploaded_by', 'created_at')
    list_filter = ('ativo', 'created_at')
    search_fields = ('versao', 'notas_versao')
    readonly_fields = ('tamanho', 'downloads', 'uploaded_by', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def tamanho_formatado(self, obj):
        return obj.get_tamanho_formatado()
    tamanho_formatado.short_description = 'Tamanho'


@admin.register(QRCodeClick)
class QRCodeClickAdmin(admin.ModelAdmin):
    list_display = ('video', 'ip_address', 'created_at')
    list_filter = ('created_at', 'video__cliente')
    search_fields = ('video__titulo', 'ip_address')
    readonly_fields = ('video', 'tracking_code', 'ip_address', 'user_agent', 'referer', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
