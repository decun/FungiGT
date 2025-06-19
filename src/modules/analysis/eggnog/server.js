#!/usr/bin/env node

/**
 * Servidor eggNOG-mapper para FungiGT
 * ===================================
 * 
 * Proporciona API REST para análisis funcional usando eggNOG-mapper
 * - Anotación funcional de proteínas
 * - Análisis de ontología genética (GO)
 * - Clasificación COG/KEGG
 * - Gestión inteligente de base de datos
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { spawn, exec } = require('child_process');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3001;

// Variables globales para progreso y estado
let eggnogProgress = 0;
let eggnogLogs = [];
let progressClients = [];
let databaseStatus = {
    isDownloaded: false,
    isDownloading: false,
    size: '0 GB',
    lastCheck: null
};

// Configuración de middleware
app.use(cors({
    origin: ['http://localhost:4005', 'http://frontend:4005', 'http://127.0.0.1:4005'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'Accept']
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configuración de almacenamiento para archivos
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadPath = '/data/eggnog_uploads';
        cb(null, uploadPath);
    },
    filename: (req, file, cb) => {
        const uniqueId = uuidv4();
        const ext = path.extname(file.originalname);
        cb(null, `${uniqueId}_${file.originalname}`);
    }
});

const upload = multer({ 
    storage: storage,
    limits: { fileSize: 500 * 1024 * 1024 }, // 500MB
    fileFilter: (req, file, cb) => {
        const allowedTypes = ['.faa', '.fasta', '.fa', '.fas', '.pep'];
        const ext = path.extname(file.originalname).toLowerCase();
        if (allowedTypes.includes(ext)) {
            cb(null, true);
        } else {
            cb(new Error('Tipo de archivo no permitido. Use: .faa, .fasta, .fa, .fas, .pep (archivos de proteínas)'));
        }
    }
});

// Utilidades
const createDirectoryIfNotExists = async (dirPath) => {
    try {
        await fs.access(dirPath);
    } catch {
        await fs.mkdir(dirPath, { recursive: true });
    }
};

const executeCommand = (command, args, options = {}) => {
    return new Promise((resolve, reject) => {
        console.log(`🚀 Ejecutando: ${command} ${args.join(' ')}`);
        
        const process = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            ...options
        });

        let stdout = '';
        let stderr = '';

        process.stdout.on('data', (data) => {
            const output = data.toString();
            stdout += output;
            // Actualizar progreso si es posible extraer del output
            updateProgressFromOutput(output);
        });

        process.stderr.on('data', (data) => {
            const error = data.toString();
            stderr += error;
            console.log(`📝 eggNOG log: ${error}`);
            eggnogLogs.push(`${new Date().toISOString()}: ${error}`);
        });

        process.on('close', (code) => {
            if (code === 0) {
                resolve({ stdout, stderr, code });
            } else {
                reject(new Error(`Comando falló con código ${code}: ${stderr}`));
            }
        });

        process.on('error', (error) => {
            reject(error);
        });
    });
};

const updateProgressFromOutput = (output) => {
    console.log(`🔍 Analizando línea para progreso: "${output}"`);
    
    // Extraer progreso de descarga de archivos (formato: XX% YY.ZM 5mXXs)
    const downloadMatches = output.match(/(\d+)%\s+[\d.]+[KMG]?\s+\d+[ms]\d+s/);
    if (downloadMatches) {
        const newProgress = parseInt(downloadMatches[1]);
        console.log(`🎯 Progreso de descarga detectado: ${newProgress}% (anterior: ${eggnogProgress}%)`);
        if (newProgress >= eggnogProgress) { // Permitir igual para mantener progreso
            eggnogProgress = newProgress;
            console.log(`📊 Progreso de descarga actualizado: ${eggnogProgress}%`);
        }
        return;
    }
    
    // Extraer progreso general (formato: XX%)
    const progressMatches = output.match(/(\d+)%/);
    if (progressMatches) {
        const newProgress = parseInt(progressMatches[1]);
        console.log(`🎯 Progreso general detectado: ${newProgress}% (anterior: ${eggnogProgress}%)`);
        if (newProgress >= eggnogProgress) { // Permitir igual para mantener progreso
            eggnogProgress = newProgress;
            console.log(`📊 Progreso general actualizado: ${eggnogProgress}%`);
        }
        return;
    }
    
    // Detectar fases específicas
    if (output.includes('Downloading')) {
        eggnogProgress = Math.max(eggnogProgress, 5);
        console.log(`📥 Fase de descarga detectada, progreso mínimo: ${eggnogProgress}%`);
    } else if (output.includes('Functional annotation of input sequences')) {
        eggnogProgress = Math.max(eggnogProgress, 10);
        console.log(`🧬 Fase de anotación detectada, progreso mínimo: ${eggnogProgress}%`);
    } else if (output.includes('Done') || output.includes('completed')) {
        eggnogProgress = 100;
        console.log(`✅ Proceso completado, progreso: ${eggnogProgress}%`);
    }
};

const broadcastProgress = () => {
    if (progressClients.length === 0) {
        console.log(`⚠️ No hay clientes conectados para enviar progreso ${eggnogProgress}%`);
        return;
    }
    
    const progressData = { 
        progress: eggnogProgress, 
        logs: eggnogLogs.slice(-5), 
        database: databaseStatus,
        timestamp: new Date().toISOString()
    };
    
    console.log(`📤 Enviando progreso a ${progressClients.length} clientes:`, progressData);
    
    progressClients.forEach((client, index) => {
        try {
            client.write(`data: ${JSON.stringify(progressData)}\n\n`);
        } catch (error) {
            console.log(`❌ Error enviando a cliente ${index}:`, error.message);
            // Remover cliente con error
            progressClients.splice(index, 1);
        }
    });
};

// Monitorear contenedores de descarga automáticos
const monitorDownloadContainers = async () => {
    try {
        // Buscar contenedores activos que usen la imagen eggnog-mapper
        const result = await executeCommand('docker', ['ps', '--format', '{{.Names}}:{{.Image}}:{{.CreatedAt}}']);
        const containers = result.stdout.split('\n')
            .filter(line => line.includes('eggnog-mapper'))
            .map(line => {
                const [name, image, createdAt] = line.split(':');
                return { name, image, createdAt };
            })
            .filter(container => container.name && container.name !== 'fungigt-eggnog-mapper');
        
        if (containers.length === 0) {
            // No hay contenedores de descarga activos
            if (databaseStatus.isDownloading) {
                console.log('🔄 No se encontraron contenedores de descarga activos, verificando estado...');
                databaseStatus.isDownloading = false;
                await checkDatabaseStatus();
            }
            return;
        }
        
        // Ordenar por fecha de creación (más reciente primero)
        containers.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        const activeContainer = containers[0]; // El más reciente
        
        console.log(`📡 Monitoreando contenedor más reciente: ${activeContainer.name}`);
        
        // Obtener logs recientes del contenedor activo
        try {
            const logResult = await executeCommand('docker', ['logs', '--tail', '3', activeContainer.name]);
            const logs = logResult.stdout.split('\n').filter(line => line.trim());
            
            let foundProgress = false;
            
            // Procesar logs para extraer progreso
            logs.forEach(log => {
                if (log.includes('%') && log.includes('K')) {
                    updateProgressFromOutput(log);
                    eggnogLogs.push(`📥 ${log.trim()}`);
                    if (eggnogLogs.length > 20) eggnogLogs.shift();
                    foundProgress = true;
                }
            });
            
            // Actualizar estado de descarga
            if (foundProgress) {
                if (!databaseStatus.isDownloading) {
                    console.log('🚀 Descarga detectada, activando monitoreo');
                }
                if (!databaseStatus.isDownloading) {
                    console.log('🚀 Descarga detectada, activando monitoreo');
                    databaseStatus.isDownloading = true;
                }
                console.log(`📊 Progreso actual: ${eggnogProgress}% | Clientes conectados: ${progressClients.length}`);
                broadcastProgress(); // Enviar progreso inmediatamente
            } else {
                // Verificar si el contenedor terminó
                const inspectResult = await executeCommand('docker', ['inspect', '--format', '{{.State.Status}}', activeContainer.name]);
                if (inspectResult.stdout.trim() === 'exited') {
                    console.log('✅ Contenedor de descarga terminó, verificando base de datos');
                    databaseStatus.isDownloading = false;
                    await checkDatabaseStatus();
                    broadcastProgress();
                }
            }
            
        } catch (error) {
            console.log(`⚠️ Error obteniendo logs de ${activeContainer.name}: ${error.message}`);
        }
        
    } catch (error) {
        console.log('ℹ️ Error monitoreando contenedores:', error.message);
    }
};

// Verificar estado de la base de datos eggNOG
const checkDatabaseStatus = async () => {
    try {
        // Verificar si existe la base de datos en el volumen montado
        const dbPath = '/data/eggnog_db';
        const dbFiles = ['eggnog.db', 'eggnog_proteins.dmnd'];
        
        let filesFound = 0;
        let totalSize = 0;
        
        for (const file of dbFiles) {
            try {
                const filePath = path.join(dbPath, file);
                const stats = await fs.stat(filePath);
                filesFound++;
                totalSize += stats.size;
            } catch (error) {
                // Archivo no encontrado
            }
        }
        
        databaseStatus.isDownloaded = filesFound === dbFiles.length;
        databaseStatus.size = `${(totalSize / (1024 * 1024 * 1024)).toFixed(2)} GB`;
        databaseStatus.lastCheck = new Date().toISOString();
        
        return databaseStatus;
    } catch (error) {
        console.error('❌ Error verificando base de datos:', error);
        return { ...databaseStatus, error: error.message };
    }
};

// Descargar base de datos eggNOG usando el contenedor
const downloadEggnogDatabase = async () => {
    // Verificar si ya hay contenedores de descarga activos
    try {
        const activeContainers = await executeCommand('docker', ['ps', '--format', '{{.Names}}:{{.Image}}']);
        const eggnogContainers = activeContainers.stdout.split('\n')
            .filter(line => line.includes('eggnog-mapper') && !line.includes('fungigt-eggnog-mapper'));
        
        if (eggnogContainers.length > 0) {
            console.log('⚠️ Ya hay contenedores de descarga activos, abortando para evitar duplicados');
            throw new Error('Ya hay una descarga en progreso. Use el botón LIMPIAR si necesita reiniciar.');
        }
    } catch (error) {
        if (error.message.includes('Ya hay una descarga')) {
            throw error;
        }
        // Si hay error verificando contenedores, continuar con precaución
        console.log('⚠️ No se pudo verificar contenedores existentes, continuando...');
    }
    
    if (databaseStatus.isDownloading) {
        throw new Error('La descarga de la base de datos ya está en progreso según el estado interno');
    }
    
    databaseStatus.isDownloading = true;
    eggnogProgress = 0;
    
    try {
        console.log('📥 Iniciando descarga de base de datos eggNOG...');
        
        // Crear directorio para la base de datos
        await createDirectoryIfNotExists('/data/eggnog_db');
        
        // Usar el contenedor nanozoo para descargar la base de datos con nombre único
        const containerName = `eggnog-download-${Date.now()}`;
        const downloadArgs = [
            'run', '--rm', '--name', containerName,
            '-v', '/data/eggnog_db:/data/eggnog_db',
            'nanozoo/eggnog-mapper:2.1.9--4f2b6c0',
            'download_eggnog_data.py',
            '--data_dir', '/data/eggnog_db',
            '-y'  // Confirmar automáticamente
        ];
        
        console.log(`🚀 Creando contenedor de descarga: ${containerName}`);
        
        // Ejecutar en background para no bloquear la API
        executeCommand('docker', downloadArgs).then(() => {
            console.log('✅ Base de datos eggNOG descargada exitosamente');
            databaseStatus.isDownloading = false;
            checkDatabaseStatus();
        }).catch((error) => {
            console.error('❌ Error descargando base de datos:', error);
            databaseStatus.isDownloading = false;
        });
        
        return { status: 'downloading', message: 'Descarga iniciada en background' };
        
    } catch (error) {
        databaseStatus.isDownloading = false;
        console.error('❌ Error iniciando descarga:', error);
        throw error;
    }
};

// Ejecutar eggNOG-mapper
const runEggnogMapper = async (params) => {
    const {
        inputFile,
        outputName,
        taxScope = '2759',
        cpu = 1,
        itype = 'proteins',
        mode = 'diamond',
        evalue = 0.001,
        pident,
        genepred = 'search',
        translate = false,
        noFileComments = false,
        resume = false,
        override = false
    } = params;
    
    const jobId = uuidv4();
    const outputDir = `/data/eggnog_results/${jobId}`;
    const dbPath = '/data/eggnog_db';
    
    await createDirectoryIfNotExists(outputDir);
    
    // Verificar que la base de datos esté disponible
    const dbStatus = await checkDatabaseStatus();
    if (!dbStatus.isDownloaded) {
        throw new Error('Base de datos eggNOG no encontrada. Por favor, descárguela primero.');
    }
    
    console.log(`🧬 Iniciando análisis eggNOG-mapper para: ${inputFile}`);
    
    // Convertir rutas del contenedor a rutas del host
    // El contenedor tiene montado /c/Memoriacosas/FungiGT/data como /data
    const hostBasePath = '/c/Memoriacosas/FungiGT';
    
    // Convertir la ruta del archivo de entrada
    let hostInputFile = inputFile;
    if (inputFile.startsWith('/data/')) {
        hostInputFile = hostBasePath + inputFile;
    }
    
    // Convertir rutas de directorios
    const hostInputDir = path.dirname(hostInputFile);
    const inputFileName = path.basename(hostInputFile);
    const hostOutputDir = hostBasePath + outputDir;
    const hostDbPath = hostBasePath + dbPath;
    
    console.log(`📁 Host input dir: ${hostInputDir}`);
    console.log(`📄 Archivo de entrada: ${inputFileName}`);
    console.log(`📁 Host output dir: ${hostOutputDir}`);
    console.log(`📁 Host db path: ${hostDbPath}`);
    
    // Construir argumentos para eggNOG-mapper
    const eggnogArgs = [
        'run', '--rm',
        '-v', `${hostInputDir}:/input:ro`,
        '-v', `${hostOutputDir}:/output`,
        '-v', `${hostDbPath}:/data/eggnog_db:ro`,
        'nanozoo/eggnog-mapper:2.1.9--4f2b6c0',
        'emapper.py',
        '-i', `/input/${inputFileName}`,
        '-o', outputName,
        '--output_dir', '/output',
        '--data_dir', '/data/eggnog_db',
        '--tax_scope', taxScope.toString(),
        '--cpu', cpu.toString(),
        '--itype', itype,
        '-m', mode,
        '--evalue', evalue.toString()
    ];
    
    // Agregar parámetros opcionales
    if (pident) eggnogArgs.push('--pident', pident.toString());
    if (genepred && itype !== 'proteins') eggnogArgs.push('--genepred', genepred);
    if (translate) eggnogArgs.push('--translate');
    if (noFileComments) eggnogArgs.push('--no_file_comments');
    if (resume) eggnogArgs.push('--resume');
    if (override) eggnogArgs.push('--override');
    
    console.log(`🐳 Comando Docker: docker ${eggnogArgs.join(' ')}`);
    
    try {
        eggnogProgress = 0;
        const result = await executeCommand('docker', eggnogArgs);
        
        // Verificar archivos de salida
        const outputFiles = await fs.readdir(outputDir); // Usar ruta del contenedor para leer
        const annotationFiles = outputFiles.filter(f => f.includes('.emapper.annotations'));
        
        return {
            jobId,
            outputPath: outputDir,
            annotationFiles,
            command: `docker ${eggnogArgs.join(' ')}`,
            stdout: result.stdout,
            stderr: result.stderr
        };
        
    } catch (error) {
        console.error('❌ Error ejecutando eggNOG-mapper:', error);
        throw error;
    }
};

// RUTAS DE LA API

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        service: 'eggnog-mapper',
        version: '2.1.9',
        timestamp: new Date().toISOString(),
        database: databaseStatus
    });
});

// Información del servicio
app.get('/info', (req, res) => {
    res.json({
        service: 'eggNOG-mapper Service',
        description: 'Análisis funcional de proteínas usando eggNOG-mapper',
        version: '2.1.9',
        container: 'nanozoo/eggnog-mapper:2.1.9--4f2b6c0',
        endpoints: [
            'GET /health - Health check',
            'GET /info - Información del servicio',
            'GET /database/status - Estado de la base de datos',
            'POST /database/download - Descargar base de datos',
            'POST /upload - Subir archivos de proteínas',
            'POST /run-eggnog - Ejecutar análisis eggNOG-mapper',
            'GET /progress - Stream de progreso en tiempo real',
            'GET /results/:jobId - Obtener resultados de análisis'
        ],
        formats: ['FASTA proteínas (.faa, .fasta, .fa, .fas, .pep)'],
        maxFileSize: '500MB',
        databaseSize: databaseStatus.size
    });
});

// Estado de la base de datos
app.get('/database/status', async (req, res) => {
    try {
        const status = await checkDatabaseStatus();
        res.json(status);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Confirmar y descargar base de datos
app.post('/database/download', async (req, res) => {
    try {
        const { confirm = false } = req.body;
        
        if (!confirm) {
            return res.json({
                message: 'Confirmación requerida',
                warning: 'La base de datos eggNOG ocupa aproximadamente 2.9 GB. ¿Desea continuar?',
                estimatedSize: '~2.9 GB',
                estimatedTime: '10-30 minutos (dependiendo de la conexión)',
                requiresConfirmation: true
            });
        }
        
        const status = await checkDatabaseStatus();
        if (status.isDownloaded) {
            return res.json({
                message: 'La base de datos ya está descargada',
                status: status
            });
        }
        
        if (status.isDownloading) {
            return res.json({
                message: 'Descarga en progreso',
                progress: eggnogProgress
            });
        }
        
        // Iniciar descarga en background
        downloadEggnogDatabase()
            .then(() => {
                console.log('✅ Descarga de base de datos completada');
            })
            .catch((error) => {
                console.error('❌ Error en descarga:', error);
            });
        
        res.json({
            message: 'Descarga iniciada',
            progress: 0,
            status: 'downloading'
        });
        
    } catch (error) {
        console.error('❌ Error manejando descarga:', error);
        res.status(500).json({ error: error.message });
    }
});

// Subir archivos
app.post('/upload', upload.array('files', 5), async (req, res) => {
    try {
        if (!req.files || req.files.length === 0) {
            return res.status(400).json({ error: 'No se subieron archivos' });
        }

        const fileInfo = req.files.map(file => ({
            originalName: file.originalname,
            filename: file.filename,
            size: file.size,
            path: file.path
        }));

        console.log(`📁 Subidos ${req.files.length} archivo(s)`);

        res.json({
            message: 'Archivos subidos correctamente',
            files: fileInfo,
            totalFiles: req.files.length
        });

    } catch (error) {
        console.error('❌ Error subiendo archivos:', error);
        res.status(500).json({ error: error.message });
    }
});

// Ejecutar eggNOG-mapper
app.post('/run-eggnog', async (req, res) => {
    try {
        console.log('📨 Solicitud recibida en /run-eggnog');
        console.log('📋 Body de la solicitud:', JSON.stringify(req.body, null, 2));
        
        const params = req.body;
        
        // Verificar parámetros requeridos
        if (!params.proteinFilePath || !params.outputName) {
            console.log('❌ Faltan parámetros requeridos');
            return res.status(400).json({ 
                error: 'Se requieren proteinFilePath y outputName' 
            });
        }
        
        // Mapear proteinFilePath a inputFile para la función runEggnogMapper
        const mappedParams = {
            ...params,
            inputFile: params.proteinFilePath
        };
        
        console.log('🚀 Iniciando análisis eggNOG-mapper...');
        console.log(`📁 Archivo de entrada: ${params.proteinFilePath}`);
        console.log(`📝 Parámetros mapeados:`, mappedParams);
        
        const result = await runEggnogMapper(mappedParams);
        
        console.log('✅ Análisis eggNOG-mapper completado');
        res.json({
            success: true,
            message: 'Análisis completado exitosamente',
            ...result
        });
        
    } catch (error) {
        console.error('❌ Error ejecutando eggNOG-mapper:', error);
        console.error('📍 Stack trace:', error.stack);
        
        // Enviar error más detallado
        const errorResponse = {
            error: error.message || 'Error interno del servidor',
            type: error.constructor.name,
            details: error.stack
        };
        
        console.log('📤 Enviando respuesta de error:', errorResponse);
        res.status(500).json(errorResponse);
    }
});

// Stream de progreso en tiempo real
app.get('/progress', (req, res) => {
    console.log(`📡 Nueva conexión de progreso desde ${req.ip || req.connection.remoteAddress}`);
    
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
        'Access-Control-Allow-Methods': 'GET'
    });
    
    progressClients.push(res);
    console.log(`📊 Total clientes conectados: ${progressClients.length}`);
    
    // Enviar estado inicial
    const initialData = { 
        progress: eggnogProgress, 
        logs: eggnogLogs.slice(-5),
        database: databaseStatus,
        timestamp: new Date().toISOString()
    };
    
    console.log(`📤 Enviando estado inicial:`, initialData);
    res.write(`data: ${JSON.stringify(initialData)}\n\n`);
    
    req.on('close', () => {
        progressClients = progressClients.filter(client => client !== res);
        console.log(`📡 Cliente desconectado. Total clientes: ${progressClients.length}`);
    });
});

// Obtener resultados de análisis
app.get('/results/:jobId', async (req, res) => {
    try {
        const { jobId } = req.params;
        const resultDir = `/data/eggnog_results/${jobId}`;
        
        const files = await fs.readdir(resultDir);
        const results = [];
        
        for (const file of files) {
            const filePath = path.join(resultDir, file);
            const stats = await fs.stat(filePath);
            results.push({
                filename: file,
                path: filePath,
                size: stats.size,
                modified: stats.mtime
            });
        }
        
        res.json({
            jobId,
            resultDir,
            files: results,
            totalFiles: results.length
        });
        
    } catch (error) {
        console.error('❌ Error obteniendo resultados:', error);
        res.status(404).json({ error: 'Resultados no encontrados' });
    }
});

// Limpiar logs
app.post('/clear-logs', (req, res) => {
    eggnogLogs = [];
    res.json({ message: 'Logs limpiados' });
});

// Limpiar descarga fallida y reiniciar
app.post('/database/clean', async (req, res) => {
    try {
        console.log('🧹 Limpiando descarga fallida...');
        
        // Detener y eliminar todos los contenedores de descarga activos
        try {
            const activeContainers = await executeCommand('docker', ['ps', '--format', '{{.Names}}:{{.Image}}']);
            const eggnogContainers = activeContainers.stdout.split('\n')
                .filter(line => line.includes('eggnog-mapper') && !line.includes('fungigt-eggnog-mapper'))
                .map(line => line.split(':')[0]);
            
            for (const containerName of eggnogContainers) {
                if (containerName.trim()) {
                    console.log(`🛑 Deteniendo contenedor: ${containerName}`);
                    try {
                        await executeCommand('docker', ['stop', containerName]);
                        await executeCommand('docker', ['rm', containerName]);
                        console.log(`✅ Contenedor eliminado: ${containerName}`);
                    } catch (error) {
                        console.log(`⚠️ Error eliminando ${containerName}: ${error.message}`);
                    }
                }
            }
        } catch (error) {
            console.log('ℹ️ No se encontraron contenedores de descarga activos');
        }
        
        // Resetear estado interno
        databaseStatus.isDownloading = false;
        eggnogProgress = 0;
        eggnogLogs = [];
        
        // Limpiar directorio de base de datos
        const dbDir = '/data/eggnog_db';
        try {
            const files = await fs.readdir(dbDir);
            for (const file of files) {
                const filePath = path.join(dbDir, file);
                await fs.unlink(filePath);
                console.log(`🗑️ Eliminado: ${file}`);
            }
        } catch (error) {
            console.log('📁 Directorio de BD ya está vacío');
        }
        
        // Verificar estado de la base de datos
        await checkDatabaseStatus();
        
        // Notificar a todos los clientes conectados
        broadcastProgress();
        
        console.log('✅ Limpieza completada - todos los contenedores eliminados');
        res.json({ 
            message: 'Descarga limpiada exitosamente - contenedores duplicados eliminados',
            status: databaseStatus 
        });
        
    } catch (error) {
        console.error('❌ Error limpiando descarga:', error);
        res.status(500).json({ error: error.message });
    }
});

// Inicializar directorios y verificar base de datos al iniciar
const initializeService = async () => {
    try {
        await createDirectoryIfNotExists('/data/eggnog_uploads');
        await createDirectoryIfNotExists('/data/eggnog_results');
        await createDirectoryIfNotExists('/data/eggnog_db');
        
        console.log('📁 Directorios inicializados');
        
        // Verificar estado inicial de la base de datos
        await checkDatabaseStatus();
        console.log(`💾 Estado de base de datos: ${databaseStatus.isDownloaded ? 'Disponible' : 'No descargada'} (${databaseStatus.size})`);
        
        // Iniciar monitoreo de contenedores de descarga
        setInterval(monitorDownloadContainers, 10000); // Cada 10 segundos
        console.log('📡 Monitor de contenedores de descarga iniciado');
        
    } catch (error) {
        console.error('❌ Error inicializando servicio:', error);
    }
};

// Iniciar servidor
const startServer = async () => {
    await initializeService();
    
    app.listen(PORT, () => {
        console.log(`🧬 eggNOG-mapper Service ejecutándose en puerto ${PORT}`);
        console.log(`📊 Panel de control: http://localhost:${PORT}/info`);
        console.log(`💾 Estado de BD: ${databaseStatus.isDownloaded ? '✅ Disponible' : '❌ No descargada'}`);
    });
};

startServer().catch(console.error);

module.exports = app; 