const express = require('express');
const { spawn, exec } = require('child_process');
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');
const cors = require('cors');
const os = require('os');
const archiver = require('archiver');
const { v4: uuidv4 } = require('uuid');

// Utilidades personalizadas
const FastaHeaderFixer = require('./utils/fasta_header_fixer');
const FunannotateProgressParser = require('./utils/progress_parser');

const app = express();
const port = 3005;

// Almacenar los trabajos de Funannotate en ejecución y sus logs
const runningJobs = {};
let currentProcess = null;
let funannotateProgress = 0;
let funannotateLogs = [];
let currentJobId = null;

// Instancias de utilidades
const headerFixer = new FastaHeaderFixer();
const progressParser = new FunannotateProgressParser();

// CORS configuration para permitir solicitudes desde el frontend
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint para Docker
app.get('/health', (req, res) => {
    res.status(200).json({
        success: true,
        message: 'Servicio Funannotate funcionando correctamente',
        timestamp: new Date().toISOString()
    });
});

// Función para convertir rutas de Windows a formato Docker
const convertPath = (p) => {
    return p.replace(/\\/g, '/');
};

// Función para convertir rutas del frontend a rutas del contenedor
const convertToContainerPath = (frontendPath) => {
    // El frontend envía rutas como: C:/Memoriacosas/FungiGT/data/test
    // Necesitamos convertir a: /data/test
    
    if (frontendPath.includes('C:/Memoriacosas/FungiGT/data/')) {
        return frontendPath.replace('C:/Memoriacosas/FungiGT/data/', '/data/');
    }
    if (frontendPath.includes('C:\\Memoriacosas\\FungiGT\\data\\')) {
        return frontendPath.replace('C:\\Memoriacosas\\FungiGT\\data\\', '/data/').replace(/\\/g, '/');
    }
    
    // Si ya es una ruta de contenedor, devolverla tal como está
    if (frontendPath.startsWith('/data/')) {
        return frontendPath;
    }
    
    // Fallback: asumir que es una ruta relativa a /data
    return frontendPath.startsWith('/') ? frontendPath : `/data/${frontendPath}`;
};

// Función para convertir rutas del contenedor de vuelta a rutas del host para Docker bind mount
const convertToHostPath = (containerPath) => {
    // El contenedor tiene rutas como: /data/test
    // Para el bind mount necesitamos: C:/Memoriacosas/FungiGT/data/test
    
    if (containerPath.startsWith('/data/')) {
        return containerPath.replace('/data/', 'C:/Memoriacosas/FungiGT/data/');
    }
    
    // Si ya es una ruta de host, devolverla tal como está
    if (containerPath.includes('C:/Memoriacosas/FungiGT/data/')) {
        return containerPath;
    }
    
    // Fallback: asumir que es una ruta relativa
    return `C:/Memoriacosas/FungiGT/data/${containerPath}`;
};

