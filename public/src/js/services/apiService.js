const CONFIG = {
    API_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://localhost:8010' 
        : window.location.origin,
    ENDPOINTS: {
        LOGIN: '/api/auth/login',
        PROFILE: '/api/user/profile',
        REGISTROS: '/api/registros',
        VALIDATIONS: '/api/Dados/validations',
        DASHBOARD: '/api/Dados/dashboard',
        PIVOT: '/api/Dados/pivot',
        ADMIN_USERS: '/api/admin/users',
        ADMIN_RESET_PW: '/api/admin/users/reset-password',
        ADMIN_CACHE: '/api/admin/cache/clear',
        ADMIN_SYNC: '/api/admin/sync'
    }
};

const apiService = {
    checkAuth() {
        const isLoginPage = window.location.pathname.includes('login.html');
        const isAuthenticated = localStorage.getItem('hm_token');

        if (!isAuthenticated && !isLoginPage) {
            console.log('[Core] Sessão ausente. Redirecionando.');
            this.logout();
            return false;
        }
        return true;
    },

    logout() {
        localStorage.clear();
        if (!window.location.pathname.includes('login.html')) {
            window.location.href = 'login.html';
        }
    },

    async _fetch(url, options = {}) {
        this.checkAuth();
        const token = localStorage.getItem('hm_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers
        };

        const response = await fetch(url, { ...options, headers });
        
        if (response.status === 401 || response.status === 403) {
            console.warn('[API] Sessão expirada ou negada.');
            this.logout();
            throw new Error('Não autorizado');
        }

        return response;
    },

    async login(email, password) {
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.LOGIN}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        if (!response.ok) throw new Error('Falha na autenticação');
        return response.json();
    },

    async getDashboard(unit, month, year) {
        const url = `${CONFIG.API_URL}${CONFIG.ENDPOINTS.DASHBOARD}?unit=${unit}&month=${month}&year=${year}`;
        const res = await this._fetch(url);
        return res.json();
    },

    async getValidations() {
        const res = await this._fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.VALIDATIONS}`);
        return res.json();
    },

    async getTabulation() {
        const res = await this._fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.TABULATION || '/api/Dados/tabulation'}`);
        return res.json();
    },

    async getAdminUsers() {
        const res = await this._fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_USERS}`);
        return res.json();
    }
};

window.apiService = apiService;
