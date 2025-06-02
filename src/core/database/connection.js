const mongoose = require('mongoose');
const dotenv = require('dotenv');

// Cargar variables de entorno
dotenv.config();

class DatabaseConnection {
    constructor() {
        this.connection = null;
        this.mongoUri = process.env.MONGODB_URI || 'mongodb://mongodb:27017/fungigt';
    }

    async connect() {
        try {
            this.connection = await mongoose.connect(this.mongoUri, {
                useNewUrlParser: true,
                useUnifiedTopology: true,
            });

            console.log('✅ Conectado a MongoDB Atlas');
            return this.connection;
        } catch (error) {
            console.error('❌ Error conectando a MongoDB:', error);
            throw error;
        }
    }

    async disconnect() {
        if (this.connection) {
            await mongoose.disconnect();
            console.log('🔌 Desconectado de MongoDB');
        }
    }

    getConnection() {
        return this.connection;
    }

    async isConnected() {
        return mongoose.connection.readyState === 1;
    }
}

module.exports = new DatabaseConnection(); 