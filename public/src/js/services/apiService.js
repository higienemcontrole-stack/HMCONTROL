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
    async login(email, password) {
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.LOGIN}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        if (!response.ok) throw new Error('Falha na autenticação');
        return response.json();
    },

    async saveRegistro(payload) {
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.REGISTROS}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return response.json();
    },

    async getStats() {
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.STATS}`);
        return response.json();
    },

    async getValidations() {
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.VALIDATIONS}`);
        return response.json();
    },

    async getAdminUsers() {
        const token = localStorage.getItem('hm_token');
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_USERS}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.json();
    },

    async createAdminUser(payload) {
        const token = localStorage.getItem('hm_token');
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_USERS}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        return response.json();
    },

    async deleteAdminUser(userId) {
        const token = localStorage.getItem('hm_token');
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_USERS}/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.json();
    },

    async resetAdminPassword(userId, newPassword) {
        const token = localStorage.getItem('hm_token');
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_RESET_PW}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ user_id: userId, new_password: newPassword })
        });
        return response.json();
    },

    async clearCache() {
        const token = localStorage.getItem('hm_token');
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_CACHE}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.json();
    },

    async syncDatabase() {
        const token = localStorage.getItem('hm_token');
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.ADMIN_SYNC}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.json();
    }
};

window.apiService = apiService;
