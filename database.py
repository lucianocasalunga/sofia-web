#!/usr/bin/env python3
"""
Sofia Web - Database Models
"""

import sqlite3
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import json

DB_PATH = '/app/data/sofia_users.db'

# Planos disponíveis (atualizado 2025-11-11)
PLANS = {
    'free': {
        'name': 'Free (teste)',
        'tokens_month': 100000,  # 100k tokens
        'price_usd': 0,
        'price_sats': 0,
        'price_brl': 0,
        'description': 'Teste gratuito com doação opcional'
    },
    'light': {
        'name': 'Light',
        'tokens_month': 500000,  # 500k tokens
        'price_usd': 2.50,
        'price_sats': 2600,
        'price_brl': 6,
        'description': 'Uso pessoal leve'
    },
    'standard': {
        'name': 'Standard',
        'tokens_month': 2000000,  # 2M tokens
        'price_usd': 10.00,
        'price_sats': 10000,
        'price_brl': 23,
        'description': 'Uso profissional'
    },
    'pro': {
        'name': 'Pro',
        'tokens_month': 10000000,  # 10M tokens
        'price_usd': 50.00,
        'price_sats': 50000,
        'price_brl': 115,
        'description': 'Uso intensivo e empresarial'
    }
}


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Inicializa o banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Tabela de usuários
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'user',
            plan TEXT DEFAULT 'free',
            tokens_used INTEGER DEFAULT 0,
            tokens_limit INTEGER DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            active BOOLEAN DEFAULT 1
        )
        ''')

        # Tabela de assinaturas/pagamentos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            payment_hash TEXT,
            amount_sats INTEGER,
            status TEXT DEFAULT 'pending',
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Tabela de uso (logs)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tokens_used INTEGER,
            model TEXT,
            request_text TEXT,
            response_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Tabela de chats nomeados
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_name TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            tokens_limit INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Tabela de mensagens do chat
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
        )
        ''')

        # Tabela de transações de tokens (recargas e uso)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            plan_name TEXT,
            payment_hash TEXT,
            amount_sats INTEGER,
            provider TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Tabela de projetos/pastas (para organizar chats)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            collapsed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Tabela de relação many-to-many entre projetos e chats
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE,
            UNIQUE(project_id, chat_id)
        )
        ''')

        # Adicionar coluna token_balance se não existir (migration)
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'token_balance' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN token_balance INTEGER DEFAULT 0')
            print("[DB] Coluna token_balance adicionada à tabela users")

        # Adicionar coluna preferred_model se não existir
        if 'preferred_model' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_model TEXT DEFAULT 'gpt-4o-mini'")
            print("[DB] Coluna preferred_model adicionada à tabela users")

        conn.commit()
        conn.close()

    def create_user(self, email: str, password: str, name: str = None, role: str = 'user') -> Optional[int]:
        """Cria um novo usuário"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Hash da senha
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            cursor.execute('''
            INSERT INTO users (email, password_hash, name, role, plan, tokens_limit)
            VALUES (?, ?, ?, ?, 'free', 50)
            ''', (email, password_hash, name, role))

            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Busca usuário por email"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Busca usuário por ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def verify_password(self, email: str, password: str) -> Optional[Dict]:
        """Verifica senha e retorna usuário"""
        user = self.get_user_by_email(email)
        if not user:
            return None

        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Atualizar last_login
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                          (datetime.now(), user['id']))
            conn.commit()
            conn.close()
            return user
        return None

    def update_tokens_used(self, user_id: int, tokens: int):
        """Incrementa tokens usados"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE users SET tokens_used = tokens_used + ?
        WHERE id = ?
        ''', (tokens, user_id))

        conn.commit()
        conn.close()

    def reset_monthly_tokens(self, user_id: int):
        """Reseta tokens do mês"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE users SET tokens_used = 0 WHERE id = ?', (user_id,))

        conn.commit()
        conn.close()

    def can_use_tokens(self, user_id: int, tokens_needed: int) -> bool:
        """Verifica se usuário pode usar N tokens"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        return (user['tokens_used'] + tokens_needed) <= user['tokens_limit']

    def upgrade_plan(self, user_id: int, plan: str, payment_hash: str = None):
        """Faz upgrade do plano do usuário"""
        if plan not in PLANS:
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        plan_info = PLANS[plan]
        expires_at = datetime.now() + timedelta(days=30)

        # Atualizar usuário
        cursor.execute('''
        UPDATE users
        SET plan = ?, tokens_limit = ?, tokens_used = 0
        WHERE id = ?
        ''', (plan, plan_info['tokens_month'], user_id))

        # Registrar assinatura
        cursor.execute('''
        INSERT INTO subscriptions (user_id, plan, payment_hash, amount_sats, status, expires_at)
        VALUES (?, ?, ?, ?, 'active', ?)
        ''', (user_id, plan, payment_hash, plan_info['price_sats'], expires_at))

        conn.commit()
        conn.close()
        return True

    def log_usage(self, user_id: int, tokens: int, model: str, request: str, response: str):
        """Registra uso no log"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO usage_logs (user_id, tokens_used, model, request_text, response_text)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, tokens, model, request[:1000], response[:1000]))

        conn.commit()
        conn.close()

    def get_user_stats(self, user_id: int) -> Dict:
        """Retorna estatísticas do usuário"""
        user = self.get_user_by_id(user_id)
        if not user:
            return {}

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT COUNT(*) as total_requests, SUM(tokens_used) as total_tokens
        FROM usage_logs WHERE user_id = ?
        ''', (user_id,))

        stats = dict(cursor.fetchone())
        conn.close()

        return {
            'user': user,
            'plan': PLANS.get(user['plan'], PLANS['free']),
            'tokens_used': user['tokens_used'],
            'tokens_remaining': user['tokens_limit'] - user['tokens_used'],
            'total_requests': stats['total_requests'] or 0,
            'total_tokens_all_time': stats['total_tokens'] or 0
        }

    def get_all_users(self) -> List[Dict]:
        """Retorna todos os usuários"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_user_plan(self, user_id: int, plan: str, tokens_limit: int = None):
        """Atualiza plano e limite de tokens do usuário"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if tokens_limit is None:
            tokens_limit = PLANS.get(plan, {}).get('tokens_month', 50)

        cursor.execute('''
        UPDATE users
        SET plan = ?, tokens_limit = ?
        WHERE id = ?
        ''', (plan, tokens_limit, user_id))

        conn.commit()
        conn.close()

    def update_user_nostr_profile(self, user_id: int, name: str, picture: str):
        """Atualiza nome e picture do usuário Nostr"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE users
        SET name = ?, picture = ?
        WHERE id = ?
        ''', (name, picture, user_id))

        conn.commit()
        conn.close()

    # ============= MÉTODOS DE CHATS NOMEADOS =============

    def create_chat(self, user_id: int, chat_name: str) -> Optional[int]:
        """Cria um novo chat nomeado para o usuário"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None

            # Limite de tokens do chat baseado no plano do usuário
            plan = PLANS.get(user['plan'], PLANS['free'])
            tokens_limit = plan['tokens_month']

            # Expira em 30 dias
            expires_at = datetime.now() + timedelta(days=30)

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO chats (user_id, chat_name, tokens_limit, expires_at)
            VALUES (?, ?, ?, ?)
            ''', (user_id, chat_name, tokens_limit, expires_at))

            chat_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return chat_id
        except Exception as e:
            print(f"Erro ao criar chat: {e}")
            return None

    def rename_chat(self, chat_id: int, new_name: str) -> bool:
        """Renomeia um chat"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE chats SET chat_name = ? WHERE id = ?
            ''', (new_name, chat_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao renomear chat: {e}")
            return False

    def delete_chat(self, chat_id: int) -> bool:
        """Exclui um chat (soft delete)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE chats SET active = 0 WHERE id = ?
            ''', (chat_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao excluir chat: {e}")
            return False

    def get_user_chats(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Lista todos os chats do usuário"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if active_only:
            cursor.execute('''
            SELECT * FROM chats
            WHERE user_id = ? AND active = 1
            ORDER BY updated_at DESC
            ''', (user_id,))
        else:
            cursor.execute('''
            SELECT * FROM chats
            WHERE user_id = ?
            ORDER BY updated_at DESC
            ''', (user_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_chat(self, chat_id: int) -> Optional[Dict]:
        """Busca chat por ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM chats WHERE id = ?', (chat_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def update_chat_tokens(self, chat_id: int, tokens: int):
        """Incrementa tokens usados no chat"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE chats SET tokens_used = tokens_used + ?
        WHERE id = ?
        ''', (tokens, chat_id))

        conn.commit()
        conn.close()

    def update_chat_accessed(self, chat_id: int):
        """Atualiza updated_at quando chat é acessado (para ordenação)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE chats SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (chat_id,))

        conn.commit()
        conn.close()

    def can_chat_use_tokens(self, chat_id: int, tokens_needed: int) -> bool:
        """Verifica se chat pode usar N tokens"""
        chat = self.get_chat(chat_id)
        if not chat or not chat['active']:
            return False

        return (chat['tokens_used'] + tokens_needed) <= chat['tokens_limit']

    def check_chat_limit(self, chat_id: int) -> Dict:
        """Verifica status do limite do chat (para avisar aos 80%)"""
        chat = self.get_chat(chat_id)
        if not chat:
            return {'error': 'Chat não encontrado'}

        usage_percent = (chat['tokens_used'] / chat['tokens_limit']) * 100

        return {
            'tokens_used': chat['tokens_used'],
            'tokens_limit': chat['tokens_limit'],
            'usage_percent': usage_percent,
            'warning': usage_percent >= 80,
            'limit_reached': usage_percent >= 100
        }

    def add_chat_message(self, chat_id: int, role: str, content: str, tokens: int = 0):
        """Adiciona mensagem ao histórico do chat"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO chat_messages (chat_id, role, content, tokens_used)
        VALUES (?, ?, ?, ?)
        ''', (chat_id, role, content, tokens))

        conn.commit()
        conn.close()

    def get_chat_messages(self, chat_id: int, limit: int = 100) -> List[Dict]:
        """Retorna histórico de mensagens do chat"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT * FROM chat_messages
        WHERE chat_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
        ''', (chat_id, limit))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def deactivate_chat(self, chat_id: int):
        """Desativa chat (soft delete)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE chats SET active = 0 WHERE id = ?', (chat_id,))

        conn.commit()
        conn.close()

    def delete_expired_chats(self):
        """Deleta chats expirados (7 dias após atingir limite)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Buscar chats que atingiram 100% do limite há mais de 7 dias
        cursor.execute('''
        SELECT c.id, c.chat_name, c.tokens_used, c.tokens_limit,
               MAX(cm.timestamp) as last_message
        FROM chats c
        LEFT JOIN chat_messages cm ON c.id = cm.chat_id
        WHERE c.active = 1 AND c.tokens_used >= c.tokens_limit
        GROUP BY c.id
        HAVING last_message < datetime('now', '-7 days')
        ''')

        expired_chats = cursor.fetchall()

        for chat in expired_chats:
            print(f"Deletando chat expirado: {chat['chat_name']} (ID: {chat['id']})")
            cursor.execute('DELETE FROM chats WHERE id = ?', (chat['id'],))

        conn.commit()
        count = len(expired_chats)
        conn.close()

        return count

    # ============= NOSTR INTEGRATION =============

    def add_npub_column_if_not_exists(self):
        """Adiciona coluna npub na tabela users se não existir"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Verificar se coluna já existe
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'npub' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN npub TEXT')
                conn.commit()
                print("[DB] Coluna 'npub' adicionada à tabela users")

                # Tentar criar índice único (pode falhar se já existir, mas não é crítico)
                try:
                    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_npub ON users(npub)')
                    conn.commit()
                    print("[DB] Índice único criado para npub")
                except:
                    pass
        except Exception as e:
            print(f"[DB] Erro ao adicionar coluna npub: {e}")
        finally:
            conn.close()

    def create_nostr_user(self, npub: str, name: str = None, plan: str = 'free') -> Optional[int]:
        """
        Cria usuário com autenticação Nostr

        Args:
            npub: Chave pública Nostr (npub1...)
            name: Nome do usuário (opcional)
            plan: Plano de assinatura

        Returns:
            ID do usuário criado ou None se já existir
        """
        self.add_npub_column_if_not_exists()

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Usar npub como email (temporário) e gerar hash vazio
            # (usuários Nostr não usam senha)
            dummy_password_hash = bcrypt.hashpw(b'nostr_user', bcrypt.gensalt()).decode()

            if not name:
                name = f"Nostr User {npub[:12]}..."

            cursor.execute('''
            INSERT INTO users (email, password_hash, name, role, plan, tokens_limit, npub)
            VALUES (?, ?, ?, 'user', ?, ?, ?)
            ''', (f"{npub}@nostr.local", dummy_password_hash, name, plan, PLANS[plan]['tokens_month'], npub))

            conn.commit()
            user_id = cursor.lastrowid
            print(f"[DB] Usuário Nostr criado: {npub[:16]}... (ID: {user_id})")
            return user_id

        except sqlite3.IntegrityError:
            # Usuário já existe
            print(f"[DB] Usuário Nostr já existe: {npub[:16]}...")
            return None
        except Exception as e:
            print(f"[DB] Erro ao criar usuário Nostr: {e}")
            return None
        finally:
            conn.close()

    def get_user_by_npub(self, npub: str) -> Optional[Dict]:
        """
        Busca usuário por npub

        Args:
            npub: Chave pública Nostr

        Returns:
            Dict com dados do usuário ou None
        """
        self.add_npub_column_if_not_exists()

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE npub = ?', (npub,))
        user = cursor.fetchone()
        conn.close()

        if user:
            return dict(user)
        return None

    def verify_nostr_login(self, npub: str) -> Optional[Dict]:
        """
        Verifica login Nostr

        Args:
            npub: Chave pública Nostr

        Returns:
            Dict com dados do usuário ou None se não existir
        """
        user = self.get_user_by_npub(npub)

        if user:
            # Atualizar last_login
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                          (datetime.now(), user['id']))
            conn.commit()
            conn.close()

            return user

        return None

    def link_npub_to_existing_user(self, user_id: int, npub: str) -> bool:
        """
        Vincula npub a um usuário existente

        Args:
            user_id: ID do usuário
            npub: Chave pública Nostr

        Returns:
            True se vinculado com sucesso
        """
        self.add_npub_column_if_not_exists()

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('UPDATE users SET npub = ? WHERE id = ?', (npub, user_id))
            conn.commit()
            print(f"[DB] npub vinculado ao usuário ID {user_id}")
            return True
        except Exception as e:
            print(f"[DB] Erro ao vincular npub: {e}")
            return False
        finally:
            conn.close()

    # ===== MÉTODOS DE GERENCIAMENTO DE TOKENS =====

    def add_tokens_to_user(self, user_id: int, tokens: int, plan: str,
                          payment_hash: str, amount_sats: int, provider: str) -> bool:
        """
        Adiciona tokens ao saldo do usuário após pagamento confirmado

        Args:
            user_id: ID do usuário
            tokens: Quantidade de tokens a adicionar
            plan: Nome do plano (starter, light, standard, pro, enterprise)
            payment_hash: Hash do pagamento Lightning
            amount_sats: Valor pago em satoshis
            provider: Provedor de pagamento (lnbits ou opennode)

        Returns:
            True se tokens foram creditados com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Atualizar saldo do usuário
            cursor.execute('''
                UPDATE users
                SET token_balance = token_balance + ?
                WHERE id = ?
            ''', (tokens, user_id))

            # Registrar transação
            description = f"Recarga {plan} - {tokens:,} tokens"
            cursor.execute('''
                INSERT INTO token_transactions
                (user_id, amount, transaction_type, plan_name, payment_hash,
                 amount_sats, provider, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, tokens, 'recharge', plan, payment_hash,
                  amount_sats, provider, description))

            conn.commit()
            print(f"[DB] ✓ {tokens:,} tokens creditados ao usuário {user_id} (plano {plan})")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Erro ao adicionar tokens: {e}")
            return False
        finally:
            conn.close()

    def deduct_tokens_from_user(self, user_id: int, tokens: int,
                               model: str = None, description: str = None) -> bool:
        """
        Deduz tokens do usuário ao usar a API

        Args:
            user_id: ID do usuário
            tokens: Quantidade de tokens a deduzir
            model: Modelo usado (gpt-4o-mini ou gpt-4o)
            description: Descrição opcional do uso

        Returns:
            True se tokens foram deduzidos com sucesso, False se saldo insuficiente
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Verificar saldo atual
            cursor.execute('SELECT token_balance FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()

            if not result:
                print(f"[DB] ✗ Usuário {user_id} não encontrado")
                return False

            current_balance = result['token_balance']

            if current_balance < tokens:
                print(f"[DB] ✗ Saldo insuficiente: {current_balance} < {tokens}")
                return False

            # Deduzir tokens
            cursor.execute('''
                UPDATE users
                SET token_balance = token_balance - ?
                WHERE id = ?
            ''', (tokens, user_id))

            # Registrar transação
            if not description:
                model_name = "Sofia 4.0 (mini)" if model == "gpt-4o-mini" else "Sofia 4.5 (full)"
                description = f"Uso da API - {model_name} ({tokens} tokens)"

            cursor.execute('''
                INSERT INTO token_transactions
                (user_id, amount, transaction_type, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, -tokens, 'usage', description))

            conn.commit()
            new_balance = current_balance - tokens
            print(f"[DB] ✓ {tokens} tokens deduzidos do usuário {user_id} (saldo: {new_balance})")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Erro ao deduzir tokens: {e}")
            return False
        finally:
            conn.close()

    def get_user_balance(self, user_id: int) -> int:
        """
        Retorna saldo atual de tokens do usuário

        Args:
            user_id: ID do usuário

        Returns:
            Saldo de tokens (0 se usuário não encontrado)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT token_balance FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()

            if result:
                return result['token_balance'] or 0
            return 0

        except Exception as e:
            print(f"[DB] Erro ao buscar saldo: {e}")
            return 0
        finally:
            conn.close()

    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Retorna histórico de transações de tokens do usuário

        Args:
            user_id: ID do usuário
            limit: Número máximo de transações a retornar

        Returns:
            Lista de transações ordenadas por data (mais recente primeiro)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM token_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))

            transactions = [dict(row) for row in cursor.fetchall()]
            return transactions

        except Exception as e:
            print(f"[DB] Erro ao buscar transações: {e}")
            return []
        finally:
            conn.close()

    def deduct_tokens(self, user_id: int, tokens: int, model_id: str,
                     chat_id: int = None, input_tokens: int = 0,
                     output_tokens: int = 0) -> bool:
        """
        Deduz tokens do saldo do usuário após uso REAL da OpenAI API

        Args:
            user_id: ID do usuário
            tokens: Quantidade REAL de tokens internos a deduzir
            model_id: ID do modelo usado (gpt-4o-mini, gpt-5, gpt-5-internet)
            chat_id: ID do chat (opcional, para rastreamento)
            input_tokens: Tokens de input da OpenAI (para auditoria)
            output_tokens: Tokens de output da OpenAI (para auditoria)

        Returns:
            True se deduzido com sucesso, False se saldo insuficiente
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Verificar saldo atual
            cursor.execute('SELECT token_balance FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()

            if not result:
                print(f"[DB] ✗ Usuário {user_id} não encontrado")
                return False

            current_balance = result['token_balance'] or 0

            if current_balance < tokens:
                print(f"[DB] ✗ Saldo insuficiente: {current_balance} < {tokens}")
                return False

            # Deduzir tokens
            cursor.execute('''
                UPDATE users
                SET token_balance = token_balance - ?
                WHERE id = ?
            ''', (tokens, user_id))

            # Registrar transação detalhada
            model_names = {
                'gpt-4o-mini': 'Sofia Mini ⚡',
                'gpt-5': 'Sofia 5.0 💎',
                'gpt-5-internet': 'Sofia 5.0+ 🌐'
            }
            model_name = model_names.get(model_id, model_id)

            description = f"Uso de {model_name}"
            if chat_id:
                description += f" (Chat #{chat_id})"
            if input_tokens and output_tokens:
                description += f" - {input_tokens}→{output_tokens} tokens OpenAI"

            cursor.execute('''
                INSERT INTO token_transactions
                (user_id, amount, transaction_type, plan_name, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, -tokens, 'usage', model_id, description))

            conn.commit()
            new_balance = current_balance - tokens
            print(f"[DB] ✓ {tokens:,} tokens deduzidos do usuário {user_id} "
                  f"({model_name}, saldo: {new_balance:,})")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Erro ao deduzir tokens: {e}")
            return False
        finally:
            conn.close()

    def check_sufficient_balance(self, user_id: int, model_id: str) -> Dict:
        """
        Verifica se usuário tem saldo suficiente para usar um modelo

        Args:
            user_id: ID do usuário
            model_id: ID do modelo (gpt-4o-mini, gpt-5, gpt-5-internet)

        Returns:
            Dict com: sufficient (bool), balance (int), estimated_cost (int),
                     shortage (int), messages_remaining (int)
        """
        from pricing_config import TOKEN_USAGE_PER_MESSAGE

        balance = self.get_user_balance(user_id)
        estimated_cost = TOKEN_USAGE_PER_MESSAGE.get(model_id, 0)

        return {
            'sufficient': balance >= estimated_cost,
            'balance': balance,
            'estimated_cost': estimated_cost,
            'shortage': max(0, estimated_cost - balance),
            'messages_remaining': int(balance / estimated_cost) if estimated_cost > 0 else 0
        }

    def set_preferred_model(self, user_id: int, model_id: str) -> bool:
        """
        Define modelo preferido do usuário

        Args:
            user_id: ID do usuário
            model_id: ID do modelo

        Returns:
            True se atualizado com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE users
                SET preferred_model = ?
                WHERE id = ?
            ''', (model_id, user_id))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Erro ao atualizar modelo preferido: {e}")
            return False
        finally:
            conn.close()

    def get_preferred_model(self, user_id: int) -> str:
        """
        Retorna modelo preferido do usuário

        Args:
            user_id: ID do usuário

        Returns:
            ID do modelo preferido (padrão: gpt-4o-mini)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT preferred_model FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()

            if result and result['preferred_model']:
                return result['preferred_model']
            return 'gpt-4o-mini'  # padrão

        except Exception as e:
            print(f"[DB] Erro ao buscar modelo preferido: {e}")
            return 'gpt-4o-mini'
        finally:
            conn.close()

    # ============= MÉTODOS DE PROJETOS/PASTAS =============

    def create_project(self, user_id: int, name: str) -> Optional[int]:
        """
        Cria um novo projeto/pasta para organizar chats

        Args:
            user_id: ID do usuário
            name: Nome do projeto

        Returns:
            ID do projeto criado ou None em caso de erro
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO projects (user_id, name)
                VALUES (?, ?)
            ''', (user_id, name))

            project_id = cursor.lastrowid
            conn.commit()
            print(f"[DB] Projeto criado: {name} (ID: {project_id})")
            return project_id

        except Exception as e:
            print(f"[DB] Erro ao criar projeto: {e}")
            return None
        finally:
            conn.close()

    def get_user_projects(self, user_id: int) -> List[Dict]:
        """
        Lista todos os projetos do usuário com seus chats

        Args:
            user_id: ID do usuário

        Returns:
            Lista de projetos com campo 'chat_ids' contendo IDs dos chats
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Buscar projetos
            cursor.execute('''
                SELECT * FROM projects
                WHERE user_id = ?
                ORDER BY created_at ASC
            ''', (user_id,))

            projects = [dict(row) for row in cursor.fetchall()]

            # Para cada projeto, buscar IDs dos chats associados
            for project in projects:
                cursor.execute('''
                    SELECT chat_id FROM project_chats
                    WHERE project_id = ?
                    ORDER BY added_at ASC
                ''', (project['id'],))

                project['chat_ids'] = [row['chat_id'] for row in cursor.fetchall()]

            return projects

        except Exception as e:
            print(f"[DB] Erro ao buscar projetos: {e}")
            return []
        finally:
            conn.close()

    def rename_project(self, project_id: int, new_name: str) -> bool:
        """
        Renomeia um projeto

        Args:
            project_id: ID do projeto
            new_name: Novo nome

        Returns:
            True se renomeado com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE projects
                SET name = ?
                WHERE id = ?
            ''', (new_name, project_id))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Erro ao renomear projeto: {e}")
            return False
        finally:
            conn.close()

    def delete_project(self, project_id: int) -> bool:
        """
        Deleta um projeto (e remove todos os chats dele)

        Args:
            project_id: ID do projeto

        Returns:
            True se deletado com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # O ON DELETE CASCADE na tabela project_chats remove automaticamente
            # as associações quando o projeto é deletado
            cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Erro ao deletar projeto: {e}")
            return False
        finally:
            conn.close()

    def toggle_project_collapsed(self, project_id: int) -> bool:
        """
        Alterna estado collapsed/expanded do projeto

        Args:
            project_id: ID do projeto

        Returns:
            True se atualizado com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE projects
                SET collapsed = NOT collapsed
                WHERE id = ?
            ''', (project_id,))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Erro ao alternar collapsed: {e}")
            return False
        finally:
            conn.close()

    def add_chat_to_project(self, project_id: int, chat_id: int) -> bool:
        """
        Adiciona um chat a um projeto

        Args:
            project_id: ID do projeto
            chat_id: ID do chat

        Returns:
            True se adicionado com sucesso (ou já existia)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO project_chats (project_id, chat_id)
                VALUES (?, ?)
            ''', (project_id, chat_id))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Erro ao adicionar chat ao projeto: {e}")
            return False
        finally:
            conn.close()

    def remove_chat_from_project(self, project_id: int, chat_id: int) -> bool:
        """
        Remove um chat de um projeto

        Args:
            project_id: ID do projeto
            chat_id: ID do chat

        Returns:
            True se removido com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                DELETE FROM project_chats
                WHERE project_id = ? AND chat_id = ?
            ''', (project_id, chat_id))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Erro ao remover chat do projeto: {e}")
            return False
        finally:
            conn.close()

    def get_project_chats(self, project_id: int) -> List[int]:
        """
        Retorna lista de IDs dos chats de um projeto

        Args:
            project_id: ID do projeto

        Returns:
            Lista de IDs de chats
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT chat_id FROM project_chats
                WHERE project_id = ?
                ORDER BY added_at ASC
            ''', (project_id,))

            return [row['chat_id'] for row in cursor.fetchall()]

        except Exception as e:
            print(f"[DB] Erro ao buscar chats do projeto: {e}")
            return []
        finally:
            conn.close()

    # ============================================
    # BTC Exchange Rate Cache (para preços dinâmicos)
    # ============================================

    def get_btc_price_usd(self) -> float:
        """
        Retorna preço do BTC em USD do cache.
        Se não houver cache ou estiver desatualizado (>24h), retorna None.

        Returns:
            float: Preço do BTC em USD ou None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS btc_exchange_rate (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    usd_price REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

            cursor.execute('SELECT usd_price, updated_at FROM btc_exchange_rate WHERE id = 1')
            row = cursor.fetchone()

            if not row:
                return None

            # Verificar se não está desatualizado (>24h)
            from datetime import datetime, timedelta
            updated_at = datetime.fromisoformat(row['updated_at'])
            now = datetime.now()

            if now - updated_at > timedelta(hours=24):
                print(f"[DB] Taxa BTC desatualizada ({row['updated_at']}) - precisa atualizar")
                return None

            return row['usd_price']

        except Exception as e:
            print(f"[DB] Erro ao buscar taxa BTC: {e}")
            return None
        finally:
            conn.close()

    def update_btc_price_usd(self, usd_price: float) -> bool:
        """
        Atualiza preço do BTC em USD no cache.

        Args:
            usd_price: Preço do BTC em USD

        Returns:
            bool: True se atualizado com sucesso
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS btc_exchange_rate (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    usd_price REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

            cursor.execute('''
                INSERT OR REPLACE INTO btc_exchange_rate (id, usd_price, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            ''', (usd_price,))

            conn.commit()
            print(f"[DB] Taxa BTC atualizada: ${usd_price:,.2f} USD")
            return True

        except Exception as e:
            print(f"[DB] Erro ao atualizar taxa BTC: {e}")
            return False
        finally:
            conn.close()

    def get_btc_last_update(self) -> str:
        """
        Retorna timestamp da última atualização da taxa BTC.

        Returns:
            str: Timestamp ISO ou None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT updated_at FROM btc_exchange_rate WHERE id = 1')
            row = cursor.fetchone()
            return row['updated_at'] if row else None

        except Exception as e:
            print(f"[DB] Erro ao buscar última atualização BTC: {e}")
            return None
        finally:
            conn.close()


# Instância global
db = Database()
