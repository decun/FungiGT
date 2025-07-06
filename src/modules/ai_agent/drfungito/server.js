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
const fsExtra = require('fs-extra');
// Puppeteer para generación de PDFs
const puppeteer = require('puppeteer');
// const { PDFDocument, rgb } = require('pdf-lib');
// const moment = require('moment');
// const MarkdownIt = require('markdown-it');
// const { BufferMemory } = require('langchain/memory');
// const { ConversationChain } = require('langchain/chains');
// const { ChatAnthropic } = require('@langchain/anthropic');
require('dotenv').config();

// Configuración del servidor
const app = express();
const PORT = process.env.PORT || 4009;

// Temporalmente deshabilitado
// const md = new MarkdownIt();

// Temporalmente deshabilitado - memoria contextual
// const memory = new BufferMemory({
//     returnMessages: true,
//     memoryKey: 'chat_history',
//     inputKey: 'input',
//     outputKey: 'output'
// });

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

// Esquemas de MongoDB mejorados
const userMemorySchema = new mongoose.Schema({
    userId: { type: String, required: true, unique: true },
    images: [{
        imageId: String,
        filename: String,
        originalName: String,
        analysisType: String,
        uploadDate: { type: Date, default: Date.now },
        analysis: String,
        metadata: mongoose.Schema.Types.Mixed,
        imageData: String, // Base64 de la imagen para reportes
        contextualMemory: [{ // Memoria contextual con LangChain
            question: String,
            response: String,
            timestamp: { type: Date, default: Date.now }
        }]
    }],
    reports: [{
        reportId: String,
        title: String,
        content: String,
        htmlContent: String, // Para generar PDF
        images: [String], // Array de imageIds
        createdAt: { type: Date, default: Date.now },
        type: String, // 'detailed', 'summary', 'comparative'
        pdfPath: String, // Ruta del PDF generado
        downloadCount: { type: Number, default: 0 },
        // Nuevos campos para PDF
        imageCount: { type: Number, default: 0 },
        analysisTypes: [String],
        pdfAvailable: { type: Boolean, default: false },
        downloadUrl: String
    }],
    chatHistory: [{
        message: String,
        response: String,
        timestamp: { type: Date, default: Date.now },
        imageContext: [String] // imageIds relacionados
    }],
    lastActivity: { type: Date, default: Date.now }
});

const UserMemory = mongoose.model('UserMemory', userMemorySchema);

// Mapa de memoria contextual por usuario (LangChain)
const userMemoryMap = new Map();

// Temporalmente deshabilitado - función para obtener memoria contextual
// function getUserContextualMemory(userId) {
//     if (!userMemoryMap.has(userId)) {
//         userMemoryMap.set(userId, new BufferMemory({
//             returnMessages: true,
//             memoryKey: 'chat_history',
//             inputKey: 'input',
//             outputKey: 'output'
//         }));
//     }
//     return userMemoryMap.get(userId);
// }

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
            userMemory = new UserMemory({ userId, images: [], reports: [], chatHistory: [] });
            await userMemory.save();
        }
        
        // Verificar que reports sea un array válido
        if (!Array.isArray(userMemory.reports)) {
            logger.warn(`🍄 [MIDDLEWARE] Reparando campo reports para usuario ${userId}`);
            userMemory.reports = [];
            await userMemory.save();
        }
        
        req.userMemory = userMemory;
        req.userId = userId;
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

