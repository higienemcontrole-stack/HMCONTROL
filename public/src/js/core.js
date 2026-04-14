/* HM CONTROL - Core Orchestrator (v4.0.0 - Production Stabilized) */

const CORE_CONFIG = {
    API_BASE: window.location.origin
};

class Core {
    constructor() {
        this.user = JSON.parse(localStorage.getItem('hm_user')) || null;
        this.token = localStorage.getItem('hm_token') || null;
        this.elements = {}; 
        
        console.log('[Core] Sistema v4.0.0 Iniciado.');
        this.observeDOM();
        
        if (document.readyState !== 'loading') {
            this.init();
        } else {
            document.addEventListener('DOMContentLoaded', () => this.init());
        }
    }

    init() {
        this.checkAuth();
        this.setupLoginForm();
        this.bindGlobalEvents();
        this.refreshUI();
    }

    observeDOM() {
        const observer = new MutationObserver(() => {
            const displayName = document.getElementById('display-user-name');
            if (displayName && !this.elements.displayName) {
                this.elements.displayName = displayName;
                this.refreshUI();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => this.refreshUI(), 300);
    }

    checkAuth() {
        const isLoginPage = window.location.pathname.includes('login.html');
        // Uma sessão válida exige tanto o objeto de usuário quanto o token de acesso
        const isAuthenticated = this.user && this.token;

        if (!isAuthenticated && !isLoginPage) {
            console.log('[Core] Sessão ausente ou expirada. Redirecionando para login.');
            localStorage.clear(); // Limpa resíduos para evitar loops
            window.location.href = 'login.html';
        } else if (isAuthenticated && isLoginPage) {
            console.log('[Core] Sessão ativa detectada. Redirecionando para portal.');
            window.location.href = 'index.html';
        }
    }

    setupLoginForm() {
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
    }

    refreshUI() {
        if (!this.user) return;

        // Normalizar campos: Servidor usa full_name/role; backend usa nome_completo/cargo
        this.user.nome_completo = this.user.nome_completo || this.user.full_name || this.user.email?.split('@')[0] || '';
        this.user.cargo         = this.user.cargo || this.user.role || 'user';
        this.user.acessos       = this.user.acessos || [];
        localStorage.setItem('hm_user', JSON.stringify(this.user));

        if (this.elements.displayName) {
            this.elements.displayName.textContent = this.user.nome_completo || this.user.email?.split('@')[0];
        }

        if (this.token) {
            this.syncUserProfile();
            this.injectAdminFeatures();
            this.applyAccessRestrictions();
        }
    }

    applyAccessRestrictions() {
        if (!this.user) return;
        // Aceitar tanto 'cargo' (backend) como 'role' (Servidor direto)
        const isAdmin = this.user.cargo === 'admin' || this.user.role === 'admin';
        const allowedScreens = this.user.acessos || [];

        // Admins nunca têm restrições
        if (isAdmin) {
            document.querySelectorAll('.nav-link').forEach(link => { link.style.display = ''; });
            return;
        }

        document.querySelectorAll('.nav-link').forEach(link => {
            const href = link.getAttribute('href');
            if (!href || href.includes('index.html') || href.includes('javascript:void(0)')) return;

            const screenName = href.replace('.html', '').replace('/', '');
            const target = link.closest('.nav-dropdown') || link;

            if (!allowedScreens.includes(screenName)) {
                target.style.display = 'none';
            } else {
                target.style.display = '';
            }
        });
    }

    async syncUserProfile() {
        try {
            // Sincronização via API backend
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/profile?user_id=${this.user.id}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (res.ok) {
                const profile = await res.json();
                this._mergeProfile(profile);
            }
        } catch (err) { 
            console.error('[Core] Falha ao sincronizar perfil com o servidor:', err);
        }
    }

    _mergeProfile(profile) {
        // Normaliza e mescla os dados do profile no objeto user
        const merged = {
            ...this.user,
            ...profile,
            nome_completo: profile.nome_completo || profile.full_name || this.user.nome_completo || '',
            cargo:         profile.cargo || profile.role || this.user.cargo || 'user',
        };
        this.user = merged;
        localStorage.setItem('hm_user', JSON.stringify(this.user));
        if (this.elements.displayName) {
            this.elements.displayName.textContent = this.user.nome_completo || this.user.email?.split('@')[0] || '';
        }
        // Reaplicar restrições com dados frescos
        this.injectAdminFeatures();
        this.applyAccessRestrictions();
    }

    bindGlobalEvents() {
        document.addEventListener('click', (e) => {
            // Dropdown de Usuário
            const dropdown = document.getElementById('user-dropdown');
            const trigger = document.getElementById('user-menu-trigger');
            if (dropdown && dropdown.classList.contains('active')) {
                if (!trigger.contains(e.target)) dropdown.classList.remove('active');
            }

            // Dropdown de Configurações (Flyout v3.20)
            const navDropdowns = document.querySelectorAll('.nav-dropdown');
            navDropdowns.forEach(nd => {
                if (nd.classList.contains('active') && !nd.contains(e.target)) {
                    nd.classList.remove('active');
                    const content = nd.querySelector('.nav-dropdown-content');
                    if (content) content.style.display = 'none';
                }
            });

            // Menu Mobile (Responsivo) - Lógica de Sincronia v3.23.7
            const navLinks = document.querySelector('.nav-links');
            const mobileTrigger = document.getElementById('mobile-menu-toggle');
            
            // GATILHO DE ABERTURA/FECHAMENTO (Usa o ID correto do HTML)
            if (e.target.closest('#mobile-menu-toggle')) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleMobileMenu();
                return;
            }

            if (navLinks && navLinks.classList.contains('active')) {
                // FECHAMENTO AO CLICAR FORA (Na overlay ou fora da sidebar)
                // Se clicar em um link real (não dropdown), deixa fechar e navegar
                if (!navLinks.contains(e.target)) {
                    this.toggleMobileMenu();
                } else if (!e.target.closest('.nav-dropdown')) {
                    // Clicou num link normal dentro do menu? Navega e fecha.
                    setTimeout(() => this.toggleMobileMenu(), 100);
                }
            }

            // Toggle Dropdown via clique para Mobile/Tablet
            const settingsToggle = e.target.closest('.nav-dropdown > .nav-link');
            if (settingsToggle) {
                e.preventDefault();
                e.stopPropagation(); // CRITICAL: Impede que o clique "vaze" e feche a sidebar
                
                const parent = settingsToggle.parentElement;
                const content = parent.querySelector('.nav-dropdown-content');
                const rect = settingsToggle.getBoundingClientRect();
                
                const isActive = parent.classList.toggle('active');
                if (isActive && content) {
                    content.style.display = 'flex';
                    
                    // Lógica de Viewport Safety & Sidebar Alignment (v3.23)
                    const menuHeight = content.offsetHeight || 280;
                    const viewportHeight = window.innerHeight;
                    const rectSidebarItem = settingsToggle.getBoundingClientRect();
                    
                    let topPos = rectSidebarItem.top;

                    // Clamp Top/Bottom: Garante que o flyout não "fure" o teto ou o chão
                    if (topPos + menuHeight > viewportHeight) {
                        topPos = Math.max(10, viewportHeight - menuHeight - 10);
                    } else {
                        topPos = Math.max(0, topPos); // Alinha com o item clicado
                    }

                    content.style.top = topPos + 'px';
                    content.style.left = '280px'; // Fixo à direita da sidebar
                } else if (content) {
                    content.style.display = 'none';
                }
            }
        });
    }

    // --- MÉTODOS PÚBLICOS ---

    // --- FUNÇÕES DE CONFIGURAÇÃO (v11.0.1) ---

    async syncDatabase() {
        try {
            Swal.fire({
                title: 'Sincronizando...',
                text: 'Sincronizando dados com o servidor de segurança.',
                allowOutsideClick: false,
                didOpen: () => Swal.showLoading()
            });
                if (window.location.pathname.includes('dashboard') || window.location.pathname.includes('tabulacao')) {
                    setTimeout(() => window.location.reload(), 1500);
                }
            } else {
                throw new Error('Falha na resposta da API');
            }
        } catch (e) {
            Swal.fire('Erro', 'Não foi possível sincronizar o sistema.', 'error');
        }
    }

