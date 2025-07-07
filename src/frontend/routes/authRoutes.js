const express = require('express');
const router = express.Router();
const authClient = require('../utils/authClient');

// Ruta para la página de inicio de sesión
router.get('/login', (req, res) => {
    res.render('auth/login', {
        title: 'Iniciar sesión | FungiGT',
        description: 'Accede a tu cuenta en FungiGT',
        currentPage: 'login',
        error: req.query.error
    });
});

// Procesar inicio de sesión
router.post('/login', async (req, res) => {
    try {
        const { email, password, rememberMe } = req.body;
        const result = await authClient.login(email, password);
        
        // Guardar token en cookie
        const cookieOptions = {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production'
        };
        
        if (rememberMe) {
            cookieOptions.maxAge = 7 * 24 * 60 * 60 * 1000; // 7 días
        }
        
        res.cookie('token', result.token, cookieOptions);
        res.cookie('refreshToken', result.refreshToken, cookieOptions);
        
        // Redireccionar al anotador
        res.redirect('/annotator');
    } catch (error) {
        res.render('auth/login', {
            title: 'Iniciar sesión | FungiGT',
            description: 'Accede a tu cuenta en FungiGT',
            currentPage: 'login',
            error: error.message
        });
    }
});

// Ruta para la página de registro
router.get('/register', (req, res) => {
    res.render('auth/register', {
        title: 'Crear cuenta | FungiGT',
        description: 'Crea una nueva cuenta en FungiGT',
        currentPage: 'register'
    });
});

// Procesar registro
router.post('/register', async (req, res) => {
    try {
        console.log('🔍 [DEBUG] Solicitud de registro recibida:', JSON.stringify(req.body, null, 2));
        
        const { username, email, password, firstName, lastName } = req.body;

        // Validaciones básicas
        if (!username || !email || !password || !firstName || !lastName) {
            console.log('❌ [DEBUG] Faltan campos:', { username: !!username, email: !!email, password: !!password, firstName: !!firstName, lastName: !!lastName });
            return res.status(400).json({
                error: 'Todos los campos son requeridos',
                code: 'MISSING_FIELDS'
            });
        }
        
        const result = await authClient.register({
            firstName,
            lastName,
            username,
            email,
            password
        });
        
        // Guardar token en cookie
        res.cookie('token', result.token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production'
        });
        
        res.cookie('refreshToken', result.refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production'
        });
        
        // Redireccionar al anotador
        res.redirect('/annotator');
    } catch (error) {
        console.error('❌ [DEBUG] Error en registro:', error);
        res.status(400).json({
            error: error.message,
            code: 'REGISTRATION_ERROR',
            stack: process.env.NODE_ENV === 'production' ? undefined : error.stack
        });
    }
});

// Ruta para cerrar sesión
router.get('/logout', (req, res) => {
    res.clearCookie('token');
    res.clearCookie('refreshToken');
    res.redirect('/');
});

// Ruta para la página de recuperación de contraseña
router.get('/forgot-password', (req, res) => {
    res.render('auth/forgot-password', {
        title: 'Recuperar contraseña | FungiGT',
        description: 'Recupera tu contraseña de FungiGT',
        currentPage: 'forgot-password'
    });
});

// Ruta para la página de restablecimiento de contraseña
router.get('/reset-password/:token', (req, res) => {
    res.render('auth/reset-password', {
        title: 'Restablecer contraseña | FungiGT',
        description: 'Establece una nueva contraseña para tu cuenta de FungiGT',
        currentPage: 'reset-password',
        token: req.params.token
    });
});

// Ruta para la verificación del correo electrónico
router.get('/verify-email/:token', (req, res) => {
    res.render('auth/verify-email', {
        title: 'Verificar correo | FungiGT',
        description: 'Verificación de correo electrónico de FungiGT',
        currentPage: 'verify-email',
        token: req.params.token
    });
});

// Ruta para la confirmación de registro exitoso
router.get('/registration-success', (req, res) => {
    res.render('auth/registration-success', {
        title: 'Registro Exitoso | FungiGT',
        description: 'Tu cuenta ha sido creada exitosamente'
    });
});

module.exports = router; 