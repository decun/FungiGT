const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const authRoutes = require('./routes/authRoutes');
const dbConnection = require('./database/connection');

// Cargar variables de entorno
dotenv.config();

// Inicializar app
const app = express();
const PORT = process.env.AUTH_PORT || 4001;

// Middlewares
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors());

// Rutas
app.use('/api/auth', authRoutes);

// Ruta de verificación de estado
app.get('/health', (req, res) => {
    res.json({
        service: 'auth-service',
        status: 'ok',
        timestamp: new Date()
    });
});

// Manejo de errores
app.use((err, req, res, next) => {
    console.error('Error:', err);
    res.status(500).json({
        error: 'Error interno del servidor',
        message: err.message
    });
});

// Conexión a la base de datos y arranque del servidor
async function startServer() {
    try {
        // Conectar a MongoDB
        await dbConnection.connect();
        
        // Iniciar servidor
        app.listen(PORT, () => {
            console.log(`🔐 Servicio de autenticación ejecutándose en el puerto ${PORT}`);
        });
    } catch (error) {
        console.error('❌ Error al iniciar el servicio de autenticación:', error);
        process.exit(1);
    }
}

// Si este archivo se ejecuta directamente, iniciar el servidor
if (require.main === module) {
    startServer();
}

module.exports = {
    app,
    startServer
}; 