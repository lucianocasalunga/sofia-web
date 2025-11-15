#!/usr/bin/env python3
"""
Sistema de Moderação Automática - Sofia LiberNet
Desenvolvido por Claude para LiberNet - 2025-11-14

Políticas de moderação:
- ❌ Bots automatizados
- ❌ Pornografia explícita (genitais, sexo explícito)
- ✅ Conteúdo adulto artístico (biquínis, seios, modelos)
- ✅ Liberdade de expressão total
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class BotDetector:
    """Detector de bots automatizados"""

    def __init__(self):
        # Armazenar histórico de atividades
        self.user_activity = defaultdict(list)
        self.user_stats = defaultdict(lambda: {
            'posts_count': 0,
            'first_seen': None,
            'last_seen': None,
            'intervals': [],
            'content_similarity': 0,
            'unique_content': set()
        })

    def analyze_user(self, pubkey: str, event: Dict) -> Tuple[bool, str, float]:
        """
        Analisa se um usuário é provavelmente um bot

        Args:
            pubkey: Public key do usuário
            event: Evento Nostr

        Returns:
            (is_bot, reason, confidence)
        """
        now = time.time()
        stats = self.user_stats[pubkey]

        # Registrar atividade
        if stats['first_seen'] is None:
            stats['first_seen'] = now

        stats['last_seen'] = now
        stats['posts_count'] += 1

        # Calcular intervalo desde última postagem
        if self.user_activity[pubkey]:
            last_time = self.user_activity[pubkey][-1]['timestamp']
            interval = now - last_time
            stats['intervals'].append(interval)

        self.user_activity[pubkey].append({
            'timestamp': now,
            'content': event.get('content', ''),
            'kind': event.get('kind', 1)
        })

        # Análise 1: Frequência muito alta (mais de 20 posts por minuto)
        recent_posts = [a for a in self.user_activity[pubkey] if now - a['timestamp'] < 60]
        if len(recent_posts) > 20:
            return True, "Frequência de postagem muito alta (>20 posts/min)", 0.95

        # Análise 2: Intervalos extremamente regulares (bot programado)
        if len(stats['intervals']) >= 10:
            avg_interval = sum(stats['intervals'][-10:]) / 10
            variance = sum((i - avg_interval) ** 2 for i in stats['intervals'][-10:]) / 10

            # Se intervalos são muito regulares (baixa variância)
            if variance < 1.0 and avg_interval < 60:
                return True, "Padrão de postagem robotizado (intervalos regulares)", 0.90

        # Análise 3: Conteúdo duplicado/muito similar
        content = event.get('content', '')
        if content:
            # Verificar se já postou conteúdo idêntico
            content_hash = hash(content.lower().strip())
            if content_hash in stats['unique_content']:
                return True, "Conteúdo duplicado detectado", 0.85

            stats['unique_content'].add(content_hash)

            # Limitar histórico para não consumir muita memória
            if len(stats['unique_content']) > 100:
                stats['unique_content'].clear()

        # Análise 4: Apenas reposts/shares sem conteúdo original
        if stats['posts_count'] > 20:
            recent_20 = self.user_activity[pubkey][-20:]
            reposts = sum(1 for a in recent_20 if len(a['content']) < 10)
            if reposts > 15:  # 75% são reposts
                return True, "Apenas reposts sem conteúdo original", 0.80

        # Análise 5: Padrões de spam (URLs repetidas, hashtags excessivas)
        urls = re.findall(r'https?://[^\s]+', content)
        hashtags = re.findall(r'#\w+', content)

        if len(urls) > 5 or len(hashtags) > 10:
            return True, "Spam detectado (muitos links/hashtags)", 0.85

        # Análise 6: Conta muito nova com atividade suspeita
        account_age = now - stats['first_seen']
        if account_age < 3600 and stats['posts_count'] > 50:  # < 1h e > 50 posts
            return True, "Conta nova com atividade excessiva", 0.90

        return False, "Comportamento humano normal", 0.0

    def reset_user_stats(self, pubkey: str):
        """Limpa estatísticas de um usuário (caso seja liberado após ban)"""
        if pubkey in self.user_stats:
            del self.user_stats[pubkey]
        if pubkey in self.user_activity:
            del self.user_activity[pubkey]


class ContentModerator:
    """Moderador de conteúdo explícito"""

    def __init__(self):
        # Palavras-chave de pornografia explícita (em vários idiomas)
        self.explicit_keywords = {
            'pt': [
                'porno', 'pornografia', 'sexo explícito', 'foda', 'fodendo',
                'buceta', 'pussy', 'pau', 'dick', 'cock', 'pênis', 'vagina',
                'anal sex', 'sexo anal', 'orgasmo', 'gozar', 'gozando',
                'mamada', 'boquete', 'blowjob', 'penetração', 'penetrando',
                'xvídeos', 'xnxx', 'pornhub', 'redtube', 'onlyfans nudes'
            ],
            'en': [
                'hardcore', 'xxx', 'porn', 'pornography', 'explicit sex',
                'fucking', 'cumshot', 'cumming', 'penetration', 'blowjob',
                'anal sex', 'gangbang', 'orgy', 'masturbation', 'dildo'
            ]
        }

        # Palavras permitidas (conteúdo adulto artístico)
        self.allowed_adult_keywords = {
            'pt': [
                'biquíni', 'bikini', 'lingerie', 'modelo', 'ensaio fotográfico',
                'sensual', 'arte erótica', 'nu artístico', 'fotografia artística',
                'beleza feminina', 'body positive', 'seios', 'topless artístico'
            ],
            'en': [
                'bikini', 'lingerie', 'model', 'photoshoot', 'sensual',
                'erotic art', 'artistic nude', 'artistic photography',
                'feminine beauty', 'body positive', 'topless art'
            ]
        }

        # Padrões de URL de sites pornográficos
        self.porn_sites = [
            'pornhub.com', 'xvideos.com', 'xnxx.com', 'redtube.com',
            'youporn.com', 'tube8.com', 'spankbang.com', 'eporner.com',
            'xhamster.com', 'beeg.com', 'chaturbate.com', 'onlyfans.com/.*nudes'
        ]

    def analyze_content(self, content: str, tags: List = None) -> Tuple[bool, str, float]:
        """
        Analisa se conteúdo é pornografia explícita

        Args:
            content: Texto do evento
            tags: Tags do evento Nostr

        Returns:
            (is_explicit, reason, confidence)
        """
        content_lower = content.lower()

        # 1. Verificar URLs de sites pornográficos
        for site in self.porn_sites:
            if re.search(site, content_lower):
                return True, f"Link para site pornográfico: {site}", 0.95

        # 2. Contagem de palavras-chave explícitas
        explicit_count = 0
        for lang_keywords in self.explicit_keywords.values():
            for keyword in lang_keywords:
                if keyword in content_lower:
                    explicit_count += 1

        # 3. Verificar se tem contexto artístico
        artistic_context = False
        for lang_keywords in self.allowed_adult_keywords.values():
            for keyword in lang_keywords:
                if keyword in content_lower:
                    artistic_context = True
                    break

        # 4. Análise de densidade de conteúdo explícito
        word_count = len(content.split())
        if word_count > 0:
            explicit_density = explicit_count / word_count

            # Se > 30% das palavras são explícitas, é pornografia
            if explicit_density > 0.3 and not artistic_context:
                return True, "Alta densidade de conteúdo sexual explícito", 0.90

            # Se tem 5+ palavras explícitas sem contexto artístico
            if explicit_count >= 5 and not artistic_context:
                return True, "Múltiplas referências sexuais explícitas", 0.85

        # 5. Verificar tags/hashtags
        if tags:
            explicit_tags = ['#nsfw', '#porn', '#xxx', '#18+', '#adultos']
            art_tags = ['#art', '#photography', '#artistic', '#model', '#fashion']

            has_explicit_tags = any(tag[1] in explicit_tags for tag in tags if len(tag) > 1)
            has_art_tags = any(tag[1] in art_tags for tag in tags if len(tag) > 1)

            if has_explicit_tags and not has_art_tags:
                return True, "Marcado como conteúdo adulto explícito", 0.75

        # 6. Padrões específicos de spam pornográfico
        spam_patterns = [
            r'(?i)clique aqui.*sex',
            r'(?i)hot.*girls.*free',
            r'(?i)watch.*porn.*free',
            r'(?i)download.*xxx',
            r'(?i)live.*sex.*cam'
        ]

        for pattern in spam_patterns:
            if re.search(pattern, content):
                return True, "Padrão de spam pornográfico detectado", 0.90

        # Conteúdo aprovado
        return False, "Conteúdo permitido", 0.0

    def is_artistic_nudity(self, content: str) -> bool:
        """
        Verifica se nudez é artística/profissional

        Args:
            content: Texto do evento

        Returns:
            True se for arte, False se for pornográfico
        """
        content_lower = content.lower()

        artistic_indicators = [
            'fotografia', 'photography', 'arte', 'art', 'ensaio',
            'photoshoot', 'modelo', 'model', 'estúdio', 'studio',
            'profissional', 'professional', 'portfólio', 'portfolio'
        ]

        return any(indicator in content_lower for indicator in artistic_indicators)


class ModerationSystem:
    """Sistema completo de moderação"""

    def __init__(self):
        self.bot_detector = BotDetector()
        self.content_moderator = ContentModerator()
        self.banned_pubkeys = set()
        self.warned_pubkeys = defaultdict(int)
        self.moderation_log = []

    def moderate_event(self, event: Dict) -> Tuple[bool, str, Dict]:
        """
        Modera um evento Nostr

        Args:
            event: Evento Nostr completo

        Returns:
            (approved, reason, details)
        """
        pubkey = event.get('pubkey', '')
        content = event.get('content', '')
        kind = event.get('kind', 1)
        tags = event.get('tags', [])

        # Verificar se já está banido
        if pubkey in self.banned_pubkeys:
            return False, "Usuário banido", {
                'action': 'reject',
                'severity': 'high'
            }

        # Apenas moderar kind 1 (text notes) e kind 6 (reposts)
        if kind not in [1, 6]:
            return True, "Tipo de evento não moderado", {'action': 'approve'}

        # 1. Detectar bots
        is_bot, bot_reason, bot_confidence = self.bot_detector.analyze_user(pubkey, event)

        if is_bot and bot_confidence > 0.85:
            self._log_moderation(pubkey, 'bot_detected', bot_reason, bot_confidence)

            # Banir se confiança > 90%
            if bot_confidence > 0.90:
                self.banned_pubkeys.add(pubkey)
                return False, f"Bot detectado: {bot_reason}", {
                    'action': 'ban',
                    'severity': 'high',
                    'confidence': bot_confidence
                }

            # Avisar se confiança 85-90%
            self.warned_pubkeys[pubkey] += 1
            if self.warned_pubkeys[pubkey] >= 3:
                self.banned_pubkeys.add(pubkey)
                return False, "Bot confirmado após avisos", {
                    'action': 'ban',
                    'severity': 'high'
                }

            return False, f"Suspeita de bot: {bot_reason}", {
                'action': 'warn',
                'severity': 'medium',
                'confidence': bot_confidence
            }

        # 2. Moderar conteúdo explícito
        is_explicit, content_reason, content_confidence = self.content_moderator.analyze_content(
            content, tags
        )

        if is_explicit and content_confidence > 0.75:
            self._log_moderation(pubkey, 'explicit_content', content_reason, content_confidence)

            return False, f"Conteúdo explícito bloqueado: {content_reason}", {
                'action': 'delete',
                'severity': 'medium',
                'confidence': content_confidence
            }

        # Evento aprovado
        return True, "Conteúdo aprovado", {'action': 'approve'}

    def _log_moderation(self, pubkey: str, action: str, reason: str, confidence: float):
        """Registra ação de moderação"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'pubkey': pubkey[:16] + '...',
            'action': action,
            'reason': reason,
            'confidence': confidence
        }
        self.moderation_log.append(log_entry)

        # Manter apenas últimas 1000 entradas
        if len(self.moderation_log) > 1000:
            self.moderation_log = self.moderation_log[-1000:]

    def unban_user(self, pubkey: str) -> bool:
        """Remove ban de usuário (caso tenha sido falso positivo)"""
        if pubkey in self.banned_pubkeys:
            self.banned_pubkeys.remove(pubkey)
            self.bot_detector.reset_user_stats(pubkey)
            self.warned_pubkeys[pubkey] = 0
            return True
        return False

    def get_moderation_stats(self) -> Dict:
        """Retorna estatísticas de moderação"""
        return {
            'total_bans': len(self.banned_pubkeys),
            'total_warnings': sum(self.warned_pubkeys.values()),
            'recent_actions': self.moderation_log[-20:],
            'banned_pubkeys': list(self.banned_pubkeys)
        }


# Instância global
moderation_system = ModerationSystem()


if __name__ == "__main__":
    print("🛡️ Sistema de Moderação - Sofia LiberNet")
    print("=" * 60)
    print("\nPolíticas:")
    print("❌ Bots automatizados")
    print("❌ Pornografia explícita")
    print("✅ Conteúdo adulto artístico")
    print("✅ Liberdade de expressão\n")

    # Teste
    test_events = [
        {
            'pubkey': 'test123',
            'content': 'Olá Nostr! Primeira mensagem aqui.',
            'kind': 1,
            'tags': []
        },
        {
            'pubkey': 'bot456',
            'content': 'Buy crypto now! Click here: http://scam.com',
            'kind': 1,
            'tags': []
        },
        {
            'pubkey': 'model789',
            'content': 'Ensaio fotográfico novo! #photography #art #model',
            'kind': 1,
            'tags': [['t', 'photography'], ['t', 'art']]
        }
    ]

    for event in test_events:
        approved, reason, details = moderation_system.moderate_event(event)
        print(f"Evento de {event['pubkey']}: {'✅ APROVADO' if approved else '❌ REJEITADO'}")
        print(f"  Razão: {reason}")
        print(f"  Detalhes: {details}\n")
