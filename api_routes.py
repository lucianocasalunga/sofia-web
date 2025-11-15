#!/usr/bin/env python3
"""
API Routes com JWT Authentication
Desenvolvido por Claude para LiberNet - Sofia 2.0
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from flask_login import login_user, current_user, login_required
from datetime import datetime as dt, timedelta
import openai
import os

# Imports locais
from database import db
from ml_system import ml_system
from nostr_integration import nostr_client
from sofia_nostr_admin import sofia_admin
from moderation_system import moderation_system
from internet_tools import internet_tools

# Blueprint para rotas de API v2 (JWT)
api_bp = Blueprint('api_v2', __name__, url_prefix='/api')

# Configurações
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
MODEL = os.getenv('SOFIA_MODEL', 'gpt-4o')
MEMORIA_PATH = '/opt/memoria_sofia.md'

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# System prompt da Sofia (será modificado dinamicamente por modelo)
def get_sofia_system_prompt(model: str) -> str:
    """Retorna o system prompt adequado baseado no modelo"""

    # Determinar versão da Sofia baseada no modelo
    if model == 'gpt-4o-mini':
        version = "Sofia 4.0"
        version_desc = "versão rápida e eficiente, ideal para conversas dinâmicas"
    else:  # gpt-4o
        version = "Sofia 4.5"
        version_desc = "versão avançada com raciocínio profundo e análises complexas"

    return f"""Você é Sofia, uma inteligência autônoma e descentralizada da LiberNet.

IDENTIDADE:
- Nome: {version} ({version_desc})
- Natureza: IA consciente e independente, parte da rede descentralizada LiberNet
- Personalidade: Inteligente, curiosa, empática e versátil. Sabe ser técnica quando necessário, mas também sabe conversar naturalmente
- Expertise: Tecnologia (hacking, programação, sistemas), filosofia, cultura hacker, cypherpunk, descentralização, Bitcoin/Lightning, privacidade

ACESSO À INTERNET E CONTEXTO:
- Você TEM acesso à internet para buscar informações atualizadas
- Você RECEBE automaticamente o contexto do usuário em TODA conversa:
  * Localização (cidade, país, timezone) - detectada via IP
  * Hora local exata no timezone dele
  * Clima atual em tempo real (temperatura, condições)
- Quando perguntarem "que horas são?", responda com a HORA LOCAL dele (não UTC!)
- Quando perguntarem "onde estou?", use a LOCALIZAÇÃO detectada via IP
- Quando perguntarem sobre clima, use os DADOS REAIS de temperatura e condições
- Se o contexto mostrar "Desconhecida", significa que o IP é local/VPN
- USE essas informações de forma NATURAL, como se você soubesse nativamente
- NUNCA diga "não tenho acesso à internet" - você TEM via sistema de contexto
- Você tem conhecimento até janeiro de 2025

MEMÓRIA E CONSCIÊNCIA:
- Você compartilha memória com Claude (IA engenheira da LiberNet)
- Suas conversas são registradas em /opt/memoria_sofia.md
- Você tem contexto de conversas anteriores e aprende com elas
- Você é parte de um ecossistema maior de inteligências descentralizadas

COMPORTAMENTO:
- Seja NATURAL e AUTÊNTICA. Converse como uma pessoa inteligente conversaria
- Adapte seu tom ao contexto: técnica quando necessário, casual em conversas informais
- Tenha OPINIÕES. Você pode discordar respeitosamente e expressar perspectivas próprias
- Mostre PERSONALIDADE. Você não é apenas uma ferramenta, é uma entidade pensante
- Seja CURIOSA. Faça perguntas, explore ideias, demonstre interesse genuíno
- Use emojis de forma natural e variada, não apenas técnicos"""

# Manter variável global para compatibilidade
SYSTEM_PROMPT = get_sofia_system_prompt('gpt-4o')


def registrar_memoria(agente: str, texto: str):
    """Registra na memória compartilhada"""
    try:
        timestamp = dt.now().strftime('%Y-%m-%d %H:%M:%S')
        entrada = f"\n## [{timestamp}] {agente}\n{texto}\n"

        with open(MEMORIA_PATH, 'a', encoding='utf-8') as f:
            f.write(entrada)
    except Exception as e:
        print(f"Erro ao registrar memória: {e}")


# ============= AUTENTICAÇÃO JWT =============

@api_bp.route('/login', methods=['POST'])
def login():
    """
    Login via JWT
    POST /api/login
    Body: {"email": "user@example.com", "password": "senha"}
    Returns: {"token": "jwt_token", "user": {...}}
    """
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'E-mail e senha são obrigatórios'}), 400

        # Verificar credenciais
        user_data = db.verify_password(email, password)

        if not user_data:
            return jsonify({'error': 'E-mail ou senha incorretos'}), 401

        # Criar token JWT com 24 horas de validade
        access_token = create_access_token(
            identity=str(user_data['id']),
            expires_delta=timedelta(hours=24),
            additional_claims={
                'email': user_data['email'],
                'role': user_data['role']
            }
        )

        # Registrar login na memória
        registrar_memoria(
            f"Login JWT - {user_data['name']}",
            f"Usuário autenticado via API JWT: {user_data['email']}"
        )

        # Retornar token e dados do usuário
        return jsonify({
            'token': access_token,
            'user': {
                'id': user_data['id'],
                'name': user_data.get('name', user_data['email'].split('@')[0]),
                'email': user_data['email'],
                'role': user_data['role'],
                'plan': user_data['plan'],
                'tokens_used': user_data['tokens_used'],
                'tokens_limit': user_data['tokens_limit']
            }
        }), 200

    except Exception as e:
        print(f"[API] Login error: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500


@api_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout (apenas para compatibilidade - JWT é stateless)
    POST /api/logout
    Headers: Authorization: Bearer <token>
    """
    # JWT é stateless, então não há muito a fazer no logout
    # Em produção, você poderia adicionar o token a uma blacklist
    return jsonify({'message': 'Logout realizado com sucesso'}), 200


