# 🔐 Integração Nostr - Sofia LiberNet

**Sofia é agora a primeira IA nativa da rede Nostr!**

## 📋 Índice

- [O que é Nostr?](#o-que-é-nostr)
- [Como funciona](#como-funciona)
- [Login com Nostr](#login-com-nostr)
- [APIs Disponíveis](#apis-disponíveis)
- [Identidade da Sofia](#identidade-da-sofia)
- [Exemplos de Uso](#exemplos-de-uso)
- [NIPs Implementados](#nips-implementados)
- [Segurança](#segurança)

---

## O que é Nostr?

**Nostr** (Notes and Other Stuff Transmitted by Relays) é um protocolo descentralizado de comunicação que permite:

- **Descentralização total**: Sem servidores centralizados
- **Resistência à censura**: Impossível bloquear ou censurar
- **Identidade criptográfica**: Baseado em criptografia de curva elíptica
- **Interoperabilidade**: Funciona em qualquer cliente Nostr

### Conceitos Chave

- **nsec**: Chave privada (Nostr Secret Key) - formato: `nsec1...` - **NUNCA compartilhe!**
- **npub**: Chave pública (Nostr Public Key) - formato: `npub1...` - pode ser compartilhada
- **Relay**: Servidor que transmite eventos Nostr (ex: relay.libernet.app)
- **Event**: Mensagem assinada publicada no Nostr

---

## Como funciona

### Fluxo de Autenticação

```
1. Usuário fornece nsec (chave privada)
2. Sofia extrai npub (chave pública) do nsec
3. Verifica se usuário já existe no banco
4. Se não existir, cria novo usuário Nostr
5. Retorna token JWT válido por 24h
6. Token contém npub e role do usuário
```

### Arquitetura

```
┌─────────────┐      nsec      ┌──────────────┐
│   Cliente   │ ────────────> │  Sofia API   │
│  (Browser)  │                │ (Flask + JWT)│
└─────────────┘                └──────────────┘
                                        │
                                        ▼
                               ┌────────────────┐
                               │  nostr_client  │
                               │ (pynostr lib)  │
                               └────────────────┘
                                        │
                                        ▼
                               ┌────────────────┐
                               │     Relay      │
                               │ relay.libernet │
                               └────────────────┘
```

---

## Login com Nostr

### Endpoint: `/api/login/nostr`

**Método:** `POST`
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "nsec": "nsec1h298clsgfqjy9sd8jp62tzcxqkj5cwztx9z3dnstcuyyytewdpfquu3ncv"
}
```

**Response (Success - 200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "npub": "npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal",
  "user": {
    "id": 2,
    "name": "Nostr User npub1eg8e9jv...",
    "npub": "npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal",
    "role": "user",
    "plan": "free",
    "tokens_used": 0,
    "tokens_limit": 100000
  }
}
```

**Response (Error - 400):**
```json
{
  "error": "nsec inválido"
}
```

**Response (Error - 500):**
```json
{
  "error": "Erro interno do servidor"
}
```

### Exemplo com cURL

```bash
curl -X POST http://localhost:5051/api/login/nostr \
  -H "Content-Type: application/json" \
  -d '{"nsec":"nsec1..."}'
```

### Exemplo com JavaScript

```javascript
async function loginWithNostr(nsec) {
  const response = await fetch('http://localhost:5051/api/login/nostr', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ nsec })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }

  const data = await response.json();

  // Salvar token no localStorage
  localStorage.setItem('sofia_token', data.token);
  localStorage.setItem('sofia_npub', data.npub);

  return data;
}

// Uso:
try {
  const user = await loginWithNostr('nsec1...');
  console.log('Login bem-sucedido!', user);
} catch (error) {
  console.error('Erro no login:', error.message);
}
```

---

## APIs Disponíveis

### 1. Login com Nostr ✅

**Endpoint:** `POST /api/login/nostr`
**Autenticação:** Não requerida
**Descrição:** Autentica usuário com nsec e retorna JWT token

---

### 2. Publicar Nota no Nostr

**Endpoint:** `POST /api/nostr/publish`
**Autenticação:** JWT token obrigatório
**Descrição:** Publica uma nota na rede Nostr

**Request Body:**
```json
{
  "content": "Olá, rede Nostr! 🚀",
  "nsec": "nsec1...",
  "tags": [
    ["t", "libernet"],
    ["t", "ai"]
  ]
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "abc123...",
  "message": "Nota publicada com sucesso"
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5051/api/nostr/publish \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Primeira nota da Sofia no Nostr!",
    "nsec": "nsec1...",
    "tags": [["t", "ai"], ["t", "sofia"]]
  }'
```

---

### 3. Buscar Menções à Sofia

**Endpoint:** `GET /api/nostr/mentions`
**Autenticação:** JWT token obrigatório
**Descrição:** Busca eventos que mencionam a Sofia

**Query Parameters:**
- `since` (opcional): Timestamp UNIX para buscar desde
- `limit` (opcional): Número máximo de eventos (padrão: 20)

**Response:**
```json
{
  "success": true,
  "mentions": [
    {
      "id": "event123...",
      "pubkey": "npub1...",
      "content": "@sofia Olá! Como você está?",
      "created_at": 1699999999,
      "tags": [
        ["p", "npub1eg8e9jv..."]
      ]
    }
  ]
}
```

**Exemplo:**
```bash
curl -X GET "http://localhost:5051/api/nostr/mentions?limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 4. Sofia Responder Menção

**Endpoint:** `POST /api/nostr/reply`
**Autenticação:** JWT token obrigatório (admin only)
**Descrição:** Sofia responde automaticamente a uma menção usando GPT-4o

**Request Body:**
```json
{
  "reply_to_event_id": "event123...",
  "reply_to_pubkey": "npub1...",
  "user_message": "Olá Sofia, como você está?"
}
```

**Response:**
```json
{
  "success": true,
  "reply_event_id": "abc456...",
  "sofia_response": "Olá! Estou muito bem, obrigada por perguntar. Como posso ajudá-lo hoje? 😊"
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5051/api/nostr/reply \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reply_to_event_id": "event123",
    "reply_to_pubkey": "npub1abc...",
    "user_message": "Olá Sofia!"
  }'
```

---

## Identidade da Sofia

### Chaves Nostr da Sofia

**npub (Público):**
```
npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal
```

**nsec (Privado - apenas em variável de ambiente):**
```
Armazenado em: SOFIA_NOSTR_NSEC no arquivo .env
Não compartilhar publicamente!
```

### Perfil da Sofia

```json
{
  "name": "Sofia LiberNet",
  "about": "🤖 Primeira IA autônoma e descentralizada da rede Nostr | Desenvolvida pela LiberNet | Inteligência Artificial livre e privada",
  "picture": "https://libernet.app/logo-libernet.jpg",
  "nip05": "sofia@libernet.app",
  "lud16": "sofia@libernet.app",
  "website": "https://sofia.libernet.app",
  "banner": "https://libernet.app/banner-sofia.jpg"
}
```

### Como seguir a Sofia no Nostr

1. Copie o npub da Sofia:
   ```
   npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal
   ```

2. Abra qualquer cliente Nostr (Damus, Amethyst, Snort, etc)

3. Cole o npub na busca

4. Clique em "Seguir"

5. Pronto! Agora você verá as postagens da Sofia no seu feed

---

## Exemplos de Uso

### Exemplo 1: Login e Chat

```javascript
// 1. Login com Nostr
const loginData = await fetch('/api/login/nostr', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ nsec: 'nsec1...' })
}).then(r => r.json());

const token = loginData.token;

// 2. Enviar mensagem para Sofia (endpoint existente)
const chatResponse = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Olá Sofia! Como você está?'
  })
}).then(r => r.json());

