#!/usr/bin/env python3
"""
Sofia ML System - Machine Learning e Adaptive Intelligence
Sistema de aprendizado contínuo baseado em interações e feedback
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import openai
import numpy as np
from pathlib import Path

# Configurações
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sofia_ml.db")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"  # Modelo de embeddings da OpenAI

client = openai.OpenAI(api_key=OPENAI_API_KEY)


class SofiaMLSystem:
    """Sistema de Machine Learning da Sofia"""

    def __init__(self):
        self.db_path = DB_PATH
        self._init_database()

    def _init_database(self):
        """Inicializa banco de dados de ML"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela de conversas com embeddings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                embedding BLOB,
                context_tags TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                feedback_score REAL DEFAULT 0.0
            )
        """)

        # Tabela de preferências do usuário
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                learned_from TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, preference_key)
            )
        """)

        # Tabela de padrões aprendidos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                effectiveness_score REAL DEFAULT 0.5
            )
        """)

        # Tabela de feedback explícito
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS explicit_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                user_id INTEGER,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversation_embeddings(id)
            )
        """)

        conn.commit()
        conn.close()

        print("[ML] 🧠 Sistema de ML inicializado")

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Gera embedding usando OpenAI"""
        try:
            response = client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL
            )
            embedding = np.array(response.data[0].embedding)
            return embedding
        except Exception as e:
            print(f"[ML] ❌ Erro ao gerar embedding: {e}")
            return None

    def store_conversation(self, user_id: int, message: str, response: str, context_tags: List[str] = None):
        """Armazena conversa com embedding para aprendizado futuro"""
        try:
            # Combinar mensagem e resposta para embedding
            combined_text = f"User: {message}\nSofia: {response}"
            embedding = self.get_embedding(combined_text)

            if embedding is None:
                return False

            # Serializar embedding como bytes
            embedding_bytes = embedding.tobytes()
            tags_json = json.dumps(context_tags) if context_tags else "[]"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversation_embeddings
                (user_id, message, response, embedding, context_tags)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, message, response, embedding_bytes, tags_json))

            conn.commit()
            conn.close()

            print(f"[ML] 💾 Conversa armazenada com embedding (user_id: {user_id})")
            return True

        except Exception as e:
            print(f"[ML] ❌ Erro ao armazenar conversa: {e}")
            return False

    def find_similar_conversations(self, query: str, user_id: Optional[int] = None, limit: int = 5) -> List[Dict]:
        """Busca conversas similares usando embeddings (RAG)"""
        try:
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                return []

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Buscar todas as conversas (filtrar por user_id se fornecido)
            if user_id:
                cursor.execute("""
                    SELECT id, message, response, embedding, feedback_score, context_tags
                    FROM conversation_embeddings
                    WHERE user_id = ?
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT id, message, response, embedding, feedback_score, context_tags
                    FROM conversation_embeddings
                """)

            results = []
            for row in cursor.fetchall():
                conv_id, message, response, embedding_bytes, feedback_score, context_tags = row

                # Converter bytes de volta para numpy array
                stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float64)

                # Calcular similaridade de cosseno
                similarity = np.dot(query_embedding, stored_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
                )

                results.append({
                    'id': conv_id,
                    'message': message,
                    'response': response,
                    'similarity': float(similarity),
                    'feedback_score': feedback_score,
                    'context_tags': json.loads(context_tags) if context_tags else []
                })

            conn.close()

            # Ordenar por similaridade e retornar top N
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:limit]

        except Exception as e:
            print(f"[ML] ❌ Erro ao buscar conversas similares: {e}")
            return []

    def learn_user_preference(self, user_id: int, key: str, value: str, confidence: float = 1.0, source: str = "explicit"):
        """Aprende preferência do usuário"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences
                (user_id, preference_key, preference_value, confidence, learned_from, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, key, value, confidence, source, datetime.now()))

            conn.commit()
            conn.close()

            print(f"[ML] 🎓 Preferência aprendida: {key} = {value} (confidence: {confidence})")
            return True

        except Exception as e:
            print(f"[ML] ❌ Erro ao aprender preferência: {e}")
            return False

    def get_user_preferences(self, user_id: int) -> Dict[str, str]:
        """Retorna preferências do usuário"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT preference_key, preference_value, confidence
                FROM user_preferences
                WHERE user_id = ?
                ORDER BY confidence DESC
            """, (user_id,))

            preferences = {}
            for key, value, confidence in cursor.fetchall():
                preferences[key] = {
                    'value': value,
                    'confidence': confidence
                }

            conn.close()
            return preferences

        except Exception as e:
            print(f"[ML] ❌ Erro ao buscar preferências: {e}")
            return {}

    def record_feedback(self, conversation_id: int, user_id: int, rating: int, feedback_text: str = ""):
        """Registra feedback explícito do usuário"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Registrar feedback
            cursor.execute("""
                INSERT INTO explicit_feedback
                (conversation_id, user_id, rating, feedback_text)
                VALUES (?, ?, ?, ?)
            """, (conversation_id, user_id, rating, feedback_text))

            # Atualizar score na conversa
            cursor.execute("""
                UPDATE conversation_embeddings
                SET feedback_score = ?
                WHERE id = ?
            """, (rating / 5.0, conversation_id))

            conn.commit()
            conn.close()

            print(f"[ML] ⭐ Feedback registrado: {rating}/5 para conversa {conversation_id}")
            return True

        except Exception as e:
            print(f"[ML] ❌ Erro ao registrar feedback: {e}")
            return False

    def enhance_context_with_memory(self, user_id: int, current_message: str, max_memories: int = 3) -> str:
        """Enriquece contexto com memórias relevantes (RAG)"""
        try:
            similar_convs = self.find_similar_conversations(current_message, user_id, limit=max_memories)

            if not similar_convs:
                return ""

            # Filtrar apenas conversas com alta similaridade (>0.7)
            relevant_convs = [c for c in similar_convs if c['similarity'] > 0.7]

            if not relevant_convs:
                return ""

            # Construir contexto adicional
            context_parts = ["MEMÓRIAS RELEVANTES DE CONVERSAS ANTERIORES:"]
            for i, conv in enumerate(relevant_convs, 1):
                context_parts.append(f"\n[Memória {i} - Similaridade: {conv['similarity']:.2f}]")
                context_parts.append(f"Usuário: {conv['message']}")
                context_parts.append(f"Sofia: {conv['response']}")

            return "\n".join(context_parts)

        except Exception as e:
            print(f"[ML] ❌ Erro ao enriquecer contexto: {e}")
            return ""

    def get_learning_stats(self) -> Dict:
        """Retorna estatísticas de aprendizado"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM conversation_embeddings")
            total_conversations = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM user_preferences")
            total_preferences = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM explicit_feedback")
            total_feedback = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(rating) FROM explicit_feedback")
            avg_rating = cursor.fetchone()[0] or 0.0

            conn.close()

            return {
                'total_conversations': total_conversations,
                'total_preferences': total_preferences,
                'total_feedback': total_feedback,
                'average_rating': round(avg_rating, 2)
            }

        except Exception as e:
            print(f"[ML] ❌ Erro ao obter estatísticas: {e}")
            return {}


# Instância global
ml_system = SofiaMLSystem()


if __name__ == "__main__":
    # Teste do sistema
    print("🧠 Sofia ML System - Test Mode")

    # Teste de embedding
    test_text = "Como configurar um servidor Lightning Network?"
    embedding = ml_system.get_embedding(test_text)
    if embedding is not None:
        print(f"✅ Embedding gerado com {len(embedding)} dimensões")

    # Teste de armazenamento
    success = ml_system.store_conversation(
        user_id=1,
        message="Como instalar Bitcoin Core?",
        response="Para instalar o Bitcoin Core, você pode usar: sudo apt install bitcoind",
        context_tags=["bitcoin", "instalação", "linux"]
    )
    print(f"{'✅' if success else '❌'} Teste de armazenamento")

    # Teste de busca
    similar = ml_system.find_similar_conversations("instalar bitcoin", user_id=1, limit=3)
    print(f"✅ Encontradas {len(similar)} conversas similares")

    # Estatísticas
    stats = ml_system.get_learning_stats()
    print(f"📊 Estatísticas: {stats}")