// Función para generar respuestas de chat locales sin Anthropic
function generateLocalChatResponse(message, imageContext) {
    const lowerMessage = message.toLowerCase();
    
    // Respuestas contextual si hay imágenes
    if (imageContext && imageContext.length > 0) {
        const analysisTypes = [...new Set(imageContext.map(img => img.analysisType))];
        const contextInfo = `He analizado ${imageContext.length} imagen(es) de tipo: ${analysisTypes.join(', ')}.`;
        
        if (lowerMessage.includes('reporte') || lowerMessage.includes('report')) {
            return `🍄 **Dr. Fungito responde:**\n\n📊 ${contextInfo}\n\nPara generar un reporte detallado con estas imágenes, usa el botón "📄 Generar reporte" en el panel superior. El reporte se guardará automáticamente en la carpeta "reports" del File Manager para fácil acceso. El reporte incluirá:\n\n✅ Análisis individual de cada imagen\n✅ Síntesis comparativa\n✅ Interpretación biológica\n✅ Recomendaciones técnicas\n\n¿Te gustaría que analice algún aspecto específico de las imágenes?`;
        }
        
        if (lowerMessage.includes('análisis') || lowerMessage.includes('analisis') || lowerMessage.includes('resultado')) {
            const summaries = imageContext.map(img => `• **${img.filename}**: ${img.analysis.substring(0, 100)}...`).join('\n');
            return `🍄 **Dr. Fungito responde:**\n\n🔬 ${contextInfo}\n\n**Resumen de análisis:**\n${summaries}\n\n¿Quieres que profundice en algún resultado específico o genere un reporte completo?`;
        }
        
        if (lowerMessage.includes('qué') || lowerMessage.includes('que') || lowerMessage.includes('explica')) {
            return `🍄 **Dr. Fungito responde:**\n\n🧬 ${contextInfo}\n\nBasándome en las imágenes analizadas, puedo explicarte:\n\n🔍 **Aspectos técnicos** de cada análisis\n📊 **Patrones identificados** en los datos\n🧪 **Interpretación biológica** de los resultados\n📈 **Recomendaciones** para análisis adicionales\n\n¿Sobre qué aspecto específico te gustaría que profundice?`;
        }
    }
    
    // Respuestas generales sin contexto de imágenes
    if (lowerMessage.includes('hola') || lowerMessage.includes('buenas') || lowerMessage.includes('saludos')) {
        return `🍄 **¡Hola! Soy Dr. Fungito**\n\n¡Bienvenido al análisis genómico inteligente!\n\n🔬 Puedo ayudarte con:\n• **Análisis automático** de imágenes genómicas\n• **Interpretación** de resultados BinDash, EggNOG, CheckM\n• **Generación de reportes** detallados\n• **Consultas** sobre genómica de hongos\n\n💡 **Tip:** Usa los botones 🍄 en cada visualizador para análisis directo de imágenes.`;
    }
    
    if (lowerMessage.includes('reporte') || lowerMessage.includes('report')) {
        return `🍄 **Dr. Fungito responde:**\n\n📄 **Generación de Reportes:**\n\nPara crear un reporte inteligente:\n\n1️⃣ **Analiza imágenes** usando los botones 🍄 en cada módulo\n2️⃣ **Haz clic** en "📄 Generar reporte" arriba\n3️⃣ **Selecciona** el tipo de reporte deseado\n\n**Tipos disponibles:**\n🔬 **Contextual** - Análisis integrado con toda la conversación\n📋 **Resumen** - Síntesis ejecutiva de resultados\n📊 **Detallado** - Análisis técnico completo\n\n📁 **Tu reporte se guardará automáticamente** en la carpeta "reports" del File Manager para fácil acceso posterior.\n\n¿Has analizado ya algunas imágenes?`;
    }
    
    if (lowerMessage.includes('memoria') || lowerMessage.includes('historial')) {
        return `🍄 **Dr. Fungito responde:**\n\n🧠 **Sistema de Memoria:**\n\nGuardo automáticamente:\n✅ Todos los análisis de imágenes\n✅ Nuestras conversaciones\n✅ Reportes generados\n✅ Contexto para análisis futuros\n\nUsa el botón "📊 Ver mi memoria" para consultar tu historial completo de análisis genómicos.\n\n🔍 ¿Necesitas revisar algún análisis específico?`;
    }
    
    if (lowerMessage.includes('bindash') || lowerMessage.includes('distancia')) {
        return `🍄 **Dr. Fungito responde:**\n\n🧬 **Análisis BinDash:**\n\nBinDash es excelente para:\n🔹 **Comparaciones genómicas** rápidas\n🔹 **Matrices de distancia** entre genomas\n🔹 **Dendrogramas filogenéticos** automáticos\n🔹 **Clustering** de muestras relacionadas\n\n💡 **Consejo:** Usa el módulo "Visualizador BinDash" y luego el botón 🍄 para interpretación automática de las matrices de distancia.\n\n¿Tienes datos BinDash para analizar?`;
    }
    
    if (lowerMessage.includes('eggnog') || lowerMessage.includes('anotación') || lowerMessage.includes('anotacion')) {
        return `🍄 **Dr. Fungito responde:**\n\n🔬 **Análisis EggNOG-mapper:**\n\nPerfecto para anotación funcional:\n🔹 **Ortólogos** y grupos funcionales\n🔹 **Pathways metabólicos** identificados\n🔹 **Dominios proteicos** conservados\n🔹 **Análisis GO** (Gene Ontology)\n\n📊 Usa el "Visualizador de Anotaciones" para procesar tus archivos .emapper y obtener insights automáticos.\n\n¿Qué aspectos funcionales te interesan más?`;
    }
    
    if (lowerMessage.includes('checkm') || lowerMessage.includes('calidad')) {
        return `🍄 **Dr. Fungito responde:**\n\n✅ **Control de Calidad CheckM:**\n\nEvalúo automáticamente:\n🔹 **Completitud** del ensamblaje genómico\n🔹 **Contaminación** detectada\n🔹 **Calidad general** del genoma\n🔹 **Métricas de confiabilidad**\n\n📈 Fundamental antes de análisis downstream. ¿Tienes resultados CheckM para revisar?`;
    }
    
    if (lowerMessage.includes('ayuda') || lowerMessage.includes('help') || lowerMessage.includes('como') || lowerMessage.includes('cómo')) {
        return `🍄 **Dr. Fungito - Guía Rápida:**\n\n🚀 **Workflow recomendado:**\n\n1️⃣ **Sube archivos** en cada módulo del visualizador\n2️⃣ **Analiza gráficos** con botones 🍄 Dr. Fungito\n3️⃣ **Genera reportes** inteligentes con toda la información\n4️⃣ **Consulta** sobre interpretaciones específicas\n\n💬 **Comandos útiles:**\n• "generar reporte" - Crea análisis completo\n• "mostrar memoria" - Ve tu historial\n• "analizar [tipo]" - Info sobre análisis específicos\n\n¿En qué paso necesitas ayuda?`;
    }
    
    // Respuesta por defecto
    return `🍄 **Dr. Fungito responde:**\n\n🤔 Interesante pregunta sobre genómica de hongos.\n\n💡 **Puedo ayudarte mejor si:**\n• Analizas imágenes usando los botones 🍄 en el visualizador\n• Me preguntas sobre resultados específicos\n• Solicitas un reporte detallado\n\n🔬 **Especialidades:**\n• Análisis BinDash y distancias genómicas\n• Anotación funcional con EggNOG\n• Control de calidad CheckM\n• Interpretación de resultados\n\n¿Qué tipo de análisis genómico estás realizando?`;
}

// Función para renderizar markdown básico en el servidor
function renderMarkdownToHTML(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>')
        .replace(/•/g, '&bull;')
        .replace(/([🔬🧬📊🗺️🎯🌳🧪⚗️🔍📈🧠💡✅❌⚠️🚨])/g, '<span class="emoji">$1</span>');
}

