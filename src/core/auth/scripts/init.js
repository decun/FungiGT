const AuthService = require('../services/AuthService');
const dbConnection = require('../../database/connection');
const dotenv = require('dotenv');

// Cargar variables de entorno
dotenv.config();

// Usuario admin por defecto
const DEFAULT_ADMIN = {
    username: 'admin',
    email: 'admin@fungigt.com',
    password: 'Admin@123',
    firstName: 'Admin',
    lastName: 'FungiGT',
    role: 'admin'
};

// Inicializar la base de datos con un usuario admin
async function initializeDatabase() {
    try {
        console.log('🔄 Iniciando conexión a la base de datos...');
        await dbConnection.connect();
        
        console.log('🔍 Verificando si existe un usuario admin...');
        const authService = new AuthService();
        
        try {
            // Intentar crear un usuario admin
            await authService.createAdminUser(DEFAULT_ADMIN);
            console.log('✅ Usuario admin creado exitosamente');
        } catch (error) {
            if (error.message.includes('ya existe')) {
                console.log('ℹ️ El usuario admin ya existe');
            } else {
                throw error;
            }
        }
        
        console.log('✅ Inicialización completada con éxito');
    } catch (error) {
        console.error('❌ Error durante la inicialización:', error);
    } finally {
        // Cerrar la conexión
        await dbConnection.disconnect();
        process.exit(0);
    }
}

// Ejecutar la inicialización
initializeDatabase(); 