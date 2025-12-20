// Sofia Chat - Main JavaScript
// Version: 2025-11-17 - Separated from HTML for performance

// ===== AUTH =====
function getAuthHeaders() {
    const token = localStorage.getItem('sofia_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

function checkAuth() {
    const token = localStorage.getItem('sofia_token');
    console.log('[CHAT DEBUG] checkAuth - token exists:', !!token);

    if (token) {
        // Usuário Nostr - buscar dados do localStorage
        const storedUser = localStorage.getItem('sofia_user');
        console.log('[CHAT DEBUG] storedUser raw:', storedUser);

        if (storedUser) {
            const user = JSON.parse(storedUser);
            console.log('[CHAT DEBUG] User parsed:', user);
            console.log('[CHAT DEBUG] User name:', user.name);
            console.log('[CHAT DEBUG] User picture:', user.picture);

            const initial = user.name ? user.name[0] : 'N';
            console.log('[CHAT DEBUG] Calling updateUserUI with:', { initial, name: user.name, picture: user.picture });
            updateUserUI(initial, user.name || 'Nostr User', user.picture || null);
        } else {
            console.log('[CHAT DEBUG] No storedUser, usando npub');
            const npub = localStorage.getItem('sofia_npub');
            if (npub) {
                updateUserUI(npub.substring(5, 6).toUpperCase(), npub.substring(0, 16) + '...', null);
            }
        }
        return true;
    }

    // Se não tem token JWT, verificar se é usuário tradicional via template
    // Este bloco será preenchido pelo backend (Flask)
    if (window.sofiaUser) {
        updateUserUI(window.sofiaUser.initial, window.sofiaUser.name, null);
        localStorage.setItem('sofia_user', JSON.stringify({
            id: window.sofiaUser.id,
            name: window.sofiaUser.name
        }));
        return true;
    }

    window.location.href = '/login';
    return false;
}

function updateUserUI(initial, name, picture = null) {
    console.log('[CHAT DEBUG] updateUserUI called:', { initial, name, picture });

    const avatarEl = document.getElementById('user-avatar');
    console.log('[CHAT DEBUG] Avatar element:', avatarEl);

    // Se tiver foto do perfil Nostr, mostrar imagem
    if (picture) {
        console.log('[CHAT DEBUG] Setting avatar image:', picture);
        avatarEl.innerHTML = `<img src="${picture}" alt="${name}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
    } else {
        // Senão, mostrar inicial
        console.log('[CHAT DEBUG] Setting avatar initial:', initial);
        avatarEl.textContent = initial.toUpperCase();
    }

    const nameEl = document.getElementById('user-name');
    console.log('[CHAT DEBUG] Name element:', nameEl);
    nameEl.textContent = name;
    console.log('[CHAT DEBUG] updateUserUI completed');
}

// ===== STATE =====
let currentChatId = null;
let currentModel = localStorage.getItem('selectedModel') || 'gpt-5'; // Sofia 5.0 por padrão
let chats = [];
let selectedImage = null;
let renamingChatId = null;

// ===== UI =====
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('sidebar-overlay').classList.toggle('active');
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('active');
}

function toggleTheme() {
    const body = document.body;
    const currentTheme = localStorage.getItem('theme') || 'auto';
    let newTheme;

    if (currentTheme === 'auto') {
        newTheme = 'light';
        body.classList.add('light-theme');
        body.classList.remove('dark-theme');
    } else if (currentTheme === 'light') {
        newTheme = 'dark';
        body.classList.add('dark-theme');
        body.classList.remove('light-theme');
    } else {
        newTheme = 'auto';
        body.classList.remove('light-theme', 'dark-theme');
    }

    localStorage.setItem('theme', newTheme);
}

function applyTheme() {
    const theme = localStorage.getItem('theme') || 'auto';
    const body = document.body;

    // Get highlight.js theme stylesheets
    const hljsLight = document.getElementById('hljs-light');
    const hljsDark = document.getElementById('hljs-dark');

    if (theme === 'light') {
        body.classList.add('light-theme');
        body.classList.remove('dark-theme');
        // Enable light syntax highlighting
        if (hljsLight) hljsLight.disabled = false;
        if (hljsDark) hljsDark.disabled = true;
    } else if (theme === 'dark') {
        body.classList.add('dark-theme');
        body.classList.remove('light-theme');
        // Enable dark syntax highlighting
        if (hljsLight) hljsLight.disabled = true;
        if (hljsDark) hljsDark.disabled = false;
    } else {
        // Auto mode: follow system preference
        body.classList.remove('light-theme', 'dark-theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (hljsLight) hljsLight.disabled = prefersDark;
        if (hljsDark) hljsDark.disabled = !prefersDark;
    }
}

// ===== MESSAGES =====
function addMessage(text, sender, skipScroll = false) {
    const messagesContainer = document.getElementById('messages');
    const welcome = messagesContainer.querySelector('.welcome');
    if (welcome) welcome.remove();

    const msg = document.createElement('div');
    msg.className = `message ${sender}`;

    const avatar = sender === 'user'
        ? document.getElementById('user-avatar').textContent
        : '<img src="/static/logo-sofia.png" alt="Sofia">';

    // Para mensagens da Sofia, renderizar markdown
    // Para mensagens do usuário, manter como texto simples
    const content = sender === 'sofia' ? renderMarkdown(text) : escapeHtml(text);

    msg.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-bubble">${content}</div>
    `;
    messagesContainer.appendChild(msg);

    // Adicionar botões de cópia para blocos de código
    if (sender === 'sofia') {
        addCopyButtons(msg);
        // Aplicar syntax highlighting (apenas se hljs estiver disponível)
        if (typeof hljs !== 'undefined') {
            msg.querySelectorAll('pre code').forEach((block) => {
                try {
                    hljs.highlightElement(block);
                } catch (e) {
                    console.warn('[Sofia] Erro ao aplicar syntax highlighting:', e);
                }
            });
        }
    }

    // Só faz scroll se não foi pedido para pular
    if (!skipScroll) {
        scrollToBottom();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    // Configurar marked.js para parsing seguro
    const markedOptions = {
        breaks: true,
        gfm: true,
        sanitize: false, // Não sanitize pois já confiamos na Sofia
        headerIds: false,
        mangle: false
    };

    // Adicionar highlight apenas se hljs estiver disponível
    if (typeof hljs !== 'undefined') {
        markedOptions.highlight = function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (e) {
                    console.warn('[Sofia] Erro no highlight:', e);
                }
            }
            try {
                return hljs.highlightAuto(code).value;
            } catch (e) {
                console.warn('[Sofia] Erro no highlightAuto:', e);
                return code;
            }
        };
    }

    marked.setOptions(markedOptions);

    // Parse markdown para HTML
    return marked.parse(text);
}

function addCopyButtons(messageElement) {
    const codeBlocks = messageElement.querySelectorAll('pre');
    codeBlocks.forEach((pre) => {
        const button = document.createElement('button');
        button.className = 'copy-button';
        button.textContent = 'Copiar';
        button.onclick = () => copyToClipboard(pre, button);
        pre.appendChild(button);
    });
}

async function copyToClipboard(pre, button) {
    const code = pre.querySelector('code');
    const text = code ? code.textContent : pre.textContent;

    try {
        await navigator.clipboard.writeText(text);
        const originalText = button.textContent;
        button.textContent = '✓ Copiado!';
        button.classList.add('copied');

        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Erro ao copiar:', err);
        button.textContent = '✗ Erro';
        setTimeout(() => {
            button.textContent = 'Copiar';
        }, 2000);
    }
}

function addTyping() {
    const msg = document.createElement('div');
    msg.id = 'typing';
    msg.className = 'message sofia';
    msg.innerHTML = `
        <div class="message-avatar">
            <img src="/static/logo-sofia.png" alt="Sofia">
        </div>
        <div class="message-bubble">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    document.getElementById('messages').appendChild(msg);
    scrollToBottom();
}

function removeTyping() {
    const typing = document.getElementById('typing');
    if (typing) typing.remove();
}

function scrollToBottom() {
    // MOBILE-FIRST: Usar window scroll ao invés de container
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        // Mobile: scroll da janela
        requestAnimationFrame(() => {
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
        });
    } else {
        // Desktop: scroll do container
        const container = document.getElementById('chat-container');
        if (container) {
            requestAnimationFrame(() => {
                container.scrollTop = container.scrollHeight;
            });
        }
    }
}

function handleScrollToBottomButton() {
    const scrollBtn = document.getElementById('scroll-to-bottom');
    if (!scrollBtn) return;

    const isMobile = window.innerWidth < 768;
    const threshold = 100; // Show button if more than 100px from bottom

    let isNearBottom = false;

    if (isMobile) {
        // Mobile: check window scroll
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollHeight = document.body.scrollHeight;
        const clientHeight = window.innerHeight;
        isNearBottom = (scrollHeight - scrollTop - clientHeight) < threshold;
    } else {
        // Desktop: check container scroll
        const container = document.getElementById('chat-container');
        if (container) {
            const scrollTop = container.scrollTop;
            const scrollHeight = container.scrollHeight;
            const clientHeight = container.clientHeight;
            isNearBottom = (scrollHeight - scrollTop - clientHeight) < threshold;
        }
    }

    // Show button if NOT near bottom, hide if near bottom
    scrollBtn.style.display = isNearBottom ? 'none' : 'flex';
}

// ===== SEND MESSAGE =====
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text && !selectedImage) return;

    if (!currentChatId) {
        await createNewChat();
        if (!currentChatId) return;
    }

    // Pegar modelo selecionado atual
    const modelToUse = localStorage.getItem('selectedModel') || 'gpt-5';

    // CAPTURAR O ID DO CHAT NO MOMENTO DO ENVIO (fix race condition)
    const chatIdWhenSent = currentChatId;

    addMessage(text || '📷 Imagem', 'user');
    const imageToSend = selectedImage;
    messageInput.value = '';
    messageInput.style.height = 'auto';
    selectedImage = null;
    document.getElementById('sendBtn').disabled = true;
    addTyping();

    try {
        let response;
        if (imageToSend) {
            const formData = new FormData();
            formData.append('message', text || 'Analise esta imagem');
            formData.append('model', modelToUse);
            formData.append('image', imageToSend);
            const headers = getAuthHeaders();
            delete headers['Content-Type'];
            response = await fetch(`/api/chats/${chatIdWhenSent}/message`, {
                method: 'POST',
                headers: headers,
                body: formData,
                credentials: 'include'
            });
        } else {
            response = await fetch(`/api/chats/${chatIdWhenSent}/message`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ message: text, model: modelToUse }),
                credentials: 'include'
            });
        }

        const data = await response.json();
        removeTyping();

        // VERIFICAR SE O USUÁRIO NÃO TROCOU DE CHAT enquanto aguardava resposta (fix race condition)
        if (currentChatId !== chatIdWhenSent) {
            console.warn('Chat mudou durante o envio. Resposta descartada para evitar confusão.', {
                chatIdWhenSent,
                currentChatId
            });
            return; // Descartar resposta
        }

        if (data.content) {
            addMessage(data.content, 'sofia');

            // Auto-renomear conversa se ainda tiver nome padrão
            const currentTitle = document.getElementById('chat-title').textContent;
            if (currentTitle === 'Nova Conversa' && text) {
                // Pegar primeiras palavras (máximo 50 caracteres)
                const newName = text.substring(0, 50).trim();
                try {
                    await fetch(`/api/chats/${chatIdWhenSent}`, {
                        method: 'PATCH',
                        headers: getAuthHeaders(),
                        body: JSON.stringify({ name: newName }),
                        credentials: 'include'
                    });
                    document.getElementById('chat-title').textContent = newName;
                } catch (err) {
                    console.error('Erro ao renomear automaticamente:', err);
                }
            }

            await loadChats();
            await loadBalance();
        } else if (data.error) {
            addMessage('⚠️ ' + data.error, 'sofia');
        }
    } catch (error) {
        removeTyping();
        addMessage('Erro de conexão: ' + error.message, 'sofia');
    } finally {
        document.getElementById('sendBtn').disabled = false;
        messageInput.focus();
    }
}

// ===== IMAGE =====
function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
        alert('Por favor, selecione apenas arquivos de imagem');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        alert('Imagem muito grande. Tamanho máximo: 10MB');
        return;
    }
    selectedImage = file;
    event.target.value = '';
}

// ===== CHATS =====
async function createNewChat() {
    try {
        const response = await fetch('/api/chats', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name: 'Nova Conversa' }),
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            currentChatId = data.id;
            document.getElementById('messages').innerHTML = '';
            document.getElementById('chat-title').textContent = 'Nova Conversa';
            await loadChats();
            messageInput.focus();
            closeSidebar();
        }
    } catch (error) {
        console.error('Erro ao criar chat:', error);
    }
}

async function createChatInProject(projectId) {
    console.log('[PROJECT] Criando nova conversa no projeto ID:', projectId);
    try {
        // 1. Criar o chat
        const response = await fetch('/api/chats', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name: 'Nova Conversa' }),
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Falha ao criar chat');
        }

        const data = await response.json();
        const chatId = data.id;
        console.log('[PROJECT] Chat criado com ID:', chatId);

        // 2. Adicionar chat ao projeto NO SERVIDOR
        console.log('[PROJECT] Adicionando chat ao projeto no servidor...');
        const addResponse = await fetch(`/api/projects/${projectId}/chats`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ chat_id: chatId })
        });

        if (!addResponse.ok) {
            const error = await addResponse.json();
            console.error('[PROJECT] Erro ao adicionar ao projeto:', error);
            throw new Error(error.error || 'Erro ao adicionar ao projeto');
        }

        console.log('[PROJECT] Chat adicionado ao projeto com sucesso!');

        // 3. Recarregar projetos do servidor
        await loadProjects();

        // 4. Abrir o chat criado
        currentChatId = chatId;
        document.getElementById('messages').innerHTML = '';
        document.getElementById('chat-title').textContent = 'Nova Conversa';
        await loadChats();
        messageInput.focus();
        closeSidebar();

        alert('Conversa criada e adicionada ao projeto!');
    } catch (error) {
        console.error('[PROJECT] Erro ao criar chat no projeto:', error);
        alert('Erro ao criar chat no projeto: ' + error.message);
    }
}

async function loadChats() {
    try {
        const response = await fetch('/api/chats', {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        chats = await response.json() || [];
        updateRecentChats();
    } catch (error) {
        console.error('Erro ao carregar chats:', error);
    }
}

function updateRecentChats() {
    const container = document.getElementById('recent-chats');

    // Get all chat IDs that are in projects
    const projectChatIds = new Set();
    projects.forEach(project => {
        if (project.chatIds && Array.isArray(project.chatIds)) {
            project.chatIds.forEach(chatId => projectChatIds.add(chatId));
        }
    });

    // Filter out chats that are in projects
    const filteredChats = chats.filter(chat => !projectChatIds.has(chat.id));

    if (!filteredChats.length) {
        container.innerHTML = '<div style="padding: 12px 16px; color: var(--text-secondary); font-size: 13px;">Nenhuma conversa</div>';
        return;
    }

    container.innerHTML = filteredChats.slice(0, 10).map(chat => `
        <div class="chat-item ${currentChatId === chat.id ? 'active' : ''}" data-chat-id="${chat.id}">
            <div style="display: flex; align-items: center; flex: 1; gap: 8px;" onclick="loadChat(${chat.id})">
                <div class="chat-item-checkbox" onclick="event.stopPropagation(); toggleChatSelection(${chat.id}, this)" style="width: 20px; height: 20px; border: 2px solid var(--border-light); border-radius: 4px; cursor: pointer; transition: all 0.2s; flex-shrink: 0;"></div>
                <div class="chat-item-name" style="flex: 1;">${escapeHtml(chat.chat_name || 'Sem nome')}</div>
            </div>
            <div class="chat-item-menu" onclick="event.stopPropagation(); showChatContextMenu(event, ${chat.id})">⋯</div>
        </div>
    `).join('');
}

async function loadChat(chatId) {
    try {
        // BUGFIX #3: Remove imediatamente a classe .active de TODOS os itens de chat
        // para garantir que apenas UMA conversa fique marcada por vez
        document.querySelectorAll('.chat-item.active').forEach(item => {
            item.classList.remove('active');
        });

        const response = await fetch(`/api/chats/${chatId}`, {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        const data = await response.json();

        if (data.chat) {
            currentChatId = chatId;
            document.getElementById('messages').innerHTML = '';
            document.getElementById('chat-title').textContent = data.chat.chat_name || 'Conversa';

            // Adicionar todas as mensagens SEM fazer scroll
            data.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user' ? 'user' : 'sofia', true);
            });

            // Fazer scroll UMA ÚNICA VEZ no final
            scrollToBottom();

            updateRecentChats();
            renderProjects(); // Atualiza também os projetos para refletir seleção
            messageInput.focus();
            closeSidebar();
        }
    } catch (error) {
        console.error('Erro ao carregar chat:', error);
    }
}

// ===== RENAME MODAL =====
function openRenameModal(chatId) {
    renamingChatId = chatId;
    const chat = chats.find(c => c.id === chatId);
    const currentName = chat ? (chat.chat_name || 'Nova Conversa') : '';
    document.getElementById('rename-input').value = currentName;
    document.getElementById('rename-modal').classList.add('active');
    setTimeout(() => document.getElementById('rename-input').focus(), 300);
}

function closeRenameModal() {
    document.getElementById('rename-modal').classList.remove('active');
    renamingChatId = null;
}

async function saveRename() {
    const newName = document.getElementById('rename-input').value.trim();
    console.log('saveRename chamado:', { newName, renamingChatId });

    if (!newName) {
        alert('Por favor, digite um nome');
        return;
    }

    if (!renamingChatId) {
        alert('Erro: nenhum chat selecionado');
        return;
    }

    try {
        console.log('Enviando PATCH para:', `/api/chats/${renamingChatId}`);
        const headers = getAuthHeaders();
        console.log('Headers:', headers);
        console.log('Has token:', !!localStorage.getItem('sofia_token'));

        const response = await fetch(`/api/chats/${renamingChatId}`, {
            method: 'PATCH',
            headers: headers,
            body: JSON.stringify({ name: newName }),
            credentials: 'include'  // SEMPRE incluir cookies para Flask-Login funcionar
        });

        console.log('Response status:', response.status);

        if (response.ok) {
            if (currentChatId === renamingChatId) {
                document.getElementById('chat-title').textContent = newName;
            }
            await loadChats();
            closeRenameModal();
        } else {
            const errorText = await response.text();
            console.error('Erro response:', errorText);
            alert('Erro ao renomear: ' + response.status);
        }
    } catch (error) {
        console.error('Erro ao renomear:', error);
        alert('Erro de conexão: ' + error.message);
    }
}

// ===== CHAT SELECTION =====
function toggleChatSelection(chatId, checkboxEl) {
    const chatItem = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
    if (!chatItem) return;

    // Toggle selection
    const isSelected = chatItem.classList.contains('selected');

    // Desmarcar todas as outras conversas primeiro
    document.querySelectorAll('.chat-item.selected').forEach(item => {
        item.classList.remove('selected');
        const checkbox = item.querySelector('.chat-item-checkbox');
        if (checkbox) {
            checkbox.style.background = 'transparent';
            checkbox.innerHTML = '';
        }
    });

    if (!isSelected) {
        // Marcar esta conversa
        chatItem.classList.add('selected');
        checkboxEl.style.background = 'var(--accent)';
        checkboxEl.style.borderColor = 'var(--accent)';
        checkboxEl.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"><polyline points="20 6 9 17 4 12"></polyline></svg>';
        checkboxEl.style.position = 'relative';
    }
}

// Desmarcar ao clicar fora
document.addEventListener('click', (e) => {
    if (!e.target.closest('.chat-item') && !e.target.closest('.context-menu')) {
        document.querySelectorAll('.chat-item.selected').forEach(item => {
            item.classList.remove('selected');
            const checkbox = item.querySelector('.chat-item-checkbox');
            if (checkbox) {
                checkbox.style.background = 'transparent';
                checkbox.style.borderColor = 'var(--border-light)';
                checkbox.innerHTML = '';
            }
        });
    }
});

// ===== CONTEXT MENU =====
let contextMenuChatId = null;
let pendingDeleteChatId = null; // Guarda o ID para exclusão
let pendingMoveChatId = null; // Guarda o ID para mover
let menuIsOpen = false;

function showChatContextMenu(event, chatId) {
    event.stopPropagation();
    event.preventDefault();

    const menu = document.getElementById('chat-context-menu');

    // Se já está aberto, fechar
    if (menuIsOpen) {
        menu.style.display = 'none';
        menuIsOpen = false;
        contextMenuChatId = null;
        return;
    }

    // Abrir menu
    contextMenuChatId = chatId;
    menuIsOpen = true;

    // Posicionar menu
    const x = event.clientX || (event.touches && event.touches[0].clientX) || 0;
    const y = event.clientY || (event.touches && event.touches[0].clientY) || 0;

    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.style.display = 'block';
}

function closeContextMenu() {
    document.getElementById('chat-context-menu').style.display = 'none';
    contextMenuChatId = null;
    menuIsOpen = false;
}

function openRenameModalFromMenu() {
    // Salvar chatId ANTES de fechar menu (que apaga contextMenuChatId)
    const chatId = contextMenuChatId;
    closeContextMenu();

    if (chatId) {
        openRenameModal(chatId);
    }
}

function confirmDeleteChat() {
    console.log('[DELETE] confirmDeleteChat chamada, contextMenuChatId:', contextMenuChatId);
    // Salvar o ID ANTES de fechar o menu (que apaga contextMenuChatId)
    pendingDeleteChatId = contextMenuChatId;
    console.log('[DELETE] pendingDeleteChatId salvo:', pendingDeleteChatId);
    closeContextMenu();
    document.getElementById('confirm-delete-modal').classList.add('active');
}

function closeConfirmDeleteModal() {
    document.getElementById('confirm-delete-modal').classList.remove('active');
    pendingDeleteChatId = null; // Limpar ao cancelar
}

async function executeDeleteChat() {
    console.log('[DELETE] executeDeleteChat chamada, pendingDeleteChatId:', pendingDeleteChatId);
    const chatId = pendingDeleteChatId;
    if (!chatId) {
        console.error('[DELETE] pendingDeleteChatId está vazio!');
        return;
    }

    console.log('[DELETE] Fechando modal e chamando deleteChat para ID:', chatId);
    closeConfirmDeleteModal();
    await deleteChat(chatId);
}

function showMoveToProjectModal() {
    console.log('[MOVE] showMoveToProjectModal chamada, contextMenuChatId:', contextMenuChatId);
    // Salvar o ID ANTES de fechar o menu
    pendingMoveChatId = contextMenuChatId;
    console.log('[MOVE] pendingMoveChatId salvo:', pendingMoveChatId);
    closeContextMenu();

    if (projects.length === 0) {
        alert('Nenhum projeto disponível. Crie um projeto primeiro.');
        pendingMoveChatId = null;
        return;
    }

    const projectList = document.getElementById('project-list-move');
    projectList.innerHTML = projects.map(p => `
        <div style="padding: 12px; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.2s;"
             onmouseover="this.style.background='var(--hover-color)'"
             onmouseout="this.style.background='transparent'"
             onclick="moveChatToProject(${p.id})">
            <div style="font-weight: 500;">${p.name}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                ${p.chatIds.length} conversa(s)
            </div>
        </div>
    `).join('');

    document.getElementById('move-project-modal').classList.add('active');
}

function closeMoveProjectModal() {
    document.getElementById('move-project-modal').classList.remove('active');
    pendingMoveChatId = null; // Limpar ao cancelar
}

async function moveChatToProject(projectId) {
    console.log('[MOVE] moveChatToProject chamada, pendingMoveChatId:', pendingMoveChatId, 'projectId:', projectId);
    const chatId = pendingMoveChatId;
    if (!chatId) {
        console.error('[MOVE] pendingMoveChatId está vazio!');
        return;
    }

    console.log('[MOVE] Movendo chat', chatId, 'para projeto', projectId);

    try {
        const response = await fetch(`/api/projects/${projectId}/chats`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ chat_id: chatId })
        });

        console.log('[MOVE] Response status:', response.status);

        if (response.ok) {
            await loadProjects();
            closeMoveProjectModal();
            alert('Conversa movida com sucesso!');
        } else {
            const error = await response.json();
            console.error('[MOVE] Error:', error);
            alert(error.error || 'Erro ao mover conversa');
        }
    } catch (error) {
        console.error('[MOVE] Erro:', error);
        alert('Erro ao mover conversa: ' + error.message);
    }
}

async function deleteChat(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            credentials: 'include'
        });

        if (response.ok) {
            // Se era o chat atual, criar um novo
            if (currentChatId === chatId) {
                await createNewChat();
            }
            await loadChats();
        } else {
            alert('Erro ao excluir conversa: ' + response.status);
        }
    } catch (error) {
        console.error('Erro ao excluir:', error);
        alert('Erro de conexão: ' + error.message);
    }
}

// Fechar menu ao clicar fora
document.addEventListener('click', (e) => {
    if (!menuIsOpen) return;

    const menu = document.getElementById('chat-context-menu');
    const clickedMenuButton = e.target.closest('.chat-item-menu');

    // Não fechar se clicou no botão de menu ou dentro do menu
    if (clickedMenuButton || menu.contains(e.target)) return;

    closeContextMenu();
});

// ===== PROJECTS AND CONVERSAS MENUS =====
let projectsMenuOpen = false;
let conversasMenuOpen = false;

function showProjectsMenu(event) {
    event.stopPropagation();
    event.preventDefault();

    const menu = document.getElementById('projects-context-menu');

    // Se já está aberto, fechar
    if (projectsMenuOpen) {
        menu.style.display = 'none';
        projectsMenuOpen = false;
        return;
    }

    // Fechar outros menus se estiverem abertos
    if (conversasMenuOpen) {
        document.getElementById('conversas-context-menu').style.display = 'none';
        conversasMenuOpen = false;
    }
    if (menuIsOpen) {
        closeContextMenu();
    }

    // Abrir menu
    projectsMenuOpen = true;

    // Posicionar menu
    const x = event.clientX || (event.touches && event.touches[0].clientX) || 0;
    const y = event.clientY || (event.touches && event.touches[0].clientY) || 0;

    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.style.display = 'block';
}

function showConversasMenu(event) {
    event.stopPropagation();
    event.preventDefault();

    const menu = document.getElementById('conversas-context-menu');

    // Se já está aberto, fechar
    if (conversasMenuOpen) {
        menu.style.display = 'none';
        conversasMenuOpen = false;
        return;
    }

    // Fechar outros menus se estiverem abertos
    if (projectsMenuOpen) {
        document.getElementById('projects-context-menu').style.display = 'none';
        projectsMenuOpen = false;
    }
    if (menuIsOpen) {
        closeContextMenu();
    }

    // Abrir menu
    conversasMenuOpen = true;

    // Posicionar menu
    const x = event.clientX || (event.touches && event.touches[0].clientX) || 0;
    const y = event.clientY || (event.touches && event.touches[0].clientY) || 0;

    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.style.display = 'block';
}

function closeProjectsMenu() {
    document.getElementById('projects-context-menu').style.display = 'none';
    projectsMenuOpen = false;
}

function closeConversasMenu() {
    document.getElementById('conversas-context-menu').style.display = 'none';
    conversasMenuOpen = false;
}

// Fechar menus ao clicar fora
document.addEventListener('click', (e) => {
    if (projectsMenuOpen) {
        const menu = document.getElementById('projects-context-menu');
        if (!menu.contains(e.target)) {
            closeProjectsMenu();
        }
    }
    if (conversasMenuOpen) {
        const menu = document.getElementById('conversas-context-menu');
        if (!menu.contains(e.target)) {
            closeConversasMenu();
        }
    }
});

// ===== PROFILE =====
function openProfile() {
    const userData = JSON.parse(localStorage.getItem('sofia_user') || '{}');
    const npub = localStorage.getItem('sofia_npub');

    document.getElementById('profile-name').textContent = userData.name || 'Não informado';

    // Authentication method and Nostr key
    if (npub) {
        // Nostr user
        document.getElementById('profile-auth').innerHTML = '🔑 Nostr';
        document.getElementById('profile-npub').textContent = npub;
        document.getElementById('profile-npub-section').classList.remove('hidden');
    } else {
        // Traditional user
        document.getElementById('profile-auth').innerHTML = '📧 Email/Senha';
        document.getElementById('profile-npub-section').classList.add('hidden');
    }

    document.getElementById('profile-tokens').textContent = `${userData.tokens_used || 0} / ${userData.tokens_limit || 0}`;
    document.getElementById('profile-modal').classList.add('active');
}

function closeProfile() {
    document.getElementById('profile-modal').classList.remove('active');
}

// ===== PROJECTS =====
let projects = [];

async function loadProjects() {
    console.log('[DEBUG loadProjects] Function called');
    try {
        const response = await fetch('/api/projects', {
            headers: getAuthHeaders(),
            credentials: 'include'
        });

        console.log('[DEBUG loadProjects] API response status:', response.status, response.ok);

        if (response.ok) {
            const data = await response.json();
            console.log('[DEBUG loadProjects] API response data:', data);

            projects = data.projects.map(p => ({
                id: p.id,
                name: p.name,
                chatIds: p.chat_ids || [],
                collapsed: p.collapsed === 1 || p.collapsed === true
            }));

            console.log('[DEBUG loadProjects] Updated projects array:', projects);
            console.log('[DEBUG loadProjects] Calling renderProjects()');
            renderProjects();
            console.log('[DEBUG loadProjects] renderProjects() completed');
        }
    } catch (error) {
        console.error('[PROJECTS] Erro ao carregar projetos:', error);
    }
}

function openCreateProjectModal() {
    document.getElementById('project-name-input').value = '';
    document.getElementById('create-project-modal').classList.add('active');
    setTimeout(() => document.getElementById('project-name-input').focus(), 300);
}

function closeCreateProjectModal() {
    document.getElementById('create-project-modal').classList.remove('active');
}

async function createProject() {
    let name = document.getElementById('project-name-input').value.trim();

    // Auto-generate name if empty
    if (!name) {
        // Find existing projects with auto-generated names
        const autoNamePattern = /^novo projeto( \d+)?$/;
        const autoProjects = projects.filter(p => autoNamePattern.test(p.name));

        if (autoProjects.length === 0) {
            name = 'novo projeto';
        } else {
            // Extract numbers from existing auto-named projects
            const numbers = autoProjects.map(p => {
                const match = p.name.match(/^novo projeto( (\d+))?$/);
                return match && match[2] ? parseInt(match[2]) : 1;
            });

            // Find next available number
            const maxNum = Math.max(...numbers);
            name = `novo projeto ${maxNum + 1}`;
        }
    }

    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ name })
        });

        if (response.ok) {
            await loadProjects(); // Recarregar projetos do backend
            closeCreateProjectModal();
        } else {
            const error = await response.json();
            alert(error.error || 'Erro ao criar projeto');
        }
    } catch (error) {
        console.error('[PROJECTS] Erro ao criar projeto:', error);
        alert('Erro ao criar projeto');
    }
}

async function toggleProject(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'PATCH',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ collapsed: true })
        });

        if (response.ok) {
            // Atualizar localmente primeiro para resposta instantânea
            const project = projects.find(p => p.id === projectId);
            if (project) {
                project.collapsed = !project.collapsed;
                renderProjects();
            }
        }
    } catch (error) {
        console.error('[PROJECTS] Erro ao alternar projeto:', error);
    }
}

function renderProjects() {
    console.log('[DEBUG renderProjects] Function called');
    console.log('[DEBUG renderProjects] Projects array:', projects);

    const container = document.getElementById('projects-list');
    console.log('[DEBUG renderProjects] Container element:', container);

    if (!projects.length) {
        console.log('[DEBUG renderProjects] No projects to render, clearing container');
        container.innerHTML = '';
        return;
    }

    console.log('[DEBUG renderProjects] Rendering', projects.length, 'projects');

    container.innerHTML = projects.map(project => {
        console.log('[DEBUG renderProjects] Rendering project:', project.id, project.name);
        const projectChats = chats.filter(c => project.chatIds.includes(c.id));
        return `
            <div class="project-item ${project.collapsed ? 'collapsed' : ''}">
                <div class="project-header" onclick="toggleProject(${project.id})">
                    <svg class="project-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                    <div class="project-name">${escapeHtml(project.name)}</div>
                    <button class="icon-btn-small" onclick="event.stopPropagation(); createChatInProject(${project.id})" title="Nova conversa neste projeto" style="margin-left: auto; margin-right: 4px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                    </button>
                    <div class="project-menu" onclick="event.stopPropagation(); showProjectMenu(event, ${project.id})">⋯</div>
                </div>
                <div class="project-chats">
                    ${projectChats.map(chat => `
                        <div class="chat-item ${currentChatId === chat.id ? 'active' : ''}" data-chat-id="${chat.id}">
                            <div style="display: flex; align-items: center; flex: 1; gap: 8px;" onclick="loadChat(${chat.id})">
                                <div class="chat-item-checkbox" onclick="event.stopPropagation(); toggleChatSelection(${chat.id}, this)" style="width: 20px; height: 20px; border: 2px solid var(--border-light); border-radius: 4px; cursor: pointer; transition: all 0.2s; flex-shrink: 0;"></div>
                                <div class="chat-item-name" style="flex: 1;">${escapeHtml(chat.chat_name || 'Sem nome')}</div>
                            </div>
                            <div class="chat-item-menu" onclick="event.stopPropagation(); showChatContextMenu(event, ${chat.id})">⋯</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');

    console.log('[DEBUG renderProjects] DOM updated, function complete');
}

async function renameProject(projectId) {
    console.log('[RENAME] Renomeando projeto ID:', projectId);
    const project = projects.find(p => p.id === projectId);
    if (!project) {
        console.error('[RENAME] Projeto não encontrado:', projectId);
        return;
    }

    console.log('[RENAME] Projeto atual:', project);
    const newName = prompt('Novo nome do projeto:', project.name);
    if (!newName || newName.trim() === '' || newName === project.name) {
        console.log('[RENAME] Renomeação cancelada ou nome igual');
        return;
    }

    console.log('[RENAME] Novo nome:', newName.trim());

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'PATCH',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ name: newName.trim() })
        });

        console.log('[RENAME] Response status:', response.status);

        if (response.ok) {
            // BUGFIX #7: Update local projects array immediately for instant UI feedback
            // (mirrors chat rename pattern from saveRename() - update visible element before server refresh)
            const project = projects.find(p => p.id === projectId);
            if (project) {
                console.log('[RENAME] Updating local project name immediately');
                project.name = newName.trim();
                renderProjects();  // Force immediate re-render with updated local data
            }
            await loadProjects();  // Then fetch from server to ensure full synchronization
            alert('Projeto renomeado com sucesso!');
        } else {
            const error = await response.json();
            console.error('[RENAME] Error:', error);
            alert(error.error || 'Erro ao renomear projeto');
        }
    } catch (error) {
        console.error('[PROJECTS] Erro ao renomear projeto:', error);
        alert('Erro ao renomear projeto: ' + error.message);
    }
}

async function deleteProject(projectId) {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    if (!confirm(`Deseja excluir o projeto "${project.name}"?\n\nAs conversas não serão deletadas, apenas removidas do projeto.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            credentials: 'include'
        });

        if (response.ok) {
            await loadProjects();
        } else {
            const error = await response.json();
            alert(error.error || 'Erro ao deletar projeto');
        }
    } catch (error) {
        console.error('[PROJECTS] Erro ao deletar projeto:', error);
        alert('Erro ao deletar projeto');
    }
}

function showProjectMenu(event, projectId) {
    event.stopPropagation();

    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.style.position = 'fixed';
    menu.style.zIndex = '9999';
    menu.style.left = event.clientX + 'px';
    menu.style.top = event.clientY + 'px';

    menu.innerHTML = `
        <div class="context-menu-item" onclick="renameProject(${projectId}); this.parentElement.remove()">
            Renomear
        </div>
        <div class="context-menu-item" onclick="deleteProject(${projectId}); this.parentElement.remove()">
            Excluir
        </div>
    `;

    document.body.appendChild(menu);

    // Fechar ao clicar fora
    const closeMenu = (e) => {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    };
    setTimeout(() => document.addEventListener('click', closeMenu), 10);
}

// ===== BALANCE =====
async function loadBalance() {
    try {
        const response = await fetch('/api/user/balance', {
            headers: getAuthHeaders(),
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            updateBalance(data.balance);
        }
    } catch (error) {
        console.error('Erro ao carregar saldo:', error);
    }
}

function updateBalance(balance) {
    const sidebarTokens = document.getElementById('sidebar-tokens');

    let formatted;
    if (balance >= 1000000) {
        formatted = `${(balance / 1000000).toFixed(1)}M`;
    } else if (balance >= 1000) {
        formatted = `${Math.floor(balance / 1000)}k`;
    } else {
        formatted = String(balance);
    }

    // Atualizar contador na sidebar
    if (sidebarTokens) {
        sidebarTokens.textContent = formatted;
    }
}

// ===== MODEL SELECTOR =====
function toggleModelDropdown() {
    const dropdown = document.getElementById('model-dropdown');
    if (dropdown) {
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    }
}

function selectModel(modelId) {
    // Salvar modelo selecionado
    localStorage.setItem('selectedModel', modelId);

    // Atualizar UI
    const options = document.querySelectorAll('.model-option');
    options.forEach(opt => opt.classList.remove('selected'));

    const selected = document.querySelector(`[data-model="${modelId}"]`);
    if (selected) {
        selected.classList.add('selected');

        // Atualizar texto do botão
        const title = selected.querySelector('.model-option-title').textContent;
        document.getElementById('current-model-text').textContent = title;
    }

    // Recalcular custo estimado com novo modelo
    estimateTokenCost();

    // Fechar dropdown
    document.getElementById('model-dropdown').style.display = 'none';
}

// Fechar dropdown ao clicar fora
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('model-dropdown');
    const selector = document.querySelector('.model-selector');

    if (dropdown && selector && !selector.contains(event.target)) {
        dropdown.style.display = 'none';
    }
});

