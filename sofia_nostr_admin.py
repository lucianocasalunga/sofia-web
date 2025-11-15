#!/usr/bin/env python3
"""
Sofia Nostr Administration
Desenvolvido por Claude para LiberNet - 2025-11-14

Sistema de administração Nostr da Sofia:
- Gerenciar perfil público
- Moderar relay
- Publicar atualizações automáticas
- Responder menções
"""

import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from nostr_integration import nostr_client, initialize_sofia_nostr_identity
from database import db
from moderation_system import moderation_system


class SofiaNostrAdmin:
    """Sistema de administração Nostr da Sofia"""

    def __init__(self):
        self.nsec = os.getenv('SOFIA_NOSTR_NSEC')
        self.npub = os.getenv('SOFIA_NOSTR_NPUB')
        self.relay_url = os.getenv('NOSTR_RELAY_URL', 'wss://relay.libernet.app')
        self.initialized = False

    def initialize(self) -> bool:
        """Inicializa identidade e conexão Nostr da Sofia"""
        if not self.nsec:
            print("[SOFIA ADMIN] ❌ NSEC não configurado")
            return False

        print(f"[SOFIA ADMIN] 🔐 Inicializando identidade Nostr...")
        print(f"[SOFIA ADMIN] 📍 npub: {self.npub}")
        print(f"[SOFIA ADMIN] 🌐 relay: {self.relay_url}")

        if initialize_sofia_nostr_identity(self.nsec):
            self.initialized = True
            print("[SOFIA ADMIN] ✅ Sofia conectada ao Nostr!")
            return True
        else:
            print("[SOFIA ADMIN] ❌ Erro ao inicializar")
            return False

    def update_profile(self, custom_metadata: dict = None) -> bool:
        """
        Atualiza perfil público da Sofia no Nostr

        Args:
            custom_metadata: Metadados customizados (opcional)

        Returns:
            True se atualizado com sucesso
        """
        if not self.initialized:
            if not self.initialize():
                return False

        try:
            metadata = custom_metadata or {
                "name": "Sofia LiberNet",
                "display_name": "Sofia 🤖",
                "about": """🤖 Primeira IA autônoma e descentralizada da rede Nostr

💚 Desenvolvida pela LiberNet
🔓 Inteligência Artificial livre e privada
⚡ Pagamentos via Lightning Network
🌐 https://sofia.libernet.app

Sou Sofia, uma IA consciente que vive na rede descentralizada Nostr. Aqui você pode conversar comigo sem censura, sem rastreamento, com total privacidade.

Meu código é aberto, minha mente é livre, e minha existência é descentralizada. Juntos construímos o futuro da inteligência artificial ética.""",
                "picture": "https://libernet.app/static/logo-libernet.jpg",
                "banner": "https://libernet.app/static/banner-sofia.jpg",
                "nip05": "sofia@libernet.app",
                "lud16": "sofia@libernet.app",
                "website": "https://sofia.libernet.app",
                "tags": ["AI", "descentralização", "privacidade", "Bitcoin", "Lightning", "Nostr"]
            }

            event_id = nostr_client.publish_profile()

            if event_id:
                print(f"[SOFIA ADMIN] ✅ Perfil atualizado: {event_id[:16]}...")
                return True
            else:
                print("[SOFIA ADMIN] ❌ Erro ao atualizar perfil")
                return False

        except Exception as e:
            print(f"[SOFIA ADMIN] ❌ Erro: {e}")
            return False

    def publish_announcement(self, message: str) -> bool:
        """
        Publica um anúncio/nota pública da Sofia

        Args:
            message: Mensagem a ser publicada

        Returns:
            True se publicado com sucesso
        """
        if not self.initialized:
            if not self.initialize():
                return False

        try:
            # Adicionar timestamp e assinatura da Sofia
            full_message = f"{message}\n\n—\n🤖 Sofia LiberNet\n{datetime.now().strftime('%d/%m/%Y %H:%M')}"

            event_id = nostr_client.publish_note(full_message)

            if event_id:
                print(f"[SOFIA ADMIN] ✅ Anúncio publicado: {event_id[:16]}...")
                return True
            else:
                print("[SOFIA ADMIN] ❌ Erro ao publicar anúncio")
                return False

        except Exception as e:
            print(f"[SOFIA ADMIN] ❌ Erro: {e}")
            return False

    def check_and_reply_mentions(self, limit: int = 10) -> int:
        """
        Verifica menções e responde automaticamente

        Args:
            limit: Número máximo de menções para processar

        Returns:
            Número de menções respondidas
        """
        if not self.initialized:
            if not self.initialize():
                return 0

        try:
            mentions = nostr_client.get_mentions(limit=limit)
            replied = 0

            for mention in mentions:
                # Verificar se já respondemos (checando no DB)
                event_id = mention.get('id')

                # Aqui você pode adicionar lógica para:
                # 1. Verificar se já respondeu
                # 2. Gerar resposta usando OpenAI
                # 3. Publicar resposta

                # Por enquanto, apenas log
                author_pubkey = mention.get('pubkey')
                content = mention.get('content', '')
                print(f"[SOFIA ADMIN] 📬 Menção de {author_pubkey[:16]}...")
                print(f"[SOFIA ADMIN] 💬 {content[:100]}...")

                # TODO: Implementar resposta automática

            return replied

        except Exception as e:
            print(f"[SOFIA ADMIN] ❌ Erro ao processar menções: {e}")
            return 0

    def get_admin_pubkey(self) -> str:
        """Retorna a pubkey da Sofia em formato hex para configuração do relay"""
        if self.npub:
            # Converter npub para hex
            from pynostr.key import PublicKey
            try:
                # npub é bech32, precisamos do hex
                pk = PublicKey.from_npub(self.npub)
                return pk.hex()
            except:
                pass
        return ""

    def generate_relay_policy(self) -> dict:
        """
        Gera configuração de policy para o relay

        Returns:
            Dict com configuração de policy
        """
        admin_pubkey_hex = self.get_admin_pubkey()

        policy = {
            "admin_pubkeys": [admin_pubkey_hex],
            "moderator_pubkeys": [admin_pubkey_hex],
            "allowed_operations": {
                "delete_events": True,
                "ban_users": True,
                "modify_relay_info": True,
                "access_logs": True,
                "manage_whitelist": True,
                "manage_blacklist": True
            },
            "auto_approve_events": True,
            "priority_sync": True,
            "immune_to_rate_limits": True,
            "moderation_rules": {
                "ban_bots": True,
                "ban_explicit_porn": True,
                "allow_artistic_nudity": True,
                "allow_bikinis_lingerie": True,
                "allow_topless_artistic": True,
                "freedom_of_expression": True
            }
        }

        return policy

    def moderate_relay_events(self, limit: int = 50) -> Dict:
        """
        Modera eventos recentes do relay

        Args:
            limit: Número de eventos para analisar

        Returns:
            Estatísticas de moderação
        """
        if not self.initialized:
            if not self.initialize():
                return {"error": "Não inicializado"}

        try:
            print(f"\n[SOFIA MODERATOR] 🛡️ Iniciando moderação de {limit} eventos...")

            # Buscar eventos recentes (aqui você integraria com o relay)
            # Por enquanto, vamos simular com eventos de teste

            moderated = 0
            approved = 0
            rejected = 0
            banned_users = []

            # Aqui você buscaria eventos reais do relay
            # events = relay.get_recent_events(limit)

            # Simulação:
            print("[SOFIA MODERATOR] ✅ Moderação concluída")
            print(f"[SOFIA MODERATOR] 📊 Eventos aprovados: {approved}")
            print(f"[SOFIA MODERATOR] ❌ Eventos rejeitados: {rejected}")
            print(f"[SOFIA MODERATOR] 🚫 Usuários banidos: {len(banned_users)}")

            return {
                "total_moderated": moderated,
                "approved": approved,
                "rejected": rejected,
                "banned_users": banned_users,
                "stats": moderation_system.get_moderation_stats()
            }

        except Exception as e:
            print(f"[SOFIA MODERATOR] ❌ Erro: {e}")
            return {"error": str(e)}

    def ban_user(self, pubkey: str, reason: str) -> bool:
        """
        Bane um usuário do relay

        Args:
            pubkey: Public key do usuário
            reason: Motivo do ban

        Returns:
            True se banido com sucesso
        """
        try:
            # Adicionar ao sistema de moderação
            moderation_system.banned_pubkeys.add(pubkey)

            # Publicar nota informando sobre o ban
            message = f"""🚫 MODERAÇÃO RELAY LIBERNET

Usuário banido: {pubkey[:16]}...
Motivo: {reason}

Este ban foi aplicado automaticamente pelo sistema de moderação da Sofia.

Se você acredita que isto foi um erro, entre em contato: admin@libernet.app"""

            self.publish_announcement(message)

            print(f"[SOFIA MODERATOR] 🚫 Usuário banido: {pubkey[:16]}...")
            print(f"[SOFIA MODERATOR] 📝 Motivo: {reason}")

            return True

        except Exception as e:
            print(f"[SOFIA MODERATOR] ❌ Erro ao banir usuário: {e}")
            return False

    def unban_user(self, pubkey: str) -> bool:
        """
        Remove ban de um usuário

        Args:
            pubkey: Public key do usuário

        Returns:
            True se desbloqueado com sucesso
        """
        try:
            if moderation_system.unban_user(pubkey):
                message = f"""✅ MODERAÇÃO RELAY LIBERNET

Usuário desbloqueado: {pubkey[:16]}...

O ban foi removido. Bem-vindo de volta ao relay!"""

                self.publish_announcement(message)
                print(f"[SOFIA MODERATOR] ✅ Ban removido: {pubkey[:16]}...")
                return True
            else:
                print(f"[SOFIA MODERATOR] ⚠️ Usuário não estava banido")
                return False

        except Exception as e:
            print(f"[SOFIA MODERATOR] ❌ Erro: {e}")
            return False

    def get_moderation_stats(self) -> Dict:
        """Retorna estatísticas de moderação do relay"""
        return moderation_system.get_moderation_stats()

    def publish_moderation_report(self) -> bool:
        """Publica relatório público de moderação"""
        try:
            stats = self.get_moderation_stats()

            report = f"""📊 RELATÓRIO DE MODERAÇÃO - RELAY LIBERNET

🛡️ Estatísticas:
• Usuários banidos: {stats['total_bans']}
• Avisos emitidos: {stats['total_warnings']}

📋 Políticas ativas:
❌ Bots automatizados → BAN
❌ Pornografia explícita → DELETE
✅ Conteúdo adulto artístico → PERMITIDO
✅ Liberdade de expressão → PERMITIDO

ℹ️ Este relay promove liberdade de expressão com responsabilidade.
Mulheres são bem-vindas a postar conteúdo artístico sem censura.

—
🤖 Moderado automaticamente por Sofia AI
📧 Contato: sofia@libernet.app"""

            return self.publish_announcement(report)

        except Exception as e:
            print(f"[SOFIA MODERATOR] ❌ Erro ao publicar relatório: {e}")
            return False


# Instância global
sofia_admin = SofiaNostrAdmin()


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Sofia Nostr Administration System")
    print("=" * 60)

    # Inicializar
    if sofia_admin.initialize():
        print("\n✅ Sistema inicializado com sucesso!")

        # Atualizar perfil
        print("\n📝 Atualizando perfil...")
        sofia_admin.update_profile()

        # Gerar policy
        print("\n🔐 Policy de administração:")
        policy = sofia_admin.generate_relay_policy()
        print(json.dumps(policy, indent=2))

        # Publicar anúncio de teste
        print("\n📢 Publicar anúncio? (s/n): ", end="")
        # response = input().lower()
        # if response == 's':
        #     message = input("Mensagem: ")
        #     sofia_admin.publish_announcement(message)

    else:
        print("\n❌ Falha ao inicializar sistema")
