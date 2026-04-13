/* HM CONTROL - Core Orchestrator (v5.1 - Final) */

const CORE_CONFIG = {
    API_BASE: window.location.origin
};

class Core {
    constructor() {
        this.user = JSON.parse(localStorage.getItem('hm_user')) || null;
        this.token = localStorage.getItem('hm_token') || null;
        this.elements = {}; 
        
        console.log('[Core] Sistema v5.1 Iniciado.');
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
        if (!this.user && !isLoginPage) {
            window.location.href = 'login.html';
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
        
        if (this.elements.displayName) {
            const fallbackName = this.user.nome_completo || this.user.email.split('@')[0];
            this.elements.displayName.textContent = fallbackName;
        }

        if (this.token) {
            this.syncUserProfile();
            this.injectAdminFeatures();
            this.applyAccessRestrictions();
        }
    }

    applyAccessRestrictions() {
        if (!this.user) return;
        const isAdmin = this.user.cargo === 'admin';
        const allowedScreens = this.user.acessos || ['dashboard'];

        document.querySelectorAll('.nav-link').forEach(link => {
            const href = link.getAttribute('href');
            if (!href || href.includes('index.html') || href === 'javascript:void(0)') return;

            const screenName = href.replace('.html', '').replace('/', '');
            
            if (!isAdmin && !allowedScreens.includes(screenName)) {
                link.parentElement.style.display = 'none'; 
            } else {
                link.parentElement.style.display = 'block';
            }
        });
    }

    async syncUserProfile() {
        if (!this.user || !this.user.id) return;
        try {
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/profile?user_id=${this.user.id}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (res.ok) {
                const profile = await res.json();
                if (this.elements.displayName) {
                    const name = profile.nome_completo || profile.email.split('@')[0];
                    this.elements.displayName.textContent = name;
                }
                this.user = { ...this.user, ...profile };
                localStorage.setItem('hm_user', JSON.stringify(this.user));
            }
        } catch (err) { console.warn('[Core] Sync Profile Fail'); }
    }

    bindGlobalEvents() {
        document.addEventListener('click', (e) => {
            // Dropdown de Usuário
            const dropdown = document.getElementById('user-dropdown');
            const trigger = document.getElementById('user-menu-trigger');
            if (dropdown && dropdown.classList.contains('active')) {
                if (!trigger.contains(e.target)) dropdown.classList.remove('active');
            }

            // Menu Mobile (Responsivo)
            const navLinks = document.querySelector('.nav-links');
            const mobileTrigger = document.getElementById('mobile-menu-toggle');
            if (navLinks && navLinks.classList.contains('active') && mobileTrigger) {
                if (!mobileTrigger.contains(e.target) && !navLinks.contains(e.target)) {
                    navLinks.classList.remove('active');
                }
            }
        });
    }

    // --- MÉTODOS PÚBLICOS ---

    toggleUserMenu(event) {
        if (event) event.stopPropagation();
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) dropdown.classList.toggle('active');
    }

    toggleMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        if (navLinks) {
            navLinks.classList.toggle('active');
        }
    }

    async openProfileModal(externalUser = null) {
        const modal = document.getElementById('profile-modal');
        if (!modal) return;

        try {
            // Se externalUser for passado (Admin), usamos os dados dele
            // Caso contrário, buscamos do usuário logado diretamente do Supabase
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
                alert('Sucesso: Perfil e Senha sincronizados no Supabase.');
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
        if (!this.user || this.user.cargo !== 'admin') return;
        
        // 1. Localizar o container de navegação ou dropdown de configurações
        const navDropdown = document.querySelector('.nav-dropdown-content');
        if (navDropdown) {
            console.log('[Core] Injetando Elite Hub Administrativo.');
            // Garantir que o texto seja visível colocando estilo inline se necessário
            navDropdown.style.visibility = 'visible';
            navDropdown.style.opacity = '1';
            
            navDropdown.innerHTML = `
                <a href="javascript:HM.syncDatabase()" style="color: #475569 !important;"><i class="fas fa-sync"></i> Sistema (Sincronizar)</a>
                <a href="javascript:HM.openUserManagementModal()" style="color: #475569 !important;"><i class="fas fa-users-cog"></i> Gestão de Contas</a>
                <a href="javascript:HM.exportSnapshot()" style="color: #475569 !important;"><i class="fas fa-file-excel"></i> Snapshots (Backup)</a>
                <a href="javascript:HM.openMetas()" style="color: #475569 !important;"><i class="fas fa-bullseye"></i> Configurar Metas</a>
                <a href="javascript:HM.openAuditLogs()" style="color: #475569 !important;"><i class="fas fa-history"></i> Logs de Auditoria</a>
                <a href="javascript:HM.clearCache()" style="color: var(--danger) !important;"><i class="fas fa-eraser"></i> Limpar Cache</a>
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
                        <div class="modal-header" style="background: var(--excel-blue); color: white;">
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
                                    CRIAR CONTA NO SUPABASE
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
        alert('Gerando Snapshot... Todos os dados do Supabase serão exportados para Excel.');
        window.location.href = `${CORE_CONFIG.API_BASE}/api/excel/tabulation`; // Reaproveita a tabulação purificada
    }

    openMetas() {
        alert('Módulo de Metas: Em breve você poderá configurar o volume de auditoria por unidade diretamente aqui.');
    }

    openAuditLogs() {
        alert('Logs de Auditoria: Rastreando ações de Julia e outros administradores via Supabase.');
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
