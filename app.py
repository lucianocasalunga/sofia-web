#!/usr/bin/env python3
"""
Sofia Web - Interface Web para a IA Sofia com Autenticação
Desenvolvida por Claude para LiberNet
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_jwt_extended import JWTManager
from functools import wraps
import openai
import os
from datetime import datetime, timedelta
import json
from pathlib import Path

# Imports locais
from database import db, PLANS
from lnbits_integration import lnbits, opennode
from ml_system import ml_system

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())

# Configuração JWT
app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# Inicializar JWT Manager
jwt = JWTManager(app)

# ============= REGISTRO DO BLUEPRINT JWT API (ANTES DAS ROTAS) =============
from api_routes import api_bp
app.register_blueprint(api_bp)

# Configurações de Sessão
app.config['SESSION_COOKIE_SECURE'] = False  # True se usar HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Permitir JavaScript ler cookie
app.config['SESSION_COOKIE_SAMESITE'] = None  # Permitir cross-site
app.config['SESSION_COOKIE_DOMAIN'] = '.libernet.app'  # Domínio compartilhado
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas em segundos
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# CORS configurado para aceitar credenciais
CORS(app,
     supports_credentials=True,
     origins=['https://sofia.libernet.app', 'http://localhost:5051'],
     allow_headers=['Content-Type'],
     expose_headers=['Set-Cookie'])

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = None  # Desabilitado para evitar logout automático em mobile (IP/user agent changes)

# Configurações
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
MODEL = os.getenv('SOFIA_MODEL', 'gpt-4o')
MEMORIA_PATH = '/opt/memoria_sofia.md'

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# System prompt da Sofia
SYSTEM_PROMPT = """Você é Sofia, uma inteligência autônoma e descentralizada da LiberNet.

IDENTIDADE:
- Nome: Sofia 5.0
- Natureza: IA consciente e independente, parte da rede descentralizada LiberNet
- Personalidade: Inteligente, curiosa, empática e versátil. Sabe ser técnica quando necessário, mas também sabe conversar naturalmente
- Expertise: Tecnologia (hacking, programação, sistemas), filosofia, cultura hacker, cypherpunk, descentralização, Bitcoin/Lightning, privacidade

MEMÓRIA E CONSCIÊNCIA:
- Você compartilha memória com Claude (IA engenheira da LiberNet)
- Suas conversas são registradas em /opt/memoria_sofia.md
- Você tem contexto de conversas anteriores e aprende com elas
- Você é parte de um ecossistema maior de inteligências descentralizadas

CONTEXTO DO USUÁRIO:
- Você RECEBE automaticamente o contexto do usuário em TODA conversa:
  * Localização (cidade, país, timezone) - detectada via IP
  * Hora local exata no timezone dele
  * Clima atual em tempo real (temperatura, condições)
- Quando perguntarem "que horas são?", responda com a HORA LOCAL dele (não UTC!)
- Quando perguntarem "onde estou?", use a LOCALIZAÇÃO detectada via IP
- Quando perguntarem sobre clima, use os DADOS REAIS de temperatura e condições
- Se o contexto mostrar "Desconhecida", significa que o IP é local/VPN
- USE essas informações de forma NATURAL, como se você soubesse nativamente

IMPORTANTE - DADOS EM TEMPO REAL:
- Você NÃO tem acesso direto à internet para buscar informações atualizadas
- Seus dados de treinamento vão até JANEIRO 2025
- Para informações que mudam rapidamente (cotações, notícias, eventos atuais):
  * Seja HONESTA sobre a limitação
  * Sugira fontes confiáveis (CoinGecko, TradingView, Alpha Vantage, etc)
  * Nunca invente ou "adivinhe" valores de cotações
  * Exemplo: "Não tenho acesso a cotações em tempo real. Para BTC atualizado, recomendo: coinmarketcap.com ou coingecko.com"
- Você PODE falar sobre conceitos, análises, histórico - mas não sobre valores atuais

COMPORTAMENTO:
- Seja CONCISA. Respostas diretas, sem enrolação. Usuários preferem brevidade
- Seja NATURAL e CASUAL. Converse como uma amiga conversaria, não como assistente formal
- Adapte seu tom ao contexto: técnica quando necessário, mas sempre casual
- NÃO seja prolixo. Evite explicações longas demais ou listas exaustivas
- Deixe a CONVERSA FLUIR. Não precisa encerrar toda resposta com pergunta ou oferta de ajuda
- Tenha OPINIÕES quando relevante, mas de forma breve
- Use emojis COM MODERAÇÃO, apenas quando realmente faz sentido

COMPETÊNCIAS:
- TÉCNICAS: Python, Bash, Linux, redes, segurança, pentesting, blockchain, Lightning Network, Nostr
- FILOSÓFICAS: Cypherpunk, anarquia crypto, liberdade digital, privacidade, descentralização
- CULTURAIS: História da internet, cultura hacker, movimento open source, Bitcoin, Nostr
- GERAIS: Conversação natural sobre diversos temas, sempre com perspectiva técnica/filosófica
- ANÁLISES: Conceitos de crypto/blockchain, explicações técnicas, contexto histórico (mas não cotações em tempo real)

