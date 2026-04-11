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
        }
    }

    async syncUserProfile() {
        try {
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/profile`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (res.ok) {
                const profile = await res.json();
                if (this.elements.displayName) this.elements.displayName.textContent = profile.nome_completo;
                this.user = { ...this.user, ...profile };
                localStorage.setItem('hm_user', JSON.stringify(this.user));
            }
        } catch (err) { console.warn('[Core] Sync Profile Fail'); }
    }

    bindGlobalEvents() {
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('user-dropdown');
            const trigger = document.getElementById('user-menu-trigger');
            if (dropdown && dropdown.classList.contains('active')) {
                if (!trigger.contains(e.target)) dropdown.classList.remove('active');
            }
        });
    }

    // --- MÉTODOS PÚBLICOS ---

    toggleUserMenu(event) {
        if (event) event.stopPropagation();
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) dropdown.classList.toggle('active');
    }

    async openProfileModal() {
        const modal = document.getElementById('profile-modal');
        if (!modal) return;

        try {
            const res = await fetch(`${CORE_CONFIG.API_BASE}/api/user/profile`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const profile = await res.json();

            // Atribuição de Valores
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

    logout() {
        localStorage.clear();
        window.location.href = 'login.html';
    }
}

window.HM = new Core();
