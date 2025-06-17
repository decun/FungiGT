const express = require('express');
const cors = require('cors');
const multer = require('multer');
const mongoose = require('mongoose');
const Anthropic = require('@anthropic-ai/sdk');
const sharp = require('sharp');
const winston = require('winston');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs').promises;
require('dotenv').config();

// Configuración del servidor
const app = express();
const PORT = process.env.PORT || 4009;

// Configuración de seguridad y middleware
app.use(helmet());
app.use(compression());
app.use(cors({
    origin: [
        'http://localhost:4005',      // Para acceso desde navegador
        'http://frontend:4005',       // Para acceso desde contenedor Docker
        'http://127.0.0.1:4005',      // Para acceso local alternativo
        process.env.FRONTEND_URL || 'http://localhost:4005'
    ],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-User-ID', 'Accept']
}));
app.use(morgan('combined'));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configuración de Winston para logging
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    defaultMeta: { service: 'drfungito-agent' },
    transports: [
        new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
        new winston.transports.File({ filename: 'logs/combined.log' }),
        new winston.transports.Console({
            format: winston.format.simple()
        })
    ]
});

// Configuración de Anthropic
const anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
});

// Configuración de MongoDB
const mongoUri = process.env.MONGODB_URI || 'mongodb://admin:admin123@localhost:27017/fungigt?authSource=admin';
mongoose.connect(mongoUri, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
    maxPoolSize: 10,
    serverSelectionTimeoutMS: 5000,
    socketTimeoutMS: 45000,
});

// Esquemas de MongoDB
const userMemorySchema = new mongoose.Schema({
    userId: { type: String, required: true, unique: true },
    images: [{
        imageId: String,
        filename: String,
        originalName: String,
        analysisType: String,
        uploadDate: { type: Date, default: Date.now },
        analysis: String,
        metadata: mongoose.Schema.Types.Mixed
    }],
    reports: [{
        reportId: String,
        title: String,
        content: String,
        images: [String], // Array de imageIds
        createdAt: { type: Date, default: Date.now },
        type: String // 'detailed', 'summary', 'comparative'
    }],
    lastActivity: { type: Date, default: Date.now }
});

const UserMemory = mongoose.model('UserMemory', userMemorySchema);

// Configuración de multer para carga de archivos
const storage = multer.memoryStorage();
const upload = multer({ 
    storage: storage,
    limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
    fileFilter: (req, file, cb) => {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        if (allowedTypes.includes(file.mimetype)) {
            cb(null, true);
        } else {
            cb(new Error('Tipo de archivo no permitido. Solo se permiten imágenes.'), false);
        }
    }
});

// Middleware para obtener o crear memoria del usuario
async function getUserMemory(req, res, next) {
    try {
        const userId = req.headers['x-user-id'] || 'anonymous';
        let userMemory = await UserMemory.findOne({ userId });
        
        if (!userMemory) {
            userMemory = new UserMemory({ userId, images: [], reports: [] });
            await userMemory.save();
        }
        
        req.userMemory = userMemory;
        next();
    } catch (error) {
        logger.error('Error al obtener memoria del usuario:', error);
        res.status(500).json({ error: 'Error interno del servidor' });
    }
}

// Función para optimizar imágenes
async function optimizeImage(buffer, maxWidth = 1024, maxHeight = 1024) {
    try {
        return await sharp(buffer)
            .resize(maxWidth, maxHeight, { fit: 'inside', withoutEnlargement: true })
            .jpeg({ quality: 85 })
            .toBuffer();
    } catch (error) {
        logger.error('Error al optimizar imagen:', error);
        return buffer;
    }
}

// Función para convertir imagen a base64
function bufferToBase64(buffer, mimetype) {
    return `data:${mimetype};base64,${buffer.toString('base64')}`;
}

