const express = require('express');
const AuthService = require('../services/AuthService');
const { authenticateToken, requireAdmin, requireOwnershipOrAdmin } = require('../middleware/authMiddleware');
const router = express.Router();

// Registro de usuario
router.post('/register', async (req, res) => {
    try {
        const { username, email, password, firstName, lastName } = req.body;

        // Validaciones básicas
        if (!username || !email || !password || !firstName || !lastName) {
            return res.status(400).json({
                error: 'Todos los campos son requeridos',
                code: 'MISSING_FIELDS'
            });
        }

        if (password.length < 6) {
            return res.status(400).json({
                error: 'La contraseña debe tener al menos 6 caracteres',
                code: 'INVALID_PASSWORD'
            });
        }

        const result = await AuthService.register({
            username,
            email,
            password,
            firstName,
            lastName
        });

        res.status(201).json({
            message: 'Usuario registrado exitosamente',
            user: result.user,
            token: result.token,
            refreshToken: result.refreshToken
        });
    } catch (error) {
        res.status(400).json({
            error: error.message,
            code: 'REGISTRATION_ERROR'
        });
    }
});

// Inicio de sesión
router.post('/login', async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({
                error: 'Email y contraseña son requeridos',
                code: 'MISSING_CREDENTIALS'
            });
        }

        const result = await AuthService.login(email, password);

        res.json({
            message: 'Inicio de sesión exitoso',
            user: result.user,
            token: result.token,
            refreshToken: result.refreshToken
        });
    } catch (error) {
        res.status(401).json({
            error: error.message,
            code: 'LOGIN_ERROR'
        });
    }
});

// Obtener perfil del usuario actual
router.get('/profile', authenticateToken, async (req, res) => {
    try {
        const user = await AuthService.getUserById(req.user.id);
        res.json({ user });
    } catch (error) {
        res.status(404).json({
            error: error.message,
            code: 'USER_NOT_FOUND'
        });
    }
});

// Cambiar contraseña
router.post('/change-password', authenticateToken, async (req, res) => {
    try {
        const { currentPassword, newPassword } = req.body;

        if (!currentPassword || !newPassword) {
            return res.status(400).json({
                error: 'Contraseña actual y nueva son requeridas',
                code: 'MISSING_PASSWORD_FIELDS'
            });
        }

        if (newPassword.length < 6) {
            return res.status(400).json({
                error: 'La nueva contraseña debe tener al menos 6 caracteres',
                code: 'INVALID_NEW_PASSWORD'
            });
        }

        const result = await AuthService.changePassword(
            req.user.id,
            currentPassword,
            newPassword
        );

        res.json(result);
    } catch (error) {
        res.status(400).json({
            error: error.message,
            code: 'PASSWORD_CHANGE_ERROR'
        });
    }
});

// Actualizar perfil
router.put('/profile', authenticateToken, async (req, res) => {
    try {
        const { firstName, lastName, username, profileImage } = req.body;
        
        const updateData = {};
        if (firstName) updateData.firstName = firstName;
        if (lastName) updateData.lastName = lastName;
        if (username) updateData.username = username;
        if (profileImage) updateData.profileImage = profileImage;

        const updatedUser = await AuthService.updateProfile(req.user.id, updateData);
        
        res.json({
            message: 'Perfil actualizado exitosamente',
            user: updatedUser
        });
    } catch (error) {
        res.status(400).json({
            error: error.message,
            code: 'PROFILE_UPDATE_ERROR'
        });
    }
});

// Renovar token de acceso con refresh token
router.post('/refresh-token', async (req, res) => {
    try {
        const { refreshToken } = req.body;
        
        if (!refreshToken) {
            return res.status(400).json({
                error: 'Refresh token es requerido',
                code: 'MISSING_REFRESH_TOKEN'
            });
        }
        
        const result = await AuthService.refreshAccessToken(refreshToken);
        
        res.json({
            message: 'Token renovado exitosamente',
            token: result.token
        });
    } catch (error) {
        res.status(401).json({
            error: error.message,
            code: 'REFRESH_TOKEN_ERROR'
        });
    }
});

// Verificar token
router.get('/verify', authenticateToken, (req, res) => {
    res.json({
        valid: true,
        user: {
            id: req.user.id,
            username: req.user.username,
            email: req.user.email,
            role: req.user.role
        }
    });
});

// ---- RUTAS DE ADMINISTRACIÓN ----

// Listar todos los usuarios (solo admin)
router.get('/users', authenticateToken, requireAdmin, async (req, res) => {
    try {
        const page = parseInt(req.query.page) || 1;
        const limit = parseInt(req.query.limit) || 10;
        const search = req.query.search || '';
        
        const result = await AuthService.getAllUsers(page, limit, search);
        
        res.json(result);
    } catch (error) {
        res.status(500).json({
            error: error.message,
            code: 'USER_LIST_ERROR'
        });
    }
});

// Actualizar rol de usuario (solo admin)
router.put('/users/:userId/role', authenticateToken, requireAdmin, async (req, res) => {
    try {
        const { userId } = req.params;
        const { role } = req.body;
        
        if (!role) {
            return res.status(400).json({
                error: 'Rol es requerido',
                code: 'MISSING_ROLE'
            });
        }
        
        const updatedUser = await AuthService.updateUserRole(userId, role);
        
        res.json({
            message: 'Rol actualizado exitosamente',
            user: updatedUser
        });
    } catch (error) {
        res.status(400).json({
            error: error.message,
            code: 'ROLE_UPDATE_ERROR'
        });
    }
});

// Activar/desactivar usuario (solo admin)
router.put('/users/:userId/status', authenticateToken, requireAdmin, async (req, res) => {
    try {
        const { userId } = req.params;
        const { isActive } = req.body;
        
        if (isActive === undefined) {
            return res.status(400).json({
                error: 'Estado de activación es requerido',
                code: 'MISSING_STATUS'
            });
        }
        
        const updatedUser = await AuthService.toggleUserActive(userId, isActive);
        
        res.json({
            message: `Usuario ${isActive ? 'activado' : 'desactivado'} exitosamente`,
            user: updatedUser
        });
    } catch (error) {
        res.status(400).json({
            error: error.message,
            code: 'STATUS_UPDATE_ERROR'
        });
    }
});

// Crear admin inicial (solo para inicialización del sistema)
router.post('/init-admin', async (req, res) => {
    try {
        const { username, email, password, firstName, lastName } = req.body;
        
        if (!username || !email || !password || !firstName || !lastName) {
            return res.status(400).json({
                error: 'Todos los campos son requeridos',
                code: 'MISSING_FIELDS'
            });
        }
        
        const result = await AuthService.createAdminUser({
            username,
            email,
            password,
            firstName,
            lastName
        });
        
        res.status(201).json(result);
    } catch (error) {
        res.status(400).json({
            error: error.message,
            code: 'ADMIN_CREATION_ERROR'
        });
    }
});

module.exports = router; 