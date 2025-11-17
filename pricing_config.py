"""
Configuração de Preços - Sistema de Tokens Sofia Web
Preços em USD com conversão dinâmica para sats (atualização 24h)
Margem mínima para sustentabilidade (6% = overhead Lightning + infra)
"""

# ============================================
# CONFIGURAÇÕES BASE
# ============================================

# Preço base por 1 milhão de tokens (USD)
# Calculado: Custo OpenAI GPT-4o ($7.50/1M) + margem 6% = $7.95 → arredondado $8.00
USD_PER_MILLION_TOKENS = 8.00

# Margem sobre custo OpenAI (apenas overhead)
# Lightning fees (~1.5%) + Infra (~2%) + Buffer (~2.5%) = 6%
OVERHEAD_MARGIN = 1.06

# Custos OpenAI reais (USD por 1M tokens, média ponderada input:output = 1:2)
OPENAI_COSTS = {
    'gpt-4o-mini': 0.45,      # ($0.15 * 1/3) + ($0.60 * 2/3) = $0.45/1M
    'gpt-4o': 7.50,           # ($2.50 * 1/3) + ($10.00 * 2/3) = $7.50/1M
}

# Taxa BTC padrão (será atualizada automaticamente via cron)
DEFAULT_BTC_PRICE_USD = 94000  # Fallback se DB falhar

# ============================================
# PACOTES DE RECARGA
# ============================================

RECHARGE_PACKAGES = {
    'starter': {
        'type': 'custom',           # Pacote customizável
        'name': 'Starter',
        'min_usd': 1.00,           # Pagamento mínimo: $1
        'max_usd': 100.00,         # Pagamento máximo: $100
        'rate': USD_PER_MILLION_TOKENS,  # $8 por 1M tokens
        'popular': False,
        'description': 'Escolha quanto quer adicionar (mínimo $1)'
    },
    'light': {
        'type': 'fixed',
        'name': 'Light',
        'usd_price': 10.00,
        'tokens': 1_250_000,       # 10 / 8 * 1M = 1.25M
        'popular': False,
        'description': 'Ideal para uso ocasional'
    },
    'standard': {
        'type': 'fixed',
        'name': 'Standard',
        'usd_price': 20.00,
        'tokens': 2_500_000,       # 20 / 8 * 1M = 2.5M
        'popular': True,           # Mais popular
        'description': 'Melhor custo-benefício'
    },
    'pro': {
        'type': 'fixed',
        'name': 'Pro',
        'usd_price': 50.00,
        'tokens': 6_250_000,       # 50 / 8 * 1M = 6.25M
        'popular': False,
        'description': 'Para uso intensivo'
    },
    'enterprise': {
        'type': 'fixed',
        'name': 'Enterprise',
        'usd_price': 100.00,
        'tokens': 12_500_000,      # 100 / 8 * 1M = 12.5M
        'popular': False,
        'description': 'Volume máximo'
    }
}

# ============================================
# CONSUMO ESTIMADO POR MODELO (tokens/mensagem)
# ============================================
# Baseado em dados reais de uso médio do sistema

TOKEN_USAGE_PER_MESSAGE = {
    'gpt-4o-mini': 300,        # 150 input + 150 output
    'gpt-5': 600,              # 250 input + 350 output (mapeado para gpt-4o) - REDUZIDO
    'gpt-5-internet': 1200     # 400 input + 600 output + 200 function calls - REDUZIDO
}

# ============================================
# MODELOS DISPONÍVEIS
# ============================================