// Función para analizar imagen con Claude
async function analyzeImageWithClaude(imageBuffer, mimetype, analysisType = 'general', userContext = '') {
    try {
        // Detectar el formato real de la imagen y convertir a PNG si es necesario
        let finalBuffer = imageBuffer;
        let finalMimetype = mimetype;
        
        try {
            const metadata = await sharp(imageBuffer).metadata();
            
            // Si el formato no coincide o hay problemas, convertir a PNG
            if (!metadata.format || metadata.format !== 'png') {
                finalBuffer = await sharp(imageBuffer)
                    .png({ quality: 90 })
                    .toBuffer();
                finalMimetype = 'image/png';
                logger.info(`Imagen convertida de ${metadata.format} a PNG para análisis`);
            } else {
                finalMimetype = 'image/png';
            }
        } catch (error) {
            // Si hay error detectando formato, forzar conversión a PNG
            logger.warn('Error detectando formato, convirtiendo a PNG:', error.message);
            finalBuffer = await sharp(imageBuffer)
                .png({ quality: 90 })
                .toBuffer();
            finalMimetype = 'image/png';
        }
        
        const base64Image = bufferToBase64(finalBuffer, finalMimetype);
        
        const prompts = {
            general: `Eres Dr. Fungito, un experto en genómica de hongos. Analiza esta imagen científica/gráfico genómico y proporciona:
1. **Tipo de análisis detectado** (ej: heatmap, dendrograma, gráfico de barras, etc.)
2. **Interpretación biológica** específica para genómica fúngica
3. **Observaciones clave** sobre patrones, tendencias o anomalías
4. **Recomendaciones** para análisis adicionales
5. **Contexto genómico** relevante para hongos

Responde en español de manera profesional pero accesible.`,
            
            bindash: `Como Dr. Fungito, especialista en genómica comparativa, analiza este resultado de BinDash:
1. **Matriz de distancias genómicas** - interpreta los valores
2. **Relaciones filogenéticas** - identifica clusters y outliers
3. **ANI (Average Nucleotide Identity)** - evalúa similitudes
4. **Recomendaciones taxonómicas** - posibles clasificaciones
5. **Calidad del análisis** - evalúa la robustez de los resultados`,
            
            annotation: `Analiza estos resultados de anotación genómica como Dr. Fungito:
1. **Categorías funcionales** dominantes (COG, GO, KEGG)
2. **Completitud del análisis** de anotación
3. **Patrones metabólicos** específicos de hongos
4. **Genes de interés** (metabolismo secundario, patogenicidad)
5. **Comparación con genomas de referencia**`,
            
            quality: `Evalúa estos resultados de control de calidad genómica:
1. **Completitud del genoma** - % de genes esenciales
2. **Contaminación detectada** - niveles y posibles fuentes
3. **Calidad del ensamblaje** - N50, gaps, contigs
4. **Recomendaciones de mejora** para el pipeline
5. **Interpretación para hongos** - estándares específicos`
        };
        
        const systemPrompt = prompts[analysisType] || prompts.general;
        
        const message = await anthropic.messages.create({
            model: "claude-3-sonnet-20240229",
            max_tokens: 1000,
            temperature: 0.3,
            system: systemPrompt,
            messages: [
                {
                    role: "user",
                    content: [
                        {
                            type: "image",
                            source: {
                                type: "base64",
                                media_type: finalMimetype,
                                data: base64Image.split(',')[1]
                            }
                        },
                        {
                            type: "text",
                            text: userContext ? `Contexto adicional: ${userContext}` : "Analiza esta imagen genómica en detalle."
                        }
                    ]
                }
            ]
        });
        
        return message.content[0].text;
    } catch (error) {
        logger.error('Error al analizar imagen con Claude:', error);
        throw new Error('Error en el análisis de imagen: ' + error.message);
    }
}

// RUTAS DE LA API

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy',
        service: 'Dr. Fungito AI Agent',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

// Información del agente
app.get('/info', (req, res) => {
    res.json({
        name: 'Dr. Fungito',
        version: '1.0.0',
        description: 'Agente de IA especializado en análisis genómico de hongos con capacidades de análisis de imágenes',
        capabilities: [
            'Análisis de imágenes genómicas',
            'Interpretación de gráficos bioinformáticos',
            'Generación de reportes detallados',
            'Memoria por usuario',
            'Análisis comparativo'
        ],
        supportedAnalysisTypes: ['general', 'bindash', 'annotation', 'quality'],
        maxImageSize: '10MB',
        supportedFormats: ['jpeg', 'png', 'gif', 'webp']
    });
});

