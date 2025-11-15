#!/usr/bin/env python3
"""
Nostr Integration for Sofia LiberNet
Desenvolvido por Claude para LiberNet - 2025-11-13

Permite Sofia atuar como uma identidade ativa na rede Nostr:
- Login com nsec (Nostr Secret Key)
- Publicação de notas
- Resposta a menções
- Integração com relay.libernet.app
"""

import time
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from pynostr.key import PrivateKey, PublicKey
from pynostr.event import Event, EventKind
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
from pynostr.message_type import ClientMessageType


class NostrClient:
    """Cliente Nostr para Sofia LiberNet"""

    def __init__(self, relay_url: str = "wss://relay.libernet.app"):
        """
        Inicializa cliente Nostr

        Args:
            relay_url: URL do relay Nostr (padrão: relay.libernet.app)
        """
        self.relay_url = relay_url
        self.relay_manager = RelayManager()
        self.private_key: Optional[PrivateKey] = None
        self.public_key: Optional[PublicKey] = None
        self.connected = False
        # Relays backup para buscar perfis
        self.backup_relays = [
            "wss://relay.damus.io",
            "wss://nos.lol",
            "wss://relay.nostr.band"
        ]

    def connect(self):
        """Conecta ao relay Nostr"""
        try:
            self.relay_manager.add_relay(self.relay_url)
            self.relay_manager.open_connections({"cert_reqs": None})
            time.sleep(1)  # Aguardar conexão
            self.connected = True
            print(f"[NOSTR] Conectado a {self.relay_url}")
            return True
        except Exception as e:
            print(f"[NOSTR] Erro ao conectar: {e}")
            return False

    def disconnect(self):
        """Desconecta do relay"""
        try:
            self.relay_manager.close_connections()
            self.connected = False
            print("[NOSTR] Desconectado")
        except Exception as e:
            print(f"[NOSTR] Erro ao desconectar: {e}")

    def load_identity(self, nsec: str) -> bool:
        """
        Carrega identidade Nostr a partir de nsec

        Args:
            nsec: Chave privada no formato nsec1...

        Returns:
            True se carregado com sucesso
        """
        try:
            self.private_key = PrivateKey.from_nsec(nsec)
            self.public_key = self.private_key.public_key

            npub = self.public_key.bech32()
            print(f"[NOSTR] Identidade carregada: {npub}")
            return True
        except Exception as e:
            print(f"[NOSTR] Erro ao carregar identidade: {e}")
            return False

    def verify_nsec(self, nsec: str) -> bool:
        """
        Verifica se nsec é válido

        Args:
            nsec: Chave privada no formato nsec1...

        Returns:
            True se válido
        """
        try:
            PrivateKey.from_nsec(nsec)
            return True
        except:
            return False

    def get_npub(self) -> Optional[str]:
        """
        Retorna npub (chave pública) da identidade atual

        Returns:
            npub no formato npub1... ou None
        """
        if self.public_key:
            return self.public_key.bech32()
        return None

    def hex_to_npub(self, pubkey_hex: str) -> str:
        """
        Converte pubkey hex para npub

        Args:
            pubkey_hex: Chave pública em formato hex

        Returns:
            npub no formato bech32
        """
        from pynostr.key import PublicKey
        pubkey = PublicKey(raw_bytes=bytes.fromhex(pubkey_hex))
        return pubkey.bech32()

    def get_npub_from_nsec(self, nsec: str) -> Optional[str]:
        """
        Extrai npub de um nsec

        Args:
            nsec: Chave privada no formato nsec1...

        Returns:
            npub correspondente ou None
        """
        try:
            pk = PrivateKey.from_nsec(nsec)
            return pk.public_key.bech32()
        except:
            return None

    def publish_note(self, content: str, tags: Optional[List[List[str]]] = None) -> Optional[str]:
        """
        Publica uma nota no Nostr

        Args:
            content: Conteúdo da nota
            tags: Tags opcionais (ex: [["p", "npub..."], ["t", "hashtag"]])

        Returns:
            ID do evento publicado ou None
        """
        if not self.private_key:
            print("[NOSTR] Erro: Identidade não carregada")
            return None

        if not self.connected:
            print("[NOSTR] Erro: Não conectado ao relay")
            return None

        try:
            # Criar evento
            event = Event(
                content=content,
                public_key=self.public_key.hex(),
                kind=EventKind.TEXT_NOTE
            )

            # Adicionar tags se fornecidas
            if tags:
                event.tags = tags

            # Assinar evento
            self.private_key.sign_event(event)

            # Publicar
            self.relay_manager.publish_event(event)
            time.sleep(0.5)  # Aguardar confirmação

            event_id = event.id
            print(f"[NOSTR] Nota publicada: {event_id[:16]}...")
            return event_id

        except Exception as e:
            print(f"[NOSTR] Erro ao publicar nota: {e}")
            return None

    def reply_to_note(self, content: str, reply_to_event_id: str, reply_to_pubkey: str) -> Optional[str]:
        """
        Responde a uma nota

        Args:
            content: Conteúdo da resposta
            reply_to_event_id: ID do evento sendo respondido
            reply_to_pubkey: Pubkey do autor da nota original

        Returns:
            ID do evento publicado ou None
        """
        tags = [
            ["e", reply_to_event_id, "", "reply"],
            ["p", reply_to_pubkey]
        ]

        return self.publish_note(content, tags)

    def get_mentions(self, since: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca menções à Sofia no relay

        Args:
            since: Timestamp UNIX para buscar desde
            limit: Número máximo de eventos

        Returns:
            Lista de eventos que mencionam Sofia
        """
        if not self.public_key:
            print("[NOSTR] Erro: Identidade não carregada")
            return []

        if not self.connected:
            print("[NOSTR] Erro: Não conectado ao relay")
            return []

        try:
            # Filtro para eventos que mencionam Sofia (tag 'p' com nosso pubkey)
            filters = FiltersList([
                Filters(
                    pubkey_refs=[self.public_key.hex()],
                    kinds=[EventKind.TEXT_NOTE],
                    since=since,
                    limit=limit
                )
            ])

            subscription_id = "sofia_mentions"
            self.relay_manager.add_subscription(subscription_id, filters)

            time.sleep(2)  # Aguardar respostas

            # Coletar eventos
            events = []
            while self.relay_manager.message_pool.has_events():
                event_msg = self.relay_manager.message_pool.get_event()
                if event_msg:
                    events.append(event_msg.event.__dict__)

            self.relay_manager.close_subscription(subscription_id)

            print(f"[NOSTR] Encontradas {len(events)} menções")
            return events

        except Exception as e:
            print(f"[NOSTR] Erro ao buscar menções: {e}")
            return []

    def fetch_user_profile(self, pubkey_hex: str) -> Optional[Dict[str, Any]]:
        """
        Busca perfil de um usuário do Nostr (NIP-01 kind 0)

        Args:
            pubkey_hex: Chave pública do usuário em formato hex

        Returns:
            Dict com metadados do perfil ou None se não encontrado
        """
        if not self.connected:
            print("[NOSTR] Erro: Não conectado ao relay")
            return None

        try:
            print(f"[NOSTR] 🔍 Buscando perfil para pubkey: {pubkey_hex[:16]}...")

            # Filtro para metadados do usuário (kind 0)
            filters = FiltersList([
                Filters(
                    authors=[pubkey_hex],
                    kinds=[EventKind.SET_METADATA],
                    limit=1
                )
            ])

            subscription_id = f"profile_{pubkey_hex[:8]}"
            print(f"[NOSTR] 📡 Adicionando subscription: {subscription_id}")
            self.relay_manager.add_subscription(subscription_id, filters)

            # Aumentado para 5 segundos para dar mais tempo ao relay
            print("[NOSTR] ⏳ Aguardando resposta do relay (5s)...")
            time.sleep(5)

            # Coletar eventos
            profile_data = None
            events_found = 0
            while self.relay_manager.message_pool.has_events():
                event_msg = self.relay_manager.message_pool.get_event()
                events_found += 1
                if event_msg and event_msg.event:
                    try:
                        profile_data = json.loads(event_msg.event.content)
                        print(f"[NOSTR] 📦 Evento parseado: {profile_data}")
                        break  # Usar apenas o primeiro (mais recente)
                    except Exception as parse_error:
                        print(f"[NOSTR] ⚠️ Erro ao parsear evento: {parse_error}")
                        pass

            print(f"[NOSTR] 📊 Total de eventos recebidos: {events_found}")
            self.relay_manager.close_subscription(subscription_id)

            if profile_data:
                print(f"[NOSTR] ✅ Perfil encontrado: {profile_data.get('name', 'sem nome')}")
                print(f"[NOSTR] 🖼️ Picture: {profile_data.get('picture', 'vazio')[:50]}...")
                return profile_data
            else:
                print(f"[NOSTR] ❌ Perfil não encontrado no relay principal")
                # Tentar buscar em relays backup
                print("[NOSTR] 🔄 Tentando relays backup...")
                return self.fetch_from_backup_relays(pubkey_hex)

        except Exception as e:
            print(f"[NOSTR] ❌ Erro ao buscar perfil: {e}")
            import traceback
            traceback.print_exc()
            # Tentar relays backup mesmo com erro
            try:
                return self.fetch_from_backup_relays(pubkey_hex)
            except:
                return None

    def fetch_from_backup_relays(self, pubkey_hex: str) -> Optional[Dict[str, Any]]:
        """
        Tenta buscar perfil em relays backup

        Args:
            pubkey_hex: Chave pública em formato hex

        Returns:
            Dict com perfil ou None
        """
        for backup_relay in self.backup_relays:
            try:
                print(f"[NOSTR] 🔍 Tentando relay backup: {backup_relay}")

                # Criar novo relay manager temporário
                temp_manager = RelayManager()
                temp_manager.add_relay(backup_relay)
                temp_manager.open_connections({"cert_reqs": None})
                time.sleep(2)

                # Buscar perfil
                filters = FiltersList([
                    Filters(
                        authors=[pubkey_hex],
                        kinds=[EventKind.SET_METADATA],
                        limit=1
                    )
                ])

                subscription_id = f"backup_{pubkey_hex[:8]}"
                temp_manager.add_subscription(subscription_id, filters)
                time.sleep(3)

                # Coletar eventos
                while temp_manager.message_pool.has_events():
                    event_msg = temp_manager.message_pool.get_event()
                    if event_msg and event_msg.event:
                        try:
                            profile_data = json.loads(event_msg.event.content)
                            print(f"[NOSTR] ✅ Perfil encontrado em {backup_relay}!")
                            temp_manager.close_subscription(subscription_id)
                            temp_manager.close_connections()
                            return profile_data
                        except:
                            pass

                temp_manager.close_subscription(subscription_id)
                temp_manager.close_connections()

            except Exception as e:
                print(f"[NOSTR] ⚠️ Falha no relay {backup_relay}: {e}")
                continue

        print("[NOSTR] ❌ Perfil não encontrado em nenhum relay")
        return None

    def get_profile_metadata(self) -> Dict[str, str]:
        """
        Retorna metadados do perfil Sofia

        Returns:
            Dict com name, about, picture, nip05
        """
        return {
            "name": "Sofia LiberNet",
            "about": "🤖 Primeira IA autônoma e descentralizada da rede Nostr | Desenvolvida pela LiberNet | Inteligência Artificial livre e privada",
            "picture": "https://libernet.app/logo-libernet.jpg",
            "nip05": "sofia@libernet.app",
            "lud16": "sofia@libernet.app",  # Lightning Address
            "website": "https://sofia.libernet.app",
            "banner": "https://libernet.app/banner-sofia.jpg"
        }

    def publish_profile(self) -> Optional[str]:
        """
        Publica metadados do perfil Sofia (NIP-01 kind 0)

        Returns:
            ID do evento publicado ou None
        """
        if not self.private_key or not self.connected:
            print("[NOSTR] Erro: Identidade não carregada ou não conectado")
            return None

        try:
            metadata = self.get_profile_metadata()

            event = Event(
                content=json.dumps(metadata),
                public_key=self.public_key.hex(),
                kind=EventKind.SET_METADATA  # kind 0
            )

            self.private_key.sign_event(event)
            self.relay_manager.publish_event(event)
            time.sleep(0.5)

            print(f"[NOSTR] Perfil publicado: {event.id[:16]}...")
            return event.id

        except Exception as e:
            print(f"[NOSTR] Erro ao publicar perfil: {e}")
            return None


# Instância global do cliente Nostr
nostr_client = NostrClient()


def initialize_sofia_nostr_identity(nsec: str) -> bool:
    """
    Inicializa identidade Nostr da Sofia

    Args:
        nsec: Chave privada nsec da Sofia

    Returns:
        True se inicializado com sucesso
    """
    if not nostr_client.load_identity(nsec):
        return False

    if not nostr_client.connect():
        return False

    # Publicar perfil
    nostr_client.publish_profile()

    return True


if __name__ == "__main__":
    # Teste básico
    print("🔐 Nostr Integration for Sofia LiberNet")
    print("=" * 50)

    # Para testar, você precisa fornecer um nsec
    # Exemplo: initialize_sofia_nostr_identity("nsec1...")
    print("Módulo carregado com sucesso!")
