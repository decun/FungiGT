const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path');
const mongoose = require('./config/database');
const cors = require('cors');
const frontRoutes = require('./routes/index');
const authRoutes = require('./routes/authRoutes');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');
const dotenv = require('dotenv');

// Cargar variables de entorno
dotenv.config();

const app = express();
const PORT = process.env.FRONTEND_PORT || 4005;

// Middleware
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());
app.use(session({
  secret: process.env.SESSION_SECRET || 'default_session_secret',
  resave: false,
  saveUninitialized: true
}));
app.use(express.static(path.join(__dirname, 'public')));
app.use(cors());
app.use(cookieParser());

// View engine setup
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middleware para verificar la autenticación en las páginas protegidas
const requireAuth = (req, res, next) => {
    const publicPaths = ['/auth/login', '/auth/register', '/', '/landing'];
    const isPublicPath = publicPaths.some(path => req.path.startsWith(path));
    
    if (!isPublicPath) {
        // Verificar token JWT
        const token = req.cookies.token || req.headers.authorization?.split(' ')[1];
        
        if (!token) {
            return res.redirect('/auth/login');
        }
        
        try {
            // Verificar el token usando la clave secreta de las variables de entorno
            const decoded = jwt.verify(token, process.env.JWT_SECRET || 'default_jwt_secret');
            req.user = decoded;
            next();
        } catch (error) {
            console.error('Error de autenticación:', error);
            res.clearCookie('token');
            return res.redirect('/auth/login?error=session_expired');
        }
    } else {
        next();
    }
};

// Routes
const indexRoutes = require('./routes/index');
const annotatorRoutes = require('./routes/annotator');
const databaseRoutes = require('./routes/database');
const analyzerRoutes = require('./routes/analyzer');
const visualizerRoutes = require('./routes/visualizer');

app.use(requireAuth);
app.use('/', indexRoutes);
app.use('/auth', authRoutes);
app.use('/annotator', annotatorRoutes);
app.use('/database', databaseRoutes);
app.use('/analyzer', analyzerRoutes);
app.use('/visualizer', visualizerRoutes);

// Ruta de fallback
app.use((req, res) => {
    res.status(404).render('404', {
        title: 'Página no encontrada | FungiGT',
        description: 'La página que buscas no existe'
    });
});

// Start server
app.listen(PORT, () => {
  console.log(`Frontend ejecutándose en puerto ${PORT}`);
});

module.exports = app;
