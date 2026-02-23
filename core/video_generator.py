"""
Gerador de vídeos para conteúdos corporativos (previsão do tempo, cotações, notícias).

Gera imagens com Pillow e converte para MP4 com imageio-ffmpeg.
Cada playlist pode ter sua própria versão do vídeo (ex: clima específico do município).
Os vídeos são gerenciados com TTL baseado nas configurações de cache da ConfiguracaoAPI.
"""

import hashlib
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import imageio.v3 as iio
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
FPS = 1  # 1 frame por segundo — vídeo estático, economiza espaço
CORP_VIDEO_DIR = 'corporativo_videos'

# Cores do tema
COLOR_BG_DARK = (18, 18, 30)
COLOR_BG_CARD = (30, 30, 50)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (180, 180, 200)
COLOR_LIGHT_GRAY = (120, 120, 140)
COLOR_GREEN = (46, 204, 113)
COLOR_RED = (231, 76, 60)
COLOR_YELLOW = (241, 196, 15)
COLOR_BLUE = (52, 152, 219)
COLOR_CYAN = (26, 188, 156)
COLOR_ORANGE = (243, 156, 18)
COLOR_BRAND = (0, 150, 255)
COLOR_CARD_BORDER = (50, 50, 80)

# Gradientes de fundo por tipo
BG_GRADIENTS = {
    'PREVISAO_TEMPO': [(15, 32, 65), (25, 60, 120)],
    'COTACOES': [(15, 25, 35), (20, 40, 55)],
    'NOTICIAS': [(30, 15, 15), (50, 25, 35)],
}

# Ícones weather em Unicode/texto
WEATHER_ICONS = {
    'ensolarado': '☀',
    'nublado': '☁',
    'chuvoso': '🌧',
    'tempestade': '⛈',
}

ARROW_UP = '▲'
ARROW_DOWN = '▼'
ARROW_STABLE = '●'


def _get_output_dir():
    """Retorna o diretório de saída para vídeos corporativos."""
    media_root = Path(settings.MEDIA_ROOT)
    output = media_root / CORP_VIDEO_DIR
    output.mkdir(parents=True, exist_ok=True)
    return output


def _get_media_url(filename):
    """Retorna o path relativo (media URL) do vídeo gerado."""
    return f'{settings.MEDIA_URL}{CORP_VIDEO_DIR}/{filename}'


def _video_cache_key(tipo, playlist_id):
    """Gera nome de arquivo baseado no tipo + playlist."""
    return f'{tipo.lower()}_{playlist_id}'