// Subir y analizar imagen
app.post('/analyze-image', upload.single('image'), getUserMemory, async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No se proporcionó ninguna imagen' });
        }
        
        const { analysisType = 'general', userContext = '', saveToMemory = 'true' } = req.body;
        
        // Optimizar imagen
        const optimizedBuffer = await optimizeImage(req.file.buffer);
        
        // Analizar con Claude
        const analysis = await analyzeImageWithClaude(
            optimizedBuffer,
            req.file.mimetype,
            analysisType,
            userContext
        );
        
        const imageId = uuidv4();
        const result = {
            imageId,
            filename: req.file.originalname,
            analysisType,
            analysis,
            uploadDate: new Date().toISOString(),
            metadata: {
                originalSize: req.file.size,
                optimizedSize: optimizedBuffer.length,
                mimetype: req.file.mimetype,
                dimensions: await sharp(optimizedBuffer).metadata()
            }
        };
        
        // Guardar en memoria del usuario si se solicita
        if (saveToMemory === 'true') {
            req.userMemory.images.push({
                imageId,
                filename: req.file.originalname,
                originalName: req.file.originalname,
                analysisType,
                analysis,
                metadata: result.metadata
            });
            req.userMemory.lastActivity = new Date();
            await req.userMemory.save();
        }
        
        logger.info(`Imagen analizada exitosamente: ${imageId}`);
        res.json(result);
        
    } catch (error) {
        logger.error('Error al analizar imagen:', error);
        res.status(500).json({ error: error.message });
    }
});

// Obtener memoria del usuario
app.get('/memory', getUserMemory, async (req, res) => {
    try {
        const { limit = 10, type = 'all' } = req.query;
        
        let images = req.userMemory.images;
        if (type !== 'all') {
            images = images.filter(img => img.analysisType === type);
        }
        
        const result = {
            userId: req.userMemory.userId,
            totalImages: images.length,
            totalReports: req.userMemory.reports.length,
            lastActivity: req.userMemory.lastActivity,
            images: images.slice(-limit).reverse(),
            reports: req.userMemory.reports.slice(-5).reverse()
        };
        
        res.json(result);
    } catch (error) {
        logger.error('Error al obtener memoria:', error);
        res.status(500).json({ error: error.message });
    }
});

