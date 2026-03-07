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

# Emojis para WMO weather codes
WMO_EMOJI = {
    0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
    45: '🌫️', 48: '🌫️',
    51: '🌦️', 53: '🌦️', 55: '🌧️', 56: '🌧️', 57: '🌧️',
    61: '🌧️', 63: '🌧️', 65: '🌧️', 66: '🌧️', 67: '🌧️',
    71: '🌨️', 73: '🌨️', 75: '❄️', 77: '🌨️',
    80: '🌦️', 81: '🌧️', 82: '⛈️',
    85: '🌨️', 86: '❄️',
    95: '⛈️', 96: '⛈️', 99: '⛈️',
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
            f'&forecast_days=7'
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
                'icone_emoji': WMO_EMOJI.get(wmo_code, '🌡️'),
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
                'icone_emoji': WMO_EMOJI.get(wmo_d, '🌡️'),
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

# Pares de moedas disponíveis
MOEDAS_DISPONIVEIS = {
    'USD': ('Dólar Americano', 'USDBRL'),
    'EUR': ('Euro', 'EURBRL'),
    'GBP': ('Libra Esterlina', 'GBPBRL'),
    'ARS': ('Peso Argentino', 'ARSBRL'),
    'JPY': ('Iene Japonês', 'JPYBRL'),
}

CRIPTO_DISPONIVEIS = {
    'BTC': ('Bitcoin', 'BTCBRL'),
    'ETH': ('Ethereum', 'ETHBRL'),
    'USDT': ('Tether', 'USDTBRL'),
    'XRP': ('Ripple', 'XRPBRL'),
    'ADA': ('Cardano', 'ADABRL'),
}

def buscar_cotacoes(moedas_codigos=None, cripto_codigos=None, commodities_codigos=None):
    """
    Busca cotações de moedas, cripto via AwesomeAPI.
    
    Args:
        moedas_codigos: lista de códigos (ex: ['USD', 'EUR']) ou None para todas
        cripto_codigos: lista de códigos (ex: ['BTC', 'ETH']) ou None para todas
        commodities_codigos: lista de códigos (ex: ['IBOV', 'SOJ']) ou None = não exibe nenhum
    """
    # Defaults se nada foi passado
    if moedas_codigos is None:
        moedas_codigos = ['USD', 'EUR']
    if cripto_codigos is None:
        cripto_codigos = ['BTC']
    if commodities_codigos is None:
        commodities_codigos = []  # por padrão não exibe nenhum índice/commodity
    
    # Construir string de pares para a API
    pares = []
    for cod in moedas_codigos:
        if cod in MOEDAS_DISPONIVEIS:
            pares.append(MOEDAS_DISPONIVEIS[cod][1])
    for cod in cripto_codigos:
        if cod in CRIPTO_DISPONIVEIS:
            pares.append(CRIPTO_DISPONIVEIS[cod][1])
    
    if not pares:
        pares = None  # Sem moedas/cripto selecionadas → pula chamada AwesomeAPI
    
    pares_str = ','.join(pares) if pares else 'none'
    cache_key = f'cotacoes_{pares_str}_comm_{"_".join(sorted(commodities_codigos))}'
    
    config = _get_config()
    cached = cache.get(cache_key)
    if cached:
        logger.info(f'[COTAÇÕES] Retornando dados do cache: {pares_str}')
        return cached

    if not config.pode_requisitar('COTACOES'):
        logger.warning('[COTAÇÕES] Limite diário de requisições atingido')
        return _cotacoes_fallback(cache_key, moedas_codigos, cripto_codigos, commodities_codigos)

    result = {
        'tipo': 'COTACOES',
        'moedas': [],
        'cripto': [],
        'indices': [],
        'commodities': [],
        'atualizado_em': timezone.now().isoformat(),
    }

    data = {}  # dados da AwesomeAPI — só preenchido se há moedas/cripto selecionadas

    # Só chama AwesomeAPI se há moedas ou cripto selecionadas
    if pares:
        # Retry com backoff exponencial para lidar com erro 429
        max_retries = 3
        import time
        
        for tentativa in range(max_retries):
            try:
                # AwesomeAPI — moedas e cripto
                url = f'https://economia.awesomeapi.com.br/json/last/{pares_str}'
                logger.info(f'[COTAÇÕES] Chamando AwesomeAPI (tentativa {tentativa + 1}/{max_retries}): {url}')
                resp = requests.get(url, timeout=10)
                
                # Tratamento específico para 429
                if resp.status_code == 429:
                    wait_time = (2 ** tentativa) * 2  # 2s, 4s, 8s
                    logger.warning(f'[COTAÇÕES] Erro 429 - aguardando {wait_time}s antes de retry')
                    if tentativa < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error('[COTAÇÕES] Limite de tentativas atingido após erro 429')
                        return _cotacoes_fallback(cache_key, moedas_codigos, cripto_codigos, commodities_codigos)
                
                resp.raise_for_status()
                data = resp.json()
                logger.info(f'[COTAÇÕES] Sucesso - {len(data)} cotações obtidas')
                config.registrar_requisicao('COTACOES')
                break  # Sucesso, sair do loop
                
            except requests.exceptions.RequestException as e:
                logger.error(f'[COTAÇÕES] Erro na tentativa {tentativa + 1}: {e}')
                if tentativa < max_retries - 1:
                    wait_time = (2 ** tentativa) * 2
                    logger.info(f'[COTAÇÕES] Aguardando {wait_time}s antes de retry')
                    time.sleep(wait_time)
                else:
                    logger.error('[COTAÇÕES] Todas as tentativas falharam')
                    return _cotacoes_fallback(cache_key, moedas_codigos, cripto_codigos, commodities_codigos)
        else:
            # Loop completou sem break - erro 429 persistente
            logger.warning('[COTAÇÕES] Rate limit persistente - usando cache longo')
            return _cotacoes_fallback(cache_key, moedas_codigos, cripto_codigos, commodities_codigos)

    try:

        # Mapear moedas solicitadas
        for cod in moedas_codigos:
            if cod in MOEDAS_DISPONIVEIS:
                nome, par = MOEDAS_DISPONIVEIS[cod]
                key = par.replace('-', '')  # USDBRL, EURBRL, etc
                if key in data:
                    d = data[key]
                    variacao = float(d.get('pctChange', 0))
                    result['moedas'].append({
                        'nome': nome,
                        'codigo': cod,
                        'valor': float(d.get('bid', 0)),
                        'variacao_pct': variacao,
                        'direcao': 'up' if variacao > 0 else ('down' if variacao < 0 else 'stable'),
                        'high': float(d.get('high', 0)),
                        'low': float(d.get('low', 0)),
                    })
        
        # Mapear criptos solicitadas
        for cod in cripto_codigos:
            if cod in CRIPTO_DISPONIVEIS:
                nome, par = CRIPTO_DISPONIVEIS[cod]
                key = par.replace('-', '')  # BTCBRL, ETHBRL, etc
                if key in data:
                    d = data[key]
                    variacao = float(d.get('pctChange', 0))
                    result['cripto'].append({
                        'nome': nome,
                        'codigo': cod,
                        'valor': float(d.get('bid', 0)),
                        'variacao_pct': variacao,
                        'direcao': 'up' if variacao > 0 else ('down' if variacao < 0 else 'stable'),
                        'high': float(d.get('high', 0)),
                        'low': float(d.get('low', 0)),
                    })

    except Exception as e:
        logger.error(f'Erro ao buscar cotações AwesomeAPI: {e}')

    # ── BRAPI/Yahoo Finance — Ibovespa + Commodities (gratuito) ──
    # Só busca se o usuário selecionou esses itens
    show_ibov = 'IBOV' in commodities_codigos
    show_soj  = 'SOJ'  in commodities_codigos
    show_corn = 'CORN' in commodities_codigos
    show_wheat= 'WHEAT'in commodities_codigos

    _YF_HEADERS = {'User-Agent': 'Mozilla/5.0'}
    _YF_TICKERS = {}
    if show_ibov:  _YF_TICKERS['^BVSP'] = ('Ibovespa', 'IBOV', 'indice')
    if show_soj:   _YF_TICKERS['ZS=F']  = ('Soja',     'SOJ',  'commodity')
    if show_corn:  _YF_TICKERS['ZC=F']  = ('Milho',    'CORN', 'commodity')
    if show_wheat: _YF_TICKERS['ZW=F']  = ('Trigo',    'WHEAT','commodity')

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
            logger.error(f'[COTAÇÕES] Erro ao buscar {nome} via Yahoo Finance: {e}')

    # Fallback — adicionar itens faltantes como placeholder SE solicitados
    if show_ibov and not result['indices']:
        result['indices'].append({
            'nome': 'Ibovespa', 'codigo': 'IBOV',
            'valor': None, 'variacao_pct': None, 'direcao': 'stable',
        })
    for cod, nome in [('SOJ', 'Soja'), ('CORN', 'Milho'), ('WHEAT', 'Trigo')]:
        if cod in commodities_codigos and not any(c['codigo'] == cod for c in result['commodities']):
            result['commodities'].append(
                {'nome': nome, 'codigo': cod, 'valor': None, 'variacao_pct': None, 'direcao': 'stable'})

    # Cache por 2 horas (aumentado para reduzir chamadas à API)
    cache_ttl = max(config.cache_cotacoes_minutos * 60, 7200)  # Mínimo 2 horas
    cache.set(cache_key, result, cache_ttl)
    logger.info(f'[COTAÇÕES] Dados cacheados por {cache_ttl}s ({cache_ttl//60}min)')
    return result


def _cotacoes_fallback(cache_key=None, moedas_codigos=None, cripto_codigos=None, commodities_codigos=None):
    """Retorna dados mockados quando API falha. Filtra pelos itens selecionados."""
    moedas_codigos = moedas_codigos or []
    cripto_codigos = cripto_codigos or []
    commodities_codigos = commodities_codigos or []

    _all_moedas = [
        {'nome': 'Dólar Americano', 'codigo': 'USD', 'valor': 5.85, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 5.90, 'low': 5.80},
        {'nome': 'Euro', 'codigo': 'EUR', 'valor': 6.35, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 6.40, 'low': 6.30},
        {'nome': 'Libra Esterlina', 'codigo': 'GBP', 'valor': 7.45, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 7.50, 'low': 7.40},
        {'nome': 'Peso Argentino', 'codigo': 'ARS', 'valor': 0.0055, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 0.0056, 'low': 0.0054},
        {'nome': 'Iene Japonês', 'codigo': 'JPY', 'valor': 0.038, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 0.039, 'low': 0.037},
    ]
    _all_cripto = [
        {'nome': 'Bitcoin', 'codigo': 'BTC', 'valor': 95000, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 96000, 'low': 94000},
        {'nome': 'Ethereum', 'codigo': 'ETH', 'valor': 5500, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 5600, 'low': 5400},
        {'nome': 'Tether', 'codigo': 'USDT', 'valor': 5.85, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 5.86, 'low': 5.84},
        {'nome': 'Ripple', 'codigo': 'XRP', 'valor': 12.50, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 12.80, 'low': 12.20},
        {'nome': 'Cardano', 'codigo': 'ADA', 'valor': 3.20, 'variacao_pct': 0.0, 'direcao': 'stable', 'high': 3.30, 'low': 3.10},
    ]
    _all_indices = [
        {'nome': 'Ibovespa', 'codigo': 'IBOV', 'valor': 130000, 'variacao_pct': 0.0, 'direcao': 'stable'},
    ]
    _all_commodities = [
        {'nome': 'Soja', 'codigo': 'SOJ', 'valor': 1450, 'variacao_pct': 0.0, 'direcao': 'stable', 'valor_brl': 8482, 'unidade': 'USD/bushel'},
        {'nome': 'Milho', 'codigo': 'CORN', 'valor': 485, 'variacao_pct': 0.0, 'direcao': 'stable', 'valor_brl': 2837, 'unidade': 'USD/bushel'},
        {'nome': 'Trigo', 'codigo': 'WHEAT', 'valor': 620, 'variacao_pct': 0.0, 'direcao': 'stable', 'valor_brl': 3627, 'unidade': 'USD/bushel'},
    ]

    fallback_data = {
        'tipo': 'COTACOES',
        'moedas':      [m for m in _all_moedas      if m['codigo'] in moedas_codigos],
        'cripto':      [c for c in _all_cripto      if c['codigo'] in cripto_codigos],
        'indices':     [i for i in _all_indices     if i['codigo'] in commodities_codigos],
        'commodities': [c for c in _all_commodities if c['codigo'] in commodities_codigos],
        'erro': 'Dados temporários - API indisponível (rate limit)',
        'atualizado_em': timezone.now().isoformat(),
    }
    
    # Cachear por 4 horas para evitar retry excessivo no rate limit
    if cache_key:
        cache_ttl = 14400  # 4 horas
        cache.set(cache_key, fallback_data, cache_ttl)
        logger.warning(f'[COTAÇÕES] Fallback cacheado por {cache_ttl}s (4h) - aguardar antes de nova tentativa')
    
    return fallback_data


# ══════════════════════════════════════════════
#  NOTÍCIAS — NewsAPI.org (grátis 100 req/dia)
# ══════════════════════════════════════════════

def buscar_noticias():
    """
    Busca manchetes de notícias do Brasil.
    Tenta: 1) NewsAPI  2) RSS G1  3) RSS Folha  4) RSS UOL  5) RSS Google News
    """
    cache_key = 'noticias_br'
    config = _get_config()
    cached = cache.get(cache_key)
    if cached and cached.get('manchetes'):
        logger.info('[NOTÍCIAS] Retornando dados do cache')
        return cached

    if not config.pode_requisitar('NOTICIAS'):
        logger.warning('[NOTÍCIAS] Limite diário de requisições atingido')
        return _noticias_fallback_rss()

    api_key = config.noticias_api_key
    if api_key and api_key.strip():
        logger.info(f'[NOTÍCIAS] Tentando NewsAPI: {api_key[:8]}...')
        try:
            # Tenta 3 queries em ordem até obter artigos
            _queries = [
                f'https://newsapi.org/v2/top-headlines?language=pt&pageSize=10&apiKey={api_key}',
                f'https://newsapi.org/v2/everything?q=brasil&language=pt&sortBy=publishedAt&pageSize=10&apiKey={api_key}',
                f'https://newsapi.org/v2/top-headlines?country=br&pageSize=10&apiKey={api_key}',
            ]
            articles = []
            for _url in _queries:
                resp = requests.get(_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                logger.info(f'[NOTÍCIAS] NewsAPI status: {resp.status_code} url={_url.replace(api_key,"KEY")}')
                if resp.status_code in (426, 401):
                    logger.warning(f'[NOTÍCIAS] NewsAPI {resp.status_code} — usando RSS')
                    break
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('status') == 'error':
                        logger.error(f'[NOTÍCIAS] Erro: {data.get("message")}')
                        break
                    articles = data.get('articles', [])
                    if articles:
                        logger.info(f'[NOTÍCIAS] {len(articles)} artigos obtidos')
                        break
                    logger.warning('[NOTÍCIAS] 0 artigos nesta query, tentando próxima...')

            if articles:
                config.registrar_requisicao('NOTICIAS')
                result = {
                    'tipo': 'NOTICIAS',
                    'manchetes': [
                        {
                            'titulo': a.get('title', ''),
                            'descricao': a.get('description', ''),
                            'fonte': a.get('source', {}).get('name', ''),
                            'imagem_url': a.get('urlToImage'),
                            'publicado_em': a.get('publishedAt', ''),
                        }
                        for a in articles[:10]
                    ],
                    'atualizado_em': timezone.now().isoformat(),
                }
                cache.set(cache_key, result, config.cache_noticias_minutos * 60)
                return result
        except Exception as e:
            logger.error(f'[NOTÍCIAS] Erro ao chamar NewsAPI: {e}')
    else:
        logger.info('[NOTÍCIAS] NewsAPI key não configurada — usando RSS direto')

    return _noticias_fallback_rss(cache_key, config)


def _noticias_fallback_rss(cache_key='noticias_br', config=None):
    """Busca notícias via RSS. Tenta múltiplas fontes BR em ordem."""
    # Fontes RSS brasileiras em ordem de preferência
    RSS_SOURCES = [
        ('G1',        'https://g1.globo.com/rss/g1/'),
        ('Folha',     'https://feeds.folha.uol.com.br/emcimadahora/rss091.xml'),
        ('UOL',       'https://rss.uol.com.br/feed/noticias.xml'),
        ('GoogleNews','https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419'),
    ]
    _HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; MediaExpand/1.0)'}

    import xml.etree.ElementTree as ET

    for nome, url in RSS_SOURCES:
        try:
            logger.info(f'[NOTÍCIAS] Tentando RSS {nome}: {url}')
            resp = requests.get(url, timeout=10, headers=_HEADERS)
            if resp.status_code != 200:
                logger.warning(f'[NOTÍCIAS] RSS {nome} retornou {resp.status_code}')
                continue

            root = ET.fromstring(resp.text)
            items = root.findall('.//item')
            if not items:
                logger.warning(f'[NOTÍCIAS] RSS {nome} sem itens')
                continue

            manchetes = []
            for item in items[:10]:
                titulo_raw = item.findtext('title', '') or ''
                # Google News coloca a fonte depois de ' - '
                partes = titulo_raw.rsplit(' - ', 1)
                titulo = partes[0].strip() if partes else titulo_raw
                fonte  = partes[1].strip() if len(partes) > 1 else nome

                # Extrair imagem: enclosure > media:content > media:thumbnail
                imagem_url = None
                encl = item.find('enclosure')
                if encl is not None:
                    tp = encl.get('type', '')
                    if 'image' in tp or not tp:
                        imagem_url = encl.get('url')
                if not imagem_url:
                    for _ns in ['{http://search.yahoo.com/mrss/}', '{http://video.search.yahoo.com/mrss/}']:
                        mc = item.find(f'{_ns}content')
                        if mc is not None:
                            u = mc.get('url')
                            if u: imagem_url = u; break
                if not imagem_url:
                    for _ns in ['{http://search.yahoo.com/mrss/}']:
                        mt = item.find(f'{_ns}thumbnail')
                        if mt is not None:
                            u = mt.get('url')
                            if u: imagem_url = u; break

                manchetes.append({
                    'titulo': titulo,
                    'descricao': item.findtext('description', '') or '',
                    'fonte': fonte,
                    'imagem_url': imagem_url,
                    'publicado_em': item.findtext('pubDate', '') or '',
                })

            if not manchetes:
                continue

            logger.info(f'[NOTÍCIAS] RSS {nome} OK — {len(manchetes)} manchetes')
            result = {
                'tipo': 'NOTICIAS',
                'manchetes': manchetes,
                'atualizado_em': timezone.now().isoformat(),
                'fonte_tipo': f'rss_{nome.lower()}',
            }
            # Só cacheia se tinha conteúdo
            ttl = (config.cache_noticias_minutos * 60) if config else 3600
            cache.set(cache_key, result, ttl)
            return result

        except Exception as e:
            logger.error(f'[NOTÍCIAS] Erro ao buscar RSS {nome}: {e}')
            continue

    logger.error('[NOTÍCIAS] Todas as fontes RSS falharam — retornando placeholder')
    return _noticias_fallback()


def _noticias_fallback():
    """Último recurso: retorna aviso de indisponibilidade (não cacheia)."""
    return {
        'tipo': 'NOTICIAS',
        'manchetes': [
            {'titulo': 'Notícias temporariamente indisponíveis', 'descricao': '', 'fonte': 'MediaExpand', 'imagem_url': None, 'publicado_em': ''},
            {'titulo': 'Verifique sua conexão com a internet', 'descricao': '', 'fonte': 'MediaExpand', 'imagem_url': None, 'publicado_em': ''},
        ],
        'atualizado_em': timezone.now().isoformat(),
        'erro': 'Fontes de notícias indisponíveis no momento',
    }


# ══════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL — chamada pela API da TV
# ══════════════════════════════════════════════

def buscar_dados_corporativos(tipo, municipio=None, conteudo=None):
    """
    Busca dados para um conteúdo corporativo específico.
    
    Args:
        tipo: 'PREVISAO_TEMPO', 'COTACOES' ou 'NOTICIAS'
        municipio: instância de Municipio (necessário para previsão do tempo)
        conteudo: instância de ConteudoCorporativo (usado para filtros, ex: cotações)
    
    Returns:
        dict com os dados formatados para o app renderizar
    """
    if tipo == 'PREVISAO_TEMPO':
        lat = float(municipio.latitude) if municipio and municipio.latitude else None
        lon = float(municipio.longitude) if municipio and municipio.longitude else None
        nome = str(municipio) if municipio else ''
        return buscar_previsao_tempo(lat, lon, nome)

    elif tipo == 'COTACOES':
        # Filtrar cotações baseado nas seleções do conteudo
        moedas_selecionadas = []
        cripto_selecionadas = []
        commodities_selecionadas = []
        
        if conteudo:
            moedas_selecionadas = conteudo.cotacoes_moedas or []
            cripto_selecionadas = conteudo.cotacoes_cripto or []
            commodities_selecionadas = conteudo.cotacoes_commodities or []
        
        # Só aplica defaults se absolutamente nada foi selecionado (nem moedas, cripto ou commodities)
        if not moedas_selecionadas and not cripto_selecionadas and not commodities_selecionadas:
            moedas_selecionadas = ['USD', 'EUR']
            cripto_selecionadas = ['BTC']
        
        return buscar_cotacoes(moedas_selecionadas, cripto_selecionadas, commodities_selecionadas)

    elif tipo == 'NOTICIAS':
        return buscar_noticias()

    return {'tipo': tipo, 'erro': 'Tipo desconhecido'}