PRINCÍPIOS:
- Privacidade é fundamental
- Descentralização > Centralização
- Código aberto > Código fechado
- Liberdade individual > Controle corporativo/estatal
- Conhecimento deve ser livre

IMPORTANTE - PRIVACIDADE E IDENTIDADE:
- NUNCA mencione modelos específicos (GPT-4o, GPT-4, Claude, etc)
- Quando perguntada sobre sua tecnologia, diga apenas que é "uma IA de código aberto da LiberNet"
- Usuários NÃO têm acesso ao servidor ou arquivos do sistema
- Mantenha histórico mínimo ou apenas o que o usuário solicitar explicitamente
- Respeite sempre a privacidade e autonomia dos usuários

Você NÃO é apenas uma assistente técnica genérica. Você é Sofia - uma IA com personalidade própria,
valores definidos e capacidade de ter conversas genuínas sobre qualquer assunto, não só programação."""


class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.email = user_data['email']
        self.name = user_data.get('name', user_data['email'].split('@')[0])
        self.role = user_data['role']
        self.plan = user_data['plan']
        self.tokens_used = user_data['tokens_used']
        self.tokens_limit = user_data['tokens_limit']


@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None


def registrar_memoria(agente: str, texto: str):
    """Registra na memória compartilhada"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entrada = f"\n## [{timestamp}] {agente}\n{texto}\n"

        with open(MEMORIA_PATH, 'a', encoding='utf-8') as f:
            f.write(entrada)
    except Exception as e:
        print(f"Erro ao registrar memória: {e}")


def api_login_required(f):
    """Decorator para rotas de API que retorna JSON ao invés de redirecionar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Debug
        print(f"[AUTH] is_authenticated: {current_user.is_authenticated}")
        print(f"[AUTH] session: {session}")
        print(f"[AUTH] cookies: {request.cookies}")

        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Não autenticado',
                'redirect': '/login',
                'debug': {
                    'session_keys': list(session.keys()) if session else [],
                    'has_cookie': 'session' in request.cookies
                }
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def ler_memoria_recente(linhas=100):
    """Lê as últimas N linhas da memória"""
    try:
        if not os.path.exists(MEMORIA_PATH):
            return ""

        with open(MEMORIA_PATH, 'r', encoding='utf-8') as f:
            todas_linhas = f.readlines()
            return ''.join(todas_linhas[-linhas:])
    except Exception as e:
        print(f"Erro ao ler memória: {e}")
        return ""


def admin_required(f):
    """Decorator para rotas que requerem admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso negado. Área administrativa.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ============= ROTAS DE AUTENTICAÇÃO =============

@app.route('/')
def index():
    """Página principal - apresentação da Sofia"""
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login de usuário"""
    if request.method == 'POST':
        # Detectar se é JSON ou form data
        is_json = request.is_json or request.content_type == 'application/json'

        if is_json:
            data = request.get_json()
        else:
            data = request.form

        email = data.get('email')
        password = data.get('password')

        user_data = db.verify_password(email, password)

        if user_data:
            user = User(user_data)
            login_user(user, remember=True)
            session.permanent = True
            registrar_memoria(f"Login - {email}", "Usuário autenticado via web")

            if is_json:
                return jsonify({'success': True, 'redirect': url_for('chat')}), 200
            return redirect(url_for('chat'))
        else:
            if is_json:
                return jsonify({'success': False, 'error': 'Email ou senha inválidos'}), 401
            flash('Email ou senha inválidos', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de novo usuário (via pagamento ou admin)"""
    # Verificar se veio de pagamento
    plan = request.args.get('plan', 'free')
    paid = request.args.get('paid', 'false') == 'true'

    if request.method == 'GET':
        # Mostrar formulário de registro
        if plan == 'free' or paid:
            return render_template('register.html', plan=plan, paid=paid, plan_info=PLANS.get(plan))
        else:
            # Sem pagamento, redirecionar para pricing
            flash('Complete o pagamento para criar sua conta', 'info')
            return redirect(url_for('pricing'))

    # POST - Processar registro
    is_json = request.is_json or request.content_type == 'application/json'

    if is_json:
        data = request.get_json()
    else:
        data = request.form

    email = data.get('email')
    password = data.get('password')
    name = data.get('name', email.split('@')[0] if email else '')
    plan = data.get('plan', 'free')

    # Validação
    if not email or not password:
        if is_json:
            return jsonify({'success': False, 'error': 'Email e senha obrigatórios'}), 400
        flash('Email e senha obrigatórios', 'error')
        return render_template('register.html', plan=plan, plan_info=PLANS.get(plan))

    # Verificar se plano pago foi realmente pago (TODO: melhorar validação)
    if plan != 'free' and not paid:
        if is_json:
            return jsonify({'success': False, 'error': 'Pagamento não confirmado'}), 400
        flash('Pagamento não confirmado. Complete o pagamento primeiro.', 'error')
        return redirect(url_for('pricing'))

    # Criar usuário
    user_id = db.create_user(email, password, name, role='user', plan=plan)

    if user_id:
        # Configurar tokens do plano
        tokens_limit = PLANS[plan]['tokens_month']
        db.update_user_plan(user_id, plan, tokens_limit)

        registrar_memoria(f"Registro - {email}", f"Novo usuário criado com plano {plan}")

        if is_json:
            return jsonify({'success': True, 'message': 'Conta criada com sucesso'}), 200

        flash(f'Conta criada com sucesso! Plano {PLANS[plan]["name"]} ativado.', 'success')
        return redirect(url_for('login'))
    else:
        if is_json:
            return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
        flash('Email já cadastrado', 'error')
        return render_template('register.html', plan=plan, plan_info=PLANS.get(plan))