// Configuración de multer para subir archivos con nombre original
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        const inputFolder = req.body.inputFolderPath || 'data/raw/genomes/funannotate';

        // Validar y sanitizar la ruta de la carpeta
        if (!inputFolder || typeof inputFolder !== 'string') {
            return cb(new Error('Ruta de carpeta de entrada no válida'));
        }

        // Crear la carpeta si no existe
        fs.ensureDirSync(inputFolder);
        cb(null, inputFolder);
    },
    filename: function (req, file, cb) {
        // Sanitizar el nombre del archivo
        const sanitizedFilename = file.originalname.replace(/[;&|`()${}[\]\\\/"'*?~<>^]/g, '');
        cb(null, sanitizedFilename);
    }
});

// Límites para la subida de archivos
const upload = multer({
    storage: storage,
    limits: { fileSize: 1000 * 1024 * 1024 } // 1GB máximo (genomas pueden ser grandes)
});

// Función para validar parámetros de Funannotate
function validateFunannotateParams(params, workflow) {
    console.log("Validando parámetros de Funannotate:", JSON.stringify(params, null, 2));
    
    const species = params.species;
    const input = params.input; // puede ser genoma para predict, o resultado anterior para annotate
    const cpus = params.cpus || 1;
    
    const inputFolder = params.inputFolder || params.inputFolderPath;
    const outputFolder = params.outputFolder || params.outputFolderPath;
    
    console.log("Parámetros extraídos:", { species, input, cpus, inputFolder, outputFolder, workflow });
    
    // Verificar valores obligatorios según el workflow
    const missing = [];
    if (!species) missing.push('species');
    if (!input) missing.push('input');
    if (!inputFolder) missing.push('inputFolder/inputFolderPath');
    if (!outputFolder) missing.push('outputFolder/outputFolderPath');
    
    if (missing.length > 0) {
        return {
            valid: false,
            error: `Faltan parámetros obligatorios para Funannotate ${workflow}: ${missing.join(', ')}`
        };
    }
    
    // Validar cpus (debe ser un número)
    if (isNaN(parseInt(cpus)) || parseInt(cpus) <= 0) {
        return {
            valid: false,
            error: 'El número de CPUs debe ser un número positivo'
        };
    }
    
    return { valid: true };
}

// Función para construir comando de Funannotate
function buildFunannotateCommand(params, workflow) {
    // Convertir rutas del contenedor a rutas del host para el bind mount
    const hostInputPath = convertToHostPath(params.inputFolder);
    const hostOutputPath = convertToHostPath(params.outputFolder);
    
    // Convertir a formato Docker (usar forward slashes)
    const dockerInputPath = convertPath(hostInputPath);
    const dockerOutputPath = convertPath(hostOutputPath);
    
    console.log(`🔄 Rutas para Docker comando:`);
    console.log(`   Input container: ${params.inputFolder} → host: ${hostInputPath} → docker: ${dockerInputPath}`);
    console.log(`   Output container: ${params.outputFolder} → host: ${hostOutputPath} → docker: ${dockerOutputPath}`);
    
    let baseCommand = `docker run --rm -v "${dockerInputPath}":/input -v "${dockerOutputPath}":/output nextgenusfs/funannotate:latest`;
    
    switch (workflow) {
        case 'predict':
            baseCommand += ` funannotate predict`;
            baseCommand += ` --input /input/${params.input}`;
            baseCommand += ` --species "${params.species}"`;
            baseCommand += ` --out /output`;
            baseCommand += ` --cpus ${params.cpus}`;
            
            // Parámetros opcionales para predict
            if (params.busco_db) baseCommand += ` --busco_db ${params.busco_db}`;
            if (params.organism) baseCommand += ` --organism ${params.organism}`;
            if (params.ploidy) baseCommand += ` --ploidy ${params.ploidy}`;
            if (params.protein_evidence) baseCommand += ` --protein_evidence /input/${params.protein_evidence}`;
            if (params.transcript_evidence) baseCommand += ` --transcript_evidence /input/${params.transcript_evidence}`;
            if (params.rna_bam) baseCommand += ` --rna_bam /input/${params.rna_bam}`;
            
            // Flags opcionales
            if (params.optimize_augustus) baseCommand += ` --optimize_augustus`;
            if (params.repeats2evm) baseCommand += ` --repeats2evm`;
            if (params.stringtie_FPKM) baseCommand += ` --stringtie_FPKM`;
            break;
            
        case 'annotate':
            baseCommand += ` funannotate annotate`;
            baseCommand += ` --input /input/${params.input}`;
            baseCommand += ` --cpus ${params.cpus}`;
            
            // Bases de datos para anotación funcional
            if (params.antismash) baseCommand += ` --antismash`;
            if (params.iprscan) baseCommand += ` --iprscan`;
            if (params.phobius) baseCommand += ` --phobius`;
            if (params.signalp) baseCommand += ` --signalp`;
            break;
            
        case 'compare':
            baseCommand += ` funannotate compare`;
            baseCommand += ` --input /input`;
            baseCommand += ` --cpus ${params.cpus}`;
            if (params.run_dnds) baseCommand += ` --run_dnds`;
            break;
            
        default:
            throw new Error(`Workflow no soportado: ${workflow}`);
    }
    
    return baseCommand;
}

// Endpoint para subir archivos
app.post('/upload-files', upload.array('files', 10), (req, res) => {
    try {
        if (!req.files || req.files.length === 0) {
            return res.status(400).json({
                success: false,
                error: 'No se subieron archivos'
            });
        }

        console.log('Archivos subidos exitosamente:', req.files.map(f => f.filename));
        
        res.json({
            success: true,
            message: 'Archivos subidos exitosamente',
            files: req.files.map(file => ({
                filename: file.filename,
                size: file.size,
                path: file.path
            }))
        });
    } catch (error) {
        console.error('Error al subir archivos:', error);
        res.status(500).json({
            success: false,
            error: 'Error interno del servidor al subir archivos'
        });
    }
});

// Endpoint para ejecutar Funannotate predict
app.post('/predict', async (req, res) => {
    try {
        console.log('Recibida petición Funannotate predict:', req.body);

        // Validar parámetros
        const validation = validateFunannotateParams(req.body, 'predict');
        if (!validation.valid) {
            return res.status(400).json({
                success: false,
                error: validation.error
            });
        }

        // Generar ID único para el trabajo
        currentJobId = uuidv4();
        funannotateProgress = 0;
        funannotateLogs = [];
        
        // Configurar el parser de progreso para predict
        progressParser.setWorkflow('predict');

        // Convertir rutas del frontend a rutas del contenedor
        const containerInputFolder = convertToContainerPath(req.body.inputFolder);
        const containerOutputFolder = convertToContainerPath(req.body.outputFolder);
        
        console.log(`🔄 Rutas convertidas para predict:`);
        console.log(`   Input: ${req.body.inputFolder} → ${containerInputFolder}`);
        console.log(`   Output: ${req.body.outputFolder} → ${containerOutputFolder}`);

        // Crear directorios de salida
        fs.ensureDirSync(containerOutputFolder);

        // Procesar archivo FASTA (limpiar headers si es necesario)
        const autoCleanHeaders = req.body.autoCleanHeaders !== false; // Default: true
        let processedFileName;
        
        try {
            const fastaResult = await processFastaFile(req.body.inputFolder, req.body.input, autoCleanHeaders);
            processedFileName = fastaResult.processedFile;
            
            if (fastaResult.needsFix) {
                funannotateLogs.push({ 
                    timestamp: new Date(), 
                    type: 'success',
                    message: `Preprocesamiento completado: Headers FASTA arreglados automáticamente`
                });
            }
        } catch (error) {
            return res.status(400).json({
                success: false,
                error: `Error procesando archivo FASTA: ${error.message}`
            });
        }

        // Construir comando Docker con el archivo procesado y rutas convertidas
        const updatedParams = { 
            ...req.body, 
            input: processedFileName,
            inputFolder: containerInputFolder,
            outputFolder: containerOutputFolder
        };
        const command = buildFunannotateCommand(updatedParams, 'predict');
        console.log('Comando Docker Funannotate predict:', command);

        // Ejecutar comando
        currentProcess = exec(command, {
            cwd: process.cwd(),
            maxBuffer: 1024 * 1024 * 10 // 10MB buffer
        });

        // Manejar salida estándar
        currentProcess.stdout.on('data', (data) => {
            const message = data.toString();
            funannotateLogs.push({ timestamp: new Date(), type: 'stdout', message });
            console.log('Funannotate stdout:', message);
            
            // Actualizar progreso basado en mensajes de salida
            updateProgressFromLogs(message);
        });

        // Manejar errores
        currentProcess.stderr.on('data', (data) => {
            const message = data.toString();
            
            // Detectar errores críticos de Funannotate
            const isCriticalError = message.includes('Genome assembly error') || 
                                   message.includes('headers contain more characters') ||
                                   message.includes('failed') ||
                                   message.includes('Error:');
            
            funannotateLogs.push({ 
                timestamp: new Date(), 
                type: isCriticalError ? 'error' : 'stderr', 
                message,
                critical: isCriticalError
            });
            
            console.error('Funannotate stderr:', message);
            
            // Si es error crítico, marcar progreso como fallido
            if (isCriticalError) {
                funannotateProgress = -1;
                console.error('❌ Error crítico detectado:', message);
            }
        });

        // Manejar finalización
        currentProcess.on('close', (code) => {
            console.log(`Proceso Funannotate predict terminado con código: ${code}`);
            funannotateProgress = code === 0 ? 100 : -1;
            
            if (code === 0) {
                funannotateLogs.push({ 
                    timestamp: new Date(), 
                    type: 'success', 
                    message: 'Funannotate predict completado exitosamente' 
                });
            } else {
                funannotateLogs.push({ 
                    timestamp: new Date(), 
                    type: 'error', 
                    message: `Funannotate predict falló con código de salida: ${code}` 
                });
            }
            
            currentProcess = null;
        });

        res.json({
            success: true,
            message: 'Funannotate predict iniciado correctamente',
            jobId: currentJobId,
            command: command
        });

    } catch (error) {
        console.error('Error al ejecutar Funannotate predict:', error);
        res.status(500).json({
            success: false,
            error: 'Error interno del servidor: ' + error.message
        });
    }
});

// Endpoint para ejecutar Funannotate annotate
app.post('/annotate', async (req, res) => {
    try {
        console.log('Recibida petición Funannotate annotate:', req.body);

        // Validar parámetros
        const validation = validateFunannotateParams(req.body, 'annotate');
        if (!validation.valid) {
            return res.status(400).json({
                success: false,
                error: validation.error
            });
        }

        // Generar ID único para el trabajo
        currentJobId = uuidv4();
        funannotateProgress = 0;
        funannotateLogs = [];
        
        // Configurar el parser de progreso para annotate
        progressParser.setWorkflow('annotate');

        // Convertir rutas del frontend a rutas del contenedor
        const containerInputFolder = convertToContainerPath(req.body.inputFolder);
        const containerOutputFolder = convertToContainerPath(req.body.outputFolder);
        
        console.log(`🔄 Rutas convertidas para annotate:`);
        console.log(`   Input: ${req.body.inputFolder} → ${containerInputFolder}`);
        console.log(`   Output: ${req.body.outputFolder} → ${containerOutputFolder}`);

        // Crear directorios de salida
        fs.ensureDirSync(containerOutputFolder);

        // Para annotate, el input debería ser una carpeta de resultados de predict
        // No necesitamos procesar headers FASTA aquí, pero podemos validar que existe
        const inputPath = path.join(containerInputFolder, req.body.input);
        if (!await fs.pathExists(inputPath)) {
            return res.status(400).json({
                success: false,
                error: `Archivo o carpeta de entrada no encontrada: ${req.body.input}`
            });
        }

        // Construir comando Docker con rutas convertidas
        const updatedParams = { 
            ...req.body,
            inputFolder: containerInputFolder,
            outputFolder: containerOutputFolder
        };
        const command = buildFunannotateCommand(updatedParams, 'annotate');
        console.log('Comando Docker Funannotate annotate:', command);

        // Ejecutar comando
        currentProcess = exec(command, {
            cwd: process.cwd(),
            maxBuffer: 1024 * 1024 * 10
        });

        currentProcess.stdout.on('data', (data) => {
            const message = data.toString();
            funannotateLogs.push({ timestamp: new Date(), type: 'stdout', message });
            console.log('Funannotate stdout:', message);
            updateProgressFromLogs(message);
        });

        currentProcess.stderr.on('data', (data) => {
            const message = data.toString();
            
            // Detectar errores críticos de Funannotate
            const isCriticalError = message.includes('Genome assembly error') || 
                                   message.includes('headers contain more characters') ||
                                   message.includes('failed') ||
                                   message.includes('Error:');
            
            funannotateLogs.push({ 
                timestamp: new Date(), 
                type: isCriticalError ? 'error' : 'stderr', 
                message,
                critical: isCriticalError
            });
            
            console.error('Funannotate stderr:', message);
            
            // Si es error crítico, marcar progreso como fallido
            if (isCriticalError) {
                funannotateProgress = -1;
                console.error('❌ Error crítico detectado:', message);
            }
        });

        currentProcess.on('close', (code) => {
            console.log(`Proceso Funannotate annotate terminado con código: ${code}`);
            funannotateProgress = code === 0 ? 100 : -1;
            currentProcess = null;
        });

        res.json({
            success: true,
            message: 'Funannotate annotate iniciado correctamente',
            jobId: currentJobId,
            command: command
        });

    } catch (error) {
        console.error('Error al ejecutar Funannotate annotate:', error);
        res.status(500).json({
            success: false,
            error: 'Error interno del servidor: ' + error.message
        });
    }
});

// Función para actualizar progreso basado en logs usando el parser especializado
function updateProgressFromLogs(message) {
    const result = progressParser.parseLogLine(message);
    
    if (result.updated) {
        funannotateProgress = result.progress;
        
        // Agregar información de etapa a los logs
        funannotateLogs.push({ 
            timestamp: new Date(), 
            type: result.progress === -1 ? 'error' : 'progress',
            message: `[${result.stage}] ${message}`,
            stage: result.stage,
            progress: result.progress
        });
        
        console.log(`📊 Progreso actualizado: ${result.progress}% - ${result.stage}`);
        
        // Manejo de errores
        if (result.error) {
            console.error(`❌ Error detectado: ${result.error}`);
            funannotateLogs.push({ 
                timestamp: new Date(), 
                type: 'error',
                message: `Error: ${result.error}`
            });
        }
    } else {
        // Aunque no hay progreso específico, agregar el log para visibilidad completa
        funannotateLogs.push({
            timestamp: new Date(),
            type: 'info',
            message: message.trim()
        });
    }
}

// Función para procesar archivo FASTA (limpiar headers si es necesario)
async function processFastaFile(inputFolder, fileName, autoCleanHeaders = true) {
    // Convertir ruta del frontend a ruta del contenedor
    const containerInputFolder = convertToContainerPath(inputFolder);
    const filePath = path.join(containerInputFolder, fileName);
    
    console.log(`🔄 Conversión de ruta:`);
    console.log(`   Frontend: ${inputFolder}`);
    console.log(`   Contenedor: ${containerInputFolder}`);
    console.log(`   Archivo completo: ${filePath}`);
    
    if (!autoCleanHeaders) {
        // Solo verificar que el archivo existe
        if (await fs.pathExists(filePath)) {
            return { processedFile: fileName, originalFile: fileName, needsFix: false };
        } else {
            throw new Error(`Archivo no encontrado: ${fileName}`);
        }
    }
    
    try {
        console.log(`🔍 Procesando archivo FASTA: ${fileName}`);
        const result = await headerFixer.processFile(filePath);
        
        if (result.needsFix) {
            // Se generó un archivo con headers arreglados
            const processedFileName = path.basename(result.processedFile);
            console.log(`✅ Headers arreglados: ${fileName} → ${processedFileName}`);
            
            funannotateLogs.push({ 
                timestamp: new Date(), 
                type: 'info',
                message: `Headers FASTA arreglados automáticamente: ${result.stats.headersProcessed} headers, ${result.stats.truncatedHeaders} truncados`
            });
            
            return { 
                processedFile: processedFileName, 
                originalFile: fileName, 
                needsFix: true,
                stats: result.stats
            };
        } else {
            // El archivo está bien, usar el original
            console.log(`✅ Headers OK: ${fileName} no necesita corrección`);
            return { 
                processedFile: fileName, 
                originalFile: fileName, 
                needsFix: false 
            };
        }
    } catch (error) {
        console.error(`❌ Error procesando FASTA: ${error.message}`);
        throw new Error(`Error procesando archivo FASTA: ${error.message}`);
    }
}

// Endpoint SSE para progreso en tiempo real
app.get('/funannotate-progress-stream', (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    });

    const sendProgress = () => {
        const data = {
            progress: funannotateProgress,
            logs: funannotateLogs.slice(-50), // Últimos 50 logs
            jobId: currentJobId,
            isRunning: currentProcess !== null
        };
        
        res.write(`data: ${JSON.stringify(data)}\n\n`);
    };

    // Enviar progreso inicial
    sendProgress();

    // Enviar progreso cada 2 segundos
    const interval = setInterval(sendProgress, 2000);

    // Limpiar cuando el cliente se desconecta
    req.on('close', () => {
        clearInterval(interval);
        res.end();
    });
});

// Endpoint para obtener status del trabajo
app.get('/status', (req, res) => {
    res.json({
        success: true,
        progress: funannotateProgress,
        isRunning: currentProcess !== null,
        jobId: currentJobId,
        logs: funannotateLogs.slice(-20) // Últimos 20 logs
    });
});

// Endpoint para cancelar trabajo
app.post('/cancel', (req, res) => {
    try {
        if (currentProcess) {
            currentProcess.kill('SIGTERM');
            currentProcess = null;
            funannotateProgress = -1;
            funannotateLogs.push({ 
                timestamp: new Date(), 
                type: 'info', 
                message: 'Trabajo cancelado por el usuario' 
            });
        }
        
        res.json({
            success: true,
            message: 'Trabajo cancelado exitosamente'
        });
    } catch (error) {
        console.error('Error al cancelar trabajo:', error);
        res.status(500).json({
            success: false,
            error: 'Error al cancelar trabajo'
        });
    }
});

// Manejo de errores no capturados
process.on('uncaughtException', (error) => {
    console.error('Error no capturado:', error);
    if (currentProcess) {
        currentProcess.kill('SIGTERM');
    }
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Promesa rechazada no manejada:', reason);
});

// Iniciar servidor
app.listen(port, () => {
    console.log(`Servidor Funannotate ejecutándose en puerto ${port}`);
    console.log(`Health check disponible en: http://localhost:${port}/health`);
});

module.exports = app;