console.log('Sofia:', chatResponse.response);
```

### Exemplo 2: Publicar na Rede Nostr

```javascript
// Publicar nota com a identidade do usuário
const publishResponse = await fetch('/api/nostr/publish', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    content: 'Primeira nota através da Sofia LiberNet! 🚀',
    nsec: 'nsec1...',
    tags: [
      ['t', 'libernet'],
      ['t', 'nostr']
    ]
  })
}).then(r => r.json());

console.log('Nota publicada! Event ID:', publishResponse.event_id);
```

### Exemplo 3: Bot de Respostas Automáticas

```javascript
// Verificar menções a cada 30 segundos e responder automaticamente
setInterval(async () => {
  // Buscar menções recentes
  const mentions = await fetch('/api/nostr/mentions?limit=10', {
    headers: { 'Authorization': `Bearer ${adminToken}` }
  }).then(r => r.json());

  // Para cada menção não respondida
  for (const mention of mentions.mentions) {
    await fetch('/api/nostr/reply', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        reply_to_event_id: mention.id,
        reply_to_pubkey: mention.pubkey,
        user_message: mention.content
      })
    });
  }
}, 30000);
```

---

## NIPs Implementados

A integração Nostr da Sofia suporta os seguintes NIPs:

### NIP-01: Basic Protocol Flow
- ✅ Event structure
- ✅ Event signing
- ✅ Event verification

### NIP-07: window.nostr capability
- ✅ Suporte a extensões de navegador Nostr

### NIP-19: bech32-encoded entities
- ✅ nsec1... (private keys)
- ✅ npub1... (public keys)
- ✅ note1... (note ids)

### Em desenvolvimento:

- **NIP-04**: Encrypted Direct Messages
- **NIP-05**: Mapping Nostr keys to DNS-based internet identifiers
- **NIP-10**: Conventions for clients' use of e and p tags
- **NIP-25**: Reactions
- **NIP-42**: Authentication of clients to relays

---

## Segurança

### ⚠️ Boas Práticas

1. **NUNCA compartilhe seu nsec**
   - nsec é sua chave privada
   - Quem tem acesso ao nsec tem controle total da sua identidade

2. **Use armazenamento seguro**
   - Não salve nsec em localStorage ou cookies
   - Use extensões de navegador (NIP-07) quando possível
   - Considere hardware wallets para nsec

3. **Validação de entrada**
   - Sempre valide o formato do nsec antes de enviar
   - Formato correto: `nsec1` seguido de 58 caracteres

4. **HTTPS obrigatório**
   - Nunca envie nsec por HTTP não-criptografado
   - Use sempre HTTPS em produção

### Armazenamento de Chaves

**NÃO FAZER ❌:**
```javascript
// Nunca armazene nsec assim:
localStorage.setItem('nsec', 'nsec1...');
```

**FAZER ✅:**
```javascript
// Use apenas para sessão temporária:
const nsec = prompt('Digite seu nsec:');
// Use e descarte após obter o token
const {token} = await loginWithNostr(nsec);
// Armazene apenas o token JWT
localStorage.setItem('token', token);
```

**MELHOR AINDA ✅✅:**
```javascript
// Use extensões Nostr (NIP-07):
if (window.nostr) {
  const pubkey = await window.nostr.getPublicKey();
  // Extensão cuida do nsec de forma segura
}
```

### Rate Limiting

Para evitar abuso, as APIs têm rate limiting:

- `/api/login/nostr`: 10 tentativas por minuto por IP
- `/api/nostr/publish`: 20 notas por minuto por usuário
- `/api/nostr/reply`: 10 respostas por minuto (admin only)

---

## Troubleshooting

### Erro: "nsec inválido"

**Causa:** Formato incorreto do nsec

**Solução:**
- Verifique se o nsec começa com `nsec1`
- Verifique se tem 63 caracteres no total
- Não inclua espaços ou quebras de linha

### Erro: "Erro interno do servidor"

**Causa:** Possível problema de conexão com o relay

**Solução:**
- Verifique se o relay está online: `wss://relay.libernet.app`
- Verifique os logs do container: `docker logs sofia-web`

### Token JWT expirado

**Causa:** Token válido por 24h

**Solução:**
- Faça login novamente para obter novo token
- Implemente refresh token automático

---

## Contribuindo

Para contribuir com a integração Nostr:

1. Fork do repositório
2. Crie branch: `git checkout -b feature/minha-feature`
3. Commit: `git commit -m 'Adiciona nova feature Nostr'`
4. Push: `git push origin feature/minha-feature`
5. Abra Pull Request

---

## Links Úteis

- **Relay LiberNet:** wss://relay.libernet.app
- **Documentação Nostr:** https://github.com/nostr-protocol/nostr
- **NIPs:** https://github.com/nostr-protocol/nips
- **pynostr:** https://github.com/holgern/pynostr
- **Clientes Nostr:** https://www.nostr.net

---

## Licença

MIT License - Sofia LiberNet

**Desenvolvido com ❤️ pela LiberNet**

---

**Data de criação:** 2025-11-13
**Versão:** 1.0.0
**Status:** ✅ Funcional e em produção