// Función para obtener la imagen de Dr. Fungito en base64
async function getDrFungitoImageBase64() {
    try {
        // Intentar leer la imagen desde la ubicación correcta
        const imagePath = '/app/DrFungito.png';
        
        try {
            const imageBuffer = await fs.readFile(imagePath);
            logger.info(`🍄 [PDF] Imagen Dr. Fungito cargada exitosamente desde: ${imagePath}`);
            return `data:image/png;base64,${imageBuffer.toString('base64')}`;
        } catch (error) {
            logger.warn(`🍄 [PDF] No se encontró la imagen de Dr. Fungito en: ${imagePath}`);
            return null;
        }
        
    } catch (error) {
        logger.error('🍄 [PDF] Error al cargar imagen de Dr. Fungito:', error);
        return null;
    }
}

// Función simplificada para generar HTML del reporte (sin dependencias problemáticas)
async function generateReportHTML(report, images) {
    const formattedDate = new Date(report.createdAt).toLocaleString('es-ES');
    
    // Renderizar el contenido con markdown
    const renderedContent = renderMarkdownToHTML(report.content);
    
    // Obtener imagen de Dr. Fungito
    const drFungitoImageBase64 = await getDrFungitoImageBase64();
    
    const imagesHTML = images.map(image => {
        const imageData = image.imageData || '';
        const renderedAnalysis = renderMarkdownToHTML(image.analysis);
        
        return `
            <div class="image-section">
                <h3>📊 ${image.filename}</h3>
                <div class="image-container">
                    <img src="${imageData}" alt="${image.filename}" class="report-image">
                </div>
                <div class="image-analysis">
                    <h4>🔬 Análisis:</h4>
                    <div class="analysis-content">${renderedAnalysis}</div>
                </div>
                <div class="image-metadata">
                    <p><strong>Tipo de análisis:</strong> ${image.analysisType}</p>
                    <p><strong>Fecha:</strong> ${new Date(image.uploadDate).toLocaleString('es-ES')}</p>
                </div>
            </div>
        `;
    }).join('');

    return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>${report.title}</title>
            <style>
                body {
                    font-family: 'Arial', sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                .report-container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .header {
                    text-align: center;
                    border-bottom: 3px solid #10b981;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }
                .header h1 {
                    color: #065f46;
                    margin-bottom: 10px;
                    font-size: 28px;
                }
                .header p {
                    color: #6b7280;
                    font-size: 14px;
                }
                .image-section {
                    margin-bottom: 40px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 20px;
                    background-color: #f9fafb;
                }
                .image-container {
                    text-align: center;
                    margin: 20px 0;
                }
                .report-image {
                    max-width: 100%;
                    height: auto;
                    border-radius: 8px;
                    border: 1px solid #d1d5db;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .image-analysis {
                    background-color: white;
                    padding: 15px;
                    border-radius: 6px;
                    margin-top: 15px;
                    border-left: 4px solid #10b981;
                }
                .image-metadata {
                    background-color: #f3f4f6;
                    padding: 10px;
                    border-radius: 6px;
                    margin-top: 10px;
                    font-size: 12px;
                }
                .content {
                    background-color: white;
                    padding: 25px;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
                    margin-bottom: 20px;
                }
                .content h2 {
                    color: #065f46;
                    border-bottom: 2px solid #10b981;
                    padding-bottom: 10px;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 12px;
                }
                .logo-container {
                    display: inline-block;
                    margin-bottom: 10px;
                }
                .logo-image {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    border: 3px solid #10b981;
                    object-fit: cover;
                    display: inline-block;
                }
                .logo-fallback {
                    display: none;
                    width: 60px;
                    height: 60px;
                    background-color: #10b981;
                    border-radius: 50%;
                    color: white;
                    text-align: center;
                    line-height: 60px;
                    font-size: 30px;
                    margin-bottom: 10px;
                }
                .content-text {
                    line-height: 1.8;
                    font-size: 14px;
                }
                .analysis-content {
                    line-height: 1.6;
                    font-size: 13px;
                }
                .emoji {
                    font-size: 16px;
                    margin-right: 4px;
                }
                strong {
                    color: #065f46;
                    font-weight: 600;
                }
                em {
                    color: #047857;
                    font-style: italic;
                }
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="header">
                    <div class="logo-container">
                        ${drFungitoImageBase64 ? 
                            `<img src="${drFungitoImageBase64}" alt="Dr. Fungito" class="logo-image">` : 
                            `<div class="logo-fallback" style="display: inline-block;">🍄</div>`
                        }
                    </div>
                    <h1>${report.title}</h1>
                    <p>Generado por Dr. Fungito AI • ${formattedDate}</p>
                </div>
                
                <div class="content">
                    <h2>📋 Reporte de Análisis Genómico</h2>
                    <div class="content-text">${renderedContent}</div>
                </div>
                
                <div class="images-section">
                    <h2>🖼️ Imágenes Analizadas</h2>
                    ${imagesHTML}
                </div>
                
                <div class="footer">
                    <p>🧬 FungiGT - Plataforma de Análisis Genómico de Hongos</p>
                    <p>Reporte generado automáticamente por Dr. Fungito AI</p>
                </div>
            </div>
        </body>
        </html>
    `;
}

// Configuración del directorio de datos del file manager
const FILE_MANAGER_DATA_DIR = path.join(__dirname, '../../../data');
const REPORTS_DIR = path.join(FILE_MANAGER_DATA_DIR, 'reports');

// Función para generar PDF del reporte
async function generateReportPDF(report, images, userId) {
    try {
        logger.info(`🍄 [PDF] Iniciando generación de PDF para reporte: ${report.reportId}`);
        const htmlContent = await generateReportHTML(report, images);
        
        // Guardar HTML temporalmente
        const tempHtmlPath = path.join(__dirname, 'temp', `report_${report.reportId}.html`);
        await fsExtra.ensureDir(path.dirname(tempHtmlPath));
        await fs.writeFile(tempHtmlPath, htmlContent);
        logger.info(`🍄 [PDF] HTML temporal guardado: ${tempHtmlPath}`);
        
        // Generar PDF con Puppeteer
        logger.info(`🍄 [PDF] Iniciando Puppeteer...`);
        const browser = await puppeteer.launch({
            headless: 'new',
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium-browser',
            args: [
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-background-timer-throttling'
            ]
        });
        
        const page = await browser.newPage();
        await page.goto(`file://${tempHtmlPath}`, { waitUntil: 'networkidle0', timeout: 30000 });
        logger.info(`🍄 [PDF] Página cargada, generando PDF...`);
        
        const pdfBuffer = await page.pdf({
            format: 'A4',
            printBackground: true,
            margin: {
                top: '1cm',
                bottom: '1cm',
                left: '1cm',
                right: '1cm'
            }
        });
        
        await browser.close();
        logger.info(`🍄 [PDF] Puppeteer cerrado, PDF buffer generado (${pdfBuffer.length} bytes)`);
        
        // Guardar PDF en dos lugares: local y file manager
        const pdfPath = path.join(__dirname, 'data', 'reports', `${report.reportId}.pdf`);
        await fsExtra.ensureDir(path.dirname(pdfPath));
        await fs.writeFile(pdfPath, pdfBuffer);
        
        // También guardarlo en el File Manager
        const fileManagerReportsDir = path.join(FILE_MANAGER_DATA_DIR, 'reports');
        await fsExtra.ensureDir(fileManagerReportsDir);
        const fileManagerPdfPath = path.join(fileManagerReportsDir, `${report.reportId}.pdf`);
        await fs.writeFile(fileManagerPdfPath, pdfBuffer);
        
        // Limpiar archivo temporal
        await fs.unlink(tempHtmlPath);
        
        logger.info(`🍄 [PDF] PDF generado exitosamente: ${pdfPath} (${pdfBuffer.length} bytes)`);
        logger.info(`🍄 [PDF] PDF también guardado en File Manager: ${fileManagerPdfPath}`);
        return pdfPath;
        
    } catch (error) {
        logger.error('🍄 [ERROR] Error al generar PDF:', error);
        throw error;
    }
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

// Subir y analizar imagen (mejorado)
app.post('/analyze-image', upload.single('image'), getUserMemory, async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No se proporcionó ninguna imagen' });
        }
        
        const { analysisType = 'general', userContext = '', saveToMemory = 'true' } = req.body;
        
        // Optimizar imagen
        const optimizedBuffer = await optimizeImage(req.file.buffer);
        
        // Convertir a base64 para guardar en memoria
        const imageBase64 = bufferToBase64(optimizedBuffer, req.file.mimetype);
        
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
                metadata: result.metadata,
                imageData: imageBase64, // Guardar imagen para reportes
                contextualMemory: []
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

// Nueva ruta para análisis desde visualizadores
app.post('/analyze-from-visualizer', getUserMemory, async (req, res) => {
    try {
        const { imageUrl, analysisType = 'general', userContext = '', filename = 'visualizer_image' } = req.body;
        
        if (!imageUrl) {
            return res.status(400).json({ error: 'URL de imagen requerida' });
        }
        
        // Convertir localhost URLs a nombres de contenedor Docker para acceso interno
        let dockerAccessibleUrl = imageUrl;
        if (imageUrl.includes('localhost:4003')) {
            dockerAccessibleUrl = imageUrl.replace('localhost:4003', 'fungigt-visualization-server:4003');
        } else if (imageUrl.includes('localhost:4002')) {
            dockerAccessibleUrl = imageUrl.replace('localhost:4002', 'fungigt-file-manager:4002');
        } else if (imageUrl.includes('localhost:4004')) {
            dockerAccessibleUrl = imageUrl.replace('localhost:4004', 'fungigt-quality-control:4004');
        } else if (imageUrl.includes('localhost:4007')) {
            dockerAccessibleUrl = imageUrl.replace('localhost:4007', 'fungigt-bindash-analysis:4007');
        } else if (imageUrl.includes('localhost:3002')) {
            dockerAccessibleUrl = imageUrl.replace('localhost:3002', 'fungigt-eggnog-mapper:3001');
        }
        
        logger.info(`Descargando imagen desde: ${dockerAccessibleUrl} (URL original: ${imageUrl})`);
        
        // Descargar imagen desde URL
        const response = await fetch(dockerAccessibleUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const arrayBuffer = await response.arrayBuffer();
        const imageBuffer = Buffer.from(arrayBuffer);
        
        // Optimizar imagen
        const optimizedBuffer = await optimizeImage(imageBuffer);
        const imageBase64 = bufferToBase64(optimizedBuffer, 'image/png');
        
        // Analizar con Claude
        const analysis = await analyzeImageWithClaude(
            optimizedBuffer,
            'image/png',
            analysisType,
            userContext
        );
        
        const imageId = uuidv4();
        
        // Guardar en memoria del usuario
        req.userMemory.images.push({
            imageId,
            filename,
            originalName: filename,
            analysisType,
            analysis,
            metadata: {
                source: 'visualizer',
                originalUrl: imageUrl,
                optimizedSize: optimizedBuffer.length,
                mimetype: 'image/png',
                dimensions: await sharp(optimizedBuffer).metadata()
            },
            imageData: imageBase64,
            contextualMemory: []
        });
        req.userMemory.lastActivity = new Date();
        await req.userMemory.save();
        
        logger.info(`Imagen del visualizador analizada exitosamente: ${imageId}`);
        res.json({
            imageId,
            filename,
            analysisType,
            analysis,
            uploadDate: new Date().toISOString(),
            success: true
        });
        
    } catch (error) {
        logger.error('Error al analizar imagen del visualizador:', error);
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

// Borrar memoria del usuario
app.delete('/clear-memory', getUserMemory, async (req, res) => {
    try {
        logger.info(`Borrando memoria del usuario: ${req.userMemory.userId}`);
        
        const previousStats = {
            images: req.userMemory.images.length,
            reports: req.userMemory.reports.length,
            chats: req.userMemory.chatHistory.length
        };
        
        // Limpiar toda la memoria del usuario
        req.userMemory.images = [];
        req.userMemory.reports = [];
        req.userMemory.chatHistory = [];
        req.userMemory.lastActivity = new Date();
        
        await req.userMemory.save();
        
        logger.info(`Memoria borrada exitosamente. Estadísticas anteriores: ${JSON.stringify(previousStats)}`);
        
        res.json({
            success: true,
            message: 'Memoria borrada exitosamente',
            cleared: previousStats,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        logger.error('Error al borrar memoria:', error);
        res.status(500).json({ error: error.message });
    }
});

// Generar reporte contextual inteligente
app.post('/generate-report', getUserMemory, async (req, res) => {
    try {
        logger.info('🍄 [DEBUG] Iniciando generación de reporte...');
        const { 
            imageIds = [], 
            reportType = 'contextual', 
            title = 'Reporte Genómico Contextual',
            includeAllImages = false,
            includeChatContext = true
        } = req.body;
        logger.info(`🍄 [DEBUG] Parámetros: imageIds=${imageIds.length}, type=${reportType}, images=${req.userMemory.images.length}`);
        
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
        logger.info(`🍄 [DEBUG] Imágenes seleccionadas: ${selectedImages.length}`);
        
        // Obtener contexto del chat si está disponible
        let chatContext = '';
        if (includeChatContext && req.userMemory.chatHistory && req.userMemory.chatHistory.length > 0) {
            const recentChats = req.userMemory.chatHistory.slice(-10);
            chatContext = recentChats.map(chat => 
                `**${chat.timestamp}** - ${chat.role === 'user' ? 'Usuario' : 'Dr. Fungito'}: ${chat.content}`
            ).join('\n');
        }
        logger.info(`🍄 [DEBUG] Chat context preparado, longitud: ${chatContext.length}`);
        
        // Crear contexto inteligente para el reporte
        const imageContext = selectedImages.map((img, i) => ({
            index: i + 1,
            filename: img.filename,
            analysisType: img.analysisType,
            analysis: img.analysis,
            uploadDate: img.uploadDate,
            metadata: img.metadata || {}
        }));
        
        // Generar reporte contextual inteligente usando análisis directo
        const reportPrompts = {
            contextual: `# 🍄 REPORTE GENÓMICO CONTEXTUAL - DR. FUNGITO
            
## 📊 RESUMEN EJECUTIVO
${imageContext.length} imágenes analizadas de tipos: ${[...new Set(imageContext.map(c => c.analysisType))].join(', ')}

## 🔬 ANÁLISIS INDIVIDUAL DE IMÁGENES
${imageContext.map(c => `
### Imagen ${c.index}: ${c.filename}
- **Tipo**: ${c.analysisType}
- **Fecha**: ${c.uploadDate}
- **Análisis**: ${c.analysis}
- **Insights**: ${c.metadata.dimensions ? `Dimensiones: ${c.metadata.dimensions.width}x${c.metadata.dimensions.height}` : 'Sin metadata adicional'}
`).join('\n')}

## 🧠 SÍNTESIS CONTEXTUAL
Los análisis revelan patrones importantes en los datos genómicos:

${imageContext.map(c => `- **${c.filename}**: ${c.analysis.substring(0, 150)}...`).join('\n')}

## 🔄 ANÁLISIS COMPARATIVO
${imageContext.length > 1 ? 
`Se observan ${imageContext.length} muestras con diferentes características:
${imageContext.map(c => `- ${c.analysisType}: ${c.analysis.split('.')[0]}`).join('\n')}` : 
'Se requieren más muestras para análisis comparativo completo.'}

## 🧬 INTERPRETACIÓN BIOLÓGICA
Los resultados sugieren:
- Diversidad genómica en las muestras analizadas
- Patrones de homología y distancia evolutiva
- Anotaciones funcionales relevantes

## 📈 RECOMENDACIONES
1. **Análisis adicional**: Considerar más muestras del mismo tipo
2. **Validación**: Confirmar resultados con técnicas complementarias  
3. **Seguimiento**: Monitorear evolución temporal de las muestras

## 🎯 CONCLUSIONES
Este reporte integra ${imageContext.length} análisis genómicos proporcionando una visión comprehensiva de los datos. Los patrones identificados sugieren direcciones específicas para investigación futura.

---
*Generado por Dr. Fungito AI - ${new Date().toLocaleString('es-ES')}*`,
            
            summary: `📋 **RESUMEN EJECUTIVO**
${imageContext.length} imágenes analizadas:
${imageContext.map(c => `- **${c.filename}**: ${c.analysis.substring(0, 100)}...`).join('\n')}

**Hallazgos principales**: Análisis exitoso de datos genómicos con insights relevantes para investigación fúngica.`,
            
            detailed: `# 📊 REPORTE DETALLADO - DR. FUNGITO

## 🔍 METODOLOGÍA
Análisis computacional de imágenes genómicas usando algoritmos de IA especializados en genómica fúngica.

## 📈 RESULTADOS DETALLADOS
${imageContext.map(c => `
### 🧬 ${c.filename}
- **Tipo de análisis**: ${c.analysisType}
- **Fecha de procesamiento**: ${c.uploadDate}
- **Análisis completo**: ${c.analysis}
- **Clasificación**: ${c.analysisType === 'bindash' ? 'Análisis de distancia genómica' : 
                  c.analysisType === 'eggnog' ? 'Anotación funcional' : 
                  c.analysisType === 'checkm' ? 'Control de calidad' : 'Análisis general'}
`).join('\n')}

## 🎯 SÍNTESIS INTEGRATIVA
Los análisis convergen en patrones consistentes que sugieren ${imageContext.length > 1 ? 'diversidad genómica significativa' : 'características genómicas específicas'}.

## 📋 RECOMENDACIONES TÉCNICAS
1. Validación experimental de resultados computacionales
2. Análisis comparativo con bases de datos públicas
3. Seguimiento longitudinal de muestras

---
*Análisis generado por Dr. Fungito AI - Sistema de análisis genómico inteligente*`
        };
        
        logger.info(`🍄 [DEBUG] Generando reporte de tipo: ${reportType}`);
        const reportId = uuidv4();
        const report = {
            reportId,
            title,
            content: reportPrompts[reportType] || reportPrompts.contextual,
            images: selectedImages.map(img => img.imageId),
            type: reportType,
            createdAt: new Date(),
            chatContext: chatContext,
            imageCount: selectedImages.length,
            analysisTypes: [...new Set(selectedImages.map(img => img.analysisType))]
        };
        logger.info(`🍄 [DEBUG] Objeto reporte creado con ID: ${reportId}`);
        
        // Generar PDF directamente en lugar de JSON gigante
        logger.info(`🍄 [DEBUG] Generando PDF del reporte...`);
        
        try {
            // Generar PDF con Puppeteer
            const pdfPath = await generateReportPDF(report, selectedImages, req.userMemory.userId);
            
            // Actualizar reporte con información del PDF
            report.pdfPath = pdfPath;
            report.pdfAvailable = true;
            report.downloadUrl = `/download-report/${reportId}`;
            
            // Solo guardar metadatos en memoria (sin HTML gigante)
            const reportForMemory = {
                reportId: report.reportId,
                title: report.title,
                content: report.content, // Incluir contenido para cumplir con el esquema
                htmlContent: '', // Campo opcional, no incluir HTML gigante
                images: selectedImages.map(img => img.imageId),
                createdAt: report.createdAt,
                type: report.type,
                pdfPath: pdfPath,
                downloadCount: 0,
                imageCount: report.imageCount,
                analysisTypes: report.analysisTypes,
                pdfAvailable: true,
                downloadUrl: `/download-report/${reportId}`
            };
            
            // Guardar reporte en memoria usando un método más seguro
            logger.info(`🍄 [DEBUG] Guardando reporte en memoria...`);
            
            // Crear un nuevo objeto plano sin referencias circulares
            const safeReportObject = {
                reportId: String(report.reportId),
                title: String(report.title),
                content: String(report.content).substring(0, 2000), // Limitar tamaño del contenido
                htmlContent: '', // Vacío para evitar problemas
                images: selectedImages.map(img => String(img.imageId)), // Usar selectedImages directamente
                createdAt: new Date(report.createdAt),
                type: String(report.type),
                pdfPath: String(pdfPath),
                downloadCount: 0,
                imageCount: Number(selectedImages.length),
                analysisTypes: [...new Set(selectedImages.map(img => img.analysisType))], // Crear array único de tipos
                pdfAvailable: true,
                downloadUrl: String(`/download-report/${reportId}`)
            };
            
            try {
                // Método más directo: actualizar el documento directamente
                req.userMemory.reports.push(safeReportObject);
                req.userMemory.lastActivity = new Date();
                await req.userMemory.save();
                
                logger.info(`🍄 [DEBUG] Reporte guardado exitosamente en MongoDB`);
                
            } catch (saveError) {
                logger.error(`🍄 [ERROR] Error específico al guardar reporte:`, saveError);
                
                // Fallback: limpiar el array de reports si hay datos corruptos
                try {
                    logger.info(`🍄 [DEBUG] Intentando limpiar y reintentar...`);
                    
                    // Recrear el array de reports sin elementos problemáticos
                    req.userMemory.reports = req.userMemory.reports.filter(r => 
                        r && typeof r === 'object' && r.reportId
                    );
                    
                    // Intentar guardar nuevamente con el objeto ya definido
                    req.userMemory.reports.push(safeReportObject);
                    req.userMemory.lastActivity = new Date();
                    await req.userMemory.save();
                    
                    logger.info(`🍄 [DEBUG] Reporte guardado exitosamente después de limpiar`);
                    
                } catch (fallbackError) {
                    logger.error(`🍄 [ERROR] Error en fallback:`, fallbackError);
                    logger.info(`🍄 [DEBUG] Continuando sin guardar en memoria...`);
                }
            }
            
            logger.info(`Reporte PDF generado exitosamente: ${reportId} con ${selectedImages.length} imágenes`);
            
            // Respuesta ligera con link de descarga
            const responseObject = {
                reportId: report.reportId,
                title: report.title,
                type: report.type,
                createdAt: report.createdAt,
                imageCount: report.imageCount,
                analysisTypes: report.analysisTypes,
                pdfAvailable: true,
                downloadUrl: `/download-report/${reportId}`,
                success: true,
                message: `✅ Reporte PDF generado exitosamente. Tu reporte se ha guardado en la carpeta "reports" del File Manager. Puedes acceder al File Manager desde el menú principal para descargar tu archivo PDF.`
            };
            
            logger.info(`🍄 [DEBUG] Respuesta ligera preparada, enviando...`);
            res.json(responseObject);
            logger.info(`🍄 [DEBUG] Respuesta enviada exitosamente`);
            
        } catch (pdfError) {
            logger.error('🍄 [ERROR] Error al generar PDF:', pdfError);
            
            // Intentar guardar al menos el contenido del reporte en el File Manager
            try {
                const reportTextPath = path.join(FILE_MANAGER_DATA_DIR, 'reports', `${report.reportId}.txt`);
                await fsExtra.ensureDir(path.dirname(reportTextPath));
                await fs.writeFile(reportTextPath, report.content);
                logger.info(`🍄 [FALLBACK] Reporte guardado como texto: ${reportTextPath}`);
                
                // Fallback: devolver respuesta con ruta del archivo de texto
                return res.json({
                    reportId: report.reportId,
                    title: report.title,
                    type: report.type,
                    createdAt: report.createdAt,
                    imageCount: report.imageCount,
                    analysisTypes: report.analysisTypes,
                    pdfAvailable: false,
                    downloadUrl: null,
                    success: true,
                    message: `📄 Reporte generado exitosamente. El PDF falló pero puedes encontrar el reporte en formato texto en: File Manager > reports > ${report.reportId}.txt`,
                    textPath: reportTextPath,
                    error: pdfError.message
                });
            } catch (textError) {
                logger.error('🍄 [ERROR] Error al guardar reporte como texto:', textError);
                
                // Fallback final: devolver respuesta con contenido del reporte
                return res.json({
                    reportId: report.reportId,
                    title: report.title,
                    type: report.type,
                    createdAt: report.createdAt,
                    imageCount: report.imageCount,
                    analysisTypes: report.analysisTypes,
                    pdfAvailable: false,
                    downloadUrl: null,
                    success: true,
                    message: `📄 Reporte generado exitosamente. El PDF falló pero el contenido está disponible en la respuesta. ID del reporte: ${report.reportId}`,
                    content: report.content,
                    error: pdfError.message
                });
            }
        }
        
    } catch (error) {
        logger.error('Error al generar reporte contextual:', error);
        res.status(500).json({ error: error.message });
    }
});

// Ruta para descargar PDF del reporte (ahora redirige al file manager)
app.get('/download-report/:reportId', getUserMemory, async (req, res) => {
    try {
        const { reportId } = req.params;
        logger.info(`🍄 [DOWNLOAD] Solicitud de descarga para reporte: ${reportId}`);
        
        // Forzar recarga de la memoria del usuario desde la base de datos
        const freshUserMemory = await UserMemory.findById(req.userMemory._id);
        if (freshUserMemory) {
            req.userMemory = freshUserMemory;
        }
        
        const report = req.userMemory.reports.find(r => r.reportId === reportId);
        if (!report) {
            logger.warn(`🍄 [DOWNLOAD] Reporte no encontrado: ${reportId}`);
            return res.status(404).json({ 
                error: 'Reporte no encontrado', 
                message: 'Este reporte ya no existe en la memoria. Genera un nuevo reporte para obtener un PDF actualizado.',
                reportId: reportId
            });
        }
        
        if (!report.pdfPath) {
            logger.warn(`🍄 [DOWNLOAD] PDF no disponible para reporte: ${reportId}`);
            return res.status(404).json({ 
                error: 'PDF no disponible para este reporte',
                message: 'El reporte existe pero no tiene un PDF asociado. Genera un nuevo reporte.'
            });
        }
        
        // Verificar que el archivo existe
        try {
            await fs.access(report.pdfPath);
            logger.info(`🍄 [DOWNLOAD] Archivo PDF encontrado: ${report.pdfPath}`);
        } catch (error) {
            logger.error(`🍄 [DOWNLOAD] Archivo PDF no encontrado: ${report.pdfPath}`, error);
            return res.status(404).json({ 
                error: 'Archivo PDF no encontrado',
                message: 'El archivo PDF fue eliminado del servidor. Genera un nuevo reporte.',
                pdfPath: report.pdfPath
            });
        }
        
        // Incrementar contador de descargas
        report.downloadCount = (report.downloadCount || 0) + 1;
        
        try {
            await req.userMemory.save();
            logger.info(`🍄 [DOWNLOAD] Contador de descargas actualizado: ${report.downloadCount}`);
        } catch (saveError) {
            logger.warn(`🍄 [DOWNLOAD] Error al actualizar contador de descargas:`, saveError);
            // Continuar con la descarga aunque no se pueda actualizar el contador
        }
        
        logger.info(`🍄 [DOWNLOAD] Iniciando descarga del reporte: ${report.title}`);
        
        // Enviar archivo
        res.download(report.pdfPath, `${report.title.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`, (err) => {
            if (err) {
                logger.error('🍄 [DOWNLOAD] Error al descargar PDF:', err);
                if (!res.headersSent) {
                    res.status(500).json({ error: 'Error al descargar el archivo' });
                }
            } else {
                logger.info(`🍄 [DOWNLOAD] Descarga completada exitosamente: ${reportId}`);
            }
        });
        
    } catch (error) {
        logger.error('🍄 [DOWNLOAD] Error al procesar descarga:', error);
        res.status(500).json({ 
            error: error.message,
            message: 'Error interno del servidor durante la descarga'
        });
    }
});

// Chat con Dr. Fungito mejorado con memoria contextual
app.post('/chat', getUserMemory, async (req, res) => {
    try {
        const { message, includeMemoryContext = true } = req.body;
        
        if (!message) {
            return res.status(400).json({ error: 'Mensaje requerido' });
        }
        
        // Obtener contexto de imágenes recientes
        const recentImages = req.userMemory.images.slice(-3);
        const imageContext = recentImages.map(img => ({
            filename: img.filename,
            analysisType: img.analysisType,
            analysis: img.analysis
        }));
        
        // Versión simplificada sin memoria contextual de LangChain
        const contextPrompt = imageContext.length > 0 
            ? `Contexto de imágenes recientes: ${imageContext.map(img => `${img.filename} (${img.analysisType}): ${img.analysis.substring(0, 100)}...`).join('; ')}`
            : '';
        
        const fullPrompt = `${contextPrompt}\n\nUsuario: ${message}`;
        
        let response;
        
        try {
            // Intentar usar Anthropic primero
            const anthropicResponse = await anthropic.messages.create({
                model: "claude-3-sonnet-20240229",
                max_tokens: 1000,
                temperature: 0.4,
                system: `Eres Dr. Fungito, un experto en genómica de hongos. Proporcionas respuestas profesionales pero amigables. Responde en español.`,
                messages: [
                    {
                        role: "user",
                        content: fullPrompt
                    }
                ]
            });
            
            response = anthropicResponse.content[0].text;
            
        } catch (anthropicError) {
            logger.warn('Anthropic no disponible, usando respuesta local:', anthropicError.message);
            
            // Fallback a respuestas locales inteligentes
            response = generateLocalChatResponse(message, imageContext);
        }
        
        // Guardar conversación en historial
        req.userMemory.chatHistory.push({
            message,
            response,
            timestamp: new Date(),
            imageContext: recentImages.map(img => img.imageId)
        });
        
        // Mantener solo las últimas 20 conversaciones
        if (req.userMemory.chatHistory.length > 20) {
            req.userMemory.chatHistory = req.userMemory.chatHistory.slice(-20);
        }
        
        req.userMemory.lastActivity = new Date();
        await req.userMemory.save();
        
        res.json({
            response,
            timestamp: new Date().toISOString(),
            contextUsed: imageContext.length > 0
        });
        
    } catch (error) {
        logger.error('Error en chat:', error);
        res.status(500).json({ error: error.message });
    }
});

// Obtener historial de chat
app.get('/chat-history', getUserMemory, async (req, res) => {
    try {
        const { limit = 10 } = req.query;
        
        const history = req.userMemory.chatHistory
            .slice(-limit)
            .reverse()
            .map(chat => ({
                message: chat.message,
                response: chat.response,
                timestamp: chat.timestamp,
                hasImageContext: chat.imageContext && chat.imageContext.length > 0
            }));
        
        res.json({
            history,
            totalChats: req.userMemory.chatHistory.length
        });
        
    } catch (error) {
        logger.error('Error al obtener historial de chat:', error);
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

// Función para limpiar completamente la base de datos
app.post('/admin/clean-database', async (req, res) => {
    try {
        logger.info('🍄 [ADMIN] Iniciando limpieza completa de base de datos...');
        
        // Eliminar todos los documentos de UserMemory
        const result = await UserMemory.deleteMany({});
        
        logger.info(`🍄 [ADMIN] Eliminados ${result.deletedCount} documentos de la base de datos`);
        
        // Verificar que la colección esté vacía
        const remainingDocs = await UserMemory.countDocuments();
        logger.info(`🍄 [ADMIN] Documentos restantes: ${remainingDocs}`);
        
        logger.info('🍄 [ADMIN] Limpieza completa de base de datos completada');
        res.json({ 
            success: true, 
            message: 'Base de datos limpiada completamente',
            deletedDocuments: result.deletedCount,
            remainingDocuments: remainingDocs
        });
        
    } catch (error) {
        logger.error('🍄 [ADMIN] Error en limpieza de base de datos:', error);
        res.status(500).json({ error: 'Error al limpiar base de datos' });
    }
});

// Función para limpiar datos problemáticos en la base de datos
app.post('/admin/fix-database', async (req, res) => {
    try {
        logger.info('🍄 [ADMIN] Iniciando reparación de base de datos...');
        
        // Buscar usuarios con problemas en el campo reports
        const problematicUsers = await UserMemory.find({
            $or: [
                { reports: { $type: "string" } }, // reports es string en lugar de array
                { reports: { $exists: false } } // reports no existe
            ]
        });
        
        logger.info(`🍄 [ADMIN] Encontrados ${problematicUsers.length} usuarios con problemas`);
        
        for (const user of problematicUsers) {
            try {
                // Resetear el campo reports a un array vacío
                await UserMemory.updateOne(
                    { _id: user._id },
                    { 
                        $set: { 
                            reports: [],
                            lastActivity: new Date() 
                        }
                    }
                );
                logger.info(`🍄 [ADMIN] Usuario ${user.userId} reparado exitosamente`);
            } catch (userError) {
                logger.error(`🍄 [ADMIN] Error reparando usuario ${user.userId}:`, userError);
            }
        }
        
        res.json({
            success: true,
            message: `Base de datos reparada. ${problematicUsers.length} usuarios procesados.`,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        logger.error('🍄 [ADMIN] Error en reparación de base de datos:', error);
        res.status(500).json({ error: error.message });
    }
});

// Endpoints de debug eliminados para simplificar el sistema

// Los reportes se guardan automáticamente en la carpeta "reports" del File Manager



// Endpoint de salud
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        service: 'Dr. Fungito AI Agent',
        version: '1.0.0'
    });
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