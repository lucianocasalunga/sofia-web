# 🚀 Sofia Nostr - Quick Start

Sofia agora está **ONLINE** e é a **primeira IA nativa do Nostr!**

## 🌐 Acesse Online

**URL:** https://sofia.libernet.app

---

## 🔑 Login com Nostr (nsec)

### Passo 1: Obter suas chaves Nostr

Se você ainda não tem, gere suas chaves em:
- https://nostr.how/en/guides/setup-keys
- Ou em qualquer cliente Nostr (Damus, Amethyst, Snort, etc)

**Importante:** Você vai precisar do seu **nsec** (chave privada)
- Formato: `nsec1...` (63 caracteres)
- **NUNCA compartilhe seu nsec com ninguém!**

### Passo 2: Login via API

```bash
curl -X POST https://sofia.libernet.app/api/login/nostr \
  -H "Content-Type: application/json" \
  -d '{"nsec":"SEU_NSEC_AQUI"}'
```

**Resposta:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "npub": "npub1...",
  "user": {
    "id": 1,
    "name": "Nostr User npub1...",
    "plan": "free",
    "tokens_limit": 100000
  }
}
```

### Passo 3: Conversar com Sofia

```bash
TOKEN="seu_token_aqui"

curl -X POST https://sofia.libernet.app/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Olá Sofia! Como você está?"}'
```

---

## 🔗 Seguir Sofia no Nostr

### npub da Sofia:
```
npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal
```

### Como seguir:

1. Abra qualquer cliente Nostr
2. Busque pelo npub da Sofia
3. Clique em "Seguir"
4. Pronto! 🎉

**Clientes recomendados:**
- **iOS:** Damus
- **Android:** Amethyst
- **Web:** Snort.social, Iris.to, Nostrudel

---

## 💡 Exemplo JavaScript

```javascript
// 1. Login com Nostr
const loginResponse = await fetch('https://sofia.libernet.app/api/login/nostr', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ nsec: 'nsec1...' })
});

const { token, npub, user } = await loginResponse.json();
console.log('✅ Logado como:', npub);

// 2. Conversar com Sofia
const chatResponse = await fetch('https://sofia.libernet.app/api/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Olá Sofia! Me explique o que é Nostr?'
  })
});

const chatData = await chatResponse.json();
console.log('Sofia:', chatData.response);
```

---

## 📊 Recursos Disponíveis

### APIs Públicas:

1. **POST /api/login/nostr**
   - Login com nsec
   - Retorna token JWT válido por 24h

2. **POST /api/chat**
   - Conversar com Sofia (GPT-4o)
   - Requer autenticação JWT

3. **POST /api/nostr/publish**
   - Publicar nota no Nostr
   - Requer autenticação JWT + nsec

4. **GET /api/nostr/mentions**
   - Buscar menções à Sofia
   - Requer autenticação JWT

5. **GET /api/health**
   - Health check (público)
   - Verifica se nostr_enabled: true

### Planos Disponíveis:

- **Free:** 100k tokens/mês - Grátis
- **Light:** 500k tokens/mês - 2.600 sats (~R$ 6)
- **Standard:** 2M tokens/mês - 10.000 sats (~R$ 23)
- **Pro:** 10M tokens/mês - 50.000 sats (~R$ 115)

---

## 🔐 Segurança

### ⚠️ Importante:

1. **NUNCA compartilhe seu nsec**
2. Use HTTPS sempre (http**s**://sofia.libernet.app)
3. Não armazene nsec em localStorage/cookies
4. Armazene apenas o token JWT (expira em 24h)

### Boas Práticas:

```javascript
// ❌ NÃO FAZER:
localStorage.setItem('nsec', 'nsec1...');

// ✅ FAZER:
const nsec = prompt('Digite seu nsec:');
const {token} = await loginWithNostr(nsec);
// Use o token e descarte o nsec
localStorage.setItem('sofia_token', token);
```

---

## 📚 Documentação Completa

Para documentação detalhada, veja:
- `/mnt/projetos/sofia-web/NOSTR_INTEGRATION.md`

Ou acesse online:
- https://sofia.libernet.app/docs (em breve)

---

## 🐛 Problemas?

### Erro: "nsec inválido"
- Verifique se o nsec começa com `nsec1`
- Verifique se tem 63 caracteres no total

### Erro: "Token expirado"
- Tokens JWT expiram em 24h
- Faça login novamente para obter novo token

### Outros problemas:
- Verifique https://sofia.libernet.app/api/health
- Se `nostr_enabled: false`, aguarde reinicialização

---

## 🌟 Exemplo Completo

```bash
# 1. Gerar chaves de teste (não use em produção!)
docker exec sofia-web python3 -c "
from pynostr.key import PrivateKey
pk = PrivateKey()
print(f'nsec: {pk.bech32()}')
print(f'npub: {pk.public_key.bech32()}')
"

# 2. Login
LOGIN=$(curl -s -X POST https://sofia.libernet.app/api/login/nostr \
  -H "Content-Type: application/json" \
  -d '{"nsec":"nsec1..."}')

TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 3. Chat
curl -s -X POST https://sofia.libernet.app/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Olá Sofia!"}' | python3 -m json.tool
```

---

## 🎉 Sofia é a primeira IA do Nostr!

**Desenvolvido pela LiberNet**
**Data:** 2025-11-13
**Status:** 🟢 Online e funcional

---

**Links:**
- Website: https://sofia.libernet.app
- Relay: wss://relay.libernet.app
- npub: npub1eg8e9jvysdkvhxu9sne2e2zl77qymd2fauuh64jwqh8zhe9dyk2qyl2hal

🤖 **Bem-vindo à era da IA descentralizada!**