// ===== RECHARGE MODAL =====
let currentPaymentHash = null;
let paymentCheckInterval = null;

function openRechargeModal() {
    const modal = document.getElementById('recharge-modal');
    const packagesList = document.getElementById('packages-list');
    const qrContainer = document.getElementById('qr-container');

    if (modal) {
        modal.style.display = 'flex';
        packagesList.style.display = 'block';
        qrContainer.style.display = 'none';

        // Limpar polling anterior se existir
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
    }
}

function closeRechargeModal() {
    const modal = document.getElementById('recharge-modal');
    if (modal) {
        modal.style.display = 'none';

        // Limpar polling
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
        currentPaymentHash = null;
    }
}

// Fechar modal ao clicar no overlay
const rechargeModal = document.getElementById('recharge-modal');
if (rechargeModal) {
    rechargeModal.addEventListener('click', function(e) {
        if (e.target === this) {
            closeRechargeModal();
        }
    });
}

async function purchasePackage(packageName, tokens, sats) {
    try {
        const headers = getAuthHeaders();
        if (!headers.Authorization) {
            showStatus('Por favor, faça login primeiro', 'error');
            return;
        }

        headers['Content-Type'] = 'application/json';

        const response = await fetch('/api/tokens/purchase', {
            method: 'POST',
            headers: headers,
            credentials: 'include',
            body: JSON.stringify({
                package: packageName,
                tokens: tokens,
                sats: sats
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro ao criar invoice');
        }

        const data = await response.json();

        // Mostrar QR code
        document.getElementById('packages-list').style.display = 'none';
        document.getElementById('qr-container').style.display = 'block';
        document.getElementById('qr-code').src = data.qr_code;

        currentPaymentHash = data.payment_hash;

        // Iniciar polling para verificar pagamento
        startPaymentPolling(data.payment_hash, tokens);

    } catch (error) {
        console.error('Error purchasing package:', error);
        showStatus('Erro ao criar pagamento: ' + error.message, 'error');
    }
}

function startPaymentPolling(paymentHash, tokens) {
    // Verificar a cada 3 segundos
    paymentCheckInterval = setInterval(async () => {
        try {
            const headers = getAuthHeaders();
            const response = await fetch(`/api/tokens/check-payment/${paymentHash}`, {
                headers,
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();

                if (data.paid) {
                    // Pagamento confirmado! Creditar tokens
                    await creditTokens(paymentHash, tokens);

                    // Limpar polling
                    clearInterval(paymentCheckInterval);
                    paymentCheckInterval = null;

                    // Fechar modal
                    closeRechargeModal();

                    // Mostrar mensagem de sucesso
                    showStatus(`✅ Recarga confirmada! ${formatTokens(tokens)} tokens adicionados`, 'success');

                    // Atualizar saldo
                    loadBalance();
                }
            }
        } catch (error) {
            console.error('Error checking payment:', error);
        }
    }, 3000);
}

async function creditTokens(paymentHash, tokens) {
    try {
        const headers = getAuthHeaders();
        headers['Content-Type'] = 'application/json';

        const response = await fetch('/api/tokens/credit', {
            method: 'POST',
            headers: headers,
            credentials: 'include',
            body: JSON.stringify({
                payment_hash: paymentHash,
                tokens: tokens
            })
        });

        if (!response.ok) {
            throw new Error('Erro ao creditar tokens');
        }

        return await response.json();
    } catch (error) {
        console.error('Error crediting tokens:', error);
        throw error;
    }
}

function formatTokens(tokens) {
    if (tokens >= 1000000) {
        return (tokens / 1000000).toFixed(1) + 'M';
    } else if (tokens >= 1000) {
        return Math.round(tokens / 1000) + 'k';
    }
    return tokens.toString();
}

function showStatus(message, type) {
    // TODO: Implementar UI de status
    console.log(`[STATUS ${type}]`, message);
}

// ===== INDICADOR DE CUSTO ESTIMADO =====
let modelCosts = {};
let estimatedCost = 0;

async function loadModelCosts() {
    try {
        const response = await fetch('/api/models');
        if (response.ok) {
            const data = await response.json();
            data.models.forEach(model => {
                modelCosts[model.id] = {
                    input: model.cost_per_1k_input || 0,
                    output: model.cost_per_1k_output || 0
                };
            });
        }
    } catch (error) {
        console.error('Error loading model costs:', error);
    }
}

function estimateTokenCost() {
    const input = document.getElementById('messageInput');
    if (!input) return;

    const text = input.value;
    if (!text || text.trim().length === 0) {
        document.getElementById('cost-estimator').style.display = 'none';
        return;
    }

    // Estimativa grosseira: 1 token ≈ 4 caracteres
    const estimatedInputTokens = Math.ceil(text.length / 4);
    const selectedModel = localStorage.getItem('selectedModel') || 'gpt-5';

    if (modelCosts[selectedModel]) {
        const costs = modelCosts[selectedModel];
        // Estimar custo (input + estimativa de output ~150 tokens)
        const inputCost = (estimatedInputTokens / 1000) * costs.input;
        const estimatedOutputCost = (150 / 1000) * costs.output;
        estimatedCost = Math.ceil(inputCost + estimatedOutputCost);

        document.getElementById('estimated-cost').textContent = `~${estimatedCost}`;
        document.getElementById('cost-estimator').style.display = 'flex';
    } else {
        document.getElementById('cost-estimator').style.display = 'none';
    }
}

// ===== HISTÓRICO DE TRANSAÇÕES =====
async function openTransactionHistory() {
    const modal = document.getElementById('transaction-modal');
    if (modal) {
        modal.style.display = 'flex';
        await loadTransactionHistory();
    }
}

function closeTransactionHistory() {
    const modal = document.getElementById('transaction-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadTransactionHistory() {
    try {
        const headers = getAuthHeaders();
        if (!headers.Authorization) {
            document.getElementById('transaction-list').innerHTML = `
                <div class="transaction-empty">
                    <p>Faça login para ver seu histórico</p>
                </div>
            `;
            return;
        }

        const response = await fetch('/api/tokens/transactions?limit=50', {
            headers,
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Erro ao carregar histórico');
        }

        const data = await response.json();
        const transactions = data.transactions;

        if (transactions.length === 0) {
            document.getElementById('transaction-list').innerHTML = `
                <div class="transaction-empty">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <path d="M12 6v6l4 2"></path>
                    </svg>
                    <p>Nenhuma transação ainda</p>
                </div>
            `;
            return;
        }

        let html = '';
        transactions.forEach(tx => {
            const isPositive = tx.type === 'purchase' || tx.amount > 0;
            const amountClass = isPositive ? 'positive' : 'negative';
            const amountPrefix = isPositive ? '+' : '';

            const date = new Date(tx.timestamp);
            const dateStr = date.toLocaleDateString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            let typeText = '';
            let detailsText = '';

            if (tx.type === 'purchase') {
                typeText = '💰 Recarga';
                detailsText = `${dateStr}`;
            } else {
                typeText = '💬 Uso';
                detailsText = `${tx.model || 'Sofia'} • ${dateStr}`;
            }

            html += `
                <div class="transaction-item">
                    <div class="transaction-info">
                        <div class="transaction-type">${typeText}</div>
                        <div class="transaction-details">${detailsText}</div>
                    </div>
                    <div class="transaction-amount ${amountClass}">
                        ${amountPrefix}${formatTokens(Math.abs(tx.amount))}
                    </div>
                </div>
            `;
        });

        document.getElementById('transaction-list').innerHTML = html;
    } catch (error) {
        console.error('Error loading transaction history:', error);
        document.getElementById('transaction-list').innerHTML = `
            <div class="transaction-empty">
                <p>Erro ao carregar histórico</p>
            </div>
        `;
    }
}

// ===== NOSTR PROFILE FETCH (ASYNC COM POLLING) =====
async function fetchNostrProfileAsync() {
    try {
        const storedUser = localStorage.getItem('sofia_user');
        if (!storedUser) return;

        const user = JSON.parse(storedUser);

        // Se tem npub mas nome é genérico, buscar perfil
        if (user.npub && user.name && user.name.startsWith('Nostr User npub')) {
            console.log('[PROFILE] Disparando busca de perfil Nostr em background...');

            // Disparar busca (retorna imediatamente)
            const response = await fetch('/api/user/fetch-nostr-profile', {
                method: 'POST',
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (response.status === 202) {
                console.log('[PROFILE] Busca iniciada, aguardando resultado...');

                // Fazer polling a cada 3 segundos por até 40 segundos
                let attempts = 0;
                const maxAttempts = 13; // 13 * 3 = 39 segundos

                const pollInterval = setInterval(async () => {
                    attempts++;

                    try {
                        // Buscar dados atualizados do usuário
                        const userResponse = await fetch('/api/user', {
                            headers: getAuthHeaders(),
                            credentials: 'include'
                        });

                        if (userResponse.ok) {
                            const userData = await userResponse.json();

                            // Se nome mudou (não é mais genérico), perfil foi encontrado
                            if (userData.name && !userData.name.startsWith('Nostr User npub')) {
                                clearInterval(pollInterval);
                                console.log('[PROFILE] Perfil encontrado:', userData.name);

                                // Atualizar localStorage
                                const updatedUser = {
                                    ...user,
                                    name: userData.name,
                                    picture: userData.picture || ''
                                };
                                localStorage.setItem('sofia_user', JSON.stringify(updatedUser));

                                // Atualizar UI (3 parâmetros separados)
                                updateUserUI(
                                    userData.name.charAt(0).toUpperCase(),
                                    userData.name,
                                    userData.picture || ''
                                );
                            }
                        }

                        // Parar polling após max attempts
                        if (attempts >= maxAttempts) {
                            clearInterval(pollInterval);
                            console.log('[PROFILE] Timeout de polling, perfil não encontrado');
                        }
                    } catch (pollError) {
                        console.error('[PROFILE] Erro no polling:', pollError);
                    }
                }, 3000); // A cada 3 segundos
            }
        }
    } catch (error) {
        console.error('[PROFILE] Erro ao buscar perfil async:', error);
    }
}

// ===== LOGOUT =====
async function logout() {
    try {
        await fetch('/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {}
    localStorage.clear();
    window.location.href = '/login';
}

// ===== MOBILE KEYBOARD FIX (DuckDuckGo/Safari/Chrome) =====
function handleKeyboardResize() {
    const inputArea = document.querySelector('.input-area');
    const chatContainer = document.querySelector('.chat-container');

    // Detectar se teclado está aberto (viewport height diminui)
    const viewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    const windowHeight = window.innerHeight;
    const keyboardHeight = windowHeight - viewportHeight;

    if (keyboardHeight > 100) {
        // Teclado aberto - garantir que input fique visível
        inputArea.style.bottom = '0';
        chatContainer.style.paddingBottom = `calc(${keyboardHeight}px + 100px)`;
    } else {
        // Teclado fechado - resetar
        inputArea.style.bottom = '0';
        chatContainer.style.paddingBottom = 'calc(100px + env(safe-area-inset-bottom, 0px))';
    }

    // Scroll para última mensagem ao abrir teclado
    if (keyboardHeight > 100) {
        setTimeout(() => {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }, 100);
    }
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', async function() {
    applyTheme();

    // Auto-resize textarea
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Enter to send
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Event listener para calcular custo estimado
        messageInput.addEventListener('input', estimateTokenCost);

        messageInput.addEventListener('focus', function(e) {
            // Scroll suave até o input
            setTimeout(() => {
                e.target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 300);
        });

        // Focus no input (evitar auto-zoom no mobile)
        if (window.innerWidth > 768) {
            messageInput.focus();
        }
    }

    // Inicializar seletor de modelo
    const selectedModel = localStorage.getItem('selectedModel') || 'gpt-5';
    const modelOption = document.querySelector(`[data-model="${selectedModel}"]`);
    if (modelOption) {
        // Marcar como selecionado
        document.querySelectorAll('.model-option').forEach(opt => opt.classList.remove('selected'));
        modelOption.classList.add('selected');

        // Atualizar texto do botão
        const title = modelOption.querySelector('.model-option-title').textContent;
        document.getElementById('current-model-text').textContent = title;
    }

    if (!checkAuth()) return;
    await loadChats();
    await loadProjects(); // Carrega projetos do backend
    await loadBalance();
    await loadModelCosts(); // Carrega custos dos modelos

    // Buscar perfil Nostr de forma assíncrona (não bloqueia UI)
    fetchNostrProfileAsync();

    // Event listeners para scroll-to-bottom button
    const isMobile = window.innerWidth < 768;
    if (isMobile) {
        // Mobile: listen to window scroll
        window.addEventListener('scroll', handleScrollToBottomButton);
    } else {
        // Desktop: listen to container scroll
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.addEventListener('scroll', handleScrollToBottomButton);
        }
    }
    // Handle window resize (mobile ↔ desktop switch)
    window.addEventListener('resize', () => {
        handleScrollToBottomButton();
        // Re-attach appropriate scroll listener
        const nowMobile = window.innerWidth < 768;
        if (nowMobile !== isMobile) {
            location.reload(); // Reload to re-initialize event listeners
        }
    });

    // Event listeners para mobile keyboard (DEPOIS do DOM carregar)
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', handleKeyboardResize);
        window.visualViewport.addEventListener('scroll', handleKeyboardResize);
    }
    window.addEventListener('resize', handleKeyboardResize);
});
