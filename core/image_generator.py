"""
Gerador de imagens PNG para conteúdos corporativos (previsão do tempo, cotações, notícias).

Usa apenas Pillow (CPU leve, ~50ms por imagem, ~30-50KB por PNG).
Cada playlist gera sua própria imagem (ex: clima específico do município).
Imagens gerenciadas com TTL baseado na ConfiguracaoAPI.

O app Android exibe a imagem num ImageView pelo tempo de duracao_segundos.
"""

import hashlib
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
IMG_WIDTH = 1920
IMG_HEIGHT = 1080
CORP_IMG_DIR = 'corporativo_img'

# ── Paleta de cores ──
WHITE       = (255, 255, 255)
GRAY_TEXT   = (200, 200, 220)
GRAY_DIM    = (140, 140, 165)
GREEN       = (46, 204, 113)
RED         = (231, 76, 60)
YELLOW      = (241, 196, 15)
BLUE        = (52, 152, 219)
CYAN        = (26, 188, 156)
BRAND       = (0, 120, 255)
BRAND_LIGHT = (60, 160, 255)

ARROW_UP   = '\u25B2'
ARROW_DOWN = '\u25BC'
DOT        = '\u25CF'


# ══════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════

def _get_output_dir():
    media_root = Path(settings.MEDIA_ROOT)
    output = media_root / CORP_IMG_DIR
    output.mkdir(parents=True, exist_ok=True)
    return output


def _get_media_url(filename):
    return f'{settings.MEDIA_URL}{CORP_IMG_DIR}/{filename}'


_font_cache = {}