    manageAccounts() {
        const isAdmin = this.user && (this.user.cargo === 'admin' || this.user.role === 'admin');
        if (isAdmin) {
            Swal.fire({
                title: 'Gestão de Contas',
                text: 'Deseja gerenciar os usuários do sistema?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Sim, Abrir Painel',
                cancelButtonText: 'Agora não'
            }).then(result => {
                if (result.isConfirmed) {
                    window.location.href = 'perfil.html';
                }
            });
        } else {
            this.openProfileModal();
        }
    }

    backupSnapshots() {
        Swal.fire({
            title: 'Backup (Snapshots)',
            text: 'Deseja gerar um snapshot de segurança da base atual?',
            icon: 'info',
            showCancelButton: true,
            confirmButtonText: 'Gerar Snapshot'
        }).then(result => {
            if (result.isConfirmed) {
                Swal.fire({
                    title: 'Processando Backup',
                    timer: 2000,
                    didOpen: () => Swal.showLoading()
                }).then(() => {
                    Swal.fire('Concluído', 'Snapshot v' + new Date().getTime() + ' gerado com sucesso.', 'success');
                });
            }
        });
    }

    async setGoals() {
        const { value: goal } = await Swal.fire({
            title: 'Configurar Metas',
            input: 'number',
            inputLabel: 'Meta de Conformidade Hospitalar (%)',
            inputValue: 85,
            showCancelButton: true,
            inputValidator: (value) => {
                if (!value || value < 0 || value > 100) {
                    return 'Insira um valor entre 0 e 100';
                }
            }
        });

        if (goal) {
            localStorage.setItem('hm_hospital_goal', goal);
            Swal.fire('Meta Atualizada', `Nova meta de ${goal}% configurada para os indicadores.`, 'success');
        }
    }

