const mongoose = require('mongoose');

class DatabaseConnection {
    constructor() {
        this.isConnected = false;
        this.maxRetries = 5;
        this.retryDelay = 5000; // 5 segundos
    }

    async connect() {
        if (this.isConnected) {
            console.log('📦 Base de datos ya conectada');
            return;
        }

        const mongoUri = process.env.MONGODB_URI || 'mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin';
        
        console.log('🔄 Conectando a MongoDB...');
        console.log(`📍 URI: ${mongoUri.replace(/\/\/.*@/, '//***:***@')}`); // Ocultar credenciales en logs

        let retries = 0;
        
        while (retries < this.maxRetries) {
            try {
                await mongoose.connect(mongoUri, {
                    serverSelectionTimeoutMS: 10000, // 10 segundos
                    connectTimeoutMS: 10000,
                    socketTimeoutMS: 45000,
                    maxPoolSize: 10,
                    retryWrites: true,
                    w: 'majority'
                });

                this.isConnected = true;
                console.log('✅ Conectado exitosamente a MongoDB');
                
                // Configurar eventos de conexión
                this.setupConnectionEvents();
                
                return;
            } catch (error) {
                retries++;
                console.error(`❌ Error conectando a MongoDB (intento ${retries}/${this.maxRetries}):`, error.message);
                
                if (retries < this.maxRetries) {
                    console.log(`⏳ Reintentando en ${this.retryDelay/1000} segundos...`);
                    await this.delay(this.retryDelay);
                } else {
                    console.error('💥 Máximo número de reintentos alcanzado');
                    throw error;
                }
            }
        }
    }

    setupConnectionEvents() {
        mongoose.connection.on('error', (error) => {
            console.error('❌ Error de conexión MongoDB:', error);
            this.isConnected = false;
        });

        mongoose.connection.on('disconnected', () => {
            console.warn('⚠️ Desconectado de MongoDB');
            this.isConnected = false;
        });

        mongoose.connection.on('reconnected', () => {
            console.log('🔄 Reconectado a MongoDB');
            this.isConnected = true;
        });

        // Cerrar conexión cuando la aplicación se cierra
        process.on('SIGINT', async () => {
            console.log('🛑 Cerrando conexión a MongoDB...');
            await mongoose.connection.close();
            process.exit(0);
        });
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async disconnect() {
        if (this.isConnected) {
            await mongoose.connection.close();
            this.isConnected = false;
            console.log('🔌 Desconectado de MongoDB');
        }
    }

    getStatus() {
        return {
            connected: this.isConnected,
            readyState: mongoose.connection.readyState,
            host: mongoose.connection.host,
            port: mongoose.connection.port,
            name: mongoose.connection.name
        };
    }
}

// Exportar instancia singleton
const dbConnection = new DatabaseConnection();
module.exports = dbConnection; 