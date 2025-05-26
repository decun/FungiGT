// src/scripts/initDatabase.js

const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

// URI de MongoDB
const MONGODB_URI = 'mongodb+srv://admin:admin44@genomictools.b2hfvdg.mongodb.net/?retryWrites=true&w=majority&appName=GenomicTools';

// Definición del esquema de usuario
const userSchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        unique: true,
        trim: true
    },
    email: {
        type: String,
        required: true,
        unique: true,
        trim: true,
        lowercase: true
    },
    password: {
        type: String,
        required: true
    },
    firstName: {
        type: String,
        required: true,
        trim: true
    },
    lastName: {
        type: String,
        required: true,
        trim: true
    },
    role: {
        type: String,
        enum: ['admin', 'researcher', 'viewer'],
        default: 'researcher'
    },
    isActive: {
        type: Boolean,
        default: true
    },
    lastLogin: {
        type: Date
    },
    profileImage: {
        type: String,
        default: null
    },
    createdAt: {
        type: Date,
        default: Date.now
    },
    updatedAt: {
        type: Date,
        default: Date.now
    }
});

// Conectar a MongoDB
async function connectDB() {
    try {
        await mongoose.connect(MONGODB_URI);
        console.log('✅ Conectado a MongoDB Atlas');
    } catch (error) {
        console.error('❌ Error conectando a MongoDB:', error);
        process.exit(1);
    }
}

// Crear colecciones e índices
async function setupCollections() {
    try {
        // Obtener referencia a la base de datos
        const db = mongoose.connection.db;
        
        // Verificar si la colección de usuarios existe
        const collections = await db.listCollections().toArray();
        const collectionNames = collections.map(c => c.name);
        
        // Crear modelo de usuario
        const User = mongoose.model('User', userSchema);
        
        // Si la colección de usuarios no existe, crear índices
        if (!collectionNames.includes('users')) {
            console.log('Creando colección de usuarios e índices...');
            
            // Crear índices para búsqueda eficiente
            await User.collection.createIndex({ email: 1 }, { unique: true });
            await User.collection.createIndex({ username: 1 }, { unique: true });
            await User.collection.createIndex({ role: 1 });
            
            console.log('✅ Índices creados para la colección de usuarios');
        }
        
        // Verificar si ya existe un administrador
        const adminExists = await User.findOne({ role: 'admin' });
        
        // Si no existe administrador, crear uno predeterminado
        if (!adminExists) {
            console.log('Creando usuario administrador predeterminado...');
            
            // Generar hash de contraseña
            const salt = await bcrypt.genSalt(12);
            const hashedPassword = await bcrypt.hash('admin123', salt);
            
            // Crear administrador
            const admin = new User({
                username: 'admin',
                email: 'admin@fungigt.com',
                password: hashedPassword,
                firstName: 'Admin',
                lastName: 'FungiGT',
                role: 'admin'
            });
            
            await admin.save();
            console.log('✅ Usuario administrador creado exitosamente');
            console.log('   - Email: admin@fungigt.com');
            console.log('   - Contraseña: admin123');
        } else {
            console.log('✅ Usuario administrador ya existe');
        }
        
        console.log('✅ Configuración de base de datos completada');
    } catch (error) {
        console.error('❌ Error configurando colecciones:', error);
    }
}

// Función principal
async function initDatabase() {
    try {
        await connectDB();
        await setupCollections();
        console.log('Base de datos inicializada correctamente');
    } catch (error) {
        console.error('Error inicializando base de datos:', error);
    } finally {
        // Cerrar conexión
        mongoose.connection.close();
        console.log('Conexión cerrada');
    }
}

// Ejecutar inicialización
initDatabase();