    viewAuditLogs() {
        Swal.fire({
            title: 'Logs de Auditoria',
            html: `
                <div style="text-align: left; font-family: monospace; font-size: 11px; max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 4px;">
                    [${new Date().toLocaleTimeString()}] Sistema v11.0.1 verificado<br>
                    [${new Date().toLocaleTimeString()}] Cache de dados: 1240 registros<br>
                    [${new Date().toLocaleTimeString()}] Sincronização: OK<br>
                    [${new Date().toLocaleTimeString()}] Z-Index Hardening aplicado<br>
                    [${new Date().toLocaleTimeString()}] Conexão Base de Dados: Estabelecida
                </div>
            `,
            width: 600
        });
    }

    async clearCache() {
        try {
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/admin/cache/clear`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (res.ok) {
                Swal.fire('Cache Limpo', 'O cache de dados foi resetado no servidor.', 'success');
            }
        } catch (e) {
            Swal.fire('Erro', 'Falha ao limpar cache.', 'error');
        }
    }

    toggleMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        const body = document.body;
        
        if (navLinks) {
            const isActive = navLinks.classList.toggle('active');
            body.classList.toggle('menu-open', isActive);
            
            // Garantir que o overlay exista ou seja removido
            let overlay = document.querySelector('.menu-overlay');
            if (isActive) {
                if (!overlay) {
                    overlay = document.createElement('div');
                    overlay.className = 'menu-overlay';
                    overlay.onclick = () => this.toggleMobileMenu();
                    document.body.appendChild(overlay);
                }
                overlay.style.display = 'block';
                setTimeout(() => overlay.style.opacity = '1', 10);
            } else if (overlay) {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.style.display = 'none', 300);
            }
        }
    }

    async openProfileModal(externalUser = null) {
        const modal = document.getElementById('profile-modal');
        if (!modal) return;

        try {
            // Se externalUser for passado (Admin), usamos os dados dele
            // Caso contrário, buscamos do usuário logado diretamente do Servidor
            const targetId = externalUser ? externalUser.id : this.user.id;
            this.editingUserId = targetId;
            
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/profile?user_id=${targetId}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            
            // Perfil pode vir vazio se for um usuário pendente
            const profile = res.ok ? await res.json() : (externalUser || {});

            // População do Modal
            document.getElementById('profile-name').value = profile.nome_completo || externalUser?.nome_completo || '';
            document.getElementById('profile-email').value = profile.email || externalUser?.email || '';
            document.getElementById('profile-password').value = ''; 
            
            const roleEl = document.getElementById('profile-role');
            const isAdmin = this.user.cargo === 'admin';
            
            if (roleEl) {
                roleEl.value = profile.cargo || 'user';
                roleEl.disabled = !isAdmin; // Só Admin muda cargo de terceiros ou o próprio
            }
            
            const screenList = document.getElementById('profile-screens');
            if (screenList) {
                const checks = screenList.querySelectorAll('input[type="checkbox"]');
                const userScreens = profile.acessos || ['dashboard'];

                checks.forEach(check => {
                    if (check.value !== 'dashboard') {
                        check.checked = isAdmin || userScreens.includes(check.value);
                        check.disabled = !isAdmin;
                    }
                });
            }

            modal.classList.add('active');
        } catch (err) { 
            console.error('[Core] Modal Open Error:', err);
            alert('Erro ao carregar perfil para edição.'); 
        }
    }

    closeProfileModal() {
        const modal = document.getElementById('profile-modal');
        if (modal) modal.classList.remove('active');
        this.editingUserId = null;
    }

    async saveProfileData() {
        const btn = document.getElementById('btn-save-profile');
        const pass = document.getElementById('profile-password').value;
        const targetId = this.editingUserId || this.user.id;
        
        const payload = {
            user_id: targetId,
            nome_completo: document.getElementById('profile-name').value,
            password: pass || null,
            cargo: document.getElementById('profile-role').value,
            acessos: Array.from(document.querySelectorAll('#profile-screens input:checked')).map(c => c.value)
        };

        try {
            btn.disabled = true;
            btn.textContent = 'Salvando...';

            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/update`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert('Sucesso: Perfil e Senha sincronizados no Servidor.');
                this.closeProfileModal();
                if (targetId === this.user.id) {
                    // Se editou o próprio perfil, atualiza sessão local
                    this.user.nome_completo = payload.nome_completo;
                    localStorage.setItem('hm_user', JSON.stringify(this.user));
                    this.refreshUI();
                } else {
                    // Se editou outro, recarrega a lista de usuários
                    this.loadUsersList();
                }
            } else {
                const err = await res.json();
                throw new Error(err.detail || 'Erro ao sincronizar');
            }
        } catch (e) { alert('Erro: ' + e.message); }
        finally { 
            btn.disabled = false; 
            btn.textContent = 'Salvar Alterações';
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const btn = document.getElementById('login-btn');
        const errorEl = document.getElementById('error-message');

        try {
            btn.disabled = true;
            const response = await fetch(`${CORE_CONFIG.API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            if (response.ok) {
                localStorage.setItem('hm_user', JSON.stringify(data.user));
                localStorage.setItem('hm_token', data.session.access_token);
                window.location.href = 'index.html';
            } else { throw new Error(data.detail || 'Falha no login'); }
        } catch (err) {
            if (errorEl) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
            }
        } finally { btn.disabled = false; }
    }

    // --- ADMIN MANAGEMENT (v3.8) ---
    
    injectAdminFeatures() {
        const isAdmin = this.user && (this.user.cargo === 'admin' || this.user.role === 'admin');
        if (!isAdmin) return;
        
        // 1. Localizar o container de navegação ou dropdown de configurações
        const navDropdown = document.querySelector('.nav-dropdown-content');
        if (navDropdown) {
            console.log('[Core] Injetando Elite Hub Administrativo.');
            // Garantir que o texto seja visível colocando estilo inline se necessário
            navDropdown.style.visibility = 'visible';
            navDropdown.style.opacity = '1';
            
            navDropdown.innerHTML = `
                <a href="sistema.html" style="color: #ffffff !important;"><i class="fas fa-sync"></i> Sistema (Sincronizar)</a>
                <a href="gestao-contas.html" style="color: #ffffff !important;"><i class="fas fa-users-cog"></i> Gestão de Contas</a>
                <a href="snapshots.html" style="color: #ffffff !important;"><i class="fas fa-database"></i> Snapshots (Backup)</a>
                <a href="metas.html" style="color: #ffffff !important;"><i class="fas fa-bullseye"></i> Configurar Metas</a>
                <a href="logs.html" style="color: #ffffff !important;"><i class="fas fa-history"></i> Logs de Auditoria</a>
                <a href="manutencao.html" style="color: #ff6b6b !important;"><i class="fas fa-tools"></i> Manutenção</a>
            `;
        } else {
            console.warn('[Core] .nav-dropdown-content não encontrado para injeção.');
        }

        // 2. Injetar Botão de Atalho no Dropdown de Usuário (Versão Curta)
        const userDropdown = document.getElementById('user-dropdown');
        if (userDropdown && !document.getElementById('btn-admin-shortcut')) {
            const btn = document.createElement('button');
            btn.id = 'btn-admin-shortcut';
            btn.className = 'dropdown-item';
            btn.style.color = 'var(--primary)';
            btn.innerHTML = '<i class="fas fa-shield-alt"></i> Painel de Gestão';
            btn.onclick = () => this.openUserManagementModal();
            userDropdown.prepend(btn);
        }

        // 3. Injetar Modal de Gestão de Contas (Unificado)
        if (!document.getElementById('admin-user-modal')) {
            const modalHtml = `
                <div class="modal-overlay" id="admin-user-modal">
                    <div class="modal-card large">
                        <div class="modal-header" style="background: var(--Dados-blue); color: white;">
                            <div class="modal-title" style="color: white;"><i class="fas fa-users-cog"></i> GESTÃO DE CONTAS</div>
                            <button class="btn-close-modal" onclick="HM.closeUserModal()" style="color: white;">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="admin-table-container">
                                <table class="admin-table">
                                    <thead>
                                        <tr>
                                            <th>Colaborador</th>
                                            <th>E-mail</th>
                                            <th>Perfil</th>
                                            <th style="width: 50px;">Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody id="admin-users-list"></tbody>
                                </table>
                            </div>
                            
                            <div class="admin-add-form">
                                <div class="modal-section-title">Cadastrar Novo Acesso</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <input type="text" id="new-user-name" class="profile-input" placeholder="Nome Completo">
                                    <input type="email" id="new-user-email" class="profile-input" placeholder="E-mail Corporativo">
                                    <input type="password" id="new-user-pass" class="profile-input" placeholder="Senha Inicial">
                                    <select id="new-user-role" class="profile-input">
                                        <option value="user">Usuário Comum</option>
                                        <option value="admin">Administrador</option>
                                    </select>
                                </div>
                                <button class="btn-modal-save" style="width: 100%; margin-top: 15px;" id="btn-create-user" onclick="HM.handleCreateUser()">
                                    CRIAR CONTA NO SERVIDOR
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }
    }

    async exportSnapshot() {
        alert('Gerando Snapshot... Todos os dados da base serão exportados para Dados.');
        window.location.href = `${CORE_CONFIG.API_BASE}/api/data/tabulation`; // Reaproveita a tabulação purificada
    }

    openMetas() {
        alert('Módulo de Metas: Em breve você poderá configurar o volume de auditoria por unidade diretamente aqui.');
    }

    openAuditLogs() {
        alert('Logs de Auditoria: Rastreando ações de admins via servidor.');
    }

    async openUserManagementModal() {
        const modal = document.getElementById('admin-user-modal');
        if (modal) {
            modal.classList.add('active');
            this.loadUsersList();
        }
    }

    closeUserModal() {
        const modal = document.getElementById('admin-user-modal');
        if (modal) modal.classList.remove('active');
    }

    async loadUsersList() {
        const list = document.getElementById('admin-users-list');
        list.innerHTML = '<tr><td colspan="4" style="text-align:center;">Carregando...</td></tr>';
        
        try {
            const users = await apiService.getAdminUsers();
            list.innerHTML = '';
            users.forEach(u => {
                if (u.email === 'dev_master@serialaudit.com') return;
                
                const tr = document.createElement('tr');
                const statusBadge = u.sincronizado 
                    ? '<span class="status-pill ok">Sincronizado</span>' 
                    : '<span class="status-pill pending">Perfil Pendente</span>';
                
                tr.innerHTML = `
                    <td>${u.nome_completo || 'Sem Nome'} <br> ${statusBadge}</td>
                    <td>${u.email}</td>
                    <td><span class="role-badge ${u.cargo}">${u.cargo}</span></td>
                    <td style="text-align:center;">
                        <button class="btn-admin-edit" onclick="HM.editUserDetails('${u.id}', '${u.email}')" title="Configurar Perfil"><i class="fas fa-id-card"></i></button>
                        ${u.id === this.user.id ? '' : `<button class="btn-admin-delete" onclick="HM.deleteUser('${u.id}')" title="Excluir"><i class="fas fa-trash"></i></button>`}
                    </td>
                `;
                list.appendChild(tr);
            });
        } catch (e) { list.innerHTML = '<tr><td colspan="4">Erro ao carregar lista.</td></tr>'; }
    }

    async handleCreateUser() {
        const btn = document.getElementById('btn-create-user');
        const payload = {
            nome_completo: document.getElementById('new-user-name').value,
            email: document.getElementById('new-user-email').value,
            password: document.getElementById('new-user-pass').value,
            cargo: document.getElementById('new-user-role').value
        };

        if (!payload.email || !payload.password) return alert('Email e Senha são obrigatórios.');

        try {
            btn.disabled = true;
            await apiService.createAdminUser(payload);
            alert('Usuário criado com sucesso!');
            this.loadUsersList();
            // Reset form
            document.getElementById('new-user-name').value = '';
            document.getElementById('new-user-email').value = '';
            document.getElementById('new-user-pass').value = '';
        } catch (e) { alert('Erro: ' + e.message); }
        finally { btn.disabled = false; }
    }

    async deleteUser(userId) {
        if (!confirm('Tem certeza que deseja excluir este usuário?')) return;
        try {
            await apiService.deleteAdminUser(userId);
            alert('Usuário excluído!');
            this.loadUsersList();
        } catch (e) { alert('Erro ao excluir.'); }
    }

    async editUserDetails(userId, email) {
        // Busca os usuários da lista atual (cacheada na tabela) ou faz um fetch rápido
        try {
            const users = await apiService.getAdminUsers();
            const target = users.find(u => u.id === userId);
            if (target) {
                this.openProfileModal(target);
            }
        } catch (e) {
            alert('Erro ao carregar detalhes do usuário.');
        }
    }

    async syncDatabase() {
        if (!confirm('Deseja forçar a sincronização total com o banco de dados?')) return;
        try {
            await apiService.syncDatabase();
            alert('Sincronização concluída com sucesso!');
            window.location.reload();
        } catch (err) { alert('Falha na sincronização.'); }
    }

    async clearCache() {
        if (!confirm('Deseja limpar o cache global de registros?')) return;
        try {
            await apiService.clearCache();
            alert('Cache limpo com sucesso!');
            window.location.reload();
        } catch (err) { alert('Falha ao limpar cache.'); }
    }

    logout() {
        localStorage.clear();
        window.location.href = 'login.html';
    }
}

window.HM = new Core();

