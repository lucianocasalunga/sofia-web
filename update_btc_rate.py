#!/usr/bin/env python3
"""
Script de Atualização Automática da Taxa BTC/USD

Busca preço atual do Bitcoin no CoinGecko e atualiza cache local.
Executar via cron a cada 24h: 0 0 * * * python3 /path/to/update_btc_rate.py

Autor: LiberNet
Data: 2025-11-17
"""

import sys
import os
from datetime import datetime

# Adicionar diretório do projeto ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from internet_tools import InternetTools


def update_btc_price():
    """
    Busca preço atual do BTC e atualiza cache.

    Returns:
        bool: True se atualizado com sucesso
    """
    print(f"\n{'='*60}")
    print(f"Atualização Taxa BTC - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    db = Database()
    internet = InternetTools()

    try:
        # Buscar preço atual do Bitcoin
        print("Buscando preço do Bitcoin no CoinGecko...")
        btc_data = internet.get_bitcoin_price()

        if 'error' in btc_data:
            print(f"❌ Erro ao buscar preço: {btc_data['error']}")
            return False

        usd_price = btc_data['price_usd']
        print(f"✅ Preço obtido: ${usd_price:,.2f} USD")

        # Atualizar cache no banco
        print("Atualizando cache no banco de dados...")
        success = db.update_btc_price_usd(usd_price)

        if success:
            print(f"✅ Cache atualizado com sucesso!")
            print(f"\nDetalhes:")
            print(f"  Preço USD: ${btc_data['price_usd']:,.2f}")
            print(f"  Preço BRL: R${btc_data['price_brl']:,.2f}")
            print(f"  Variação 24h: {btc_data['change_24h']:+.2f}%")
            print(f"  Market Cap: ${btc_data['market_cap_usd']:,.0f}")
            return True
        else:
            print(f"❌ Falha ao atualizar cache")
            return False

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print(f"\n{'='*60}\n")


def test_conversion():
    """
    Testa conversão USD → sats com taxa atualizada.
    """
    from pricing_config import usd_to_sats, sats_to_usd

    print("Testando conversões com taxa atual:\n")

    test_values_usd = [1.00, 10.00, 20.00, 50.00, 100.00]

    for usd in test_values_usd:
        sats = usd_to_sats(usd)
        usd_back = sats_to_usd(sats)
        print(f"  ${usd:6.2f} USD = {sats:8,} sats (volta: ${usd_back:.2f})")


if __name__ == '__main__':
    # Atualizar taxa
    success = update_btc_price()

    if success:
        # Testar conversões
        test_conversion()
        sys.exit(0)
    else:
        sys.exit(1)
