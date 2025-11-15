#!/usr/bin/env python3
"""
Sofia Web - Payment Integration
Integração com LNBits e OpenNode para pagamentos Lightning Network
"""

import requests
import os
from typing import Optional, Dict

# === LOAD SECRETS FROM FILES ===
def _load_lnbits_env():
    """Carrega configuração do LNBits"""
    env_path = os.path.join(os.path.dirname(__file__), "secrets", "lnbits.env")
    cfg = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    return cfg

def _load_opennode_env():
    """Carrega configuração do OpenNode"""
    env_path = os.path.join(os.path.dirname(__file__), "secrets", "opennode.env")
    cfg = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    return cfg

# Carregar configurações
_lnbits_cfg = _load_lnbits_env()
_opennode_cfg = _load_opennode_env()

LNBITS_URL = _lnbits_cfg.get('LNBITS_URL', 'https://lnbits.libernet.app')
LNBITS_INVOICE_KEY = _lnbits_cfg.get('LNBITS_INVOICE_KEY', '')
LNBITS_ADMIN_KEY = _lnbits_cfg.get('LNBITS_ADMIN_KEY', '')
LNBITS_WALLET_ID = _lnbits_cfg.get('LNBITS_WALLET_ID', '')


class LNBitsClient:
    def __init__(self):
        self.url = LNBITS_URL
        self.invoice_key = LNBITS_INVOICE_KEY
        self.admin_key = LNBITS_ADMIN_KEY
        self.wallet_id = LNBITS_WALLET_ID

    def create_invoice(self, amount_sats: int, memo: str) -> Optional[Dict]:
        """
        Cria uma invoice Lightning
        Returns: {'payment_hash': str, 'payment_request': str, 'checking_id': str}
        """
        try:
            headers = {
                'X-Api-Key': self.invoice_key,
                'Content-Type': 'application/json'
            }

            data = {
                'out': False,  # incoming payment
                'amount': amount_sats,
                'memo': memo,
                'unit': 'sat'
            }

            response = requests.post(
                f'{self.url}/api/v1/payments',
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 201:
                invoice_data = response.json()
                return {
                    'payment_hash': invoice_data['payment_hash'],
                    'payment_request': invoice_data['payment_request'],
                    'checking_id': invoice_data['checking_id']
                }
            else:
                print(f"Erro ao criar invoice: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Erro na requisição LNBits: {e}")
            return None

    def check_invoice(self, payment_hash: str) -> Optional[Dict]:
        """
        Verifica status de um pagamento
        Returns: {'paid': bool, 'amount': int, 'fee': int}
        """
        try:
            headers = {
                'X-Api-Key': self.invoice_key
            }

            response = requests.get(
                f'{self.url}/api/v1/payments/{payment_hash}',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                payment_data = response.json()
                return {
                    'paid': payment_data['paid'],
                    'amount': payment_data.get('amount', 0),
                    'fee': payment_data.get('fee', 0)
                }
            else:
                return None

        except Exception as e:
            print(f"Erro ao verificar invoice: {e}")
            return None

    def get_balance(self) -> Optional[int]:
        """Retorna saldo da wallet em satoshis"""
        try:
            headers = {
                'X-Api-Key': self.admin_key
            }

            response = requests.get(
                f'{self.url}/api/v1/wallet',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                wallet_data = response.json()
                return wallet_data.get('balance', 0)
            else:
                return None

        except Exception as e:
            print(f"Erro ao obter saldo: {e}")
            return None


# Instância global
lnbits = LNBitsClient()


# === OPENNODE INTEGRATION ===
class OpenNodeClient:
    def __init__(self):
        self.api_key = _opennode_cfg.get('OPENNODE_API_KEY', '')
        self.base_url = _opennode_cfg.get('OPENNODE_API_URL', 'https://api.opennode.com/v1')

    def create_invoice(self, amount_sats: int, memo: str, callback_url: str = None) -> Optional[Dict]:
        """
        Cria invoice no OpenNode
        Returns: {'bolt11': str, 'payment_hash': str (charge_id)}
        """
        if not self.api_key:
            raise RuntimeError("OpenNode não configurado (API_KEY ausente)")

        url = f"{self.base_url}/charges"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "amount": amount_sats,
            "currency": "btc",
            "description": memo
        }

        if callback_url:
            payload["callback_url"] = callback_url

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=20)

            if r.status_code not in [200, 201]:
                raise RuntimeError(f"OpenNode erro HTTP {r.status_code}: {r.text}")

            data = r.json()
            charge_data = data.get("data", {})

            print(f"[OPENNODE] ✅ Invoice criado: {amount_sats} sats - {charge_data.get('id')}")

            return {
                "bolt11": charge_data.get("lightning_invoice", {}).get("payreq", ""),
                "payment_hash": charge_data.get("id"),  # usado como checking_id
                "checking_id": charge_data.get("id")
            }
        except Exception as e:
            print(f"[OPENNODE] ❌ Erro ao criar invoice: {e}")
            return None

    def check_invoice(self, charge_id: str) -> Optional[Dict]:
        """
        Verifica status de pagamento no OpenNode
        Returns: {'paid': bool}
        """
        if not self.api_key:
            raise RuntimeError("OpenNode não configurado (API_KEY ausente)")

        url = f"{self.base_url}/charge/{charge_id}"
        headers = {
            "Authorization": self.api_key
        }

        try:
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code not in [200, 201]:
                raise RuntimeError(f"OpenNode erro HTTP {r.status_code}: {r.text}")

            data = r.json()
            charge_data = data.get("data", {})

            # OpenNode retorna status: "paid", "unpaid", "processing", etc
            status = charge_data.get("status", "unpaid")
            is_paid = (status == "paid")

            return {
                "paid": is_paid,
                "status": status
            }
        except Exception as e:
            print(f"[OPENNODE] ❌ Erro ao verificar invoice: {e}")
            return None


# Instância global OpenNode
opennode = OpenNodeClient()