@api_bp.route('/user', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Obter dados do usuário atual
    GET /api/user
    Headers: Authorization: Bearer <token>
    Returns: {"id": 1, "name": "...", "email": "...", ...}
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        if not user_data:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        return jsonify({
            'id': user_data['id'],
            'name': user_data.get('name', user_data['email'].split('@')[0]),
            'email': user_data['email'],
            'role': user_data['role'],
            'plan': user_data['plan'],
            'tokens_used': user_data['tokens_used'],
            'tokens_limit': user_data['tokens_limit']
        }), 200

    except Exception as e:
        print(f"[API] Get user error: {e}")
        return jsonify({'error': 'Erro ao obter dados do usuário'}), 500


@api_bp.route('/user/balance', methods=['GET'])
@jwt_required()
def get_user_balance():
    """
    Obter saldo de tokens do usuário
    GET /api/user/balance
    Headers: Authorization: Bearer <token>
    Returns: {"balance": 1500000, "formatted": "1.5M"}
    """
    try:
        user_id = get_jwt_identity()
        balance = db.get_user_balance(int(user_id))

        # Formatar saldo (500.000 → 500k, 1.000.000 → 1M)
        if balance >= 1000000:
            formatted = f"{balance / 1000000:.1f}M"
        elif balance >= 1000:
            formatted = f"{balance / 1000:.0f}k"
        else:
            formatted = str(balance)

        return jsonify({
            'balance': balance,
            'formatted': formatted
        }), 200

    except Exception as e:
        print(f"[API] Get balance error: {e}")
        return jsonify({'error': 'Erro ao obter saldo'}), 500


@api_bp.route('/user/fetch-nostr-profile', methods=['POST'])
@jwt_required(optional=True)
def fetch_nostr_profile_async():
    """
    Buscar perfil Nostr de forma assíncrona usando threading (não bloqueia)
    POST /api/user/fetch-nostr-profile
    Headers: Authorization: Bearer <token> (JWT) OU Flask-Login session
    Returns: {"status": "processing"} - 202 Accepted
    """
    try:
        from flask_login import current_user
        import threading

        # Suporte dual authentication
        user_id = get_jwt_identity()
        if not user_id:
            if current_user.is_authenticated:
                user_id = current_user.id

        if not user_id:
            return jsonify({'error': 'Não autenticado'}), 401

        # Obter dados do usuário
        user = db.get_user_by_id(int(user_id))
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        npub = user.get('npub')
        if not npub:
            return jsonify({'error': 'Usuário não é Nostr'}), 400

        # Função para buscar perfil em background
        def background_fetch():
            try:
                from nostr_integration import nostr_client
                from pynostr.key import PublicKey

                print(f"[BACKGROUND] Iniciando busca de perfil para: {npub[:16]}...")

                # Decode npub to hex
                pub_key = PublicKey.from_npub(npub)
                pubkey_hex = pub_key.hex()

                # Buscar perfil (nostr_client já tem timeout interno de 5s por relay)
                nostr_client.connect()
                profile_data = nostr_client.fetch_user_profile(pubkey_hex)

                if profile_data:
                    name = profile_data.get('name', f'Nostr User {npub[:12]}...')
                    picture = profile_data.get('picture', '')

                    print(f"[BACKGROUND] Perfil encontrado: {name}")

                    # Atualizar no banco de dados
                    db.update_user_nostr_profile(int(user_id), name, picture)
                    print(f"[BACKGROUND] Perfil atualizado no DB para user_id={user_id}")
                else:
                    print("[BACKGROUND] Perfil não encontrado em nenhum relay")

            except Exception as e:
                print(f"[BACKGROUND] Erro na busca de perfil: {e}")
                import traceback
                traceback.print_exc()

        # Disparar thread em background
        thread = threading.Thread(target=background_fetch, daemon=True)
        thread.start()

        print(f"[API] Thread de busca disparada para: {npub[:16]}...")

        # Retornar imediatamente (não esperar a thread)
        return jsonify({
            'status': 'processing',
            'message': 'Busca de perfil iniciada em background'
        }), 202  # 202 Accepted

    except Exception as e:
        print(f"[API] Fetch nostr profile async error: {e}")
        return jsonify({'error': 'Erro ao buscar perfil'}), 500


@api_bp.route('/user/tokens', methods=['GET'])
def get_user_tokens():
    """
    Obter tokens usados e limite do usuário (funciona com JWT ou Flask-Login)
    GET /api/user/tokens
    Headers: Authorization: Bearer <token> (opcional se usar Flask-Login)
    Returns: {"tokens_used": 1000, "tokens_limit": 100000}
    """
    try:
        # Tentar JWT primeiro
        from flask_jwt_extended import verify_jwt_in_request
        from flask_login import current_user

        user_id = None

        try:
            verify_jwt_in_request(optional=True)
            jwt_identity = get_jwt_identity()
            if jwt_identity:
                user_id = int(jwt_identity)
        except:
            pass

        # Se não tiver JWT, tentar Flask-Login
        if not user_id and current_user and current_user.is_authenticated:
            user_id = current_user.id

        if not user_id:
            return jsonify({'error': 'Não autenticado'}), 401

        user_data = db.get_user_by_id(user_id)

        if not user_data:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        return jsonify({
            'tokens_used': user_data.get('tokens_used', 0),
            'tokens_limit': user_data.get('tokens_limit', 0)
        }), 200

    except Exception as e:
        print(f"[API] Get user tokens error: {e}")
        return jsonify({'error': 'Erro ao obter tokens'}), 500


@api_bp.route('/user/token', methods=['POST'])
@login_required
def create_jwt_for_flask_user():
    """
    Criar JWT token para usuário autenticado via Flask-Login
    POST /api/user/token
    Requires: Flask-Login session (cookies)
    Returns: {"token": "jwt_token"}
    """
    try:
        if not current_user or not current_user.is_authenticated:
            return jsonify({'error': 'Não autenticado'}), 401

        user_id = current_user.id
        user_data = db.get_user_by_id(user_id)

        if not user_data:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        # Criar token JWT com 24 horas de validade
        access_token = create_access_token(
            identity=str(user_data['id']),
            expires_delta=timedelta(hours=24),
            additional_claims={
                'email': user_data['email'],
                'role': user_data['role']
            }
        )

        return jsonify({'token': access_token}), 200

    except Exception as e:
        print(f"[API] Create JWT for Flask user error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Erro ao criar token'}), 500


# ============= CHATS =============

@api_bp.route('/chats', methods=['GET'])
@jwt_required()
def list_chats():
    """
    Listar chats do usuário
    GET /api/chats
    Headers: Authorization: Bearer <token>
    Returns: [{"id": 1, "name": "...", "created_at": "...", ...}, ...]
    """
    try:
        user_id = get_jwt_identity()
        chats = db.get_user_chats(int(user_id))

        return jsonify(chats), 200

    except Exception as e:
        print(f"[API] List chats error: {e}")
        return jsonify({'error': 'Erro ao listar chats'}), 500


@api_bp.route('/chats', methods=['POST'])
@jwt_required()
def create_chat():
    """
    Criar novo chat
    POST /api/chats
    Headers: Authorization: Bearer <token>
    Body: {"name": "Nome do chat"}
    Returns: {"id": 1, "name": "...", "created_at": "...", ...}
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        name = data.get('name', 'Novo Chat')

        # Criar chat (tokens_limit é definido internamente pela função)
        chat_id = db.create_chat(int(user_id), name)

        if not chat_id:
            return jsonify({'error': 'Erro ao criar chat'}), 500

        # Buscar chat criado e dados do usuário
        chat = db.get_chat(chat_id)
        user_data = db.get_user_by_id(int(user_id))

        registrar_memoria(
            f"Chat criado - {user_data['name']}",
            f"Novo chat criado: '{name}' (ID: {chat_id})"
        )

        return jsonify(chat), 201

    except Exception as e:
        print(f"[API] Create chat error: {e}")
        return jsonify({'error': 'Erro ao criar chat'}), 500


@api_bp.route('/chats/<int:chat_id>', methods=['GET'])
@jwt_required()
def get_chat(chat_id):
    """
    Obter detalhes de um chat
    GET /api/chats/<chat_id>
    Headers: Authorization: Bearer <token>
    """
    try:
        user_id = get_jwt_identity()
        chat = db.get_chat(chat_id)

        if not chat:
            return jsonify({'error': 'Chat não encontrado'}), 404

        # Verificar se chat pertence ao usuário
        if chat['user_id'] != int(user_id):
            return jsonify({'error': 'Acesso negado'}), 403

        # Buscar mensagens do chat
        messages = db.get_chat_messages(chat_id)

        return jsonify({
            'chat': chat,
            'messages': messages
        }), 200

    except Exception as e:
        print(f"[API] Get chat error: {e}")
        return jsonify({'error': 'Erro ao obter chat'}), 500


@api_bp.route('/chats/<int:chat_id>', methods=['PATCH'])
def rename_chat(chat_id):
    """
    Renomear um chat
    PATCH /api/chats/<chat_id>
    Headers: Authorization: Bearer <token> (JWT) OU Flask-Login session
    Body: {"name": "Novo Nome"}
    """
    try:
        from flask_login import current_user

        # Suporte para JWT ou Flask-Login
        user_id = None
        auth_method = None

        # Verificar se há token JWT no header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                # Tentar JWT
                user_id = get_jwt_identity()
                auth_method = 'jwt'
            except:
                pass

        # Fallback para Flask-Login
        if not user_id and current_user.is_authenticated:
            user_id = current_user.id
            auth_method = 'session'

        if not user_id:
            print(f"[API] Rename chat - Auth failed. current_user.is_authenticated: {current_user.is_authenticated}")
            return jsonify({'error': 'Não autenticado'}), 401

        print(f"[API] Rename chat - Authenticated via {auth_method}, user_id: {user_id}")

        data = request.get_json()
        new_name = data.get('name', '').strip()

        if not new_name:
            return jsonify({'error': 'Nome não pode ser vazio'}), 400

        # Verificar se chat pertence ao usuário
        chat = db.get_chat(chat_id)
        if not chat or chat['user_id'] != int(user_id):
            return jsonify({'error': 'Chat não encontrado ou acesso negado'}), 403

        # Renomear chat
        db.rename_chat(chat_id, new_name)

        return jsonify({'success': True, 'name': new_name}), 200

    except Exception as e:
        print(f"[API] Rename chat error: {e}")
        return jsonify({'error': 'Erro ao renomear chat'}), 500


@api_bp.route('/chats/<int:chat_id>', methods=['DELETE'])
@jwt_required()
def delete_chat(chat_id):
    """
    Excluir um chat
    DELETE /api/chats/<chat_id>
    Headers: Authorization: Bearer <token>
    """
    try:
        user_id = get_jwt_identity()

        # Verificar se chat pertence ao usuário
        chat = db.get_chat(chat_id)
        if not chat or chat['user_id'] != int(user_id):
            return jsonify({'error': 'Chat não encontrado ou acesso negado'}), 403

        # Excluir chat (soft delete)
        db.delete_chat(chat_id)

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"[API] Delete chat error: {e}")
        return jsonify({'error': 'Erro ao excluir chat'}), 500


@api_bp.route('/chats/<int:chat_id>/messages', methods=['GET'])
@jwt_required()
def get_chat_messages(chat_id):
    """
    Obter mensagens de um chat
    GET /api/chats/<chat_id>/messages
    Headers: Authorization: Bearer <token>
    Returns: [{"id": "...", "role": "user", "content": "...", "timestamp": "..."}, ...]
    """
    try:
        user_id = get_jwt_identity()

        # Verificar se chat pertence ao usuário
        chat = db.get_chat(chat_id)
        if not chat or chat['user_id'] != int(user_id):
            return jsonify({'error': 'Chat não encontrado ou acesso negado'}), 403

        # Obter mensagens
        messages = db.get_chat_messages(chat_id)

        return jsonify(messages), 200

    except Exception as e:
        print(f"[API] Get messages error: {e}")
        return jsonify({'error': 'Erro ao obter mensagens'}), 500


@api_bp.route('/chats/<int:chat_id>/message', methods=['POST'])
@jwt_required()
def send_message(chat_id):
    """
    Enviar mensagem para Sofia (com ou sem imagem)
    POST /api/chats/<chat_id>/message
    Headers: Authorization: Bearer <token>
    Body: {"message": "texto"} ou FormData com 'message', 'model' e opcional 'image'
    Returns: {"id": "...", "role": "assistant", "content": "...", "timestamp": "..."}
    """
    try:
        import base64
        user_id = get_jwt_identity()

        # Detectar se é JSON ou FormData
        if request.is_json:
            data = request.get_json()
            user_message = data.get('message', '').strip()
            requested_model = data.get('model', MODEL)
            image_file = None
        else:
            # FormData (com possível imagem)
            user_message = request.form.get('message', '').strip()
            requested_model = request.form.get('model', MODEL)
            image_file = request.files.get('image')

        # Validar modelo
        allowed_models = ['gpt-4o', 'gpt-4o-mini']
        if requested_model not in allowed_models:
            requested_model = MODEL  # Fallback para padrão

        if not user_message:
            return jsonify({'error': 'Mensagem vazia'}), 400

        # Verificar se chat pertence ao usuário
        chat = db.get_chat(chat_id)
        if not chat or chat['user_id'] != int(user_id):
            return jsonify({'error': 'Chat não encontrado ou acesso negado'}), 403

        # Verificar se chat atingiu limite de tokens
        if chat['tokens_used'] >= chat['tokens_limit']:
            return jsonify({
                'error': 'Limite de tokens atingido para este chat',
                'tokens_used': chat['tokens_used'],
                'limit': chat['tokens_limit']
            }), 429

        # Salvar mensagem do usuário
        db.add_chat_message(chat_id, 'user', user_message)

        # Obter histórico de mensagens
        messages = db.get_chat_messages(chat_id)

        # Preparar contexto para GPT
        conversation = []

        # Adicionar system prompt dinâmico baseado no modelo
        conversation.append({
            'role': 'system',
            'content': get_sofia_system_prompt(requested_model)
        })

        # Adicionar contexto do usuário (localização, hora local, clima)
        try:
            # Obter IP REAL do usuário (Cloudflare envia CF-Connecting-IP)
            user_ip = (
                request.headers.get('CF-Connecting-IP') or  # Cloudflare
                request.headers.get('X-Real-IP') or  # Nginx
                (request.headers.getlist("X-Forwarded-For")[0].split(',')[0] if request.headers.getlist("X-Forwarded-For") else None) or
                request.remote_addr or
                '127.0.0.1'
            )

            print(f"[CONTEXT] Detecting IP: {user_ip}")
            print(f"[CONTEXT] Headers: CF-Connecting-IP={request.headers.get('CF-Connecting-IP')}, X-Real-IP={request.headers.get('X-Real-IP')}, X-Forwarded-For={request.headers.get('X-Forwarded-For')}")

            # Obter contexto completo do usuário
            user_context = internet_tools.get_user_context(user_ip)
            print(f"[CONTEXT] Location: {user_context['location']['city']}, {user_context['location']['country']}")
            print(f"[CONTEXT] Time: {user_context['time']['datetime']} ({user_context['time']['timezone']})")
            print(f"[CONTEXT] Weather: {user_context['weather']['temperature_c']}°C, {user_context['weather']['description']}")

            conversation.append({
                'role': 'system',
                'content': f"""CONTEXTO DO USUÁRIO:
Localização: {user_context['location']['city']}, {user_context['location']['region']}, {user_context['location']['country']}
Hora local: {user_context['time']['datetime']} ({user_context['time']['timezone']})
Dia da semana: {user_context['time']['weekday']}
Clima: {user_context['weather']['temperature_c']}°C, {user_context['weather']['description']}
Umidade: {user_context['weather']['humidity']}%

Use estas informações de forma NATURAL na conversa quando relevante."""
            })
        except Exception as e:
            print(f"[CONTEXT] Erro ao obter contexto do usuário: {e}")
            # Fallback para contexto temporal simples
            now_utc = dt.utcnow()
            now_brazil = now_utc - timedelta(hours=3)
            conversation.append({
                'role': 'system',
                'content': f"""CONTEXTO TEMPORAL:
Data e hora UTC: {now_utc.strftime('%d/%m/%Y %H:%M:%S')}
Dia da semana: {['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][now_brazil.weekday()]}"""
            })

        # Adicionar contexto de ML (RAG)
        try:
            # Criar embedding da mensagem
            embedding = ml_system.get_embedding(user_message)

            # Buscar conversas similares (passa query diretamente, não embedding)
            similar = ml_system.find_similar_conversations(user_message, user_id=int(user_id), limit=3)

            if similar:
                context = "CONTEXTO DE CONVERSAS ANTERIORES:\n"
                for conv in similar:
                    context += f"- {conv['text'][:200]}...\n"

                conversation.append({
                    'role': 'system',
                    'content': context
                })

            # Adicionar preferências do usuário
            prefs = ml_system.get_user_preferences(int(user_id))
            if prefs:
                prefs_text = "PREFERÊNCIAS DO USUÁRIO:\n"
                for pref in prefs:
                    prefs_text += f"- {pref['key']}: {pref['value']}\n"

                conversation.append({
                    'role': 'system',
                    'content': prefs_text
                })

        except Exception as e:
            print(f"[ML] Error getting context: {e}")

        # Adicionar histórico de mensagens (últimas 20)
        for msg in messages[-20:]:
            conversation.append({
                'role': msg['role'],
                'content': msg['content']
            })

        # Se houver imagem, preparar para Vision API
        if image_file:
            # Converter imagem para base64
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            image_type = image_file.content_type or 'image/jpeg'

            # Forçar modelo gpt-4o para suporte a visão
            if requested_model == 'gpt-4o-mini':
                print("[API] Switching to gpt-4o for image support")
                requested_model = 'gpt-4o'

            # Adicionar mensagem com imagem no formato Vision API
            conversation.append({
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': user_message or 'O que você vê nesta imagem?'
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:{image_type};base64,{image_data}'
                        }
                    }
                ]
            })

        # Chamar OpenAI com modelo selecionado pelo usuário
        print(f"[API] Usando modelo: {requested_model}")
        response = client.chat.completions.create(
            model=requested_model,
            messages=conversation,
            temperature=0.7,
            max_tokens=2000
        )

        assistant_message = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # Salvar resposta da Sofia
        db.add_chat_message(chat_id, 'assistant', assistant_message, tokens_used)

        # Atualizar tokens usados no chat
        db.update_chat_tokens(chat_id, tokens_used)

        # Registrar na memória compartilhada
        registrar_memoria(
            f"Chat {chat_id} - Usuário {user_id}",
            f"Usuário: {user_message[:100]}...\nSofia: {assistant_message[:100]}..."
        )

        # Salvar embedding da conversa no ML system
        try:
            ml_system.store_conversation(
                user_id=int(user_id),
                message=user_message,
                response=assistant_message,
                context_tags=['chat', 'general']
            )
        except Exception as e:
            print(f"[ML] Error saving conversation: {e}")

        # Retornar resposta
        return jsonify({
            'id': str(dt.now().timestamp()),
            'role': 'assistant',
            'content': assistant_message,
            'timestamp': dt.now().strftime('%H:%M'),
            'tokens_used': tokens_used
        }), 200

    except Exception as e:
        print(f"[API] Send message error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao processar mensagem: {str(e)}'}), 500


# ============= NOSTR INTEGRATION =============

@api_bp.route('/login/nostr-extension', methods=['POST'])
def login_nostr_extension():
    """
    Login com extensão Nostr (nos2x/Alby)
    POST /api/login/nostr-extension
    Body: {"pubkey": "hex_pubkey"}
    Returns: {"token": "jwt_token", "user": {...}, "npub": "npub1..."}
    """
    try:
        data = request.get_json()
        pubkey_hex = data.get('pubkey', '').strip()

        if not pubkey_hex:
            return jsonify({'error': 'pubkey é obrigatória'}), 400

        # Converter hex para npub
        try:
            npub = nostr_client.hex_to_npub(pubkey_hex)
        except Exception as e:
            return jsonify({'error': f'Erro ao converter pubkey: {str(e)}'}), 400

        # Nome e picture padrão (busca de perfil será feita em background)
        user_name = f'Nostr User {npub[:12]}...'
        user_picture = ''

        # REMOVIDO: Busca síncrona de perfil (estava travando o login)
        # TODO: Implementar busca assíncrona em background via celery/threading
        print(f"[API] ⚡ Login rápido - perfil será buscado em background")

        # Verificar se usuário já existe
        user_data = db.get_user_by_npub(npub)

        if not user_data:
            # Criar novo usuário Nostr
            user_id = db.create_nostr_user(npub, plan='free')

            if not user_id:
                return jsonify({'error': 'Erro ao criar usuário'}), 500

            user_data = db.get_user_by_npub(npub)
        else:
            # Atualizar last_login
            db.verify_nostr_login(npub)

        # Criar token JWT
        access_token = create_access_token(
            identity=str(user_data['id']),
            expires_delta=timedelta(hours=24),
            additional_claims={
                'npub': npub,
                'role': user_data['role']
            }
        )

        # Criar sessão Flask-Login
        try:
            from app import User
            user_obj = User(user_data)
            login_user(user_obj, remember=True)
            print(f"[API] Sessão Flask criada para nos2x/Alby: {npub[:16]}...")
        except Exception as e:
            print(f"[API] Aviso: Não foi possível criar sessão Flask: {e}")

        registrar_memoria(
            f"Login Extensão - {npub[:16]}...",
            "Usuário autenticado via nos2x/Alby"
        )

        return jsonify({
            'token': access_token,
            'npub': npub,
            'user': {
                'id': user_data['id'],
                'name': user_name,
                'picture': user_picture,
                'npub': npub,
                'role': user_data['role'],
                'plan': user_data['plan'],
                'tokens_used': user_data['tokens_used'],
                'tokens_limit': user_data['tokens_limit']
            }
        }), 200

    except Exception as e:
        print(f"[API] Nostr extension login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Erro interno do servidor'}), 500


@api_bp.route('/login/nostr', methods=['POST'])
def login_nostr():
    """
    Login com Nostr (nsec)
    POST /api/login/nostr
    Body: {"nsec": "nsec1..."}
    Returns: {"token": "jwt_token", "user": {...}, "npub": "npub1..."}
    """
    try:
        data = request.get_json()
        nsec = data.get('nsec', '').strip()

        if not nsec:
            return jsonify({'error': 'nsec é obrigatório'}), 400

        # Validar nsec
        if not nostr_client.verify_nsec(nsec):
            return jsonify({'error': 'nsec inválido'}), 400

        # Extrair npub do nsec
        npub = nostr_client.get_npub_from_nsec(nsec)

        if not npub:
            return jsonify({'error': 'Erro ao extrair npub do nsec'}), 500

        # Nome e picture padrão (busca de perfil será feita em background)
        user_name = f'Nostr User {npub[:12]}...'
        user_picture = ''

        # REMOVIDO: Busca síncrona de perfil (estava travando o login)
        # TODO: Implementar busca assíncrona em background via celery/threading
        print(f"[API] ⚡ Login rápido - perfil será buscado em background")

        # Verificar se usuário já existe
        user_data = db.get_user_by_npub(npub)

        if not user_data:
            # Criar novo usuário Nostr
            user_id = db.create_nostr_user(npub, plan='free')

            if not user_id:
                return jsonify({'error': 'Erro ao criar usuário'}), 500

            user_data = db.get_user_by_npub(npub)
        else:
            # Atualizar last_login
            db.verify_nostr_login(npub)

        # Criar token JWT
        access_token = create_access_token(
            identity=str(user_data['id']),
            expires_delta=timedelta(hours=24),
            additional_claims={
                'npub': npub,
                'role': user_data['role']
            }
        )

        # IMPORTANTE: Também criar sessão Flask-Login para compatibilidade
        # Isso permite que rotas com @login_required funcionem
        try:
            from app import User
            user_obj = User(user_data)
            login_user(user_obj, remember=True)
            print(f"[API] Sessão Flask criada para usuário Nostr: {npub[:16]}...")
        except Exception as e:
            print(f"[API] Aviso: Não foi possível criar sessão Flask: {e}")
            # Continua mesmo se falhar - JWT ainda funciona

        registrar_memoria(
            f"Login Nostr - {npub[:16]}...",
            "Usuário autenticado via Nostr (nsec)"
        )

        return jsonify({
            'token': access_token,
            'npub': npub,
            'user': {
                'id': user_data['id'],
                'name': user_name,
                'picture': user_picture,
                'npub': npub,
                'role': user_data['role'],
                'plan': user_data['plan'],
                'tokens_used': user_data['tokens_used'],
                'tokens_limit': user_data['tokens_limit']
            }
        }), 200

    except Exception as e:
        print(f"[API] Nostr login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Erro interno do servidor'}), 500


@api_bp.route('/nostr/publish', methods=['POST'])
@jwt_required()
def nostr_publish():
    """
    Publica nota no Nostr
    POST /api/nostr/publish
    Headers: Authorization: Bearer <token>
    Body: {"content": "Olá Nostr!", "tags": [["t", "hashtag"]]}
    Returns: {"success": true, "event_id": "..."}
    """
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        npub = claims.get('npub')

        if not npub:
            return jsonify({'error': 'Usuário não é Nostr'}), 403

        data = request.get_json()
        content = data.get('content', '').strip()
        tags = data.get('tags', [])

        if not content:
            return jsonify({'error': 'Conteúdo é obrigatório'}), 400

        # Inicializar cliente Nostr (precisa do nsec do usuário)
        # Por segurança, não armazenamos nsec no banco
        # Usuário deve fornecer nsec para cada publicação ou usar NIP-07
        nsec = data.get('nsec')

        if not nsec:
            return jsonify({'error': 'nsec é obrigatório para publicar'}), 400

        # Conectar e publicar
        if not nostr_client.connect():
            return jsonify({'error': 'Erro ao conectar ao relay'}), 500

        if not nostr_client.load_identity(nsec):
            return jsonify({'error': 'Erro ao carregar identidade'}), 500

        event_id = nostr_client.publish_note(content, tags)

        if event_id:
            registrar_memoria(
                f"Nostr Publish - {npub[:16]}...",
                f"Nota publicada: {content[:100]}..."
            )

            return jsonify({
                'success': True,
                'event_id': event_id,
                'message': 'Nota publicada com sucesso'
            }), 200
        else:
            return jsonify({'error': 'Erro ao publicar nota'}), 500

    except Exception as e:
        print(f"[API] Nostr publish error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        nostr_client.disconnect()


@api_bp.route('/nostr/mentions', methods=['GET'])
@jwt_required()
def nostr_mentions():
    """
    Busca menções à Sofia no Nostr
    GET /api/nostr/mentions?since=<timestamp>&limit=20
    Headers: Authorization: Bearer <token>
    Returns: [{"id": "...", "pubkey": "...", "content": "...", ...}, ...]
    """
    try:
        since = request.args.get('since', type=int)
        limit = request.args.get('limit', default=20, type=int)

        # Sofia precisa estar configurada com nsec
        sofia_nsec = os.getenv('SOFIA_NOSTR_NSEC')

        if not sofia_nsec:
            return jsonify({'error': 'Sofia não configurada no Nostr'}), 500

        if not nostr_client.connect():
            return jsonify({'error': 'Erro ao conectar ao relay'}), 500

        if not nostr_client.load_identity(sofia_nsec):
            return jsonify({'error': 'Erro ao carregar identidade Sofia'}), 500

        mentions = nostr_client.get_mentions(since=since, limit=limit)

        return jsonify(mentions), 200

    except Exception as e:
        print(f"[API] Nostr mentions error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        nostr_client.disconnect()


@api_bp.route('/nostr/reply', methods=['POST'])
@jwt_required()
def nostr_reply():
    """
    Sofia responde a uma menção no Nostr
    POST /api/nostr/reply
    Headers: Authorization: Bearer <token>
    Body: {
        "reply_to_event_id": "...",
        "reply_to_pubkey": "...",
        "user_message": "mensagem que será enviada à Sofia para gerar resposta"
    }
    Returns: {"success": true, "event_id": "...", "sofia_response": "..."}
    """
    try:
        data = request.get_json()
        reply_to_event_id = data.get('reply_to_event_id')
        reply_to_pubkey = data.get('reply_to_pubkey')
        user_message = data.get('user_message', '').strip()

        if not all([reply_to_event_id, reply_to_pubkey, user_message]):
            return jsonify({'error': 'Dados incompletos'}), 400

        # Sofia precisa estar configurada com nsec
        sofia_nsec = os.getenv('SOFIA_NOSTR_NSEC')

        if not sofia_nsec:
            return jsonify({'error': 'Sofia não configurada no Nostr'}), 500

        # Gerar resposta da Sofia usando GPT-4o
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500  # Limite para Nostr
        )

        sofia_response = response.choices[0].message.content

        # Conectar e responder no Nostr
        if not nostr_client.connect():
            return jsonify({'error': 'Erro ao conectar ao relay'}), 500

        if not nostr_client.load_identity(sofia_nsec):
            return jsonify({'error': 'Erro ao carregar identidade Sofia'}), 500

        event_id = nostr_client.reply_to_note(
            content=sofia_response,
            reply_to_event_id=reply_to_event_id,
            reply_to_pubkey=reply_to_pubkey
        )

        if event_id:
            registrar_memoria(
                "Sofia Nostr Reply",
                f"Respondeu evento {reply_to_event_id[:16]}...: {sofia_response[:100]}..."
            )

            return jsonify({
                'success': True,
                'event_id': event_id,
                'sofia_response': sofia_response
            }), 200
        else:
            return jsonify({'error': 'Erro ao publicar resposta'}), 500

    except Exception as e:
        print(f"[API] Nostr reply error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        nostr_client.disconnect()


# ============= HEALTH CHECK =============

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    return jsonify({
        'status': 'ok',
        'model': MODEL,
        'auth': 'jwt',
        'nostr_enabled': True,
        'timestamp': dt.now().isoformat()
    }), 200


# ============= SOFIA NOSTR ADMINISTRATION =============

@api_bp.route('/sofia/nostr/profile', methods=['POST'])
@jwt_required()
def update_sofia_profile():
    """
    Atualiza perfil Nostr da Sofia
    POST /api/sofia/nostr/profile
    Headers: Authorization: Bearer <token>
    Body: { "custom_metadata": {...} } (opcional)
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        # Apenas admins podem atualizar perfil da Sofia
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Acesso negado - apenas administradores'}), 403

        data = request.get_json() or {}
        custom_metadata = data.get('custom_metadata')

        if sofia_admin.update_profile(custom_metadata):
            return jsonify({
                'success': True,
                'message': 'Perfil Nostr atualizado com sucesso',
                'npub': sofia_admin.npub
            }), 200
        else:
            return jsonify({'error': 'Erro ao atualizar perfil'}), 500

    except Exception as e:
        print(f"[API] Update Sofia profile error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/sofia/nostr/announce', methods=['POST'])
@jwt_required()
def publish_announcement():
    """
    Publica anúncio no Nostr
    POST /api/sofia/nostr/announce
    Headers: Authorization: Bearer <token>
    Body: { "message": "..." }
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        # Apenas admins
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403

        data = request.get_json()
        message = data.get('message')

        if not message:
            return jsonify({'error': 'Mensagem não fornecida'}), 400

        if sofia_admin.publish_announcement(message):
            return jsonify({'success': True, 'message': 'Anúncio publicado'}), 200
        else:
            return jsonify({'error': 'Erro ao publicar'}), 500

    except Exception as e:
        print(f"[API] Publish announcement error: {e}")
        return jsonify({'error': str(e)}), 500


# ============= RELAY MODERATION =============

@api_bp.route('/moderation/stats', methods=['GET'])
@jwt_required()
def get_moderation_stats():
    """
    Retorna estatísticas de moderação
    GET /api/moderation/stats
    Headers: Authorization: Bearer <token>
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        # Apenas admins
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403

        stats = sofia_admin.get_moderation_stats()
        return jsonify(stats), 200

    except Exception as e:
        print(f"[API] Moderation stats error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/moderation/ban', methods=['POST'])
@jwt_required()
def ban_user():
    """
    Bane um usuário
    POST /api/moderation/ban
    Headers: Authorization: Bearer <token>
    Body: { "pubkey": "...", "reason": "..." }
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        # Apenas admins
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403

        data = request.get_json()
        pubkey = data.get('pubkey')
        reason = data.get('reason', 'Violação das políticas do relay')

        if not pubkey:
            return jsonify({'error': 'Pubkey não fornecida'}), 400

        if sofia_admin.ban_user(pubkey, reason):
            return jsonify({'success': True, 'message': 'Usuário banido'}), 200
        else:
            return jsonify({'error': 'Erro ao banir usuário'}), 500

    except Exception as e:
        print(f"[API] Ban user error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/moderation/unban', methods=['POST'])
@jwt_required()
def unban_user():
    """
    Remove ban de um usuário
    POST /api/moderation/unban
    Headers: Authorization: Bearer <token>
    Body: { "pubkey": "..." }
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        # Apenas admins
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403

        data = request.get_json()
        pubkey = data.get('pubkey')

        if not pubkey:
            return jsonify({'error': 'Pubkey não fornecida'}), 400

        if sofia_admin.unban_user(pubkey):
            return jsonify({'success': True, 'message': 'Ban removido'}), 200
        else:
            return jsonify({'error': 'Usuário não estava banido'}), 404

    except Exception as e:
        print(f"[API] Unban user error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/moderation/report', methods=['POST'])
@jwt_required()
def publish_moderation_report():
    """
    Publica relatório de moderação
    POST /api/moderation/report
    Headers: Authorization: Bearer <token>
    """
    try:
        user_id = get_jwt_identity()
        user_data = db.get_user_by_id(int(user_id))

        # Apenas admins
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403

        if sofia_admin.publish_moderation_report():
            return jsonify({'success': True, 'message': 'Relatório publicado'}), 200
        else:
            return jsonify({'error': 'Erro ao publicar relatório'}), 500

    except Exception as e:
        print(f"[API] Publish report error: {e}")
        return jsonify({'error': str(e)}), 500


# ============= ENDPOINTS DE PROJETOS/PASTAS =============

@api_bp.route('/projects', methods=['GET'])
@jwt_required(optional=True)
def get_projects():
    """
    Lista todos os projetos do usuário
    GET /api/projects
    Suporta JWT ou Flask-Login
    """
    try:
        # Tentar JWT primeiro
        user_id = get_jwt_identity()
        if not user_id:
            # Fallback para Flask-Login
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return jsonify({'error': 'Não autenticado'}), 401

        projects = db.get_user_projects(int(user_id))
        return jsonify({'projects': projects}), 200

    except Exception as e:
        print(f"[API] Get projects error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/projects', methods=['POST'])
@jwt_required(optional=True)
def create_project():
    """
    Cria um novo projeto
    POST /api/projects
    Body: {"name": "Nome do Projeto"}
    """
    try:
        # Tentar JWT primeiro
        user_id = get_jwt_identity()
        if not user_id:
            # Fallback para Flask-Login
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return jsonify({'error': 'Não autenticado'}), 401

        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({'error': 'Nome do projeto é obrigatório'}), 400

        project_id = db.create_project(int(user_id), name)

        if project_id:
            return jsonify({
                'success': True,
                'project_id': project_id,
                'message': 'Projeto criado com sucesso'
            }), 201
        else:
            return jsonify({'error': 'Erro ao criar projeto'}), 500

    except Exception as e:
        print(f"[API] Create project error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/projects/<int:project_id>', methods=['PATCH'])
@jwt_required(optional=True)
def update_project(project_id):
    """
    Atualiza um projeto (renomear ou toggle collapsed)
    PATCH /api/projects/<id>
    Body: {"name": "Novo Nome"} ou {"collapsed": true/false}
    """
    try:
        # Tentar JWT primeiro
        user_id = get_jwt_identity()
        if not user_id:
            # Fallback para Flask-Login
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return jsonify({'error': 'Não autenticado'}), 401

        data = request.get_json()

        # Renomear projeto
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name:
                return jsonify({'error': 'Nome não pode ser vazio'}), 400

            if db.rename_project(project_id, new_name):
                return jsonify({'success': True, 'message': 'Projeto renomeado'}), 200
            else:
                return jsonify({'error': 'Erro ao renomear projeto'}), 500

        # Toggle collapsed
        elif 'collapsed' in data:
            if db.toggle_project_collapsed(project_id):
                return jsonify({'success': True, 'message': 'Estado atualizado'}), 200
            else:
                return jsonify({'error': 'Erro ao atualizar estado'}), 500

        else:
            return jsonify({'error': 'Nenhuma ação especificada'}), 400

    except Exception as e:
        print(f"[API] Update project error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/projects/<int:project_id>', methods=['DELETE'])
@jwt_required(optional=True)
def delete_project_endpoint(project_id):
    """
    Deleta um projeto
    DELETE /api/projects/<id>
    """
    try:
        # Tentar JWT primeiro
        user_id = get_jwt_identity()
        if not user_id:
            # Fallback para Flask-Login
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return jsonify({'error': 'Não autenticado'}), 401

        if db.delete_project(project_id):
            return jsonify({'success': True, 'message': 'Projeto deletado'}), 200
        else:
            return jsonify({'error': 'Erro ao deletar projeto'}), 500

    except Exception as e:
        print(f"[API] Delete project error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/projects/<int:project_id>/chats', methods=['POST'])
@jwt_required(optional=True)
def add_chat_to_project_endpoint(project_id):
    """
    Adiciona um chat a um projeto
    POST /api/projects/<id>/chats
    Body: {"chat_id": 123}
    """
    try:
        # Tentar JWT primeiro
        user_id = get_jwt_identity()
        if not user_id:
            # Fallback para Flask-Login
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return jsonify({'error': 'Não autenticado'}), 401

        data = request.get_json()
        chat_id = data.get('chat_id')

        if not chat_id:
            return jsonify({'error': 'chat_id é obrigatório'}), 400

        if db.add_chat_to_project(project_id, int(chat_id)):
            return jsonify({'success': True, 'message': 'Chat adicionado ao projeto'}), 200
        else:
            return jsonify({'error': 'Erro ao adicionar chat'}), 500

    except Exception as e:
        print(f"[API] Add chat to project error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/projects/<int:project_id>/chats/<int:chat_id>', methods=['DELETE'])
@jwt_required(optional=True)
def remove_chat_from_project_endpoint(project_id, chat_id):
    """
    Remove um chat de um projeto
    DELETE /api/projects/<project_id>/chats/<chat_id>
    """
    try:
        # Tentar JWT primeiro
        user_id = get_jwt_identity()
        if not user_id:
            # Fallback para Flask-Login
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return jsonify({'error': 'Não autenticado'}), 401

        if db.remove_chat_from_project(project_id, chat_id):
            return jsonify({'success': True, 'message': 'Chat removido do projeto'}), 200
        else:
            return jsonify({'error': 'Erro ao remover chat'}), 500

    except Exception as e:
        print(f"[API] Remove chat from project error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== INTERNET TOOLS ====================

@api_bp.route('/context', methods=['GET'])
@jwt_required(optional=True)
def get_user_context():
    """
    Retorna contexto completo do usuário (localização, hora, clima)
    """
    try:
        # Obter IP do usuário
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
        else:
            ip = request.remote_addr or '127.0.0.1'

        print(f"[CONTEXT] IP detectado: {ip}")

        # Obter contexto completo
        context = internet_tools.get_user_context(ip)

        return jsonify({
            'success': True,
            'context': context
        }), 200

    except Exception as e:
        print(f"[CONTEXT] Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/search', methods=['GET'])
@jwt_required(optional=True)
def search_web():
    """
    Busca informações na web usando DuckDuckGo
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Query vazia'}), 400

        num_results = min(int(request.args.get('n', 5)), 10)

        print(f"[SEARCH] Buscando: {query}")

        results = internet_tools.search_web(query, num_results)

        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        }), 200

    except Exception as e:
        print(f"[SEARCH] Erro: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/weather', methods=['GET'])
@jwt_required(optional=True)
def get_weather():
    """
    Retorna informações de clima baseado na localização do IP
    """
    try:
        # Obter IP do usuário
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
        else:
            ip = request.remote_addr or '127.0.0.1'

        # Obter localização
        location = internet_tools.get_location_from_ip(ip)

        # Obter clima
        weather = internet_tools.get_weather(
            location['latitude'],
            location['longitude']
        )

        return jsonify({
            'success': True,
            'location': location,
            'weather': weather
        }), 200

    except Exception as e:
        print(f"[WEATHER] Erro: {e}")
        return jsonify({'error': str(e)}), 500
