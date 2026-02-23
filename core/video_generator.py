"""
Gerador de vídeos para conteúdos corporativos (previsão do tempo, cotações, notícias).

Gera imagens com Pillow e converte para MP4 com imageio-ffmpeg (ffmpeg embutido).
Cada playlist pode ter sua própria versão do vídeo (ex: clima específico do município).
Os vídeos são gerenciados com TTL baseado nas configurações de cache da ConfiguracaoAPI.
"""

import hashlib
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30        # FPS padrão — compatível com qualquer player
CORP_VIDEO_DIR = 'corporativo_videos'

# ── Paleta de cores (inspirada no preview web) ──
WHITE       = (255, 255, 255)
WHITE_90    = (255, 255, 255, 230)
WHITE_70    = (255, 255, 255, 178)
WHITE_50    = (255, 255, 255, 128)
WHITE_20    = (255, 255, 255, 51)
WHITE_10    = (255, 255, 255, 26)
GRAY_TEXT   = (200, 200, 220)
GRAY_DIM    = (140, 140, 165)
GREEN       = (46, 204, 113)
RED         = (231, 76, 60)
YELLOW      = (241, 196, 15)
BLUE        = (52, 152, 219)
CYAN        = (26, 188, 156)
BRAND       = (0, 120, 255)
BRAND_LIGHT = (60, 160, 255)

# Setas de variação
ARROW_UP   = '\u25B2'
ARROW_DOWN = '\u25BC'
DOT        = '\u25CF'


# ══════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════

def _get_output_dir():
    media_root = Path(settings.MEDIA_ROOT)
    output = media_root / CORP_VIDEO_DIR
    output.mkdir(parents=True, exist_ok=True)
    return output


def _get_media_url(filename):
    return f'{settings.MEDIA_URL}{CORP_VIDEO_DIR}/{filename}'


def _video_cache_key(tipo, playlist_id):
    return f'{tipo.lower()}_{playlist_id}'


_font_cache = {}

