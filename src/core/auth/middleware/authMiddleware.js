const AuthService = require('../services/AuthService');

// Middleware para verificar token JWT
const authenticateToken = async (req, res, next) => {
    try {
        const authHeader = req.headers['authorization'];
        const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

        if (!token) {
            return res.status(401).json({ 
                error: 'Token de acceso requerido',
                code: 'NO_TOKEN'
            });
        }

        const decoded = AuthService.verifyToken(token);
        req.user = decoded;
        next();
    } catch (error) {
        return res.status(403).json({ 
            error: 'Token inválido o expirado',
            code: 'INVALID_TOKEN'
        });
    }
};

// Middleware para verificar roles específicos
const authorizeRoles = (...roles) => {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({ 
                error: 'Usuario no autenticado',
                code: 'NOT_AUTHENTICATED'
            });
        }

        if (!roles.includes(req.user.role)) {
            return res.status(403).json({ 
                error: `Acceso denegado. Roles requeridos: ${roles.join(', ')}`,
                code: 'INSUFFICIENT_PERMISSIONS',
                requiredRoles: roles,
                userRole: req.user.role
            });
        }

        next();
    };
};

// Middleware para verificar si es admin
const requireAdmin = (req, res, next) => {
    if (!req.user) {
        return res.status(401).json({ 
            error: 'Usuario no autenticado',
            code: 'NOT_AUTHENTICATED'
        });
    }

    if (req.user.role !== 'admin') {
        return res.status(403).json({ 
            error: 'Acceso denegado. Se requiere rol de administrador',
            code: 'ADMIN_REQUIRED'
        });
    }

    next();
};

// Middleware para verificar si es researcher o admin
const requireResearcher = (req, res, next) => {
    if (!req.user) {
        return res.status(401).json({ 
            error: 'Usuario no autenticado',
            code: 'NOT_AUTHENTICATED'
        });
    }

    if (req.user.role !== 'admin' && req.user.role !== 'researcher') {
        return res.status(403).json({ 
            error: 'Acceso denegado. Se requiere rol de investigador o administrador',
            code: 'RESEARCHER_OR_ADMIN_REQUIRED'
        });
    }

    next();
};

// Middleware opcional de autenticación (no falla si no hay token)
const optionalAuth = async (req, res, next) => {
    try {
        const authHeader = req.headers['authorization'];
        const token = authHeader && authHeader.split(' ')[1];

        if (token) {
            const decoded = AuthService.verifyToken(token);
            req.user = decoded;
        }
        
        next();
    } catch (error) {
        // Si hay error en el token, continúa sin usuario
        next();
    }
};

// Middleware para verificar que el usuario puede acceder a su propio recurso
const requireOwnershipOrAdmin = (req, res, next) => {
    const resourceUserId = req.params.userId || req.params.id;
    
    if (!req.user) {
        return res.status(401).json({ 
            error: 'Usuario no autenticado',
            code: 'NOT_AUTHENTICATED'
        });
    }
    
    if (req.user.role === 'admin' || req.user.id === resourceUserId) {
        next();
    } else {
        return res.status(403).json({
            error: 'Solo puedes acceder a tus propios recursos',
            code: 'OWNERSHIP_REQUIRED'
        });
    }
};

module.exports = {
    authenticateToken,
    authorizeRoles,
    requireAdmin,
    requireResearcher,
    optionalAuth,
    requireOwnershipOrAdmin
}; 