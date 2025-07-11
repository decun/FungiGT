const express = require('express');
const axios = require('axios');
const router = express.Router();

// URL del servicio de autenticación
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://auth:4001';

// Middleware para hacer proxy de las peticiones al servicio de autenticación
const authProxyMiddleware = async (req, res, next) => {
    try {
        // Construir la URL del servicio de autenticación
        const targetUrl = `${AUTH_SERVICE_URL}/api/auth${req.path}`;
        
        // Configurar headers
        const headers = {
            'Content-Type': 'application/json',
            ...req.headers
        };

        // Remover headers que no deben ser enviados
        delete headers.host;
        delete headers.origin;
        delete headers.referer;

        // Configurar las opciones de la petición
        const options = {
            method: req.method,
            url: targetUrl,
            headers: headers,
            data: req.body
        };

        // Hacer la petición al servicio de autenticación
        const response = await axios(options);
        
        // Retornar la respuesta del servicio de autenticación
        res.status(response.status).json(response.data);
    } catch (error) {
        console.error('Error en proxy de autenticación:', error.message);
        
        if (error.response) {
            // Si hay una respuesta del servicio de autenticación
            res.status(error.response.status).json(error.response.data);
        } else {
            // Error de conexión o del middleware
            res.status(500).json({
                error: 'Error de conexión con el servicio de autenticación',
                code: 'AUTH_SERVICE_ERROR'
            });
        }
    }
};

module.exports = authProxyMiddleware; 