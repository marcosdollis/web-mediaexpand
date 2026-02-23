"""
Serviços para buscar dados de APIs externas com cache e controle de rate-limit.

APIs utilizadas (todas gratuitas):
- Previsão do Tempo: Open-Meteo  (sem chave, ilimitado)
- Cotações:           AwesomeAPI  (sem chave, gratuita)
- Notícias:           NewsAPI.org (chave grátis, 100 req/dia)
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constantes WMO Weather Codes → descrição + background
# ──────────────────────────────────────────────
WMO_CODES = {
    0: ('Céu limpo', 'ensolarado'),
    1: ('Predominantemente limpo', 'ensolarado'),
    2: ('Parcialmente nublado', 'nublado'),
    3: ('Nublado', 'nublado'),
    45: ('Neblina', 'nublado'),
    48: ('Neblina com geada', 'nublado'),
    51: ('Garoa leve', 'chuvoso'),
    53: ('Garoa moderada', 'chuvoso'),
    55: ('Garoa intensa', 'chuvoso'),
    56: ('Garoa congelante leve', 'chuvoso'),
    57: ('Garoa congelante intensa', 'chuvoso'),
    61: ('Chuva leve', 'chuvoso'),
    63: ('Chuva moderada', 'chuvoso'),
    65: ('Chuva forte', 'chuvoso'),
    66: ('Chuva congelante leve', 'chuvoso'),
    67: ('Chuva congelante forte', 'chuvoso'),
    71: ('Neve leve', 'chuvoso'),
    73: ('Neve moderada', 'chuvoso'),
    75: ('Neve forte', 'chuvoso'),
    77: ('Grãos de neve', 'chuvoso'),
    80: ('Pancadas leves', 'chuvoso'),
    81: ('Pancadas moderadas', 'chuvoso'),
    82: ('Pancadas fortes', 'chuvoso'),
    85: ('Neve leve em pancadas', 'chuvoso'),
    86: ('Neve forte em pancadas', 'chuvoso'),
    95: ('Trovoada', 'tempestade'),
    96: ('Trovoada com granizo leve', 'tempestade'),
    99: ('Trovoada com granizo forte', 'tempestade'),
}

# Backgrounds CSS para o app Android renderizar
WEATHER_BACKGROUNDS = {
    'ensolarado': {
        'gradient_start': '#FF8C00',
        'gradient_end': '#FFD700',
        'icon': 'sun',
    },
    'nublado': {
        'gradient_start': '#636FA4',
        'gradient_end': '#E8CBC0',
        'icon': 'cloud',
    },
    'chuvoso': {
        'gradient_start': '#2C3E50',
        'gradient_end': '#3498DB',
        'icon': 'rain',
    },
    'tempestade': {
        'gradient_start': '#0F2027',
        'gradient_end': '#2C5364',
        'icon': 'storm',
    },
}


def _get_config():
    """Obtém a configuração singleton (import tardio para evitar loops)"""
    from .models import ConfiguracaoAPI
    return ConfiguracaoAPI.get_config()


# ══════════════════════════════════════════════
#  PREVISÃO DO TEMPO — Open-Meteo (100% grátis)
# ══════════════════════════════════════════════

def buscar_previsao_tempo(latitude, longitude, nome_municipio=''):
    """
    Busca previsão do tempo via Open-Meteo.
    Retorna dict com dados atuais + previsão 3 dias.
    Resultado é cacheado.
    """
    if latitude is None or longitude is None:
        return _previsao_fallback(nome_municipio)

    cache_key = f'weather_{latitude}_{longitude}'
    config = _get_config()
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not config.pode_requisitar('PREVISAO_TEMPO'):
        logger.warning('Limite diário de requisições de previsão do tempo atingido.')
        return _previsao_fallback(nome_municipio)

    try:
        url = (
            f'https://api.open-meteo.com/v1/forecast'
            f'?latitude={latitude}&longitude={longitude}'
            f'&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m'
            f'&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
            f'&timezone=America/Sao_Paulo'
            f'&forecast_days=3'
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        config.registrar_requisicao('PREVISAO_TEMPO')

        current = data.get('current', {})
        daily = data.get('daily', {})

        wmo_code = current.get('weather_code', 0)
        descricao, condicao = WMO_CODES.get(wmo_code, ('Desconhecido', 'nublado'))
        bg = WEATHER_BACKGROUNDS.get(condicao, WEATHER_BACKGROUNDS['nublado'])

        result = {
            'tipo': 'PREVISAO_TEMPO',
            'municipio': nome_municipio,
            'atual': {
                'temperatura': current.get('temperature_2m'),
                'umidade': current.get('relative_humidity_2m'),
                'vento_kmh': current.get('wind_speed_10m'),
                'descricao': descricao,
                'condicao': condicao,  # ensolarado|nublado|chuvoso|tempestade
                'wmo_code': wmo_code,
            },
            'background': bg,
            'previsao': [],
        }

        # Previsão 3 dias
        datas = daily.get('time', [])
        maximas = daily.get('temperature_2m_max', [])
        minimas = daily.get('temperature_2m_min', [])
        codigos = daily.get('weather_code', [])
        precipitacao = daily.get('precipitation_probability_max', [])

        for i in range(len(datas)):
            wmo_d = codigos[i] if i < len(codigos) else 0
            desc_d, cond_d = WMO_CODES.get(wmo_d, ('', 'nublado'))
            result['previsao'].append({
                'data': datas[i],
                'max': maximas[i] if i < len(maximas) else None,
                'min': minimas[i] if i < len(minimas) else None,
                'descricao': desc_d,
                'condicao': cond_d,
                'precipitacao_pct': precipitacao[i] if i < len(precipitacao) else 0,
            })

        cache_ttl = config.cache_weather_minutos * 60
        cache.set(cache_key, result, cache_ttl)
        return result

    except Exception as e:
        logger.error(f'Erro ao buscar previsão do tempo: {e}')
        return _previsao_fallback(nome_municipio)


def _previsao_fallback(nome_municipio):
    return {
        'tipo': 'PREVISAO_TEMPO',
        'municipio': nome_municipio,
        'atual': {
            'temperatura': None,
            'descricao': 'Indisponível',
            'condicao': 'nublado',
        },
        'background': WEATHER_BACKGROUNDS['nublado'],
        'previsao': [],
        'erro': 'Dados indisponíveis no momento',
    }


# ══════════════════════════════════════════════
#  COTAÇÕES — AwesomeAPI (100% grátis, sem chave)
# ══════════════════════════════════════════════

# Pares de moedas: Dólar, Euro, Bitcoin, Ethereum, Ibovespa (via proxy), Soja, Milho, Trigo
COTACOES_PARES = 'USD-BRL,EUR-BRL,BTC-BRL,ETH-BRL'

def buscar_cotacoes():
    """
    Busca cotações de moedas, cripto via AwesomeAPI.
    Busca commodities (soja, milho, trigo) e Ibovespa de fontes gratuitas.
    """
    cache_key = 'cotacoes_all'
    config = _get_config()
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not config.pode_requisitar('COTACOES'):
        logger.warning('Limite diário de requisições de cotações atingido.')
        return _cotacoes_fallback()

    result = {
        'tipo': 'COTACOES',
        'moedas': [],
        'cripto': [],
        'indices': [],
        'commodities': [],
        'atualizado_em': timezone.now().isoformat(),
    }

    try:
        # AwesomeAPI — moedas e cripto
        url = f'https://economia.awesomeapi.com.br/json/last/{COTACOES_PARES}'
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        config.registrar_requisicao('COTACOES')

        moedas_map = {
            'USDBRL': ('Dólar', 'USD', 'moeda'),
            'EURBRL': ('Euro', 'EUR', 'moeda'),
            'BTCBRL': ('Bitcoin', 'BTC', 'cripto'),
            'ETHBRL': ('Ethereum', 'ETH', 'cripto'),
        }

        for key, (nome, codigo, categoria) in moedas_map.items():
            if key in data:
                d = data[key]
                variacao = float(d.get('pctChange', 0))
                item = {
                    'nome': nome,
                    'codigo': codigo,
                    'valor': float(d.get('bid', 0)),
                    'variacao_pct': variacao,
                    'direcao': 'up' if variacao > 0 else ('down' if variacao < 0 else 'stable'),
                    'high': float(d.get('high', 0)),
                    'low': float(d.get('low', 0)),
                }
                if categoria == 'moeda':
                    result['moedas'].append(item)
                else:
                    result['cripto'].append(item)

    except Exception as e:
        logger.error(f'Erro ao buscar cotações AwesomeAPI: {e}')

    # ── BRAPI/Yahoo Finance — Ibovespa + Commodities (gratuito) ──
    _YF_HEADERS = {'User-Agent': 'Mozilla/5.0'}
    _YF_TICKERS = {
        '^BVSP': ('Ibovespa', 'IBOV', 'indice'),
        'ZS=F':  ('Soja',     'SOJ',  'commodity'),
        'ZC=F':  ('Milho',    'CORN', 'commodity'),
        'ZW=F':  ('Trigo',    'WHEAT','commodity'),
    }

    for ticker, (nome, codigo, cat) in _YF_TICKERS.items():
        try:
            yf_url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d'
            resp_yf = requests.get(yf_url, headers=_YF_HEADERS, timeout=10)
            if resp_yf.status_code == 200:
                meta = resp_yf.json()['chart']['result'][0]['meta']
                price = meta.get('regularMarketPrice')
                prev = meta.get('chartPreviousClose') or meta.get('previousClose')
                var = round(((price - prev) / prev) * 100, 2) if prev and price else None
                item = {
                    'nome': nome,
                    'codigo': codigo,
                    'valor': price,
                    'variacao_pct': var,
                    'direcao': 'up' if (var or 0) > 0 else ('down' if (var or 0) < 0 else 'stable'),
                }
                if cat == 'indice':
                    result['indices'].append(item)
                else:
                    # Commodities CBOT são em USD — converter com câmbio já obtido
                    usd_rate = None
                    for m in result['moedas']:
                        if m['codigo'] == 'USD':
                            usd_rate = m['valor']
                            break
                    if usd_rate and price:
                        item['valor_brl'] = round(price * usd_rate, 2)
                        item['unidade'] = 'USD/bushel'
                    result['commodities'].append(item)
        except Exception as e:
            logger.error(f'Erro ao buscar {nome} via Yahoo Finance: {e}')

    # Fallback — adicionar itens faltantes como placeholder
    if not result['indices']:
        result['indices'].append({
            'nome': 'Ibovespa', 'codigo': 'IBOV',
            'valor': None, 'variacao_pct': None, 'direcao': 'stable',
        })
    for cod, nome in [('SOJ', 'Soja'), ('CORN', 'Milho'), ('WHEAT', 'Trigo')]:
        if not any(c['codigo'] == cod for c in result['commodities']):
            result['commodities'].append(
                {'nome': nome, 'codigo': cod, 'valor': None, 'variacao_pct': None, 'direcao': 'stable'})

    cache_ttl = config.cache_cotacoes_minutos * 60
    cache.set(cache_key, result, cache_ttl)
    return result


def _cotacoes_fallback():
    return {
        'tipo': 'COTACOES',
        'moedas': [],
        'cripto': [],
        'indices': [],
        'commodities': [],
        'erro': 'Dados indisponíveis no momento',
        'atualizado_em': timezone.now().isoformat(),
    }


# ══════════════════════════════════════════════
#  NOTÍCIAS — NewsAPI.org (grátis 100 req/dia)
# ══════════════════════════════════════════════

def buscar_noticias():
    """
    Busca manchetes de notícias do Brasil via NewsAPI.
    Retorna lista de 5-10 manchetes.
    """
    cache_key = 'noticias_br'
    config = _get_config()
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not config.pode_requisitar('NOTICIAS'):
        logger.warning('Limite diário de requisições de notícias atingido.')
        return _noticias_fallback()

    api_key = config.noticias_api_key
    if not api_key:
        logger.warning('Chave da NewsAPI não configurada.')
        return _noticias_fallback_rss()

    try:
        url = (
            f'https://newsapi.org/v2/top-headlines'
            f'?country=br&pageSize=10&apiKey={api_key}'
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        config.registrar_requisicao('NOTICIAS')

        articles = data.get('articles', [])
        result = {
            'tipo': 'NOTICIAS',
            'manchetes': [],
            'atualizado_em': timezone.now().isoformat(),
        }

        for art in articles[:10]:
            result['manchetes'].append({
                'titulo': art.get('title', ''),
                'descricao': art.get('description', ''),
                'fonte': art.get('source', {}).get('name', ''),
                'imagem_url': art.get('urlToImage'),
                'publicado_em': art.get('publishedAt', ''),
            })

        cache_ttl = config.cache_noticias_minutos * 60
        cache.set(cache_key, result, cache_ttl)
        return result

    except Exception as e:
        logger.error(f'Erro ao buscar notícias: {e}')
        return _noticias_fallback_rss()


def _noticias_fallback_rss():
    """Fallback: busca notícias via RSS do Google News Brasil"""
    cache_key = 'noticias_rss_br'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # RSS do Google News Brasil (não requer chave)
        url = 'https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419'
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        # Parse simples do XML (sem dependência extra)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        items = root.findall('.//item')

        result = {
            'tipo': 'NOTICIAS',
            'manchetes': [],
            'atualizado_em': timezone.now().isoformat(),
            'fonte_tipo': 'rss',
        }

        for item in items[:10]:
            titulo = item.findtext('title', '')
            # Google News coloca a fonte depois de ' - '
            partes = titulo.rsplit(' - ', 1)
            manchete = partes[0] if partes else titulo
            fonte = partes[1] if len(partes) > 1 else 'Google News'

            result['manchetes'].append({
                'titulo': manchete,
                'descricao': item.findtext('description', ''),
                'fonte': fonte,
                'imagem_url': None,
                'publicado_em': item.findtext('pubDate', ''),
            })

        cache.set(cache_key, result, 3600)  # 1h
        return result

    except Exception as e:
        logger.error(f'Erro ao buscar notícias RSS: {e}')
        return _noticias_fallback()


def _noticias_fallback():
    return {
        'tipo': 'NOTICIAS',
        'manchetes': [],
        'atualizado_em': timezone.now().isoformat(),
        'erro': 'Notícias indisponíveis no momento',
    }


# ══════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL — chamada pela API da TV
# ══════════════════════════════════════════════

def buscar_dados_corporativos(tipo, municipio=None):
    """
    Busca dados para um conteúdo corporativo específico.
    
    Args:
        tipo: 'PREVISAO_TEMPO', 'COTACOES' ou 'NOTICIAS'
        municipio: instância de Municipio (necessário para previsão do tempo)
    
    Returns:
        dict com os dados formatados para o app renderizar
    """
    if tipo == 'PREVISAO_TEMPO':
        lat = float(municipio.latitude) if municipio and municipio.latitude else None
        lon = float(municipio.longitude) if municipio and municipio.longitude else None
        nome = str(municipio) if municipio else ''
        return buscar_previsao_tempo(lat, lon, nome)

    elif tipo == 'COTACOES':
        return buscar_cotacoes()

    elif tipo == 'NOTICIAS':
        return buscar_noticias()

    return {'tipo': tipo, 'erro': 'Tipo desconhecido'}