def _load_font(size, bold=False):
    """Carrega uma fonte TrueType. Tenta várias opções de sistema."""
    font_candidates = []
    if bold:
        font_candidates = [
            'C:/Windows/Fonts/arialbd.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        ]
    else:
        font_candidates = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        ]

    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # Fallback: fonte padrão do Pillow
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _draw_gradient_bg(draw, width, height, color_top, color_bottom):
    """Desenha fundo com gradiente vertical."""
    for y in range(height):
        ratio = y / height
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_rounded_rect(draw, xy, radius, fill, outline=None):
    """Desenha retângulo arredondado."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def _draw_header(draw, titulo, subtitulo, icon_text=''):
    """Desenha header fixo com logo/brand."""
    # Barra superior com brand
    draw.rectangle([(0, 0), (VIDEO_WIDTH, 90)], fill=(10, 10, 20, 220))
    draw.line([(0, 90), (VIDEO_WIDTH, 90)], fill=COLOR_BRAND, width=3)

    font_brand = _load_font(28, bold=True)
    font_sub = _load_font(18)

    # Brand esquerdo
    draw.text((40, 18), 'MEDIAEXPAND', fill=COLOR_BRAND, font=font_brand)
    draw.text((40, 55), subtitulo, fill=COLOR_GRAY, font=font_sub)

    # Título direito
    font_title = _load_font(24, bold=True)
    bbox = draw.textbbox((0, 0), titulo, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text((VIDEO_WIDTH - tw - 40, 30), titulo, fill=COLOR_WHITE, font=font_title)

    # Horário
    now = timezone.localtime()
    hora_str = now.strftime('%H:%M')
    data_str = now.strftime('%d/%m/%Y')
    font_hora = _load_font(20)
    draw.text((VIDEO_WIDTH - 140, 58), f'{data_str}  {hora_str}', fill=COLOR_GRAY, font=font_hora)


def _image_to_video(image, duration_seconds, output_path):
    """Converte imagem PIL em vídeo MP4 usando imageio-ffmpeg."""
    frame = np.array(image.convert('RGB'))

    try:
        writer = iio.imopen(str(output_path), 'w', plugin='pyav')
        writer.write(
            np.stack([frame] * max(duration_seconds * FPS, 1)),
            codec='libx264',
            fps=FPS,
            out_pixel_format='yuv420p',
        )
        writer.close()
        logger.info(f'Vídeo gerado: {output_path} ({duration_seconds}s)')
        return True
    except Exception as e:
        logger.error(f'Erro ao gerar vídeo com imopen: {e}')

    # Fallback: usar imageio-ffmpeg diretamente
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        # Salvar frame temporário como PNG
        temp_png = str(output_path).replace('.mp4', '_temp.png')
        image.save(temp_png)

        import subprocess
        cmd = [
            ffmpeg_path, '-y',
            '-loop', '1',
            '-i', temp_png,
            '-c:v', 'libx264',
            '-t', str(duration_seconds),
            '-pix_fmt', 'yuv420p',
            '-r', str(FPS),
            '-vf', f'scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}',
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)

        if os.path.exists(temp_png):
            os.remove(temp_png)

        if os.path.exists(str(output_path)):
            logger.info(f'Vídeo gerado (ffmpeg fallback): {output_path}')
            return True
    except Exception as e2:
        logger.error(f'Erro no fallback ffmpeg: {e2}')

    return False


# ══════════════════════════════════════════════
#  PREVISÃO DO TEMPO
# ══════════════════════════════════════════════

def _gerar_imagem_previsao(dados):
    """Gera imagem 1920x1080 com dados de previsão do tempo."""
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)

    municipio = dados.get('municipio', 'Cidade')
    atual = dados.get('atual', {})
    previsao = dados.get('previsao', [])

    # Fundo gradiente baseado na condição
    condicao = atual.get('condicao', 'nublado')
    gradients = {
        'ensolarado': [(20, 50, 100), (255, 140, 0)],
        'nublado': [(40, 50, 70), (100, 110, 140)],
        'chuvoso': [(20, 30, 50), (50, 80, 130)],
        'tempestade': [(10, 15, 25), (40, 50, 80)],
    }
    g = gradients.get(condicao, gradients['nublado'])
    _draw_gradient_bg(draw, VIDEO_WIDTH, VIDEO_HEIGHT, g[0], g[1])

    # Header
    _draw_header(draw, municipio, 'PREVISÃO DO TEMPO')

    # Fontes
    font_temp_big = _load_font(180, bold=True)
    font_desc = _load_font(36)
    font_label = _load_font(24)
    font_detail = _load_font(28)
    font_day_title = _load_font(26, bold=True)
    font_day_temp = _load_font(52, bold=True)
    font_day_desc = _load_font(20)

    # ── Painel central: temperatura atual ──
    temp = atual.get('temperatura')
    temp_str = f'{temp:.0f}°' if temp is not None else '--°'
    desc_str = atual.get('descricao', 'Indisponível')

    # Temperatura grande centralizada
    bbox_temp = draw.textbbox((0, 0), temp_str, font=font_temp_big)
    tw = bbox_temp[2] - bbox_temp[0]
    tx = (VIDEO_WIDTH // 2) - (tw // 2)
    draw.text((tx, 160), temp_str, fill=COLOR_WHITE, font=font_temp_big)

    # Descrição abaixo
    bbox_desc = draw.textbbox((0, 0), desc_str, font=font_desc)
    dw = bbox_desc[2] - bbox_desc[0]
    draw.text(((VIDEO_WIDTH // 2) - (dw // 2), 370), desc_str, fill=COLOR_GRAY, font=font_desc)

    # ── Detalhes: umidade + vento ──
    y_details = 440
    umidade = atual.get('umidade')
    vento = atual.get('vento_kmh')

    details_items = []
    if umidade is not None:
        details_items.append(f'Umidade: {umidade}%')
    if vento is not None:
        details_items.append(f'Vento: {vento:.0f} km/h')

    if details_items:
        details_str = '    |    '.join(details_items)
        bbox_d = draw.textbbox((0, 0), details_str, font=font_detail)
        dw2 = bbox_d[2] - bbox_d[0]
        draw.text(((VIDEO_WIDTH // 2) - (dw2 // 2), y_details), details_str,
                  fill=COLOR_LIGHT_GRAY, font=font_detail)

    # ── Separador ──
    draw.line([(100, 520), (VIDEO_WIDTH - 100, 520)], fill=COLOR_CARD_BORDER, width=2)

    # ── Previsão 3 dias ──
    if previsao:
        card_w = 480
        gap = 60
        total_w = card_w * len(previsao) + gap * (len(previsao) - 1)
        start_x = (VIDEO_WIDTH - total_w) // 2
        card_y = 560

        dias_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

        for i, dia in enumerate(previsao[:3]):
            cx = start_x + i * (card_w + gap)

            # Card background
            _draw_rounded_rect(draw, (cx, card_y, cx + card_w, card_y + 420),
                               radius=20, fill=(255, 255, 255, 15),
                               outline=COLOR_CARD_BORDER)

            # Data
            data_str = dia.get('data', '')
            try:
                dt = datetime.strptime(data_str, '%Y-%m-%d')
                dia_nome = dias_semana[dt.weekday()]
                data_fmt = dt.strftime('%d/%m')
                label = f'{dia_nome}  {data_fmt}'
            except Exception:
                label = data_str

            bbox_l = draw.textbbox((0, 0), label, font=font_day_title)
            lw = bbox_l[2] - bbox_l[0]
            draw.text((cx + (card_w - lw) // 2, card_y + 25), label,
                      fill=COLOR_CYAN, font=font_day_title)

            # Ícone condição
            cond_d = dia.get('condicao', 'nublado')
            icon = WEATHER_ICONS.get(cond_d, '☁')
            font_icon = _load_font(64)
            bbox_i = draw.textbbox((0, 0), icon, font=font_icon)
            iw = bbox_i[2] - bbox_i[0]
            draw.text((cx + (card_w - iw) // 2, card_y + 70), icon,
                      fill=COLOR_WHITE, font=font_icon)

            # Temperaturas
            tmax = dia.get('max')
            tmin = dia.get('min')
            max_str = f'{tmax:.0f}°' if tmax is not None else '--°'
            min_str = f'{tmin:.0f}°' if tmin is not None else '--°'
            temp_line = f'{max_str}  /  {min_str}'
            bbox_t = draw.textbbox((0, 0), temp_line, font=font_day_temp)
            ttw = bbox_t[2] - bbox_t[0]
            draw.text((cx + (card_w - ttw) // 2, card_y + 160), temp_line,
                      fill=COLOR_WHITE, font=font_day_temp)

            # Labels máx/mín
            draw.text((cx + 85, card_y + 230), 'máx       mín',
                      fill=COLOR_LIGHT_GRAY, font=font_label)

            # Descrição
            desc_d = dia.get('descricao', '')
            if len(desc_d) > 25:
                desc_d = desc_d[:23] + '..'
            bbox_dd = draw.textbbox((0, 0), desc_d, font=font_day_desc)
            ddw = bbox_dd[2] - bbox_dd[0]
            draw.text((cx + (card_w - ddw) // 2, card_y + 280), desc_d,
                      fill=COLOR_GRAY, font=font_day_desc)

            # Precipitação
            prec = dia.get('precipitacao_pct', 0)
            if prec:
                prec_str = f'Chuva: {prec}%'
                bbox_p = draw.textbbox((0, 0), prec_str, font=font_day_desc)
                pw = bbox_p[2] - bbox_p[0]
                draw.text((cx + (card_w - pw) // 2, card_y + 320), prec_str,
                          fill=COLOR_BLUE, font=font_day_desc)

    # Rodapé
    font_footer = _load_font(16)
    draw.text((40, VIDEO_HEIGHT - 40), 'Dados: Open-Meteo  |  Atualização automática',
              fill=COLOR_LIGHT_GRAY, font=font_footer)

    return img


# ══════════════════════════════════════════════
#  COTAÇÕES
# ══════════════════════════════════════════════

def _gerar_imagem_cotacoes(dados):
    """Gera imagem 1920x1080 com cotações de moedas, cripto, índices e commodities."""
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)

    g = BG_GRADIENTS['COTACOES']
    _draw_gradient_bg(draw, VIDEO_WIDTH, VIDEO_HEIGHT, g[0], g[1])
    _draw_header(draw, '', 'COTAÇÕES DO MERCADO')

    font_section = _load_font(24, bold=True)
    font_code = _load_font(22, bold=True)
    font_name = _load_font(20)
    font_value = _load_font(32, bold=True)
    font_var = _load_font(20)
    font_brl = _load_font(16)

    y_start = 120

    def _draw_quote_row(x, y, w, item, show_brl=False, is_index=False):
        """Desenha uma linha de cotação dentro de um card."""
        # Card background
        _draw_rounded_rect(draw, (x, y, x + w, y + 100),
                           radius=12, fill=(35, 35, 60), outline=COLOR_CARD_BORDER)

        # Código
        draw.text((x + 20, y + 12), item.get('codigo', ''), fill=COLOR_CYAN, font=font_code)
        # Nome
        draw.text((x + 20, y + 42), item.get('nome', ''), fill=COLOR_GRAY, font=font_name)

        # Valor
        valor = item.get('valor')
        if valor is not None:
            if is_index:
                val_str = f'{valor:,.0f} pts'
            elif show_brl:
                val_str = f'$ {valor:,.2f}'
            else:
                val_str = f'R$ {valor:,.2f}'
            val_str = val_str.replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            val_str = '—'

        bbox_v = draw.textbbox((0, 0), val_str, font=font_value)
        vw = bbox_v[2] - bbox_v[0]
        draw.text((x + w - vw - 140, y + 15), val_str, fill=COLOR_WHITE, font=font_value)

        # BRL equivalente para commodities
        if show_brl:
            valor_brl = item.get('valor_brl')
            if valor_brl:
                brl_str = f'≈ R$ {valor_brl:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
                bbox_b = draw.textbbox((0, 0), brl_str, font=font_brl)
                bw = bbox_b[2] - bbox_b[0]
                draw.text((x + w - bw - 140, y + 55), brl_str, fill=COLOR_LIGHT_GRAY, font=font_brl)

        # Variação
        var = item.get('variacao_pct')
        direcao = item.get('direcao', 'stable')
        if var is not None:
            if direcao == 'up':
                color = COLOR_GREEN
                arrow = ARROW_UP
            elif direcao == 'down':
                color = COLOR_RED
                arrow = ARROW_DOWN
            else:
                color = COLOR_YELLOW
                arrow = ARROW_STABLE
            var_str = f'{arrow} {abs(var):.2f}%'
        else:
            color = COLOR_GRAY
            var_str = '—'

        bbox_vr = draw.textbbox((0, 0), var_str, font=font_var)
        vrw = bbox_vr[2] - bbox_vr[0]
        draw.text((x + w - vrw - 20, y + 38), var_str, fill=color, font=font_var)

    # ── Layout: 2 colunas ──
    col_w = 860
    col_gap = 60
    col1_x = (VIDEO_WIDTH - 2 * col_w - col_gap) // 2
    col2_x = col1_x + col_w + col_gap
    row_h = 115

    # Coluna 1: Moedas + Índices
    y = y_start
    draw.text((col1_x, y), 'MOEDAS', fill=COLOR_BRAND, font=font_section)
    y += 35
    for item in dados.get('moedas', []):
        _draw_quote_row(col1_x, y, col_w, item)
        y += row_h

    y += 15
    draw.text((col1_x, y), 'ÍNDICES', fill=COLOR_BRAND, font=font_section)
    y += 35
    for item in dados.get('indices', []):
        _draw_quote_row(col1_x, y, col_w, item, is_index=True)
        y += row_h

    # Coluna 2: Cripto + Commodities
    y = y_start
    draw.text((col2_x, y), 'CRIPTOMOEDAS', fill=COLOR_BRAND, font=font_section)
    y += 35
    for item in dados.get('cripto', []):
        _draw_quote_row(col2_x, y, col_w, item)
        y += row_h

    y += 15
    draw.text((col2_x, y), 'COMMODITIES', fill=COLOR_BRAND, font=font_section)
    y += 35
    for item in dados.get('commodities', []):
        _draw_quote_row(col2_x, y, col_w, item, show_brl=True)
        y += row_h

    # Rodapé
    atualizado = dados.get('atualizado_em', '')
    font_footer = _load_font(16)
    draw.text((40, VIDEO_HEIGHT - 40),
              f'Fonte: AwesomeAPI / Yahoo Finance  |  {atualizado[:19] if atualizado else ""}',
              fill=COLOR_LIGHT_GRAY, font=font_footer)

    return img


# ══════════════════════════════════════════════
#  NOTÍCIAS
# ══════════════════════════════════════════════

def _gerar_imagem_noticias(dados):
    """Gera imagem 1920x1080 com manchetes de notícias."""
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)

    g = BG_GRADIENTS['NOTICIAS']
    _draw_gradient_bg(draw, VIDEO_WIDTH, VIDEO_HEIGHT, g[0], g[1])
    _draw_header(draw, '', 'ÚLTIMAS NOTÍCIAS')

    font_headline = _load_font(30, bold=True)
    font_fonte = _load_font(18)
    font_num = _load_font(28, bold=True)
    font_footer = _load_font(16)

    manchetes = dados.get('manchetes', [])
    y = 120
    card_h = 110
    card_gap = 12
    margin_x = 60

    for i, m in enumerate(manchetes[:8]):  # Máximo 8 manchetes cabem na tela
        card_y = y + i * (card_h + card_gap)

        # Card background
        _draw_rounded_rect(draw, (margin_x, card_y, VIDEO_WIDTH - margin_x, card_y + card_h),
                           radius=12, fill=(35, 25, 30), outline=(80, 40, 50))

        # Número
        num_str = f'{i + 1:02d}'
        draw.text((margin_x + 20, card_y + 15), num_str,
                  fill=COLOR_RED, font=font_num)

        # Título (truncar se muito longo)
        titulo = m.get('titulo', '')
        max_chars = 90
        if len(titulo) > max_chars:
            titulo = titulo[:max_chars - 2] + '...'
        draw.text((margin_x + 80, card_y + 15), titulo,
                  fill=COLOR_WHITE, font=font_headline)

        # Fonte
        fonte = m.get('fonte', '')
        publicado = m.get('publicado_em', '')
        if publicado and len(publicado) > 10:
            try:
                dt = datetime.fromisoformat(publicado.replace('Z', '+00:00'))
                publicado = dt.strftime('%H:%M')
            except Exception:
                publicado = publicado[:10]
        meta = f'{fonte}'
        if publicado:
            meta += f'  •  {publicado}'
        draw.text((margin_x + 80, card_y + 60), meta,
                  fill=COLOR_LIGHT_GRAY, font=font_fonte)

    # Rodapé
    draw.text((40, VIDEO_HEIGHT - 40),
              'Fonte: Google News Brasil  |  Atualização automática',
              fill=COLOR_LIGHT_GRAY, font=font_footer)

    return img


# ══════════════════════════════════════════════
#  GERENCIAMENTO DE CICLO DE VIDA DOS VÍDEOS
# ══════════════════════════════════════════════

def _get_video_ttl(tipo):
    """Retorna o TTL em segundos para um tipo de conteúdo corporativo."""
    try:
        from .models import ConfiguracaoAPI
        config = ConfiguracaoAPI.get_config()
        ttl_map = {
            'PREVISAO_TEMPO': config.cache_weather_minutos * 60,
            'COTACOES': config.cache_cotacoes_minutos * 60,
            'NOTICIAS': config.cache_noticias_minutos * 60,
        }
        return ttl_map.get(tipo, 900)  # 15 min default
    except Exception:
        return 900


def _is_video_fresh(video_path, ttl_seconds):
    """Verifica se o vídeo ainda está dentro do TTL."""
    if not os.path.exists(video_path):
        return False
    mtime = os.path.getmtime(video_path)
    age = time.time() - mtime
    return age < ttl_seconds


def limpar_videos_expirados():
    """Remove vídeos corporativos que ultrapassaram o TTL. Chamado manualmente ou via cron."""
    output_dir = _get_output_dir()
    removed = 0
    for f in output_dir.glob('*.mp4'):
        # Extrair tipo do nome do arquivo
        name = f.stem  # ex: previsao_tempo_1_abc123
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

    Args:
        tipo: 'PREVISAO_TEMPO', 'COTACOES' ou 'NOTICIAS'
        dados: dict com os dados do serviço (retorno de buscar_dados_corporativos)
        playlist_id: ID da playlist (para gerar vídeo específico por cidade)
        duracao_segundos: duração do vídeo

    Returns:
        str: path relativo do vídeo (media URL) ou None se falhar
    """
    output_dir = _get_output_dir()

    # Hash dos dados para detectar mudanças no conteúdo
    dados_hash = hashlib.md5(str(dados).encode()).hexdigest()[:8]
    cache_name = _video_cache_key(tipo, playlist_id)
    filename = f'{cache_name}_{dados_hash}.mp4'
    video_path = output_dir / filename

    ttl = _get_video_ttl(tipo)

    # Se o vídeo já existe e está fresco, retorna
    if _is_video_fresh(str(video_path), ttl):
        return _get_media_url(filename)

    # Limpar vídeos antigos do mesmo tipo+playlist (diferentes hashes)
    pattern = f'{cache_name}_*.mp4'
    for old_file in output_dir.glob(pattern):
        if old_file.name != filename:
            try:
                old_file.unlink()
                logger.info(f'Vídeo antigo removido: {old_file.name}')
            except Exception:
                pass

    # Gerar imagem baseada no tipo
    try:
        if tipo == 'PREVISAO_TEMPO':
            image = _gerar_imagem_previsao(dados)
        elif tipo == 'COTACOES':
            image = _gerar_imagem_cotacoes(dados)
        elif tipo == 'NOTICIAS':
            image = _gerar_imagem_noticias(dados)
        else:
            logger.error(f'Tipo de conteúdo corporativo desconhecido: {tipo}')
            return None

        # Converter para vídeo
        success = _image_to_video(image, duracao_segundos, video_path)
        if success:
            return _get_media_url(filename)
        else:
            logger.error(f'Falha ao converter imagem em vídeo: {filename}')
            return None

    except Exception as e:
        logger.error(f'Erro ao gerar vídeo corporativo ({tipo}): {e}')
        return None
