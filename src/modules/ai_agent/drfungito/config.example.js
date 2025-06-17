// Configuración de ejemplo para Dr. Fungito AI Agent
// Copiar este archivo como config.js y completar los valores

module.exports = {
    // Configuración del servidor
    server: {
        port: process.env.PORT || 4009,
        nodeEnv: process.env.NODE_ENV || 'development'
    },

    // Configuración de Anthropic
    anthropic: {
        apiKey: process.env.ANTHROPIC_API_KEY || 'tu_api_key_aqui',
        model: 'claude-3-sonnet-20240229',
        maxTokens: {
            analysis: 1000,
            report: 2000,
            chat: 800
        },
        temperature: {
            analysis: 0.3,
            report: 0.2,
            chat: 0.4
        }
    },

    // Configuración de MongoDB
    database: {
        uri: process.env.MONGODB_URI || 'mongodb://admin:admin123@localhost:27017/fungigt?authSource=admin',
        options: {
            useNewUrlParser: true,
            useUnifiedTopology: true,
            maxPoolSize: 10,
            serverSelectionTimeoutMS: 5000,
            socketTimeoutMS: 45000
        }
    },

    // Configuración de CORS
    cors: {
        origin: process.env.FRONTEND_URL || 'http://localhost:4005',
        credentials: true
    },

    // Configuración de imágenes
    images: {
        maxSize: parseInt(process.env.MAX_IMAGE_SIZE) || 10 * 1024 * 1024, // 10MB
        allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        maxWidth: 1024,
        maxHeight: 1024,
        quality: parseInt(process.env.IMAGE_QUALITY) || 85,
        maxImagesPerUser: parseInt(process.env.MAX_IMAGES_PER_USER) || 100
    },

    // Configuración de memoria del usuario
    memory: {
        cleanupInterval: parseInt(process.env.MEMORY_CLEANUP_INTERVAL) || 24 * 60 * 60 * 1000, // 24 horas
        maxAge: parseInt(process.env.MAX_MEMORY_AGE) || 30 * 24 * 60 * 60 * 1000, // 30 días
        maxImages: 100,
        maxReports: 50
    },

    // Configuración de reportes
    reports: {
        maxLength: parseInt(process.env.MAX_REPORT_LENGTH) || 2000,
        defaultType: process.env.DEFAULT_REPORT_TYPE || 'detailed',
        types: ['detailed', 'summary', 'comparative']
    },

    // Configuración de logging
    logging: {
        level: process.env.LOG_LEVEL || 'info',
        format: 'json',
        files: {
            error: 'logs/error.log',
            combined: 'logs/combined.log'
        }
    },

    // Rate limiting
    rateLimiting: {
        windowMs: parseInt(process.env.RATE_LIMIT_WINDOW) || 15 * 60 * 1000, // 15 minutos
        max: parseInt(process.env.RATE_LIMIT_MAX) || 100, // 100 requests por ventana
        message: 'Demasiadas solicitudes desde esta IP, intenta de nuevo más tarde.'
    },

    // Tipos de análisis soportados
    analysisTypes: {
        general: 'Análisis general de imagen genómica',
        bindash: 'Análisis de resultados BinDash',
        annotation: 'Análisis de anotación genómica',
        quality: 'Análisis de control de calidad',
        phylogeny: 'Análisis filogenético',
        hmmer: 'Análisis de dominios HMMER'
    },

    // Prompts especializados por tipo de análisis
    prompts: {
        systemBase: 'Eres Dr. Fungito, un experto en genómica de hongos especializado en análisis bioinformático.',
        analysisPrefix: 'Analiza esta imagen científica/gráfico genómico y proporciona:',
        reportPrefix: 'Genera un reporte detallado integrando estos análisis genómicos:'
    }
};

// Validar configuración requerida
function validateConfig() {
    const config = module.exports;
    
    if (!config.anthropic.apiKey || config.anthropic.apiKey === 'tu_api_key_aqui') {
        console.warn('⚠️  ADVERTENCIA: ANTHROPIC_API_KEY no configurada. El agente no funcionará correctamente.');
    }
    
    if (!config.database.uri.includes('mongodb://')) {
        console.warn('⚠️  ADVERTENCIA: URI de MongoDB parece ser inválida.');
    }
    
    console.log('✅ Configuración de Dr. Fungito cargada correctamente');
}

// Ejecutar validación al cargar
validateConfig(); 