# 🤖 Sofia - IA Autônoma e Descentralizada

**Primeira inteligência artificial nativa da rede Nostr**

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![Nostr](https://img.shields.io/badge/nostr-native-purple.svg)]()
[![Model](https://img.shields.io/badge/model-GPT--4o-blue.svg)]()
[![Lightning](https://img.shields.io/badge/lightning-enabled-orange.svg)]()

---

## 🌟 Visão Geral

**Sofia** é uma inteligência artificial de código aberto que integra:
- 🔐 **Autenticação Nostr** (login com nsec ou extensão nos2x/Alby)
- 🧠 **GPT-4o** (modelo avançado com raciocínio superior)
- ⚡ **Pagamentos Lightning** (assinaturas em sats)
- 💾 **Memória persistente** (RAG + embeddings)
- 🎯 **Machine Learning** (aprende com interações)

**URL:** https://sofia.libernet.app

---

## ✨ Funcionalidades

### 🔑 Autenticação Descentralizada
- Login com **nsec** (chave privada Nostr)
- Login com **nos2x/Alby** (extensões de navegador)
- Autenticação **JWT** (tokens de 24h)
- Sem emails, sem senhas centralizadas
- **NIP-05:** sofia@libernet.app

### 🤖 Inteligência Artificial
- **Modelo:** GPT-4o (raciocínio avançado)
- **Modelo Mini:** GPT-4o-mini (respostas rápidas)
- Personalidade autêntica e natural
- Opiniões próprias sobre temas complexos
- Conversas fluidas e contextuais

### 💬 Sistema de Chat
- Múltiplas conversas simultâneas
- Histórico persistente por conversa
- Organização em **Projetos** (pastas)
- Renomear, arquivar e deletar conversas
- Interface responsiva (desktop + mobile)

### 🧠 Machine Learning
- **RAG (Retrieval Augmented Generation):** busca contexto relevante
- **Embeddings:** vetorização de conversas
- **Sistema de preferências:** aprende com o usuário
- **Feedback:** rating de respostas (1-5 estrelas)
- **Analytics:** métricas de uso e efetividade

### ⚡ Planos e Pagamentos
- **Free:** 100.000 tokens
- **Light:** 500.000 tokens - 2.600 sats
- **Standard:** 2.000.000 tokens - 10.000 sats
- **Pro:** 10.000.000 tokens - 50.000 sats
- Pagamentos via **LNBits** e **OpenNode**

### 🎨 Interface Moderna
- Design minimalista estilo Apple
- Modo claro / escuro / automático (segue sistema)
- PWA (instalável como app)
- Ícones Lucide (Apple-style)
- Responsivo mobile-first

---

## 🛠️ Tecnologias

### Backend
- **Python 3.12** + Flask
- **SQLite** (3 bancos: users, chats, ML)
- **OpenAI API** (GPT-4o)
- **nostr-sdk** (integração Nostr)
- **LNBits + OpenNode** (pagamentos)
- **numpy** (embeddings)
- **Gunicorn** (WSGI server)

### Frontend
- **JavaScript Vanilla** (sem frameworks)
- **CSS moderno** (variáveis, grid, flexbox)
- **NIP-07** (window.nostr)
- **PWA** (service worker, manifest)

### Infraestrutura
- **Docker** + **Docker Compose**
- **Caddy** (reverse proxy HTTPS)
- **Cloudflare** (CDN + proteção)

---

## 🚀 Instalação

### Pré-requisitos
- Docker 20.10+
- Docker Compose 2.0+
- Conta OpenAI (API key)
- Conta LNBits (opcional - para pagamentos)

### Passos

1. **Clone o repositório:**
```bash
git clone https://github.com/lucianocasalunga/sofia-web.git
cd sofia-web
```

2. **Configure variáveis de ambiente:**
```bash
cp .env.example .env
nano .env
```

Edite o `.env`:
```env
OPENAI_API_KEY=sk-...
LNBITS_URL=https://lnbits.libernet.app
LNBITS_INVOICE_KEY=...
OPENNODE_API_KEY=...
SECRET_KEY=sua_chave_secreta_aqui
SOFIA_NSEC=nsec1...
SOFIA_NPUB=npub1eg8e9jvysdkvh...
```

3. **Inicie os containers:**
```bash
docker-compose up -d
```

4. **Acesse a aplicação:**
```
http://localhost:5051
```

---

## 📊 NIPs Implementados

### ✅ Implementados
- **NIP-01**: Basic Protocol (eventos Nostr)
- **NIP-07**: window.nostr (extensões)
- **NIP-19**: bech32 encoding (npub/nsec)

### 🔄 Planejados
- **NIP-04**: DMs encriptadas
- **NIP-46**: Nostr Connect (remote signing)
- **NIP-57**: Lightning Zaps

---

## 👤 Autor

**Luciano Barak Casalunga**
- GitHub: [@lucianocasalunga](https://github.com/lucianocasalunga)
- Nostr: npub1nvcezhw3gze5waxtvrzzls8qzhvqpn087hj0s2jl948zr4egq0jqhm3mrr
- NIP-05: barak@libernet.app

**Sofia no Nostr:**
- Nostr: npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal
- NIP-05: sofia@libernet.app
- Lightning: sofia@libernet.app

---

## 🌐 Ecossistema LiberNet

**Sofia** faz parte do ecossistema **LiberNet**:
- 🤖 [Sofia](https://sofia.libernet.app) - IA descentralizada
- 📡 [Relay](https://relay.libernet.app) - Relay Nostr
- 🎥 [LiberMedia](https://media.libernet.app) - Hospedagem de arquivos
- 🌐 [LiberNet](https://libernet.app) - Portal principal

---

**Feito com ❤️ e Nostr**
