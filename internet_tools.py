#!/usr/bin/env python3
"""
Ferramentas de Internet para Sofia LiberNet
Geolocalização, Busca Web, Clima e Informações Contextuais
"""

import requests
from datetime import datetime
import pytz
import json
from typing import Dict, Any, Optional

class InternetTools:
    """Ferramentas de internet para a Sofia"""

    def __init__(self):
        self.cache = {}  # Cache simples para evitar chamadas repetidas

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