def _font(size, bold=False):
    """Carrega e cacheia fonte TrueType."""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    candidates = (
        [
            'C:/Windows/Fonts/arialbd.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        ] if bold else [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size)
                _font_cache[key] = f
                return f
            except Exception:
                continue
    try:
        f = ImageFont.truetype('arial.ttf', size)
    except Exception:
        f = ImageFont.load_default()
    _font_cache[key] = f
    return f


def _text_w(draw, text, font):
    """Largura do texto."""
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _center_text(draw, text, font, y, fill, x_center=VIDEO_WIDTH // 2):
    """Desenha texto centralizado horizontalmente."""
    w = _text_w(draw, text, font)
    draw.text((x_center - w // 2, y), text, fill=fill, font=font)


def _right_text(draw, text, font, y, fill, right_margin=60):
    """Desenha texto alinhado à direita."""
    w = _text_w(draw, text, font)
    draw.text((VIDEO_WIDTH - w - right_margin, y), text, fill=fill, font=font)


def _gradient_bg(img, color_a, color_b, diagonal=False):
    """Aplica gradiente no fundo da imagem."""
    w, h = img.size
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            ratio = ((x / w) + (y / h)) / 2 if diagonal else y / h
            r = int(color_a[0] + (color_b[0] - color_a[0]) * ratio)
            g = int(color_a[1] + (color_b[1] - color_a[1]) * ratio)
            b = int(color_a[2] + (color_b[2] - color_a[2]) * ratio)
            pixels[x, y] = (r, g, b)


def _glass_rect(base_img, draw, xy, radius=16, opacity=0.12, border_color=None):
    """Desenha um retângulo com efeito 'glass' semi-transparente."""
    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    fill = (255, 255, 255, int(255 * opacity))
    ov_draw.rounded_rectangle(xy, radius=radius, fill=fill)
    if border_color:
        ov_draw.rounded_rectangle(xy, radius=radius, outline=border_color, width=1)
    composite = Image.alpha_composite(base_img.convert('RGBA'), overlay)
    base_img.paste(composite.convert('RGB'), (0, 0))
    return ImageDraw.Draw(base_img)


def _header_bar(img, draw, subtitle, right_text_str=''):
    """Barra superior de branding."""
    draw = _glass_rect(img, draw, (0, 0, VIDEO_WIDTH, 80), radius=0, opacity=0.35)
    draw.line([(0, 80), (VIDEO_WIDTH, 80)], fill=BRAND, width=3)

    draw.text((50, 16), 'MEDIAEXPAND', fill=BRAND_LIGHT, font=_font(30, bold=True))
    draw.text((50, 50), subtitle, fill=GRAY_DIM, font=_font(18))

    now = timezone.localtime()
    time_str = now.strftime('%d/%m/%Y   %H:%M')
    _right_text(draw, time_str, _font(20), 28, GRAY_TEXT, 50)

    if right_text_str:
        _right_text(draw, right_text_str, _font(22, bold=True), 50, WHITE, 50)

    return draw


def _footer_bar(draw, text):
    """Rodapé com fonte de dados."""
    draw.text((50, VIDEO_HEIGHT - 45), text, fill=GRAY_DIM, font=_font(16))


def _var_color_arrow(variacao, direcao):
    """Retorna (cor, seta) baseado na direção."""
    if direcao == 'up':
        return GREEN, ARROW_UP
    elif direcao == 'down':
        return RED, ARROW_DOWN
    return YELLOW, DOT


def _format_brl(value, decimals=2):
    """Formata valor em padrão brasileiro: 1.234,56"""
    if value is None:
        return '—'
    fmt = f'{value:,.{decimals}f}'
    return fmt.replace(',', 'X').replace('.', ',').replace('X', '.')


def _image_to_video(image, duration_seconds, output_path):
    """Converte imagem PIL em vídeo MP4 usando ffmpeg embutido do imageio-ffmpeg."""
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.error(f'imageio-ffmpeg não disponível: {e}')
        return False

    temp_png = str(output_path).replace('.mp4', '_frame.png')
    try:
        image.save(temp_png, 'PNG')
        cmd = [
            ffmpeg_path, '-y',
            '-loop', '1',
            '-i', temp_png,
            '-c:v', 'libx264',
            '-t', str(duration_seconds),
            '-pix_fmt', 'yuv420p',
            '-r', str(VIDEO_FPS),
            '-preset', 'ultrafast',
            '-tune', 'stillimage',
            '-vf', f'scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}',
            '-movflags', '+faststart',
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            logger.error(f'ffmpeg erro: {result.stderr.decode("utf-8", errors="replace")[:500]}')
            return False
        logger.info(f'Vídeo gerado: {output_path} ({duration_seconds}s, {VIDEO_FPS}fps)')
        return True
    except Exception as e:
        logger.error(f'Erro ao gerar vídeo: {e}')
        return False
    finally:
        if os.path.exists(temp_png):
            os.remove(temp_png)


# ══════════════════════════════════════════════════════════════════════
#  PREVISÃO DO TEMPO
# ══════════════════════════════════════════════════════════════════════

_WEATHER_GRADIENTS = {
    'ensolarado': ((255, 140, 0),  (255, 215, 0)),
    'nublado':    ((99, 111, 164), (232, 203, 192)),
    'chuvoso':    ((44, 62, 80),   (52, 152, 219)),
    'tempestade': ((15, 32, 39),   (44, 83, 100)),
}

_DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']


def _gerar_imagem_previsao(dados):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (30, 30, 50))

    municipio = dados.get('municipio', '')
    atual = dados.get('atual', {})
    previsao = dados.get('previsao', [])
    condicao = atual.get('condicao', 'nublado')

    grad = _WEATHER_GRADIENTS.get(condicao, _WEATHER_GRADIENTS['nublado'])
    _gradient_bg(img, grad[0], grad[1], diagonal=True)
    draw = ImageDraw.Draw(img)

    draw = _header_bar(img, draw, 'PREVISÃO DO TEMPO', municipio)

    # ── Painel central ──
    temp = atual.get('temperatura')
    temp_str = f'{temp:.0f}°C' if temp is not None else '--°C'
    desc_str = atual.get('descricao', 'Indisponível')

    # Área glass atrás da temperatura
    draw = _glass_rect(img, draw,
                       (VIDEO_WIDTH // 2 - 250, 120, VIDEO_WIDTH // 2 + 250, 460),
                       radius=30, opacity=0.10)

    # Cidade
    if municipio:
        _center_text(draw, municipio, _font(30, bold=True), 140, WHITE_90)

    # Temperatura grande
    _center_text(draw, temp_str, _font(150, bold=True), 180, WHITE)

    # Descrição
    _center_text(draw, desc_str, _font(34), 365, GRAY_TEXT)

    # Detalhes (umidade + vento)
    umidade = atual.get('umidade')
    vento = atual.get('vento_kmh')
    details = []
    if umidade is not None:
        details.append(f'Umidade  {umidade}%')
    if vento is not None:
        details.append(f'Vento  {vento:.0f} km/h')
    if details:
        _center_text(draw, '     |     '.join(details), _font(24), 420, GRAY_DIM)

    # ── Separador ──
    sep_y = 490
    draw.line([(200, sep_y), (VIDEO_WIDTH - 200, sep_y)],
              fill=(255, 255, 255, 40), width=1)

    # ── Previsão 3 dias — cards estilo glass ──
    if previsao:
        n = min(len(previsao), 3)
        card_w = 480
        card_h = 440
        gap = 50
        total = card_w * n + gap * (n - 1)
        sx = (VIDEO_WIDTH - total) // 2
        cy_start = sep_y + 30

        for i, dia in enumerate(previsao[:3]):
            cx = sx + i * (card_w + gap)
            cy = cy_start

            draw = _glass_rect(img, draw,
                               (cx, cy, cx + card_w, cy + card_h),
                               radius=20, opacity=0.12,
                               border_color=(255, 255, 255, 40))

            # Nome do dia
            data_raw = dia.get('data', '')
            try:
                dt = datetime.strptime(data_raw, '%Y-%m-%d')
                dia_nome = _DIAS_SEMANA[dt.weekday()]
                data_fmt = dt.strftime('%d/%m')
                label = f'{dia_nome}  {data_fmt}'
            except Exception:
                label = data_raw
            _center_text(draw, label, _font(26, bold=True), cy + 25, CYAN, cx + card_w // 2)

            # Condição
            desc_d = dia.get('descricao', '')
            _center_text(draw, desc_d, _font(24), cy + 70, WHITE, cx + card_w // 2)

            # Temperaturas max / min
            tmax = dia.get('max')
            tmin = dia.get('min')
            max_s = f'{tmax:.0f}°' if tmax is not None else '--°'
            min_s = f'{tmin:.0f}°' if tmin is not None else '--°'

            # Máxima em grande
            _center_text(draw, max_s, _font(80, bold=True), cy + 120, WHITE, cx + card_w // 2 - 60)
            # Barra separadora
            draw.text((cx + card_w // 2 - 15, cy + 150), '/', fill=GRAY_DIM, font=_font(50))
            # Mínima
            _center_text(draw, min_s, _font(60, bold=True), cy + 145, GRAY_TEXT, cx + card_w // 2 + 70)

            # Labels
            _center_text(draw, 'máx', _font(18), cy + 225, GRAY_DIM, cx + card_w // 2 - 60)
            _center_text(draw, 'mín', _font(18), cy + 225, GRAY_DIM, cx + card_w // 2 + 70)

            # Linha separadora dentro do card
            draw.line([(cx + 40, cy + 260), (cx + card_w - 40, cy + 260)],
                      fill=(255, 255, 255, 30), width=1)

            # Precipitação
            prec = dia.get('precipitacao_pct', 0)
            if prec:
                prec_str = f'Chuva  {prec}%'
                prec_color = BLUE if prec < 50 else RED
                _center_text(draw, prec_str, _font(24), cy + 280, prec_color, cx + card_w // 2)

            # Condição climática
            cond_d = dia.get('condicao', '')
            if cond_d:
                cond_label = {
                    'ensolarado': 'Ensolarado',
                    'nublado': 'Nublado',
                    'chuvoso': 'Chuvoso',
                    'tempestade': 'Tempestade',
                }.get(cond_d, cond_d.title())
                cond_color = {
                    'ensolarado': YELLOW,
                    'nublado': GRAY_TEXT,
                    'chuvoso': BLUE,
                    'tempestade': RED,
                }.get(cond_d, GRAY_TEXT)
                _center_text(draw, cond_label, _font(22, bold=True), cy + 330, cond_color, cx + card_w // 2)

    _footer_bar(draw, 'Dados: Open-Meteo  |  Atualização automática')
    return img


# ══════════════════════════════════════════════════════════════════════
#  COTAÇÕES
# ══════════════════════════════════════════════════════════════════════

def _gerar_imagem_cotacoes(dados):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (15, 12, 41))

    _gradient_bg(img, (15, 12, 41), (36, 36, 62), diagonal=True)
    draw = ImageDraw.Draw(img)

    draw = _header_bar(img, draw, 'COTAÇÕES EM TEMPO REAL')

    # Título
    title_y = 100
    _center_text(draw, 'Cotações em Tempo Real', _font(38, bold=True), title_y, WHITE)
    draw.line([(50, title_y + 55), (VIDEO_WIDTH - 50, title_y + 55)],
              fill=(255, 255, 255, 30), width=1)

    # ── Montar lista unificada ──
    sections = []
    for m in dados.get('moedas', []):
        m['_section'] = 'MOEDA'
        sections.append(m)
    for c in dados.get('cripto', []):
        c['_section'] = 'CRIPTO'
        sections.append(c)
    for idx in dados.get('indices', []):
        idx['_section'] = 'ÍNDICE'
        sections.append(idx)
    for cm in dados.get('commodities', []):
        cm['_section'] = 'COMMODITY'
        sections.append(cm)

    # ── Layout em grid 2 colunas ──
    margin = 50
    gap = 24
    cols = 2
    usable_w = VIDEO_WIDTH - 2 * margin - (cols - 1) * gap
    card_w = usable_w // cols

    start_y = title_y + 75
    card_h = 105
    vgap = 16
    max_rows = (VIDEO_HEIGHT - start_y - 80) // (card_h + vgap)

    badge_colors = {
        'MOEDA': BRAND, 'CRIPTO': CYAN,
        'ÍNDICE': YELLOW, 'COMMODITY': GREEN,
    }

    for i, item in enumerate(sections[:max_rows * cols]):
        col = i % cols
        row = i // cols
        cx = margin + col * (card_w + gap)
        cy = start_y + row * (card_h + vgap)

        is_commodity = item.get('_section') == 'COMMODITY'
        is_index = item.get('_section') == 'ÍNDICE'

        # Card glass
        draw = _glass_rect(img, draw,
                           (cx, cy, cx + card_w, cy + card_h),
                           radius=14, opacity=0.08,
                           border_color=(255, 255, 255, 25))

        # Badge da seção
        badge = item.get('_section', '')
        badge_col = badge_colors.get(badge, GRAY_DIM)
        draw.text((cx + 18, cy + 8), badge, fill=badge_col, font=_font(13))

        # Código
        draw.text((cx + 18, cy + 28), item.get('codigo', ''),
                  fill=WHITE, font=_font(28, bold=True))

        # Nome
        draw.text((cx + 18, cy + 65), item.get('nome', ''),
                  fill=GRAY_DIM, font=_font(18))

        # Valor (alinhado à direita)
        valor = item.get('valor')
        if valor is not None:
            if is_index:
                val_str = _format_brl(valor, 0) + ' pts'
            elif is_commodity:
                val_str = f'$ {_format_brl(valor, 2)}'
            else:
                val_str = f'R$ {_format_brl(valor, 2)}'
        else:
            val_str = '—'

        val_font = _font(30, bold=True)
        val_x = cx + card_w - _text_w(draw, val_str, val_font) - 22
        draw.text((val_x, cy + 20), val_str, fill=WHITE, font=val_font)

        # BRL para commodities
        if is_commodity and item.get('valor_brl'):
            brl_str = f'≈ R$ {_format_brl(item["valor_brl"], 2)}'
            brl_font = _font(15)
            brl_x = cx + card_w - _text_w(draw, brl_str, brl_font) - 22
            draw.text((brl_x, cy + 56), brl_str, fill=GRAY_DIM, font=brl_font)

        # Variação
        var = item.get('variacao_pct')
        direcao = item.get('direcao', 'stable')
        if var is not None:
            color, arrow = _var_color_arrow(var, direcao)
            var_str = f'{arrow} {abs(var):.2f}%'
        else:
            color = GRAY_DIM
            var_str = '—'
        var_font = _font(20, bold=True)
        var_x = cx + card_w - _text_w(draw, var_str, var_font) - 22
        draw.text((var_x, cy + 76), var_str, fill=color, font=var_font)

    # Rodapé
    atualizado = dados.get('atualizado_em', '')
    ts = atualizado[:19].replace('T', '  ') if atualizado else ''
    _footer_bar(draw, f'Fontes: AwesomeAPI  •  Yahoo Finance     Atualizado: {ts}')
    return img


# ══════════════════════════════════════════════════════════════════════
#  NOTÍCIAS
# ══════════════════════════════════════════════════════════════════════

def _gerar_imagem_noticias(dados):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (26, 26, 46))

    _gradient_bg(img, (26, 26, 46), (15, 52, 96), diagonal=True)
    draw = ImageDraw.Draw(img)

    draw = _header_bar(img, draw, 'ÚLTIMAS NOTÍCIAS')

    manchetes = dados.get('manchetes', [])

    # Título
    title_y = 100
    _center_text(draw, 'Notícias do Brasil', _font(38, bold=True), title_y, WHITE)

    margin = 60
    start_y = title_y + 60
    card_h = 108
    vgap = 12
    max_news = min(len(manchetes), 8)

    for i, m in enumerate(manchetes[:max_news]):
        cy = start_y + i * (card_h + vgap)

        # Card glass com borda vermelha
        draw = _glass_rect(img, draw,
                           (margin, cy, VIDEO_WIDTH - margin, cy + card_h),
                           radius=12, opacity=0.06,
                           border_color=(255, 255, 255, 15))

        # Barra vermelha lateral
        draw.rounded_rectangle(
            (margin, cy, margin + 5, cy + card_h),
            radius=3, fill=RED)

        # Número
        num_str = f'{i + 1:02d}'
        draw.text((margin + 25, cy + 12), num_str,
                  fill=RED, font=_font(28, bold=True))

        # Título (truncar dinamicamente)
        titulo = m.get('titulo', '')
        f_headline = _font(28, bold=True)
        max_w = VIDEO_WIDTH - 2 * margin - 110
        while _text_w(draw, titulo, f_headline) > max_w and len(titulo) > 10:
            titulo = titulo[:-4] + '...'
        draw.text((margin + 80, cy + 10), titulo,
                  fill=WHITE, font=f_headline)

        # Fonte + horário
        fonte = m.get('fonte', '')
        publicado = m.get('publicado_em', '')
        if publicado:
            try:
                if 'T' in publicado or '+' in publicado or 'Z' in publicado:
                    dt = datetime.fromisoformat(publicado.replace('Z', '+00:00'))
                    publicado = dt.strftime('%H:%M')
                elif ',' in publicado:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(publicado)
                    publicado = dt.strftime('%H:%M')
            except Exception:
                publicado = ''

        meta = fonte
        if publicado:
            meta += f'  •  {publicado}'
        draw.text((margin + 80, cy + 55), meta,
                  fill=GRAY_DIM, font=_font(18))

    _footer_bar(draw, 'Fonte: Google News Brasil  |  Atualização automática')
    return img


# ══════════════════════════════════════════════
#  GERENCIAMENTO DE CICLO DE VIDA
# ══════════════════════════════════════════════

def _get_video_ttl(tipo):
    try:
        from .models import ConfiguracaoAPI
        config = ConfiguracaoAPI.get_config()
        ttl_map = {
            'PREVISAO_TEMPO': config.cache_weather_minutos * 60,
            'COTACOES': config.cache_cotacoes_minutos * 60,
            'NOTICIAS': config.cache_noticias_minutos * 60,
        }
        return ttl_map.get(tipo, 900)
    except Exception:
        return 900


def _is_video_fresh(video_path, ttl_seconds):
    if not os.path.exists(video_path):
        return False
    return (time.time() - os.path.getmtime(video_path)) < ttl_seconds


def limpar_videos_expirados():
    """Remove vídeos corporativos expirados."""
    output_dir = _get_output_dir()
    removed = 0
    for f in output_dir.glob('*.mp4'):
        name = f.stem
        tipo = None
        if name.startswith('previsao_tempo'):
            tipo = 'PREVISAO_TEMPO'
        elif name.startswith('cotacoes'):
            tipo = 'COTACOES'
        elif name.startswith('noticias'):
            tipo = 'NOTICIAS'

        ttl = _get_video_ttl(tipo) if tipo else 900
        if not _is_video_fresh(str(f), ttl):
            try:
                f.unlink()
                removed += 1
                logger.info(f'Vídeo expirado removido: {f.name}')
            except Exception as e:
                logger.error(f'Erro ao remover {f.name}: {e}')
    return removed


# ══════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL — chamada pelo serializer
# ══════════════════════════════════════════════

def gerar_video_corporativo(tipo, dados, playlist_id, duracao_segundos=15):
    """
    Gera (ou retorna do cache) o vídeo MP4 para um conteúdo corporativo.

    Returns:
        str: path relativo do vídeo (media URL) ou None se falhar
    """
    output_dir = _get_output_dir()

    dados_hash = hashlib.md5(str(dados).encode()).hexdigest()[:8]
    cache_name = _video_cache_key(tipo, playlist_id)
    filename = f'{cache_name}_{dados_hash}.mp4'
    video_path = output_dir / filename

    ttl = _get_video_ttl(tipo)

    # Se o vídeo ainda está fresco, retorna direto
    if _is_video_fresh(str(video_path), ttl):
        return _get_media_url(filename)

    # Limpar vídeos antigos do mesmo tipo+playlist
    for old in output_dir.glob(f'{cache_name}_*.mp4'):
        if old.name != filename:
            try:
                old.unlink()
                logger.info(f'Vídeo antigo removido: {old.name}')
            except Exception:
                pass

    # Gerar imagem
    try:
        if tipo == 'PREVISAO_TEMPO':
            image = _gerar_imagem_previsao(dados)
        elif tipo == 'COTACOES':
            image = _gerar_imagem_cotacoes(dados)
        elif tipo == 'NOTICIAS':
            image = _gerar_imagem_noticias(dados)
        else:
            logger.error(f'Tipo desconhecido: {tipo}')
            return None

        if _image_to_video(image, duracao_segundos, video_path):
            return _get_media_url(filename)

        logger.error(f'Falha ao converter imagem em vídeo: {filename}')
        return None

    except Exception as e:
        logger.error(f'Erro ao gerar vídeo corporativo ({tipo}): {e}')
        return None