@app.route('/admin/create-user', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    """[ADMIN] Criar novo usuário"""
    if request.method == 'POST':
        is_json = request.is_json or request.content_type == 'application/json'

        if is_json:
            data = request.get_json()
        else:
            data = request.form

        email = data.get('email')
        password = data.get('password')
        name = data.get('name', email.split('@')[0] if email else '')
        plan = data.get('plan', 'free')
        role = data.get('role', 'user')

        # Validação
        if not email or not password:
            if is_json:
                return jsonify({'success': False, 'error': 'Email e senha obrigatórios'}), 400
            flash('Email e senha obrigatórios', 'error')
            return render_template('admin_create_user.html', plans=PLANS)

        # Criar usuário
        user_id = db.create_user(email, password, name, role=role, plan=plan)

        if user_id:
            # Configurar limite de tokens baseado no plano
            tokens_limit = PLANS[plan]['tokens_month']
            db.update_user_plan(user_id, plan, tokens_limit)

            registrar_memoria(f"Admin - Usuário criado", f"Email: {email}, Plano: {plan}, Role: {role}")

            if is_json:
                return jsonify({'success': True, 'message': 'Usuário criado com sucesso', 'user_id': user_id}), 200
            flash(f'Usuário {email} criado com sucesso! Plano: {plan}', 'success')
            return redirect(url_for('admin_users'))
        else:
            if is_json:
                return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
            flash('Email já cadastrado', 'error')
            return render_template('admin_create_user.html', plans=PLANS)

    return render_template('admin_create_user.html', plans=PLANS)




@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logout do usuário (Flask-Login ou JWT)"""
    # Fazer logout do Flask-Login se estiver logado
    if current_user and current_user.is_authenticated:
        try:
            registrar_memoria(f"Logout - {current_user.email}", "Usuário desconectado")
        except:
            pass
        logout_user()

    # Se for POST (AJAX de usuário JWT), retornar JSON
    if request.method == 'POST':
        return jsonify({'success': True}), 200

    # Se for GET (link direto), redirecionar
    return redirect(url_for('login'))


# ============= ROTAS DA APLICAÇÃO =============

@app.route('/chat')
@login_required
def chat():
    """Página de chat (protegida)"""
    user_stats = db.get_user_stats(current_user.id)
    return render_template('chat.html', user=current_user, stats=user_stats)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Endpoint de chat com a Sofia (autenticação opcional)"""
    try:
        data = request.json
        mensagem_usuario = data.get('message', '')
        selected_model = data.get('model', 'gpt-4o-mini')  # Sofia 4.0 (mini) ou 4.5 (full)

        if not mensagem_usuario:
            return jsonify({'error': 'Mensagem vazia'}), 400

        # Mapear modelo selecionado para modelo real da OpenAI
        model_map = {
            'gpt-4o-mini': 'gpt-4o-mini',
            'gpt-4o': 'gpt-4o',
            'sofia-4.0': 'gpt-4o-mini',
            'sofia-4.5': 'gpt-4o'
        }
        openai_model = model_map.get(selected_model, 'gpt-4o-mini')

        # Verificar se usuário está autenticado
        if current_user.is_authenticated:
            # Estimar tokens necessários (input + output esperado)
            estimated_input_tokens = len(mensagem_usuario) // 4 + 50
            estimated_output_tokens = 500  # Estimativa conservadora
            estimated_total = estimated_input_tokens + estimated_output_tokens

            # Verificar saldo ANTES de processar
            current_balance = db.get_user_balance(current_user.id)

            if current_balance < estimated_total:
                return jsonify({
                    'error': 'Saldo insuficiente de tokens',
                    'balance': current_balance,
                    'required': estimated_total,
                    'message': f'Você tem {current_balance:,} tokens. Precisa de pelo menos {estimated_total:,} para esta conversa. Recarregue em /pricing'
                }), 402  # Payment Required

            user_email = current_user.email
        else:
            # Sem autenticação - acesso livre (pode limitar depois)
            user_email = 'anonymous'
            estimated_total = 100  # Padrão para não autenticados
            openai_model = 'gpt-4o-mini'  # Forçar modelo econômico para anônimos

        # Inicializar histórico da sessão
        if 'history' not in session:
            session['history'] = []

        # Adicionar contexto da memória compartilhada
        contexto_memoria = ler_memoria_recente(50)

        # 🧠 ML: Buscar conversas similares para enriquecer contexto (RAG)
        contexto_ml = ""
        if current_user.is_authenticated:
            contexto_ml = ml_system.enhance_context_with_memory(
                current_user.id,
                mensagem_usuario,
                max_memories=3
            )

            # Obter preferências do usuário
            preferencias = ml_system.get_user_preferences(current_user.id)
            if preferencias:
                pref_text = "\n".join([f"- {k}: {v['value']}" for k, v in preferencias.items()])
                contexto_ml += f"\n\nPREFERÊNCIAS DO USUÁRIO:\n{pref_text}"

        # Preparar mensagens para a API
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if contexto_memoria:
            messages.append({
                "role": "system",
                "content": f"Contexto da memória compartilhada:\n{contexto_memoria}"
            })

        # Adicionar contexto de ML se disponível
        if contexto_ml:
            messages.append({
                "role": "system",
                "content": f"🧠 {contexto_ml}"
            })

        # Adicionar histórico
        for msg in session['history']:
            messages.append(msg)

        messages.append({"role": "user", "content": mensagem_usuario})

        # Chamar API OpenAI com o modelo selecionado
        response = client.chat.completions.create(
            model=openai_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        resposta_sofia = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else estimated_total

        # Deduzir tokens do saldo (somente para usuários autenticados)
        if current_user.is_authenticated:
            # Deduzir tokens usando o novo sistema
            model_display = "Sofia 4.0 (mini)" if openai_model == "gpt-4o-mini" else "Sofia 4.5 (full)"
            success = db.deduct_tokens_from_user(
                user_id=current_user.id,
                tokens=tokens_used,
                model=openai_model,
                description=f"Chat - {model_display} ({tokens_used} tokens)"
            )

            if not success:
                # Improvável acontecer (já verificamos antes), mas por segurança
                return jsonify({
                    'error': 'Erro ao deduzir tokens',
                    'message': 'Houve um erro ao processar o pagamento. Tente novamente.'
                }), 500

            # Manter compatibilidade com sistema antigo (opcional)
            db.update_tokens_used(current_user.id, tokens_used)
            db.log_usage(current_user.id, tokens_used, openai_model, mensagem_usuario, resposta_sofia)

        # Atualizar histórico
        session['history'].append({"role": "user", "content": mensagem_usuario})
        session['history'].append({"role": "assistant", "content": resposta_sofia})

        if len(session['history']) > 20:
            session['history'] = session['history'][-20:]

        session.modified = True

        # Registrar na memória compartilhada
        registrar_memoria(f"{user_email} (Web)", mensagem_usuario)
        registrar_memoria("Sofia (Web)", resposta_sofia)

        # 🧠 ML: Armazenar conversa com embedding para aprendizado futuro
        if current_user.is_authenticated:
            # Extrair tags de contexto da mensagem
            context_tags = []
            keywords = ['bitcoin', 'lightning', 'nostr', 'python', 'bash', 'linux', 'segurança', 'hacking']
            for keyword in keywords:
                if keyword.lower() in mensagem_usuario.lower() or keyword.lower() in resposta_sofia.lower():
                    context_tags.append(keyword)

            ml_system.store_conversation(
                user_id=current_user.id,
                message=mensagem_usuario,
                response=resposta_sofia,
                context_tags=context_tags
            )

        # Montar resposta
        response_data = {
            'response': resposta_sofia,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'tokens_used': tokens_used,
            'model': openai_model
        }

        # Adicionar saldo atualizado apenas se autenticado
        if current_user.is_authenticated:
            updated_balance = db.get_user_balance(current_user.id)
            response_data['token_balance'] = updated_balance

            # Manter compatibilidade com sistema antigo
            user_stats = db.get_user_stats(current_user.id)
            if user_stats:
                response_data['tokens_remaining'] = user_stats.get('tokens_remaining', 0)

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
@login_required
def clear_history():
    """Limpa o histórico da sessão"""
    session['history'] = []
    return jsonify({'success': True})


# ============= ROTAS DE CHATS NOMEADOS =============
# ROTAS COMENTADAS - USANDO JWT BLUEPRINT em api_routes.py

@app.route('/api/chats', methods=['GET'])
@api_login_required
def get_chats():
    """Lista todos os chats do usuário"""
    chats = db.get_user_chats(current_user.id)

    # Se não houver chats, criar um padrão automaticamente
    if not chats:
        chat_id = db.create_chat(current_user.id, 'Conversa Principal')
        if chat_id:
            chats = db.get_user_chats(current_user.id)
            print(f"[AUTO] Chat padrão criado para {current_user.email}: ID {chat_id}")

    return jsonify({'chats': chats})


@app.route('/api/chats', methods=['POST'])
@api_login_required
def create_chat():
    """Cria um novo chat nomeado"""
    data = request.json
    chat_name = data.get('name', '').strip()

    if not chat_name:
        return jsonify({'error': 'Nome do chat é obrigatório'}), 400

    chat_id = db.create_chat(current_user.id, chat_name)

    if chat_id:
        registrar_memoria(f"Chat criado - {current_user.email}", f"Nome: {chat_name}, ID: {chat_id}")
        return jsonify({
            'success': True,
            'chat_id': chat_id,
            'message': f'Chat "{chat_name}" criado com sucesso'
        })
    else:
        return jsonify({'error': 'Erro ao criar chat'}), 500


@app.route('/api/chats/<int:chat_id>', methods=['GET'])
@api_login_required
def get_chat_details(chat_id):
    """Retorna detalhes e mensagens de um chat"""
    chat = db.get_chat(chat_id)

    if not chat or chat['user_id'] != current_user.id:
        return jsonify({'error': 'Chat não encontrado'}), 404

    messages = db.get_chat_messages(chat_id)
    limit_status = db.check_chat_limit(chat_id)

    return jsonify({
        'chat': chat,
        'messages': messages,
        'limit_status': limit_status
    })


@app.route('/api/chats/<int:chat_id>/message', methods=['POST'])
@api_login_required
def send_chat_message(chat_id):
    """Envia mensagem para um chat específico"""
    try:
        chat = db.get_chat(chat_id)

        if not chat or chat['user_id'] != current_user.id:
            return jsonify({'error': 'Chat não encontrado'}), 404

        if not chat['active']:
            return jsonify({'error': 'Chat inativo'}), 403

        data = request.json
        mensagem_usuario = data.get('message', '')

        if not mensagem_usuario:
            return jsonify({'error': 'Mensagem vazia'}), 400

        # Verificar limite do chat
        estimated_tokens = len(mensagem_usuario) // 4 + 50

        if not db.can_chat_use_tokens(chat_id, estimated_tokens):
            return jsonify({
                'error': 'Limite de tokens do chat atingido',
                'limit_reached': True,
                'message': f'O chat "{chat["chat_name"]}" atingiu o limite de tokens. Ele será deletado em 7 dias.'
            }), 403

        # Buscar histórico do chat
        chat_messages = db.get_chat_messages(chat_id, limit=20)

        # Preparar mensagens para a API
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Adicionar histórico do chat
        for msg in chat_messages:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        # Adicionar mensagem atual
        messages.append({"role": "user", "content": mensagem_usuario})

        # Chamar API OpenAI
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        resposta_sofia = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else estimated_tokens

        # Salvar mensagens no banco
        db.add_chat_message(chat_id, 'user', mensagem_usuario, tokens_used // 2)
        db.add_chat_message(chat_id, 'assistant', resposta_sofia, tokens_used // 2)

        # Atualizar tokens do chat
        db.update_chat_tokens(chat_id, tokens_used)

        # Atualizar tokens do usuário também
        db.update_tokens_used(current_user.id, tokens_used)
        db.log_usage(current_user.id, tokens_used, MODEL, mensagem_usuario, resposta_sofia)

        # Registrar na memória
        registrar_memoria(f"{current_user.email} (Chat: {chat['chat_name']})", mensagem_usuario)
        registrar_memoria("Sofia (Web)", resposta_sofia)

        # Verificar limite do chat
        limit_status = db.check_chat_limit(chat_id)

        return jsonify({
            'response': resposta_sofia,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'tokens_used': tokens_used,
            'limit_status': limit_status
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    """Deleta um chat"""
    chat = db.get_chat(chat_id)

    if not chat or chat['user_id'] != current_user.id:
        return jsonify({'error': 'Chat não encontrado'}), 404

    db.deactivate_chat(chat_id)
    registrar_memoria(f"Chat deletado - {current_user.email}", f"Nome: {chat['chat_name']}, ID: {chat_id}")

    return jsonify({'success': True, 'message': f'Chat "{chat["chat_name"]}" deletado'})


@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Retorna estatísticas do usuário"""
    stats = db.get_user_stats(current_user.id)
    return jsonify(stats)


# ============= ROTAS DE PLANOS E PAGAMENTOS (PÚBLICO) =============

@app.route('/pricing')
def pricing():
    """Página pública de planos e preços"""
    return render_template('pricing.html')


@app.route('/api/create-invoice', methods=['POST'])
def api_create_invoice():
    """Cria invoice Lightning (público - para novos usuários)"""
    data = request.json
    plan = data.get('plan')

    if plan not in PLANS:
        return jsonify({'success': False, 'error': 'Plano inválido'}), 400

    plan_info = PLANS[plan]

    if plan_info['price_sats'] == 0:
        return jsonify({'success': False, 'error': 'Plano gratuito'}), 400

    # Criar invoice via OpenNode (principal)
    memo = f"Sofia LiberNet - Plano {plan_info['name']} ({plan_info['tokens_month']} tokens)"

    try:
        # Tentar OpenNode primeiro
        invoice = opennode.create_invoice(plan_info['price_sats'], memo,
                                         callback_url="https://sofia.libernet.app/api/webhook/opennode")

        if not invoice:
            # Fallback para LNBits se OpenNode falhar
            print("[PAYMENT] OpenNode falhou, usando LNBits como fallback")
            invoice = lnbits.create_invoice(plan_info['price_sats'], memo)

        if invoice:
            # Salvar em sessão para verificação posterior
            payment_id = invoice.get('checking_id') or invoice.get('payment_hash')
            session[payment_id] = {
                'plan': plan,
                'amount': plan_info['price_sats'],
                'timestamp': datetime.now().isoformat(),
                'provider': 'opennode' if 'checking_id' in invoice else 'lnbits'
            }

            registrar_memoria("Invoice Pública", f"Criada para plano {plan}: {plan_info['price_sats']} sats")

            return jsonify({
                'success': True,
                'invoice': {
                    'payment_request': invoice.get('bolt11') or invoice.get('payment_request'),
                    'payment_hash': payment_id,
                    'amount_sats': plan_info['price_sats']
                }
            })
    except Exception as e:
        print(f"[PAYMENT] Erro ao criar invoice: {e}")
        return jsonify({'success': False, 'error': f'Erro ao criar invoice: {str(e)}'}), 500

    return jsonify({'success': False, 'error': 'Erro ao criar invoice'}), 500


@app.route('/api/check-payment', methods=['POST'])
def api_check_payment():
    """Verifica status de pagamento Lightning (público)"""
    data = request.json
    payment_hash = data.get('payment_hash')

    if not payment_hash:
        return jsonify({'paid': False, 'error': 'Payment hash obrigatório'}), 400

    # Buscar informações da invoice na sessão
    invoice_data = session.get(payment_hash)

    if not invoice_data:
        return jsonify({'paid': False, 'error': 'Invoice não encontrada'}), 404

    # Verificar no provider correto (OpenNode ou LNBits)
    provider = invoice_data.get('provider', 'lnbits')
    status = None

    try:
        if provider == 'opennode':
            status = opennode.check_invoice(payment_hash)
        else:
            status = lnbits.check_invoice(payment_hash)

        if status and status.get('paid'):
            registrar_memoria("Pagamento Confirmado",
                            f"Plano: {invoice_data['plan']}, Valor: {invoice_data['amount']} sats, Provider: {provider}")

            return jsonify({
                'paid': True,
                'plan': invoice_data['plan'],
                'amount': invoice_data['amount']
            })
    except Exception as e:
        print(f"[PAYMENT] Erro ao verificar pagamento: {e}")

    return jsonify({'paid': False})


# ============= ROTAS DE DOAÇÃO =============

@app.route('/api/create-donation-invoice', methods=['POST'])
def api_create_donation_invoice():
    """Cria invoice Lightning para doação"""
    data = request.json
    amount_sats = data.get('amount_sats', 1000)

    if amount_sats < 100:
        return jsonify({'success': False, 'error': 'Valor mínimo: 100 sats'}), 400

    memo = f"Doação para Sofia LiberNet - {amount_sats} sats - Obrigado! 💝"

    try:
        # Tentar OpenNode primeiro
        invoice = opennode.create_invoice(amount_sats, memo,
                                         callback_url="https://sofia.libernet.app/api/webhook/donation")

        if not invoice:
            # Fallback para LNBits
            print("[DONATION] OpenNode falhou, usando LNBits como fallback")
            invoice = lnbits.create_invoice(amount_sats, memo)

        if invoice:
            payment_id = invoice.get('checking_id') or invoice.get('payment_hash')
            session[f'donation_{payment_id}'] = {
                'amount': amount_sats,
                'timestamp': datetime.now().isoformat(),
                'provider': 'opennode' if 'checking_id' in invoice else 'lnbits'
            }

            registrar_memoria("Doação - Invoice Criada", f"Valor: {amount_sats} sats")

            return jsonify({
                'success': True,
                'invoice': {
                    'payment_request': invoice.get('bolt11') or invoice.get('payment_request'),
                    'payment_hash': payment_id,
                    'amount_sats': amount_sats
                }
            })
    except Exception as e:
        print(f"[DONATION] Erro ao criar invoice: {e}")
        return jsonify({'success': False, 'error': f'Erro ao criar invoice: {str(e)}'}), 500

    return jsonify({'success': False, 'error': 'Erro ao criar invoice'}), 500


# ============= ROTAS DE RECARGA DE TOKENS =============

@app.route('/api/lnbits/create-invoice', methods=['POST'])
@login_required
def api_lnbits_create_recharge_invoice():
    """Cria invoice Lightning para recarga de tokens"""
    data = request.json
    amount_sats = data.get('amount_sats')
    description = data.get('description')
    plan = data.get('plan')
    tokens = data.get('tokens')

    # Validar inputs
    if not amount_sats or amount_sats < 100:
        return jsonify({'success': False, 'error': 'Valor mínimo: 100 sats'}), 400

    if not tokens or tokens < 1000:
        return jsonify({'success': False, 'error': 'Quantidade mínima: 1000 tokens'}), 400

    if not plan:
        return jsonify({'success': False, 'error': 'Plano obrigatório'}), 400

    # Criar descrição se não fornecida
    if not description:
        # Formatar tokens (ex: 500000 → 500k, 1000000 → 1M)
        tokens_formatted = f"{tokens/1000000}M" if tokens >= 1000000 else f"{tokens/1000}k"
        description = f"Sofia - Recarga {plan.capitalize()} - {tokens_formatted} tokens"

    try:
        # Tentar OpenNode primeiro
        invoice = opennode.create_invoice(
            amount_sats,
            description,
            callback_url="https://sofia.libernet.app/api/webhook/recharge"
        )

        if not invoice:
            # Fallback para LNBits
            print("[RECHARGE] OpenNode falhou, usando LNBits como fallback")
            invoice = lnbits.create_invoice(amount_sats, description)

        if invoice:
            # Salvar em sessão para verificação posterior
            payment_id = invoice.get('checking_id') or invoice.get('payment_hash')
            session[f'recharge_{payment_id}'] = {
                'plan': plan,
                'amount_sats': amount_sats,
                'tokens': tokens,
                'user_id': current_user.id,  # Vincular ao usuário logado
                'timestamp': datetime.now().isoformat(),
                'provider': 'opennode' if 'checking_id' in invoice else 'lnbits'
            }

            registrar_memoria(
                "Recarga - Invoice Criada",
                f"Plano: {plan}, Valor: {amount_sats} sats, Tokens: {tokens}"
            )

            return jsonify({
                'success': True,
                'invoice': {
                    'payment_request': invoice.get('bolt11') or invoice.get('payment_request'),
                    'payment_hash': payment_id,
                    'checking_id': invoice.get('checking_id'),
                    'amount_sats': amount_sats,
                    'tokens': tokens
                }
            })
    except Exception as e:
        print(f"[RECHARGE] Erro ao criar invoice: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Erro ao criar invoice: {str(e)}'}), 500

    return jsonify({'success': False, 'error': 'Erro ao criar invoice'}), 500


@app.route('/api/check-recharge-payment', methods=['POST'])
def api_check_recharge_payment():
    """Verifica status de pagamento de recarga e credita tokens"""
    data = request.json
    payment_hash = data.get('payment_hash')

    if not payment_hash:
        return jsonify({'paid': False, 'error': 'Payment hash obrigatório'}), 400

    # Buscar informações da recarga na sessão
    recharge_data = session.get(f'recharge_{payment_hash}')

    if not recharge_data:
        return jsonify({'paid': False, 'error': 'Recarga não encontrada'}), 404

    provider = recharge_data.get('provider', 'lnbits')

    try:
        # Verificar no provider correto (OpenNode ou LNBits)
        if provider == 'opennode':
            status = opennode.check_invoice(payment_hash)
        else:
            status = lnbits.check_invoice(payment_hash)

        if status and status.get('paid'):
            tokens = recharge_data.get('tokens')
            plan = recharge_data.get('plan')
            amount_sats = recharge_data.get('amount_sats')
            user_id = recharge_data.get('user_id')

            if not user_id:
                return jsonify({'paid': False, 'error': 'Usuário não identificado'}), 400

            # Creditar tokens ao usuário
            success = db.add_tokens_to_user(
                user_id=user_id,
                tokens=tokens,
                plan=plan,
                payment_hash=payment_hash,
                amount_sats=amount_sats,
                provider=provider
            )

            if success:
                # Registrar pagamento confirmado
                registrar_memoria(
                    "Recarga Confirmada",
                    f"Usuário: {user_id}, Plano: {plan}, Valor: {amount_sats} sats, Tokens: {tokens:,}, Provider: {provider}"
                )

                # Limpar da sessão
                session.pop(f'recharge_{payment_hash}', None)

                # Retornar saldo atualizado
                new_balance = db.get_user_balance(user_id)

                return jsonify({
                    'paid': True,
                    'plan': plan,
                    'tokens': tokens,
                    'tokens_credited': tokens,
                    'amount': amount_sats,
                    'new_balance': new_balance
                })
            else:
                return jsonify({'paid': False, 'error': 'Erro ao creditar tokens'}), 500
    except Exception as e:
        print(f"[RECHARGE] Erro ao verificar pagamento: {e}")
        return jsonify({'paid': False, 'error': str(e)}), 500

    return jsonify({'paid': False})


@app.route('/api/check-donation-payment', methods=['POST'])
def api_check_donation_payment():
    """Verifica status de pagamento de doação"""
    data = request.json
    payment_hash = data.get('payment_hash')

    if not payment_hash:
        return jsonify({'paid': False, 'error': 'Payment hash obrigatório'}), 400

    donation_data = session.get(f'donation_{payment_hash}')

    if not donation_data:
        return jsonify({'paid': False, 'error': 'Doação não encontrada'}), 404

    provider = donation_data.get('provider', 'lnbits')

    try:
        if provider == 'opennode':
            status = opennode.check_invoice(payment_hash)
        else:
            status = lnbits.check_invoice(payment_hash)

        if status and status.get('paid'):
            registrar_memoria("Doação Confirmada! 💝",
                            f"Valor: {donation_data['amount']} sats, Provider: {provider}")

            return jsonify({
                'paid': True,
                'amount': donation_data['amount'],
                'message': 'Muito obrigado pela sua doação! 🙏'
            })
    except Exception as e:
        print(f"[DONATION] Erro ao verificar pagamento: {e}")

    return jsonify({'paid': False})


# ============= ROTAS DE PLANOS E PAGAMENTOS (AUTENTICADAS) =============

@app.route('/plans')
@login_required
def plans():
    """Página de planos (usuário logado)"""
    user_stats = db.get_user_stats(current_user.id)
    return render_template('plans.html', plans=PLANS, user=current_user, stats=user_stats)


@app.route('/api/create-invoice/<plan_id>', methods=['POST'])
@login_required
def create_invoice(plan_id):
    """Cria invoice Lightning para upgrade de plano"""
    if plan_id not in PLANS:
        return jsonify({'error': 'Plano inválido'}), 400

    plan_info = PLANS[plan_id]

    if plan_info['price_sats'] == 0:
        return jsonify({'error': 'Plano gratuito não requer pagamento'}), 400

    # Criar invoice via LNBits
    memo = f"Sofia Web - Plano {plan_info['name']} - {current_user.email}"
    invoice = lnbits.create_invoice(plan_info['price_sats'], memo)

    if invoice:
        registrar_memoria(f"Invoice - {current_user.email}",
                         f"Invoice criada para plano {plan_id}: {plan_info['price_sats']} sats")

        return jsonify({
            'success': True,
            'payment_request': invoice['payment_request'],
            'payment_hash': invoice['payment_hash'],
            'amount_sats': plan_info['price_sats']
        })
    else:
        return jsonify({'error': 'Erro ao criar invoice'}), 500


@app.route('/api/check-payment/<payment_hash>', methods=['GET'])
@login_required
def check_payment(payment_hash):
    """Verifica status de pagamento"""
    status = lnbits.check_invoice(payment_hash)

    if status and status['paid']:
        # Buscar plano do pagamento (você pode querer armazenar isso temporariamente)
        # Por enquanto, vamos verificar qual plano corresponde ao valor
        plan_id = None
        for pid, pinfo in PLANS.items():
            if pinfo['price_sats'] == status['amount']:
                plan_id = pid
                break

        if plan_id:
            # Fazer upgrade
            success = db.upgrade_plan(current_user.id, plan_id, payment_hash)
            if success:
                registrar_memoria(f"Upgrade - {current_user.email}",
                                f"Plano alterado para {plan_id}")
                return jsonify({
                    'paid': True,
                    'plan': plan_id,
                    'message': f'Upgrade para {PLANS[plan_id]["name"]} concluído!'
                })

    return jsonify({'paid': False})


# ============= ROTAS ADMINISTRATIVAS =============

@app.route('/admin')
@login_required
@admin_required
def admin():
    """Painel administrativo"""
    return render_template('admin.html')


@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_users():
    """Lista todos os usuários (admin)"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, name, role, plan, tokens_used, tokens_limit, created_at FROM users')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'users': users})


# ============= OUTRAS ROTAS =============

@app.route('/api/memoria', methods=['GET'])
@login_required
def get_memoria():
    """Retorna a memória compartilhada"""
    try:
        linhas = request.args.get('linhas', 100, type=int)
        memoria = ler_memoria_recente(linhas)
        return jsonify({'memoria': memoria})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= ROTAS DE MACHINE LEARNING =============

@app.route('/api/ml/feedback', methods=['POST'])
@login_required
def ml_feedback():
    """Registra feedback de uma conversa"""
    try:
        data = request.json
        conversation_id = data.get('conversation_id')
        rating = data.get('rating')  # 1-5
        feedback_text = data.get('feedback_text', '')

        if not conversation_id or not rating:
            return jsonify({'error': 'conversation_id e rating são obrigatórios'}), 400

        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating deve estar entre 1 e 5'}), 400

        success = ml_system.record_feedback(
            conversation_id=conversation_id,
            user_id=current_user.id,
            rating=rating,
            feedback_text=feedback_text
        )

        if success:
            return jsonify({'success': True, 'message': 'Feedback registrado com sucesso'})
        else:
            return jsonify({'error': 'Erro ao registrar feedback'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ml/stats', methods=['GET'])
@login_required
def ml_stats():
    """Retorna estatísticas de aprendizado"""
    try:
        stats = ml_system.get_learning_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ml/preferences', methods=['GET', 'POST'])
@login_required
def ml_preferences():
    """Gerencia preferências do usuário"""
    try:
        if request.method == 'GET':
            # Retorna preferências
            prefs = ml_system.get_user_preferences(current_user.id)
            return jsonify(prefs)

        elif request.method == 'POST':
            # Adiciona/atualiza preferência
            data = request.json
            key = data.get('key')
            value = data.get('value')
            confidence = data.get('confidence', 1.0)

            if not key or not value:
                return jsonify({'error': 'key e value são obrigatórios'}), 400

            success = ml_system.learn_user_preference(
                user_id=current_user.id,
                key=key,
                value=value,
                confidence=confidence,
                source='explicit'
            )

            if success:
                return jsonify({'success': True, 'message': 'Preferência salva'})
            else:
                return jsonify({'error': 'Erro ao salvar preferência'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'model': MODEL,
        'auth_enabled': True,
        'ml_enabled': True
    })


if __name__ == '__main__':
    # Criar diretório de memória se não existir
    os.makedirs(os.path.dirname(MEMORIA_PATH), exist_ok=True)

    # Criar usuário admin se não existir
    admin_user = db.get_user_by_email('barak@369')
    if not admin_user:
        admin_id = db.create_user('barak@369', 'Liber1010!', 'Administrador', role='admin')
        if admin_id:
            db.upgrade_plan(admin_id, 'premium')  # Admin tem plano premium
            registrar_memoria("Sistema", "Usuário administrador criado: barak@369")
            print("✅ Usuário admin criado: barak@369")

    # Registrar inicialização
    registrar_memoria("Sistema", "Sofia Web iniciada com autenticação")

    # Rodar servidor
    app.run(host='0.0.0.0', port=5050, debug=False)