AVAILABLE_MODELS = {
    'gpt-4o-mini': {
        'id': 'gpt-4o-mini',
        'name': 'Sofia 4.0',
        'display_name': 'Sofia 4.0 ⚡',
        'description': 'Econômica para conversas rápidas',
        'icon': '⚡',
        'openai_model': 'gpt-4o-mini',
        'has_internet': False,
        'avg_tokens_per_msg': TOKEN_USAGE_PER_MESSAGE['gpt-4o-mini']
    },
    'gpt-5': {
        'id': 'gpt-5',
        'name': 'Sofia 5.0',
        'display_name': 'Sofia 5.0 💎',
        'description': 'Avançada para trabalho sério',
        'icon': '💎',
        'openai_model': 'gpt-4o',  # Mapeado para gpt-4o
        'has_internet': False,
        'avg_tokens_per_msg': TOKEN_USAGE_PER_MESSAGE['gpt-5']
    },
    'gpt-5-internet': {
        'id': 'gpt-5-internet',
        'name': 'Sofia 5.0+',
        'display_name': 'Sofia 5.0+ 🌐',
        'description': 'Com acesso à internet em tempo real',
        'icon': '🌐',
        'openai_model': 'gpt-4o',  # Mapeado para gpt-4o
        'has_internet': True,
        'avg_tokens_per_msg': TOKEN_USAGE_PER_MESSAGE['gpt-5-internet']
    }
}

# ============================================
# FUNÇÕES UTILITÁRIAS
# ============================================

def usd_to_tokens(usd_amount: float) -> int:
    """
    Converte valor USD em tokens.

    Args:
        usd_amount: Valor em dólares

    Returns:
        int: Quantidade de tokens
    """
    return int((usd_amount / USD_PER_MILLION_TOKENS) * 1_000_000)


def tokens_to_usd(tokens: int) -> float:
    """
    Converte tokens em valor USD.

    Args:
        tokens: Quantidade de tokens

    Returns:
        float: Valor em dólares
    """
    return (tokens / 1_000_000) * USD_PER_MILLION_TOKENS


def usd_to_sats(usd_amount: float, btc_price: float = None) -> int:
    """
    Converte valor USD em satoshis.

    Args:
        usd_amount: Valor em dólares
        btc_price: Preço do Bitcoin em USD (usa cache se None)

    Returns:
        int: Quantidade de satoshis
    """
    if btc_price is None:
        # Buscar do cache (implementado em database.py)
        from database import Database
        db = Database()
        btc_price = db.get_btc_price_usd() or DEFAULT_BTC_PRICE_USD

    btc_amount = usd_amount / btc_price
    return int(btc_amount * 100_000_000)


def sats_to_usd(sats: int, btc_price: float = None) -> float:
    """
    Converte satoshis em valor USD.

    Args:
        sats: Quantidade de satoshis
        btc_price: Preço do Bitcoin em USD (usa cache se None)

    Returns:
        float: Valor em dólares
    """
    if btc_price is None:
        from database import Database
        db = Database()
        btc_price = db.get_btc_price_usd() or DEFAULT_BTC_PRICE_USD

    btc_amount = sats / 100_000_000
    return btc_amount * btc_price