def _font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    candidates = (
        [
            'C:/Windows/Fonts/arialbd.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        ] if bold else [
            'C:/Windows/Fonts/arial.ttf',
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


def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _center(draw, text, font, y, fill, cx=IMG_WIDTH // 2):
    w = _tw(draw, text, font)
    draw.text((cx - w // 2, y), text, fill=fill, font=font)


def _right(draw, text, font, y, fill, margin=50):
    w = _tw(draw, text, font)
    draw.text((IMG_WIDTH - w - margin, y), text, fill=fill, font=font)


def _gradient(img, ca, cb, diagonal=False):
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = ((x / w) + (y / h)) / 2 if diagonal else y / h
            px[x, y] = (
                int(ca[0] + (cb[0] - ca[0]) * t),
                int(ca[1] + (cb[1] - ca[1]) * t),
                int(ca[2] + (cb[2] - ca[2]) * t),
            )


def _glass(base, draw, xy, radius=16, opacity=0.12, border=None):
    overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(xy, radius=radius, fill=(255, 255, 255, int(255 * opacity)))
    if border:
        od.rounded_rectangle(xy, radius=radius, outline=border, width=1)
    comp = Image.alpha_composite(base.convert('RGBA'), overlay)
    base.paste(comp.convert('RGB'), (0, 0))
    return ImageDraw.Draw(base)


def _header(img, draw, subtitle, right_txt=''):
    draw = _glass(img, draw, (0, 0, IMG_WIDTH, 80), radius=0, opacity=0.35)
    draw.line([(0, 80), (IMG_WIDTH, 80)], fill=BRAND, width=3)
    draw.text((50, 16), 'MEDIAEXPAND', fill=BRAND_LIGHT, font=_font(30, True))
    draw.text((50, 50), subtitle, fill=GRAY_DIM, font=_font(18))
    now = timezone.localtime()
    _right(draw, now.strftime('%d/%m/%Y   %H:%M'), _font(20), 28, GRAY_TEXT, 50)
    if right_txt:
        _right(draw, right_txt, _font(22, True), 50, WHITE, 50)
    return draw


def _footer(draw, text):
    draw.text((50, IMG_HEIGHT - 45), text, fill=GRAY_DIM, font=_font(16))


def _fmt(value, dec=2):
    if value is None:
        return '—'
    s = f'{value:,.{dec}f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def _var_info(var, direcao):
    if direcao == 'up':
        return GREEN, ARROW_UP
    elif direcao == 'down':
        return RED, ARROW_DOWN
    return YELLOW, DOT


# ══════════════════════════════════════════════
#  PREVISÃO DO TEMPO
# ══════════════════════════════════════════════

_W_GRAD = {
    'ensolarado': ((255, 140, 0), (255, 215, 0)),
    'nublado':    ((99, 111, 164), (232, 203, 192)),
    'chuvoso':    ((44, 62, 80), (52, 152, 219)),
    'tempestade': ((15, 32, 39), (44, 83, 100)),
}
_DIAS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']


def _img_previsao(dados):
    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT))
    municipio = dados.get('municipio', '')
    atual = dados.get('atual', {})
    previsao = dados.get('previsao', [])
    cond = atual.get('condicao', 'nublado')

    g = _W_GRAD.get(cond, _W_GRAD['nublado'])
    _gradient(img, g[0], g[1], diagonal=True)
    draw = ImageDraw.Draw(img)
    draw = _header(img, draw, 'PREVISÃO DO TEMPO', municipio)

    # Glass central
    draw = _glass(img, draw,
                  (IMG_WIDTH // 2 - 280, 110, IMG_WIDTH // 2 + 280, 470),
                  radius=30, opacity=0.10)

    # Cidade
    if municipio:
        _center(draw, municipio, _font(30, True), 130, (255, 255, 255, 230))

    # Temperatura
    temp = atual.get('temperatura')
    _center(draw, f'{temp:.0f}°C' if temp is not None else '--°C',
            _font(150, True), 175, WHITE)

    # Descrição
    _center(draw, atual.get('descricao', 'Indisponível'), _font(34), 360, GRAY_TEXT)

    # Detalhes
    parts = []
    um = atual.get('umidade')
    vt = atual.get('vento_kmh')
    if um is not None:
        parts.append(f'Umidade  {um}%')
    if vt is not None:
        parts.append(f'Vento  {vt:.0f} km/h')
    if parts:
        _center(draw, '     |     '.join(parts), _font(24), 415, GRAY_DIM)

    # Separador
    draw.line([(200, 490), (IMG_WIDTH - 200, 490)], fill=(255, 255, 255, 40), width=1)

    # Previsão 3 dias
    if previsao:
        n = min(len(previsao), 3)
        cw, ch, gap = 480, 460, 50
        sx = (IMG_WIDTH - cw * n - gap * (n - 1)) // 2
        cy = 510

        for i, dia in enumerate(previsao[:3]):
            cx = sx + i * (cw + gap)
            draw = _glass(img, draw, (cx, cy, cx + cw, cy + ch),
                          radius=20, opacity=0.12, border=(255, 255, 255, 40))

            # Dia
            dr = dia.get('data', '')
            try:
                dt = datetime.strptime(dr, '%Y-%m-%d')
                lbl = f'{_DIAS[dt.weekday()]}  {dt.strftime("%d/%m")}'
            except Exception:
                lbl = dr
            _center(draw, lbl, _font(26, True), cy + 20, CYAN, cx + cw // 2)

            # Descrição do dia
            dd = dia.get('descricao', '')
            if len(dd) > 28:
                dd = dd[:26] + '..'
            _center(draw, dd, _font(22), cy + 65, GRAY_TEXT, cx + cw // 2)

            # Temperaturas
            tmax = dia.get('max')
            tmin = dia.get('min')
            ms = f'{tmax:.0f}°' if tmax is not None else '--°'
            ns = f'{tmin:.0f}°' if tmin is not None else '--°'
            _center(draw, ms, _font(80, True), cy + 110, WHITE, cx + cw // 2 - 70)
            draw.text((cx + cw // 2 - 18, cy + 140), '/', fill=GRAY_DIM, font=_font(50))
            _center(draw, ns, _font(60, True), cy + 130, GRAY_TEXT, cx + cw // 2 + 75)

            _center(draw, 'máx', _font(18), cy + 215, GRAY_DIM, cx + cw // 2 - 70)
            _center(draw, 'mín', _font(18), cy + 215, GRAY_DIM, cx + cw // 2 + 75)

            # Linha fina
            draw.line([(cx + 40, cy + 250), (cx + cw - 40, cy + 250)],
                      fill=(255, 255, 255, 30), width=1)

            # Precipitação
            prec = dia.get('precipitacao_pct', 0)
            if prec:
                pc = RED if prec >= 50 else BLUE
                _center(draw, f'Chuva  {prec}%', _font(24), cy + 270, pc, cx + cw // 2)

            # Condição
            cd = dia.get('condicao', '')
            cmap = {'ensolarado': ('Ensolarado', YELLOW), 'nublado': ('Nublado', GRAY_TEXT),
                    'chuvoso': ('Chuvoso', BLUE), 'tempestade': ('Tempestade', RED)}
            if cd in cmap:
                _center(draw, cmap[cd][0], _font(22, True), cy + 320, cmap[cd][1], cx + cw // 2)

    _footer(draw, 'Dados: Open-Meteo  |  Atualização automática')
    return img


# ══════════════════════════════════════════════
#  COTAÇÕES
# ══════════════════════════════════════════════

def _img_cotacoes(dados):
    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT))
    _gradient(img, (15, 12, 41), (36, 36, 62), diagonal=True)
    draw = ImageDraw.Draw(img)
    draw = _header(img, draw, 'COTAÇÕES EM TEMPO REAL')

    _center(draw, 'Cotações em Tempo Real', _font(38, True), 100, WHITE)
    draw.line([(50, 155), (IMG_WIDTH - 50, 155)], fill=(255, 255, 255, 30), width=1)

    # Lista unificada
    items = []
    for m in dados.get('moedas', []):
        items.append(('MOEDA', m))
    for c in dados.get('cripto', []):
        items.append(('CRIPTO', c))
    for x in dados.get('indices', []):
        items.append(('ÍNDICE', x))
    for c in dados.get('commodities', []):
        items.append(('COMMODITY', c))

    margin, gap, cols = 50, 24, 2
    uw = IMG_WIDTH - 2 * margin - (cols - 1) * gap
    cw = uw // cols
    sy, ch, vg = 175, 105, 16
    max_rows = (IMG_HEIGHT - sy - 80) // (ch + vg)
    badge_c = {'MOEDA': BRAND, 'CRIPTO': CYAN, 'ÍNDICE': YELLOW, 'COMMODITY': GREEN}

    for i, (sec, item) in enumerate(items[:max_rows * cols]):
        col = i % cols
        row = i // cols
        cx = margin + col * (cw + gap)
        cy = sy + row * (ch + vg)
        is_cmdt = sec == 'COMMODITY'
        is_idx = sec == 'ÍNDICE'

        draw = _glass(img, draw, (cx, cy, cx + cw, cy + ch),
                      radius=14, opacity=0.08, border=(255, 255, 255, 25))

        # Badge
        draw.text((cx + 18, cy + 8), sec, fill=badge_c.get(sec, GRAY_DIM), font=_font(13))
        # Código
        draw.text((cx + 18, cy + 28), item.get('codigo', ''), fill=WHITE, font=_font(28, True))
        # Nome
        draw.text((cx + 18, cy + 65), item.get('nome', ''), fill=GRAY_DIM, font=_font(18))

        # Valor
        v = item.get('valor')
        if v is not None:
            if is_idx:
                vs = _fmt(v, 0) + ' pts'
            elif is_cmdt:
                vs = f'$ {_fmt(v, 2)}'
            else:
                vs = f'R$ {_fmt(v, 2)}'
        else:
            vs = '—'
        vf = _font(30, True)
        draw.text((cx + cw - _tw(draw, vs, vf) - 22, cy + 20), vs, fill=WHITE, font=vf)

        # BRL commodity
        if is_cmdt and item.get('valor_brl'):
            bs = f'≈ R$ {_fmt(item["valor_brl"], 2)}'
            bf = _font(15)
            draw.text((cx + cw - _tw(draw, bs, bf) - 22, cy + 56), bs, fill=GRAY_DIM, font=bf)

        # Variação
        var = item.get('variacao_pct')
        dir_ = item.get('direcao', 'stable')
        if var is not None:
            vc, arrow = _var_info(var, dir_)
            vrs = f'{arrow} {abs(var):.2f}%'
        else:
            vc, vrs = GRAY_DIM, '—'
        vrf = _font(20, True)
        draw.text((cx + cw - _tw(draw, vrs, vrf) - 22, cy + 76), vrs, fill=vc, font=vrf)

    at = dados.get('atualizado_em', '')
    ts = at[:19].replace('T', '  ') if at else ''
    _footer(draw, f'Fontes: AwesomeAPI  •  Yahoo Finance     Atualizado: {ts}')
    return img


# ══════════════════════════════════════════════
#  NOTÍCIAS
# ══════════════════════════════════════════════

def _img_noticias(dados):
    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT))
    _gradient(img, (26, 26, 46), (15, 52, 96), diagonal=True)
    draw = ImageDraw.Draw(img)
    draw = _header(img, draw, 'ÚLTIMAS NOTÍCIAS')

    _center(draw, 'Notícias do Brasil', _font(38, True), 100, WHITE)
    mn = 60
    sy = 160
    ch, vg = 108, 12
    manchetes = dados.get('manchetes', [])

    for i, m in enumerate(manchetes[:8]):
        cy = sy + i * (ch + vg)
        draw = _glass(img, draw, (mn, cy, IMG_WIDTH - mn, cy + ch),
                      radius=12, opacity=0.06, border=(255, 255, 255, 15))

        # Barra vermelha
        draw.rounded_rectangle((mn, cy, mn + 5, cy + ch), radius=3, fill=RED)

        # Número
        draw.text((mn + 25, cy + 12), f'{i+1:02d}', fill=RED, font=_font(28, True))

        # Título (truncar)
        titulo = m.get('titulo', '')
        fh = _font(28, True)
        mw = IMG_WIDTH - 2 * mn - 110
        while _tw(draw, titulo, fh) > mw and len(titulo) > 10:
            titulo = titulo[:-4] + '...'
        draw.text((mn + 80, cy + 10), titulo, fill=WHITE, font=fh)

        # Fonte
        fonte = m.get('fonte', '')
        pub = m.get('publicado_em', '')
        if pub:
            try:
                if 'T' in pub or '+' in pub or 'Z' in pub:
                    dt = datetime.fromisoformat(pub.replace('Z', '+00:00'))
                    pub = dt.strftime('%H:%M')
                elif ',' in pub:
                    from email.utils import parsedate_to_datetime
                    pub = parsedate_to_datetime(pub).strftime('%H:%M')
            except Exception:
                pub = ''
        meta = fonte + (f'  •  {pub}' if pub else '')
        draw.text((mn + 80, cy + 55), meta, fill=GRAY_DIM, font=_font(18))

    _footer(draw, 'Fonte: Google News Brasil  |  Atualização automática')
    return img


# ══════════════════════════════════════════════
#  CICLO DE VIDA
# ══════════════════════════════════════════════

def _get_ttl(tipo):
    try:
        from .models import ConfiguracaoAPI
        cfg = ConfiguracaoAPI.get_config()
        return {'PREVISAO_TEMPO': cfg.cache_weather_minutos,
                'COTACOES': cfg.cache_cotacoes_minutos,
                'NOTICIAS': cfg.cache_noticias_minutos}.get(tipo, 15) * 60
    except Exception:
        return 900


def _is_fresh(path, ttl):
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < ttl


def limpar_imagens_expiradas():
    out = _get_output_dir()
    removed = 0
    for f in out.glob('*.png'):
        name = f.stem
        tipo = None
        if name.startswith('previsao_tempo'):
            tipo = 'PREVISAO_TEMPO'
        elif name.startswith('cotacoes'):
            tipo = 'COTACOES'
        elif name.startswith('noticias'):
            tipo = 'NOTICIAS'
        if not _is_fresh(str(f), _get_ttl(tipo) if tipo else 900):
            try:
                f.unlink()
                removed += 1
            except Exception as e:
                logger.error(f'Erro ao remover {f.name}: {e}')
    return removed


# ══════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════

def gerar_imagem_corporativa(tipo, dados, playlist_id):
    """
    Gera (ou retorna do cache) a imagem PNG para conteúdo corporativo.

    Returns:
        str: path relativo da imagem (media URL) ou None
    """
    out = _get_output_dir()
    h = hashlib.md5(str(dados).encode()).hexdigest()[:8]
    base = f'{tipo.lower()}_{playlist_id}'
    fname = f'{base}_{h}.png'
    fpath = out / fname
    ttl = _get_ttl(tipo)

    if _is_fresh(str(fpath), ttl):
        return _get_media_url(fname)

    # Limpar antigos
    for old in out.glob(f'{base}_*.png'):
        if old.name != fname:
            try:
                old.unlink()
            except Exception:
                pass

    try:
        if tipo == 'PREVISAO_TEMPO':
            image = _img_previsao(dados)
        elif tipo == 'COTACOES':
            image = _img_cotacoes(dados)
        elif tipo == 'NOTICIAS':
            image = _img_noticias(dados)
        else:
            return None

        image.save(str(fpath), 'PNG', optimize=True)
        logger.info(f'Imagem corporativa gerada: {fname} ({os.path.getsize(str(fpath)) // 1024}KB)')
        return _get_media_url(fname)

    except Exception as e:
        logger.error(f'Erro ao gerar imagem ({tipo}): {e}')
        return None
