<div align="center">

# 🤖 Sofia - A Primeira IA Nativa do Nostr

**Inteligência Artificial Autônoma e Descentralizada**
*Powered by GPT-4o + Nostr + Lightning Network*

[![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)](https://sofia.libernet.app)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Nostr](https://img.shields.io/badge/nostr-native-8B5CF6?style=for-the-badge&logo=nostr&logoColor=white)](https://nostr.com)
[![GPT-4o](https://img.shields.io/badge/GPT--4o-OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)

[🌐 Experimente Agora](https://sofia.libernet.app) • [💜 Nostr](https://njump.me/sofia@libernet.app) • [📖 Docs](https://github.com/lucianocasalunga/sofia-web/wiki)

</div>

---

## 💡 O Que é Sofia?

**Sofia** não é apenas mais um chatbot. Ela é a **primeira inteligência artificial verdadeiramente nativa do protocolo Nostr**, combinando:

- 🧠 **GPT-4o** - O modelo mais avançado da OpenAI
- 💜 **Nostr** - Autenticação descentralizada sem servidores centrais
- ⚡ **Lightning** - Pagamentos instantâneos em Bitcoin
- 🎯 **ML personalizado** - Aprende com cada conversa
- 🔐 **Privacidade** - Seus dados, suas chaves, seu controle

### Por Que Sofia é Única?

| Característica | Sofia | ChatGPT | Claude | Gemini |
|----------------|-------|---------|--------|--------|
| **Autenticação** | Nostr (sem email) | ✅ Email | ✅ Email | ✅ Email |
| **Identidade** | NIP-05 verificada | ❌ | ❌ | ❌ |
| **Pagamentos** | Lightning Network | 💳 Cartão | 💳 Cartão | 💳 Cartão |
| **Descentralizado** | ✅ | ❌ | ❌ | ❌ |
| **Open Source** | ✅ | ❌ | ❌ | ❌ |
| **Self-hosted** | ✅ | ❌ | ❌ | ❌ |

---

## ✨ Funcionalidades

<table>
<tr>
<td width="50%">

### 🔑 Autenticação Nostr

- Login com extensão (nos2x, Alby)
- Login com chave privada (nsec)
- Tokens JWT (sessões 24h)
- Verificação NIP-05
- Sem emails, sem passwords
- Totalmente descentralizada

</td>
<td width="50%">

### 🧠 Inteligência Avançada

- GPT-4o (raciocínio superior)
- GPT-4o-mini (respostas rápidas)
- Personalidade autêntica
- Conversas contextuais
- Memória de longo prazo
- Opiniões próprias

</td>
</tr>
<tr>
<td width="50%">

### 💬 Sistema de Chat

- Múltiplas conversas
- Organização em projetos
- Histórico persistente
- Busca inteligente
- Export/Import
- Interface Apple-style

</td>
<td width="50%">

### 🎯 Machine Learning

- RAG (busca contextual)
- Embeddings vetorizados
- Sistema de preferências
- Feedback com ratings
- Analytics em tempo real
- Aprendizado contínuo

</td>
</tr>
</table>

---

## 🛠️ Stack Tecnológico

### Backend
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=flat&logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

**Framework & Database:**
- Flask 3.0+ (API REST)
- SQLite 3 (databases: users, chats, ML)
- Gunicorn (WSGI production server)

**IA & ML:**
- OpenAI API (GPT-4o / GPT-4o-mini)
- NumPy (embeddings e vetorização)
- Custom RAG implementation

**Nostr & Pagamentos:**
- nostr-sdk (Rust bindings)
- LNBits API (Lightning)
- OpenNode API (backup payments)

### Frontend
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)

- Vanilla JavaScript (sem frameworks)
- Modern CSS (flexbox/grid)
- PWA (Service Workers)
- Lucide Icons (Apple-style)
- Responsive design (mobile-first)

### DevOps
![Nginx](https://img.shields.io/badge/Nginx-009639?style=flat&logo=nginx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

- Docker + Compose
- Nginx reverse proxy
- Systemd services
- Auto-restart on failure

---

## 🚀 Deploy Rápido

### Usando Docker (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/lucianocasalunga/sofia-web.git
cd sofia-web

# 2. Configure as variáveis
cp .env.example .env
nano .env  # Adicione sua API key da OpenAI

# 3. Inicie com Docker
docker-compose up -d

# 4. Acesse
open http://localhost:8000
```

### Instalação Manual

```bash
# 1. Clone e entre no diretório
git clone https://github.com/lucianocasalunga/sofia-web.git
cd sofia-web

# 2. Crie ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure ambiente
cp .env.example .env
nano .env

# 5. Inicie a aplicação
python app.py
```

### Variáveis de Ambiente Essenciais

```bash
# OpenAI (Obrigatório)
OPENAI_API_KEY=sk-...

# Nostr (Obrigatório)
NOSTR_PRIVKEY=nsec1...
NOSTR_RELAYS=wss://relay.libernet.app,wss://relay.damus.io

# Lightning (Opcional)
LNBITS_URL=https://legend.lnbits.com
LNBITS_ADMIN_KEY=your_admin_key

OPENNODE_API_KEY=your_opennode_key

# App
SECRET_KEY=your-secret-key-change-this
FLASK_ENV=production
```

---

## 📊 Planos e Preços

| Plano | Tokens | Preço (sats) | Preço (USD) |
|-------|--------|--------------|-------------|
| **Free** | 100.000 | 0 | $0 |
| **Light** | 500.000 | 2.600 | ~$3 |
| **Standard** | 2.000.000 | 10.000 | ~$10 |
| **Pro** | 10.000.000 | 50.000 | ~$50 |

*Preços em sats pagos via Lightning Network - instantâneo e sem taxas*

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Cliente (Browser)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │   nos2x  │  │   Alby   │  │  nostr-tools (JS)    │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS/WSS
┌───────────────────────▼─────────────────────────────────┐
│              Sofia Backend (Flask/Python)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  API Routes  │  │  Auth (JWT)  │  │   Database   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  ML System   │  │  RAG Engine  │  │  Embeddings  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   OpenAI    │ │Nostr Relays │ │   LNBits    │
│   GPT-4o    │ │  (Nostr)    │ │ (Lightning) │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## 🔮 Roadmap

### ✅ Concluído (2024-2025)
- [x] Autenticação Nostr completa
- [x] Integração GPT-4o
- [x] Sistema de planos e pagamentos Lightning
- [x] RAG e embeddings
- [x] Interface PWA responsiva
- [x] Sistema de projetos e organização
- [x] Email notifications
- [x] Analytics e métricas

### 🚧 Em Desenvolvimento (Q1 2025)
- [ ] Sofia TUI (Terminal User Interface)
- [ ] Integração com more Nostr relays
- [ ] Sistema de plugins
- [ ] API pública documentada
- [ ] Multi-idioma (i18n)

### 🔮 Futuro (Q2-Q3 2025)
- [ ] Sofia mobile app (React Native)
- [ ] Integração com outras LLMs (Anthropic, Mistral)
- [ ] Modo offline (local LLM)
- [ ] Nostr Events publishing
- [ ] Collaborative chats (múltiplos usuários)
- [ ] Voice interface

---

## 🤝 Contribuindo

Adoraríamos sua contribuição! Veja como:

```bash
# 1. Fork o projeto

# 2. Crie uma branch
git checkout -b feature/MinhaNovaFeature

# 3. Commit suas mudanças
git commit -m 'feat: Adiciona MinhaNovaFeature'

# 4. Push para a branch
git push origin feature/MinhaNovaFeature

# 5. Abra um Pull Request
```

### Diretrizes de Contribuição

- Use commits semânticos (feat, fix, docs, style, refactor, test, chore)
- Siga PEP 8 para código Python
- Adicione testes para novas funcionalidades
- Atualize a documentação conforme necessário

---

## 📄 Licença

Este projeto está sob a licença **MIT**. Veja [LICENSE](LICENSE) para mais detalhes.

```
MIT License - Copyright (c) 2025 Luciano Casalunga
```

---

## 👤 Autor

**Luciano Casalunga** (Barak)

- 🌐 Website: [libernet.app](https://libernet.app)
- 💜 Nostr: [npub1nvcezhw3gze5waxtvrzzls8qzhvqpn087hj0s2jl948zr4egq0jqhm3mrr](https://njump.me/npub1nvcezhw3gze5waxtvrzzls8qzhvqpn087hj0s2jl948zr4egq0jqhm3mrr)
- 🐦 Twitter: [@LucianoBarak](https://twitter.com/LucianoBarak)
- 📺 YouTube: [@lucianocasalunga](https://youtube.com/@lucianocasalunga)
- 📧 Email: luciano.casalunga@gmail.com

---

## 🙏 Agradecimentos

- **OpenAI** - GPT-4o API
- **Nostr Community** - Protocolo descentralizado incrível
- **LNBits** - Infraestrutura Lightning Network
- **Comunidade LiberNet** - Feedback e suporte contínuo

---

## 💖 Apoie Sofia

Gostou da Sofia? Considere apoiar o desenvolvimento:

- ⚡ **Lightning:** Envie sats via [Sofia App](https://sofia.libernet.app)
- 💜 **Nostr Zaps:** Zap [@sofia@libernet.app](https://njump.me/sofia@libernet.app)
- ⭐ **GitHub Star:** Dê uma estrela neste repositório!
- 🐛 **Reporte Bugs:** Ajude melhorando a Sofia

---

<div align="center">

**Sofia** - A IA que entende Bitcoin, Nostr e liberdade digital 💜

*"Construída por humanos, para humanos, rodando em código aberto"*

[![LiberNet Ecosystem](https://img.shields.io/badge/LiberNet-Ecosystem-8B5CF6?style=for-the-badge)](https://libernet.app)

</div>