def format_tokens(tokens: int) -> str:
    """
    Formata quantidade de tokens para exibição.

    Args:
        tokens: Quantidade de tokens

    Returns:
        str: String formatada (ex: 2.5M, 500k)
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.0f}k"
    else:
        return str(tokens)


def get_package_info(package_id: str, custom_usd: float = None) -> dict:
    """
    Retorna informações de um pacote de recarga.

    Args:
        package_id: ID do pacote
        custom_usd: Valor customizado (apenas para Starter)

    Returns:
        dict: Informações do pacote com preços atualizados
    """
    if package_id not in RECHARGE_PACKAGES:
        raise ValueError(f"Pacote '{package_id}' não existe")

    package = RECHARGE_PACKAGES[package_id].copy()

    # Buscar taxa BTC atual
    from database import Database
    db = Database()
    btc_price = db.get_btc_price_usd() or DEFAULT_BTC_PRICE_USD

    if package['type'] == 'custom':
        # Starter customizável
        if custom_usd is None:
            custom_usd = package['min_usd']

        # Validar limites
        if custom_usd < package['min_usd']:
            custom_usd = package['min_usd']
        if custom_usd > package['max_usd']:
            custom_usd = package['max_usd']

        package['usd_price'] = custom_usd
        package['tokens'] = usd_to_tokens(custom_usd)
        package['sats'] = usd_to_sats(custom_usd, btc_price)

    elif package['type'] == 'fixed':
        # Planos fixos
        package['sats'] = usd_to_sats(package['usd_price'], btc_price)

    # Adicionar estimativas de mensagens
    package['messages_estimate'] = {}
    for model_id, avg_tokens in TOKEN_USAGE_PER_MESSAGE.items():
        messages = int(package['tokens'] / avg_tokens)
        package['messages_estimate'][model_id] = messages

    # Adicionar info de atualização da taxa
    package['btc_price_usd'] = btc_price
    package['last_updated'] = db.get_btc_last_update()

    return package


def get_all_packages() -> dict:
    """
    Retorna todos os pacotes com preços atualizados.

    Returns:
        dict: Todos os pacotes
    """
    packages = {}
    for pkg_id in RECHARGE_PACKAGES.keys():
        packages[pkg_id] = get_package_info(pkg_id)
    return packages


def estimate_cost_usd(tokens: int) -> float:
    """
    Estima custo em USD baseado em tokens consumidos.

    Args:
        tokens: Quantidade de tokens

    Returns:
        float: Custo estimado em USD
    """
    return tokens_to_usd(tokens)


def estimate_messages(tokens: int, model_id: str = 'gpt-5') -> int:
    """
    Estima quantas mensagens dá para enviar com X tokens.

    Args:
        tokens: Quantidade de tokens
        model_id: ID do modelo

    Returns:
        int: Número estimado de mensagens
    """
    if model_id not in TOKEN_USAGE_PER_MESSAGE:
        model_id = 'gpt-5'  # Default

    avg_tokens = TOKEN_USAGE_PER_MESSAGE[model_id]
    return int(tokens / avg_tokens)


# ============================================
# VALIDAÇÃO E TESTE
# ============================================

if __name__ == '__main__':
    print("=== CONFIGURAÇÃO DE PREÇOS SOFIA WEB ===\n")

    print(f"PREÇO BASE:")
    print(f"  1 milhão de tokens = ${USD_PER_MILLION_TOKENS:.2f} USD")
    print(f"  Margem overhead: {int((OVERHEAD_MARGIN - 1) * 100)}%\n")

    print(f"TAXA BTC (fallback): ${DEFAULT_BTC_PRICE_USD:,}\n")

    print("CONSUMO MÉDIO POR MODELO:")
    for model_id, tokens in TOKEN_USAGE_PER_MESSAGE.items():
        model_name = AVAILABLE_MODELS[model_id]['display_name']
        print(f"  {model_name:20} → {tokens:5} tokens/msg")
    print()

    print("PACOTES DE RECARGA:")
    print(f"{'Nome':<12} | {'Tipo':<7} | {'USD':>8} | {'Tokens':>10} | {'Sats (BTC@$94k)':>18}")
    print("-" * 75)

    for pkg_id, pkg in RECHARGE_PACKAGES.items():
        if pkg['type'] == 'custom':
            print(f"{pkg['name']:<12} | {pkg['type']:<7} | {'$1-$100':>8} | {'Variável':>10} | {'~1.063-106.383':>18}")
        else:
            info = get_package_info(pkg_id)
            print(f"{pkg['name']:<12} | {pkg['type']:<7} | ${info['usd_price']:>7.2f} | {format_tokens(info['tokens']):>10} | ~{info['sats']:>16,}")

    print("\n" + "=" * 75 + "\n")

    # Exemplo prático
    print("EXEMPLO: Comprar $20 (Standard):")
    standard = get_package_info('standard')
    print(f"  Preço USD: ${standard['usd_price']:.2f}")
    print(f"  Preço Sats: ~{standard['sats']:,} sats (BTC @ ${standard['btc_price_usd']:,})")
    print(f"  Tokens: {format_tokens(standard['tokens'])}")
    print(f"  Mensagens estimadas:")
    for model_id, msgs in standard['messages_estimate'].items():
        model_name = AVAILABLE_MODELS[model_id]['name']
        print(f"    {model_name:12} → ~{msgs:,} mensagens")
