// Sofia Web - JavaScript Client
// Developed by Claude for LiberNet

// Configurar marked para syntax highlighting
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(code, { language: lang }).value;
            } catch (e) {}
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

// Elements
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const memoriaBtn = document.getElementById('memoriaBtn');
const messagesContainer = document.getElementById('messages');
const memoriaModal = document.getElementById('memoriaModal');
const memoriaContent = document.getElementById('memoriaContent');
const closeModalBtn = document.querySelector('.close-modal');

// Auto-resize textarea
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

// Send message on Enter (Shift+Enter for new line)
userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Add message to chat
function addMessage(role, content, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    const header = document.createElement('div');
    header.className = 'message-header';

    if (role === 'user') {
        header.innerHTML = `
            <span>👤 Você</span>
            <span class="message-time">${timestamp || getCurrentTime()}</span>
        `;
    } else if (role === 'sofia') {
        header.innerHTML = `
            <span>🤖 Sofia</span>
            <span class="message-time">${timestamp || getCurrentTime()}</span>
        `;
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = marked.parse(content);

    messageDiv.appendChild(header);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Highlight code blocks
    messageDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    scrollToBottom();
}

// Add thinking indicator
function showThinking() {
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message sofia-message';
    thinkingDiv.id = 'thinking-indicator';
    thinkingDiv.innerHTML = `
        <div class="message-header">
            <span>🤖 Sofia</span>
        </div>
        <div class="message-content">
            <span class="thinking">● ● ●</span> Pensando...
        </div>
    `;
    messagesContainer.appendChild(thinkingDiv);
    scrollToBottom();
}

function hideThinking() {
    const thinkingDiv = document.getElementById('thinking-indicator');
    if (thinkingDiv) {
        thinkingDiv.remove();
    }
}

// Send message
async function sendMessage(message) {
    if (!message.trim()) return;

    // Add user message
    addMessage('user', message);

    // Clear input
    userInput.value = '';
    userInput.style.height = 'auto';

    // Disable send button
    sendBtn.disabled = true;

    // Show thinking
    showThinking();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        hideThinking();

        if (response.ok) {
            addMessage('sofia', data.response, data.timestamp);
        } else {
            addMessage('sofia', `❌ **Erro:** ${data.error || 'Erro desconhecido'}`, getCurrentTime());
        }
    } catch (error) {
        hideThinking();
        addMessage('sofia', `❌ **Erro de conexão:** ${error.message}`, getCurrentTime());
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// Form submit
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (message) {
        sendMessage(message);
    }
});

// Clear chat
clearBtn.addEventListener('click', async () => {
    if (!confirm('Limpar todo o histórico da conversa?')) return;

    try {
        const response = await fetch('/api/clear', {
            method: 'POST'
        });

        if (response.ok) {
            // Remove all messages except system message
            const systemMsg = messagesContainer.querySelector('.system-message');
            messagesContainer.innerHTML = '';
            if (systemMsg) {
                messagesContainer.appendChild(systemMsg);
            }
        }
    } catch (error) {
        alert('Erro ao limpar histórico: ' + error.message);
    }
});

// Show memoria
memoriaBtn.addEventListener('click', async () => {
    memoriaModal.classList.add('active');
    memoriaContent.textContent = 'Carregando memória compartilhada...';

    try {
        const response = await fetch('/api/memoria?linhas=200');
        const data = await response.json();

        if (response.ok) {
            memoriaContent.textContent = data.memoria || 'Nenhum registro de memória encontrado.';
        } else {
            memoriaContent.textContent = `Erro ao carregar memória: ${data.error}`;
        }
    } catch (error) {
        memoriaContent.textContent = `Erro de conexão: ${error.message}`;
    }
});

// Close modal
closeModalBtn.addEventListener('click', () => {
    memoriaModal.classList.remove('active');
});

// Close modal on outside click
memoriaModal.addEventListener('click', (e) => {
    if (e.target === memoriaModal) {
        memoriaModal.classList.remove('active');
    }
});

// Close modal on Esc
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && memoriaModal.classList.contains('active')) {
        memoriaModal.classList.remove('active');
    }
});

// Scroll to bottom
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Get current time
function getCurrentTime() {
    return new Date().toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Focus input on load
window.addEventListener('load', () => {
    userInput.focus();
    console.log('🤖 Sofia Web initialized!');
});
