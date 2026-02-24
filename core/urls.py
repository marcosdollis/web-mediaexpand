from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, MunicipioViewSet, ClienteViewSet, VideoViewSet,
    PlaylistViewSet, PlaylistItemViewSet, DispositivoTVViewSet,
    LogExibicaoViewSet, TVAPIView, TVLogExibicaoView, TVCheckScheduleView,
    TVCorporativoHTMLView, DashboardStatsView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'municipios', MunicipioViewSet, basename='municipio')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'videos', VideoViewSet, basename='video')
router.register(r'playlists', PlaylistViewSet, basename='playlist')
router.register(r'playlist-items', PlaylistItemViewSet, basename='playlist-item')
router.register(r'dispositivos', DispositivoTVViewSet, basename='dispositivo')
router.register(r'logs-exibicao', LogExibicaoViewSet, basename='log-exibicao')

urlpatterns = [
    path('', include(router.urls)),
    
    # API para TV App
    path('tv/auth/', TVAPIView.as_view(), name='tv-auth'),
    path('tv/log-exibicao/', TVLogExibicaoView.as_view(), name='tv-log-exibicao'),
    path('tv/check-schedule/<uuid:identificador_unico>/', TVCheckScheduleView.as_view(), name='tv-check-schedule'),
    path('tv/corporativo/<str:tipo>/<int:playlist_id>/', TVCorporativoHTMLView.as_view(), name='tv-corporativo-html'),
    
    # Dashboard
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
]
