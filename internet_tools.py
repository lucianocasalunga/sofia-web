#!/usr/bin/env python3
"""
Ferramentas de Internet para Sofia LiberNet
Geolocalização, Busca Web, Clima e Informações Contextuais
"""

import requests
from datetime import datetime
import pytz
import json
import os
import time
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import re

class InternetTools:
    """Ferramentas de internet para a Sofia"""

    def __init__(self):
        self.cache = {}  # Cache simples para evitar chamadas repetidas
        self._last_brave_request = 0  # Track last Brave API call for rate limiting

    def get_location_from_ip(self, ip_address: str) -> Dict[str, Any]:
        """
        Obtém localização a partir do IP do usuário
        Usa ipapi.co (gratuito, sem necessidade de API key)
        """
        # Não rastrear IPs locais
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            return {
                'city': 'Local',
                'region': 'Local',
                'country': 'Local',
                'timezone': 'UTC',
                'latitude': 0,
                'longitude': 0
            }

        # Verificar cache
        cache_key = f'location_{ip_address}'
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                location = {
                    'city': data.get('city', 'Desconhecida'),
                    'region': data.get('region', 'Desconhecida'),
                    'country': data.get('country_name', 'Desconhecido'),
                    'country_code': data.get('country_code', 'XX'),
                    'timezone': data.get('timezone', 'UTC'),
                    'latitude': data.get('latitude', 0),
                    'longitude': data.get('longitude', 0),
                    'currency': data.get('currency', 'USD')
                }
                self.cache[cache_key] = location
                return location
        except Exception as e:
            print(f"[INTERNET] Erro ao buscar localização: {e}")

        return {
            'city': 'Desconhecida',
            'region': 'Desconhecida',
            'country': 'Desconhecido',
            'timezone': 'UTC',
            'latitude': 0,
            'longitude': 0
        }

    def get_current_time(self, timezone_str: str) -> Dict[str, str]:
        """
        Retorna hora atual no timezone especificado
        """
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            return {
                'time': now.strftime('%H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                'weekday': now.strftime('%A'),
                'timezone': timezone_str,
                'utc_offset': now.strftime('%z')
            }
        except Exception as e:
            print(f"[INTERNET] Erro ao obter hora: {e}")
            now = datetime.utcnow()
            return {
                'time': now.strftime('%H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'weekday': now.strftime('%A'),
                'timezone': 'UTC',
                'utc_offset': '+0000'
            }

    def get_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Obtém informações de clima usando wttr.in (gratuito, sem API key)
        """
        cache_key = f'weather_{latitude}_{longitude}'
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Cache válido por 30 minutos
            if (datetime.now() - cached['cached_at']).seconds < 1800:
                return cached['data']

        try:
            # Usar wttr.in com formato JSON
            response = requests.get(
                f'https://wttr.in/{latitude},{longitude}?format=j1',
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                weather = {
                    'temperature_c': current['temp_C'],
                    'temperature_f': current['temp_F'],
                    'feels_like_c': current['FeelsLikeC'],
                    'feels_like_f': current['FeelsLikeF'],
                    'description': current['weatherDesc'][0]['value'],
                    'humidity': current['humidity'],
                    'wind_speed_kmh': current['windspeedKmph'],
                    'wind_direction': current['winddir16Point'],
                    'precipitation_mm': current['precipMM'],
                    'visibility_km': current['visibility'],
                    'uv_index': current['uvIndex']
                }
                self.cache[cache_key] = {
                    'data': weather,
                    'cached_at': datetime.now()
                }
                return weather
        except Exception as e:
            print(f"[INTERNET] Erro ao buscar clima: {e}")

        return {
            'temperature_c': 'N/A',
            'description': 'Informação não disponível',
            'humidity': 'N/A'
        }

    def search_web(self, query: str, num_results: int = 5) -> list:
        """
        Busca na web usando DuckDuckGo Instant Answer API (gratuito)
        """
        try:
            # DuckDuckGo Instant Answer API
            response = requests.get(
                'https://api.duckduckgo.com/',
                params={
                    'q': query,
                    'format': 'json',
                    'no_html': 1,
                    'skip_disambig': 1
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                # Abstract (resposta principal)
                if data.get('Abstract'):
                    results.append({
                        'title': data.get('Heading', query),
                        'snippet': data['Abstract'],
                        'url': data.get('AbstractURL', ''),
                        'source': data.get('AbstractSource', 'DuckDuckGo')
                    })

                # Related Topics
                for topic in data.get('RelatedTopics', [])[:num_results-1]:
                    if isinstance(topic, dict) and 'Text' in topic:
                        results.append({
                            'title': topic.get('Text', '')[:100],
                            'snippet': topic.get('Text', ''),
                            'url': topic.get('FirstURL', ''),
                            'source': 'DuckDuckGo'
                        })

                return results[:num_results]
        except Exception as e:
            print(f"[INTERNET] Erro ao buscar na web: {e}")

        return []

    def get_bitcoin_price(self) -> Dict[str, Any]:
        """
        Obtém preço atual do Bitcoin de CoinGecko (gratuito, sem API key)
        """
        try:
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={
                    'ids': 'bitcoin',
                    'vs_currencies': 'usd,brl',
                    'include_24hr_change': 'true',
                    'include_market_cap': 'true'
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                btc_data = data.get('bitcoin', {})
                return {
                    'price_usd': btc_data.get('usd', 0),
                    'price_brl': btc_data.get('brl', 0),
                    'change_24h': btc_data.get('usd_24h_change', 0),
                    'market_cap_usd': btc_data.get('usd_market_cap', 0),
                    'source': 'CoinGecko',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"[INTERNET] Erro ao buscar preço Bitcoin: {e}")

        return {'error': 'Não foi possível obter o preço atual'}

    def get_crypto_price(self, crypto_id: str = 'bitcoin') -> Dict[str, Any]:
        """
        Obtém preço de qualquer criptomoeda do CoinGecko
        Exemplos de IDs: bitcoin, ethereum, cardano, solana, etc
        """
        try:
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={
                    'ids': crypto_id,
                    'vs_currencies': 'usd,brl',
                    'include_24hr_change': 'true',
                    'include_market_cap': 'true'
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                crypto_data = data.get(crypto_id, {})
                return {
                    'crypto': crypto_id,
                    'price_usd': crypto_data.get('usd', 0),
                    'price_brl': crypto_data.get('brl', 0),
                    'change_24h': crypto_data.get('usd_24h_change', 0),
                    'market_cap_usd': crypto_data.get('usd_market_cap', 0),
                    'source': 'CoinGecko',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"[INTERNET] Erro ao buscar preço {crypto_id}: {e}")

        return {'error': f'Não foi possível obter o preço de {crypto_id}'}

    def fetch_webpage(self, url: str, max_length: int = 5000) -> Dict[str, Any]:
        """
        Acessa qualquer URL e extrai o conteúdo principal
        Similar ao WebFetch do Claude
        """
        try:
            # Headers para simular navegador real
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }

            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remover scripts, styles, etc
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()

            # Extrair texto principal
            # Priorizar tags de conteúdo
            main_content = soup.find('main') or soup.find('article') or soup.find('body')

            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)

            # Limpar texto
            text = re.sub(r'\s+', ' ', text).strip()

            # Limitar tamanho
            if len(text) > max_length:
                text = text[:max_length] + '...'

            # Extrair título
            title = soup.find('title')
            title_text = title.get_text().strip() if title else url

            return {
                'url': url,
                'title': title_text,
                'content': text,
                'length': len(text),
                'status': 'success'
            }

        except requests.exceptions.Timeout:
            return {'error': 'Timeout ao acessar URL', 'url': url}
        except requests.exceptions.RequestException as e:
            return {'error': f'Erro ao acessar URL: {str(e)}', 'url': url}
        except Exception as e:
            return {'error': f'Erro ao processar conteúdo: {str(e)}', 'url': url}

    def web_search_brave(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Busca na web usando Brave Search API (gratuita até 2k queries/mês)
        Retorna resultados reais de busca, similar ao Google Search
        """
        api_key = os.getenv('BRAVE_SEARCH_API_KEY')

        # Fallback para DuckDuckGo se não houver API key
        if not api_key:
            print("[INTERNET] BRAVE_SEARCH_API_KEY não configurada, usando DuckDuckGo")
            return self.search_web(query, count)

        # Rate limiting: 1 request/second para Brave API (limite free tier)
        time_since_last = time.time() - self._last_brave_request
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        self._last_brave_request = time.time()

        try:
            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers={
                    'X-Subscription-Token': api_key,
                    'Accept': 'application/json'
                },
                params={
                    'q': query,
                    'count': count
                    # Nota: search_lang removido - não suportado no free tier
                    # safesearch removido - usar default
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                # Resultados web
                for result in data.get('web', {}).get('results', [])[:count]:
                    results.append({
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'description': result.get('description', ''),
                        'source': 'Brave Search'
                    })

                return results
            else:
                print(f"[INTERNET] Brave Search erro {response.status_code}, fallback para DuckDuckGo")
                return self.search_web(query, count)

        except Exception as e:
            print(f"[INTERNET] Erro Brave Search: {e}, fallback para DuckDuckGo")
            return self.search_web(query, count)

    def search_news(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Busca notícias recentes usando Google News RSS (gratuito)
        """
        try:
            # Google News RSS - gratuito e sem API key
            rss_url = f'https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419'

            response = requests.get(rss_url, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')[:count]

                results = []
                for item in items:
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    description = item.find('description')

                    results.append({
                        'title': title.get_text() if title else '',
                        'url': link.get_text() if link else '',
                        'date': pub_date.get_text() if pub_date else '',
                        'description': description.get_text() if description else '',
                        'source': 'Google News'
                    })

                return results

        except Exception as e:
            print(f"[INTERNET] Erro ao buscar notícias: {e}")

        return []

    def get_user_context(self, ip_address: str) -> Dict[str, Any]:
        """
        Retorna contexto completo do usuário (localização + hora + clima)
        """
        location = self.get_location_from_ip(ip_address)
        time_info = self.get_current_time(location['timezone'])
        weather = self.get_weather(location['latitude'], location['longitude'])

        return {
            'location': location,
            'time': time_info,
            'weather': weather,
            'summary': f"{location['city']}, {location['country']} - {time_info['datetime']} - {weather['temperature_c']}°C, {weather['description']}"
        }

# Instância global
internet_tools = InternetTools()
