"""
Sistema de Billing - Sofia Web
Responsável por calcular e deduzir tokens baseado no uso real da OpenAI.
"""

from pricing_config import (
    OPENAI_COSTS,
    TOKEN_USAGE_PER_MESSAGE,
    AVAILABLE_MODELS,
    USD_PER_MILLION_TOKENS,
    usd_to_tokens,
    tokens_to_usd,
    sats_to_usd,
    usd_to_sats,
    format_tokens
)


class TokenBilling:
    """
    Classe responsável por toda a lógica de cobrança de tokens.
    """

    @staticmethod
    def calculate_real_cost(model_id: str, input_tokens: int, output_tokens: int) -> int:
        """
        Calcula o custo REAL em tokens internos baseado no uso da OpenAI API.

        Esta função é chamada APÓS receber a resposta da OpenAI, usando os
        valores reais de tokens consumidos (não estimativa).

        Args:
            model_id: ID do modelo usado ('gpt-4o-mini', 'gpt-5', 'gpt-5-internet')
            input_tokens: Quantidade de tokens de input (prompt) usados
            output_tokens: Quantidade de tokens de output (resposta) usados

        Returns:
            int: Quantidade de tokens internos a deduzir do saldo do usuário

        Raises:
            ValueError: Se modelo não existir

        Example:
            >>> billing = TokenBilling()
            >>> cost = billing.calculate_real_cost('gpt-4o-mini', 500, 500)
            >>> print(cost)  # ~270 tokens internos
        """
        # Validar modelo
        if model_id not in AVAILABLE_MODELS:
            raise ValueError(f"Modelo '{model_id}' não existe")

        # Mapear para OpenAI model real
        openai_model = AVAILABLE_MODELS[model_id]['openai_model']

        # Buscar custos OpenAI (USD por 1M tokens)
        if openai_model == 'gpt-4o-mini':
            input_cost_per_1m = 0.15
            output_cost_per_1m = 0.60
        elif openai_model == 'gpt-4o':
            input_cost_per_1m = 2.50
            output_cost_per_1m = 10.00
        else:
            # Fallback para custo médio
            avg_cost = OPENAI_COSTS.get(openai_model, 7.50)
            input_cost_per_1m = avg_cost * 0.25
            output_cost_per_1m = avg_cost * 1.33

        # Calcular custo em USD
        input_cost_usd = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost_usd = (output_tokens / 1_000_000) * output_cost_per_1m
        total_cost_usd = input_cost_usd + output_cost_usd

        # Se for modelo com internet, adicionar custo extra (~25%)
        if AVAILABLE_MODELS[model_id].get('has_internet', False):
            total_cost_usd *= 1.25

        # Converter USD para tokens internos
        # Nossa taxa: $8 por 1M tokens
        internal_tokens = int((total_cost_usd / USD_PER_MILLION_TOKENS) * 1_000_000)

        # Sempre arredondar para cima (nunca cobrar menos que o custo real)
        if (total_cost_usd / USD_PER_MILLION_TOKENS) * 1_000_000 > internal_tokens:
            internal_tokens += 1

        return internal_tokens

    @staticmethod
    def estimate_cost(model_id: str) -> int:
        """
        Estima o custo de uma mensagem ANTES de enviar para OpenAI.

        Usa custo médio pré-calculado. Útil para exibir ao usuário antes
        de ele enviar a mensagem.

        Args:
            model_id: ID do modelo

        Returns:
            int: Custo estimado em tokens internos

        Example:
            >>> TokenBilling.estimate_cost('gpt-5')
            4062
        """
        if model_id not in AVAILABLE_MODELS:
            raise ValueError(f"Modelo '{model_id}' não existe")

        # Usar consumo médio pré-calculado
        avg_tokens = AVAILABLE_MODELS[model_id]['avg_tokens_per_msg']

        # Mapear para OpenAI model real
        openai_model = AVAILABLE_MODELS[model_id]['openai_model']

        # Calcular custo em USD baseado no consumo médio
        avg_cost_usd = OPENAI_COSTS.get(openai_model, 7.50)
        total_cost_usd = (avg_tokens / 1_000_000) * avg_cost_usd

        # Se tiver internet, adicionar 25%
        if AVAILABLE_MODELS[model_id].get('has_internet', False):
            total_cost_usd *= 1.25

        # Converter para tokens internos
        internal_tokens = int((total_cost_usd / USD_PER_MILLION_TOKENS) * 1_000_000)

        return internal_tokens

    @staticmethod
    def convert_sats_to_tokens(sats: int) -> int:
        """
        Converte satoshis em tokens internos.

        Args:
            sats: Quantidade de satoshis

        Returns:
            int: Quantidade de tokens internos

        Example:
            >>> TokenBilling.convert_sats_to_tokens(1000)
            125000  # 1000 sats → $0.01 USD → 1250 tokens (com BTC @ $100k)
        """
        # Converter sats → USD
        usd_value = sats_to_usd(sats)

        # Converter USD → tokens
        tokens = usd_to_tokens(usd_value)

        return tokens

    @staticmethod
    def convert_tokens_to_sats(tokens: int) -> int:
        """
        Converte tokens internos em satoshis.

        Args:
            tokens: Quantidade de tokens

        Returns:
            int: Quantidade de satoshis

        Example:
            >>> TokenBilling.convert_tokens_to_sats(125000)
            1000
        """
        # Converter tokens → USD
        usd_value = tokens_to_usd(tokens)

        # Converter USD → sats
        sats = usd_to_sats(usd_value)

        return sats

    @staticmethod
    def check_sufficient_balance(balance: int, model_id: str) -> bool:
        """
        Verifica se o saldo é suficiente para enviar uma mensagem.

        Args:
            balance: Saldo atual de tokens do usuário
            model_id: Modelo que será usado

        Returns:
            bool: True se saldo é suficiente, False caso contrário

        Example:
            >>> TokenBilling.check_sufficient_balance(1000, 'gpt-5')
            False  # Precisa de ~4062 tokens
        """
        estimated = TokenBilling.estimate_cost(model_id)
        return balance >= estimated

    @staticmethod
    def get_shortage(balance: int, model_id: str) -> int:
        """
        Calcula quantos tokens estão faltando para enviar uma mensagem.

        Args:
            balance: Saldo atual
            model_id: Modelo desejado

        Returns:
            int: Quantidade de tokens faltando (0 se saldo suficiente)

        Example:
            >>> TokenBilling.get_shortage(1000, 'gpt-5')
            3062  # Precisa de 4062, tem 1000, falta 3062
        """
        estimated = TokenBilling.estimate_cost(model_id)
        shortage = estimated - balance
        return max(0, shortage)  # Nunca retornar negativo

    @staticmethod
    def calculate_messages_remaining(balance: int, model_id: str) -> int:
        """
        Calcula quantas mensagens o usuário ainda pode enviar com o saldo atual.

        Args:
            balance: Saldo de tokens
            model_id: Modelo que será usado

        Returns:
            int: Número de mensagens que pode enviar

        Example:
            >>> TokenBilling.calculate_messages_remaining(10000, 'gpt-4o-mini')
            37  # 10000 / 270 = 37 mensagens
        """
        cost_per_msg = TokenBilling.estimate_cost(model_id)
        if cost_per_msg == 0:
            return 0
        return int(balance / cost_per_msg)


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def format_cost_display(tokens: int, sats_equivalent: bool = False) -> str:
    """
    Formata custo para exibição ao usuário.

    Args:
        tokens: Quantidade de tokens
        sats_equivalent: Se True, mostra equivalente em sats

    Returns:
        str: String formatada

    Example:
        >>> format_cost_display(4062)
        "4.1k tokens"
        >>> format_cost_display(4062, sats_equivalent=True)
        "4.1k tokens (~8 sats)"
    """
    formatted = format_tokens(tokens) + " tokens"

    if sats_equivalent:
        billing = TokenBilling()
        sats = billing.convert_tokens_to_sats(tokens)
        formatted += f" (~{sats} sats)"

    return formatted


