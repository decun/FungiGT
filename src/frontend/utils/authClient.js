const axios = require('axios');

const API_URL = 'http://localhost:4001/api/auth'; // URL del servicio de autenticación

const authClient = {
    async login(email, password) {
        try {
            const response = await axios.post(`${API_URL}/login`, { email, password });
            return response.data;
        } catch (error) {
            throw new Error(error.response?.data?.error || 'Error de autenticación');
        }
    },

    async register(userData) {
        try {
            const response = await axios.post(`${API_URL}/register`, userData);
            return response.data;
        } catch (error) {
            throw new Error(error.response?.data?.error || 'Error de registro');
        }
    },

    async verifyToken(token) {
        try {
            const response = await axios.get(`${API_URL}/verify`, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            return response.data;
        } catch (error) {
            throw new Error('Token inválido');
        }
    },

    async refreshToken(refreshToken) {
        try {
            const response = await axios.post(`${API_URL}/refresh-token`, { refreshToken });
            return response.data;
        } catch (error) {
            throw new Error('Error al renovar el token');
        }
    }
};

module.exports = authClient;
