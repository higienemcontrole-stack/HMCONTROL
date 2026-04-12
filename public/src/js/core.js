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
        }
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

    async openProfileModal() {
        if (!this.user || !this.user.id) return;
        const modal = document.getElementById('profile-modal');
        if (!modal) return;

        try {
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/profile?user_id=${this.user.id}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const profile = await res.json();

            // Atribuição de Valores (População Real do Supabase)
            document.getElementById('profile-name').value = profile.nome_completo || '';
            document.getElementById('profile-email').value = profile.email || '';
            document.getElementById('profile-password').value = ''; 
            
            const roleEl = document.getElementById('profile-role');
            const isAdmin = profile.cargo === 'admin';
            
            if (roleEl) {
                roleEl.value = profile.cargo || 'user';
                roleEl.disabled = !isAdmin; // Só Admin muda cargo
            }
            
            const screenList = document.getElementById('profile-screens');
            if (screenList) {
                const checks = screenList.querySelectorAll('input[type="checkbox"]');
                const userScreens = profile.acessos || ['dashboard'];

                checks.forEach(check => {
                    if (check.value !== 'dashboard') {
                        check.checked = isAdmin || userScreens.includes(check.value);
                        check.disabled = !isAdmin; // Só Admin muda acessos
                    }
                });
            }

            modal.classList.add('active');
        } catch (err) { alert('Erro ao abrir perfil.'); }
    }

    closeProfileModal() {
        const modal = document.getElementById('profile-modal');
        if (modal) modal.classList.remove('active');
    }

    async saveProfileData() {
        const btn = document.getElementById('btn-save-profile');
        const pass = document.getElementById('profile-password').value;
        
        const payload = {
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
                alert('Sucesso: Perfil e Senha (se alterada) atualizados no Supabase.');
                this.closeProfileModal();
                this.refreshUI();
            } else {
                const err = await res.json();
                throw new Error(err.detail || 'Erro ao salvar');
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
        
        // 1. Adicionar Botão no Dropdown se não existir
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown && !document.getElementById('btn-admin-users')) {
            const btn = document.createElement('button');
            btn.id = 'btn-admin-users';
            btn.className = 'dropdown-item';
            btn.style.color = 'var(--primary)';
            btn.innerHTML = '<i class="fas fa-users-cog"></i> Gestão de Usuários';
            btn.onclick = () => this.openUserManagementModal();
            dropdown.prepend(btn);
        }

        // 2. Injetar Modal de Usuários se não existir
        if (!document.getElementById('admin-user-modal')) {
            const modalHtml = `
                <div class="modal-overlay" id="admin-user-modal">
                    <div class="modal-card large">
                        <div class="modal-header" style="background: var(--primary); color: white;">
                            <div class="modal-title" style="color: white;"><i class="fas fa-users"></i> Gestão de Equipe</div>
                            <button class="btn-close-modal" onclick="HM.closeUserModal()" style="color: white;">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="admin-table-container">
                                <table class="admin-table">
                                    <thead>
                                        <tr>
                                            <th>Nome</th>
                                            <th>Email</th>
                                            <th>Cargo</th>
                                            <th style="width: 50px;">Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody id="admin-users-list">
                                        <!-- Carregado via JS -->
                                    </tbody>
                                </table>
                            </div>
                            
                            <div class="admin-add-form">
                                <div class="modal-section-title">Cadastrar Novo Usuário</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <input type="text" id="new-user-name" class="profile-input" placeholder="Nome Completo">
                                    <input type="email" id="new-user-email" class="profile-input" placeholder="Email">
                                    <input type="password" id="new-user-pass" class="profile-input" placeholder="Senha Inicial">
                                    <select id="new-user-role" class="profile-input">
                                        <option value="user">Usuário Comum</option>
                                        <option value="admin">Administrador</option>
                                    </select>
                                </div>
                                <button class="btn-modal-save" style="width: 100%; margin-top: 15px;" id="btn-create-user" onclick="HM.handleCreateUser()">
                                    Criar Usuário
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }
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
                tr.innerHTML = `
                    <td>${u.nome_completo || 'Sem Nome'}</td>
                    <td>${u.email}</td>
                    <td><span class="role-badge ${u.cargo}">${u.cargo}</span></td>
                    <td style="text-align:center;">
                        ${u.id === this.user.id ? '' : `<button class="btn-admin-delete" onclick="HM.deleteUser('${u.id}')"><i class="fas fa-trash"></i></button>`}
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