# ============================================
# TESTES
# ============================================

if __name__ == '__main__':
    print("=== TESTES DO SISTEMA DE BILLING ===\n")

    billing = TokenBilling()

    # Teste 1: Estimativa de custo
    print("1. ESTIMATIVA DE CUSTO POR MODELO:")
    for model in ['gpt-4o-mini', 'gpt-5', 'gpt-5-internet']:
        cost = billing.estimate_cost(model)
        print(f"   {model:20} → {cost:6} tokens/msg")
    print()

    # Teste 2: Cálculo real (exemplo: 500 input + 500 output)
    print("2. CUSTO REAL (500 input + 500 output tokens):")
    for model in ['gpt-4o-mini', 'gpt-5', 'gpt-5-internet']:
        real_cost = billing.calculate_real_cost(model, 500, 500)
        estimated = billing.estimate_cost(model)
        diff = real_cost - estimated
        print(f"   {model:20} → Real: {real_cost:5} | Estimado: {estimated:5} | Diff: {diff:+4}")
    print()

    # Teste 3: Conversão sats → tokens
    print("3. CONVERSÃO SATS → TOKENS:")
    for sats in [1000, 3500, 7000, 17500, 35000]:
        tokens = billing.convert_sats_to_tokens(sats)
        print(f"   {sats:6} sats → {format_tokens(tokens):>8} tokens")
    print()

    # Teste 4: Verificar saldo suficiente
    print("4. VERIFICAÇÃO DE SALDO:")
    test_balance = 10000
    print(f"   Saldo de teste: {test_balance} tokens")
    for model in ['gpt-4o-mini', 'gpt-5', 'gpt-5-internet']:
        sufficient = billing.check_sufficient_balance(test_balance, model)
        shortage = billing.get_shortage(test_balance, model)
        status = "✓ Suficiente" if sufficient else f"✗ Falta {shortage}"
        print(f"   {model:20} → {status}")
    print()

    # Teste 5: Mensagens restantes
    print("5. MENSAGENS RESTANTES COM SALDO:")
    for sats, balance_name in [(3500, 'Starter'), (17500, 'Standard'), (70000, 'Enterprise')]:
        tokens = billing.convert_sats_to_tokens(sats)
        print(f"   Pacote {balance_name} ({sats} sats = {format_tokens(tokens)} tokens):")
        for model in ['gpt-4o-mini', 'gpt-5', 'gpt-5-internet']:
            msgs = billing.calculate_messages_remaining(tokens, model)
            print(f"     {model:20} → {msgs:6} mensagens")
        print()