// Generar reporte detallado
app.post('/generate-report', getUserMemory, async (req, res) => {
    try {
        const { 
            imageIds = [], 
            reportType = 'detailed', 
            title = 'Reporte Genómico',
            includeAllImages = false 
        } = req.body;
        
        let selectedImages = [];
        
        if (includeAllImages) {
            selectedImages = req.userMemory.images;
        } else if (imageIds.length > 0) {
            selectedImages = req.userMemory.images.filter(img => imageIds.includes(img.imageId));
        } else {
            // Usar las últimas 5 imágenes por defecto
            selectedImages = req.userMemory.images.slice(-5);
        }
        
        if (selectedImages.length === 0) {
            return res.status(400).json({ error: 'No hay imágenes disponibles para generar el reporte' });
        }
        
        // Crear contexto para el reporte
        const context = selectedImages.map(img => ({
            filename: img.filename,
            analysisType: img.analysisType,
            analysis: img.analysis,
            uploadDate: img.uploadDate
        }));
        
        const reportPrompts = {
            detailed: `Como Dr. Fungito, genera un reporte detallado integrando estos análisis genómicos:
            
**ESTRUCTURA DEL REPORTE:**
1. **Resumen Ejecutivo** - Principales hallazgos
2. **Análisis Individual** - Interpretación de cada gráfico
3. **Análisis Comparativo** - Relaciones entre resultados
4. **Interpretación Biológica** - Significado para genómica fúngica
5. **Recomendaciones** - Próximos pasos de análisis
6. **Conclusiones** - Síntesis de resultados

**CONTEXTO DE ANÁLISIS:**
${context.map((c, i) => `
Imagen ${i + 1}: ${c.filename} (${c.analysisType})
Fecha: ${c.uploadDate}
Análisis: ${c.analysis}
`).join('\n')}

Genera un reporte profesional en español, enfocado en genómica de hongos.`,
            
            summary: `Crea un resumen ejecutivo conciso de estos análisis genómicos:
${context.map(c => `- ${c.filename}: ${c.analysis.substring(0, 200)}...`).join('\n')}`,
            
            comparative: `Realiza un análisis comparativo detallado entre estos resultados genómicos:
${context.map(c => `${c.filename} (${c.analysisType}): ${c.analysis}`).join('\n\n')}`
        };
        
        const message = await anthropic.messages.create({
            model: "claude-3-sonnet-20240229",
            max_tokens: 2000,
            temperature: 0.2,
            messages: [
                {
                    role: "user",
                    content: reportPrompts[reportType] || reportPrompts.detailed
                }
            ]
        });
        
        const reportId = uuidv4();
        const report = {
            reportId,
            title,
            content: message.content[0].text,
            images: selectedImages.map(img => img.imageId),
            type: reportType,
            createdAt: new Date()
        };
        
        // Guardar reporte en memoria
        req.userMemory.reports.push(report);
        req.userMemory.lastActivity = new Date();
        await req.userMemory.save();
        
        logger.info(`Reporte generado exitosamente: ${reportId}`);
        res.json(report);
        
    } catch (error) {
        logger.error('Error al generar reporte:', error);
        res.status(500).json({ error: error.message });
    }
});

// Chat con Dr. Fungito
app.post('/chat', getUserMemory, async (req, res) => {
    try {
        const { message, includeMemoryContext = true } = req.body;
        
        if (!message) {
            return res.status(400).json({ error: 'Mensaje requerido' });
        }
        
        let contextPrompt = `Eres Dr. Fungito, un experto en genómica de hongos. Responde de manera profesional pero amigable en español.`;
        
        if (includeMemoryContext && req.userMemory.images.length > 0) {
            const recentAnalyses = req.userMemory.images.slice(-3).map(img => 
                `- ${img.filename} (${img.analysisType}): ${img.analysis.substring(0, 150)}...`
            ).join('\n');
            
            contextPrompt += `\n\nCONTEXTO DE ANÁLISIS RECIENTES:\n${recentAnalyses}`;
        }
        
        const response = await anthropic.messages.create({
            model: "claude-3-sonnet-20240229",
            max_tokens: 800,
            temperature: 0.4,
            system: contextPrompt,
            messages: [
                {
                    role: "user",
                    content: message
                }
            ]
        });
        
        res.json({
            response: response.content[0].text,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        logger.error('Error en chat:', error);
        res.status(500).json({ error: error.message });
    }
});

// Limpiar memoria del usuario
app.delete('/memory', getUserMemory, async (req, res) => {
    try {
        const { type = 'all' } = req.query;
        
        if (type === 'images') {
            req.userMemory.images = [];
        } else if (type === 'reports') {
            req.userMemory.reports = [];
        } else {
            req.userMemory.images = [];
            req.userMemory.reports = [];
        }
        
        await req.userMemory.save();
        res.json({ message: 'Memoria limpiada exitosamente' });
        
    } catch (error) {
        logger.error('Error al limpiar memoria:', error);
        res.status(500).json({ error: error.message });
    }
});

// Manejo de errores
app.use((error, req, res, next) => {
    logger.error('Error no manejado:', error);
    res.status(500).json({ error: 'Error interno del servidor' });
});

// Iniciar servidor
app.listen(PORT, () => {
    logger.info(`🍄 Dr. Fungito AI Agent ejecutándose en puerto ${PORT}`);
    console.log(`🧠 Dr. Fungito AI Agent - http://localhost:${PORT}`);
    console.log('🔬 Análisis de imágenes genómicas habilitado');
    console.log('📊 Generación de reportes inteligentes activada');
});

module.exports = app; 