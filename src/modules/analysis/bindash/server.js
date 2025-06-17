#!/usr/bin/env node

/**
 * Servidor Bindash para FungiGT
 * ===========================
 * 
 * Proporciona API REST para análisis genómicos usando Bindash
 * - Comparación de genomas
 * - Análisis de distancias genómicas
 * - Clustering de secuencias
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { spawn } = require('child_process');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 4007;

// Variables globales para progreso
let bindashProgress = 0;
let bindashLogs = [];
let progressClients = [];

// Configuración de middleware
app.use(cors({
    origin: ['http://localhost:4005', 'http://localhost:3000', 'http://127.0.0.1:4005'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'Accept']
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configuración de almacenamiento para archivos
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadPath = '/data/bindash_uploads';
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
    limits: { fileSize: 100 * 1024 * 1024 }, // 100MB
    fileFilter: (req, file, cb) => {
        const allowedTypes = ['.fasta', '.fa', '.fna', '.fas', '.fastq', '.fq'];
        const ext = path.extname(file.originalname).toLowerCase();
        if (allowedTypes.includes(ext)) {
            cb(null, true);
        } else {
            cb(new Error('Tipo de archivo no permitido. Use: .fasta, .fa, .fna, .fas, .fastq, .fq'));
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

const runBindashCommand = (command, args, options = {}) => {
    return new Promise((resolve, reject) => {
        console.log(`🚀 Ejecutando: ${command} ${args.join(' ')}`);
        
        const process = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            ...options
        });

        let stdout = '';
        let stderr = '';

        process.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        process.stderr.on('data', (data) => {
            stderr += data.toString();
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

// Rutas de la API

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        service: 'bindash-analysis',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

// Información del servicio
app.get('/info', (req, res) => {
    res.json({
        service: 'Bindash Analysis Service',
        description: 'Análisis genómico usando Bindash para comparación de genomas',
        version: '1.0.0',
        endpoints: [
            'GET /health - Health check',
            'GET /info - Información del servicio',
            'POST /upload - Subir archivos FASTA',
            'POST /sketch - Crear sketch de genoma',
            'POST /compare - Comparar genomas',
            'POST /distance - Calcular distancias genómicas',
            'GET /results/:jobId - Obtener resultados de análisis'
        ],
        formats: ['FASTA', 'FASTQ'],
        maxFileSize: '100MB'
    });
});

// Subir archivos
app.post('/upload', upload.array('files', 10), async (req, res) => {
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

// Crear sketch de genoma
app.post('/sketch', async (req, res) => {
    try {
        const { inputFile, kmerSize = 21, sketchSize = 1000 } = req.body;
        
        if (!inputFile) {
            return res.status(400).json({ error: 'Se requiere inputFile' });
        }

        const jobId = uuidv4();
        const outputDir = `/data/bindash_results/${jobId}`;
        const sketchFile = path.join(outputDir, 'sketch.txt');

        await createDirectoryIfNotExists(outputDir);

        console.log(`🧬 Creando sketch para: ${inputFile}`);

        // Ejecutar bindash sketch
        const result = await runBindashCommand('bindash', [
            'sketch',
            '--kmer', kmerSize.toString(),
            '--sketch-size', sketchSize.toString(),
            '--outfn', sketchFile,
            inputFile
        ]);

        // Leer resultado del sketch
        const sketchContent = await fs.readFile(sketchFile, 'utf8');

        res.json({
            jobId,
            message: 'Sketch creado correctamente',
            parameters: { kmerSize, sketchSize },
            sketchFile,
            preview: sketchContent.split('\n').slice(0, 10).join('\n') + '...',
            stdout: result.stdout
        });

    } catch (error) {
        console.error('❌ Error creando sketch:', error);
        res.status(500).json({ error: error.message });
    }
});

// Comparar genomas
app.post('/compare', async (req, res) => {
    try {
        const { files, kmerSize = 21, threshold = 0.1 } = req.body;
        
        if (!files || files.length < 2) {
            return res.status(400).json({ error: 'Se requieren al menos 2 archivos para comparar' });
        }

        const jobId = uuidv4();
        const outputDir = `/data/bindash_results/${jobId}`;
        const resultFile = path.join(outputDir, 'comparison.txt');

        await createDirectoryIfNotExists(outputDir);

        console.log(`🔍 Comparando ${files.length} genomas`);

        // Ejecutar bindash para comparación
        const args = [
            'dist',
            '--kmer', kmerSize.toString(),
            '--threshold', threshold.toString(),
            '--outfn', resultFile,
            ...files
        ];

        const result = await runBindashCommand('bindash', args);

        // Leer y procesar resultados
        const comparisonContent = await fs.readFile(resultFile, 'utf8');
        const lines = comparisonContent.trim().split('\n');
        
        const comparisons = lines.map(line => {
            const [file1, file2, distance, pvalue, similarity] = line.split('\t');
            return {
                genome1: path.basename(file1),
                genome2: path.basename(file2),
                distance: parseFloat(distance),
                pvalue: parseFloat(pvalue),
                similarity: parseFloat(similarity)
            };
        });

        res.json({
            jobId,
            message: 'Comparación completada',
            parameters: { kmerSize, threshold },
            totalComparisons: comparisons.length,
            comparisons,
            resultFile,
            stdout: result.stdout
        });

    } catch (error) {
        console.error('❌ Error en comparación:', error);
        res.status(500).json({ error: error.message });
    }
});

// Calcular matriz de distancias
app.post('/distance', async (req, res) => {
    try {
        const { files, kmerSize = 21, outputFormat = 'phylip' } = req.body;
        
        if (!files || files.length < 2) {
            return res.status(400).json({ error: 'Se requieren al menos 2 archivos' });
        }

        const jobId = uuidv4();
        const outputDir = `/data/bindash_results/${jobId}`;
        const distanceFile = path.join(outputDir, `distances.${outputFormat}`);

        await createDirectoryIfNotExists(outputDir);

        console.log(`📊 Calculando matriz de distancias para ${files.length} genomas`);

        // Ejecutar bindash distance
        const args = [
            'dist',
            '--kmer', kmerSize.toString(),
            '--outfn', distanceFile,
            '--format', outputFormat,
            ...files
        ];

        const result = await runBindashCommand('bindash', args);

        // Leer matriz de distancias
        const distanceContent = await fs.readFile(distanceFile, 'utf8');

        res.json({
            jobId,
            message: 'Matriz de distancias calculada',
            parameters: { kmerSize, outputFormat },
            genomeCount: files.length,
            distanceMatrix: distanceContent,
            distanceFile,
            stdout: result.stdout
        });

    } catch (error) {
        console.error('❌ Error calculando distancias:', error);
        res.status(500).json({ error: error.message });
    }
});

// Obtener resultados de análisis
app.get('/results/:jobId', async (req, res) => {
    try {
        const { jobId } = req.params;
        const resultDir = `/data/bindash_results/${jobId}`;

        // Verificar que el directorio existe
        await fs.access(resultDir);

        // Listar archivos en el directorio
        const files = await fs.readdir(resultDir);
        const fileDetails = [];

        for (const file of files) {
            const filePath = path.join(resultDir, file);
            const stats = await fs.stat(filePath);
            const content = await fs.readFile(filePath, 'utf8');

            fileDetails.push({
                filename: file,
                size: stats.size,
                modified: stats.mtime,
                preview: content.length > 1000 ? content.substring(0, 1000) + '...' : content
            });
        }

        res.json({
            jobId,
            resultDirectory: resultDir,
            files: fileDetails,
            totalFiles: files.length
        });

    } catch (error) {
        if (error.code === 'ENOENT') {
            res.status(404).json({ error: 'Resultados no encontrados para este jobId' });
        } else {
            console.error('❌ Error obteniendo resultados:', error);
            res.status(500).json({ error: error.message });
        }
    }
});

// Endpoint principal para ejecutar Bindash desde el frontend
app.post('/run-bindash', async (req, res) => {
    try {
        const { mode, ...params } = req.body;
        
        if (!mode) {
            return res.status(400).json({ error: 'Se requiere especificar el modo de operación' });
        }

        const jobId = uuidv4();
        const outputDir = `/data/bindash_results/${jobId}`;
        await createDirectoryIfNotExists(outputDir);

        console.log(`🧬 Ejecutando Bindash en modo: ${mode}`);
        console.log(`📋 Parámetros:`, params);

        let result;
        let outputPath;

        if (mode === 'sketch') {
            result = await executeSketchMode(params, outputDir, jobId);
            outputPath = result.outputPath;
        } else if (mode === 'dist') {
            result = await executeDistMode(params, outputDir, jobId);
            outputPath = result.outputPath;
        } else if (mode === 'complete') {
            result = await executeCompleteMode(params, outputDir, jobId);
            outputPath = result.outputPath;
        } else {
            return res.status(400).json({ error: `Modo no soportado: ${mode}` });
        }

        res.json({
            jobId,
            mode,
            message: `Bindash ejecutado correctamente en modo ${mode}`,
            outputPath,
            ...result
        });

    } catch (error) {
        console.error('❌ Error ejecutando Bindash:', error);
        res.status(500).json({ error: error.message });
    }
});

// Función para ejecutar modo sketch
const executeSketchMode = async (params, outputDir, jobId) => {
    const { 
        sketchInput, 
        sketchOutput, 
        useListFile = false,
        kmerSize = '21',
        sketchSize = '32',
        bbits = '14',
        nthreads = '1',
        verbose = false
    } = params;

    if (!sketchInput || !sketchOutput) {
        throw new Error('Se requieren sketchInput y sketchOutput para el modo sketch');
    }

    // Construir argumentos del comando
    const args = ['sketch'];
    
    // Archivo de entrada
    if (useListFile) {
        args.push('--listfname=' + sketchInput);
    } else {
        args.push(sketchInput);
    }
    
    // Archivo de salida
    const outputPath = path.join(outputDir, sketchOutput);
    args.push('--outfname=' + outputPath);
    
    // Parámetros correctos
    args.push('--kmerlen=' + kmerSize);
    args.push('--sketchsize64=' + sketchSize);
    args.push('--bbits=' + bbits);
    args.push('--nthreads=' + nthreads);

    console.log(`🚀 Ejecutando: bindash ${args.join(' ')}`);
    
    const result = await runBindashCommand('bindash', args);
    
    return {
        outputPath,
        command: `bindash ${args.join(' ')}`,
        stdout: result.stdout,
        stderr: result.stderr
    };
};

// Función para ejecutar modo dist
const executeDistMode = async (params, outputDir, jobId) => {
    const { 
        querySketch, 
        targetSketch, 
        distOutput,
        ithres = '2',           // Umbral de intersección
        mthres = '2.5',         // Umbral de distancia de mutación
        nneighbors = '0',       // Número de mejores resultados
        nthreads = '1',         // Número de hilos
        pthres = '1.0001'       // Umbral de p-value
    } = params;

    if (!querySketch) {
        throw new Error('Se requiere querySketch para el modo dist');
    }

    // Construir argumentos del comando
    const args = ['dist'];
    
    // Sketches de entrada
    args.push(querySketch);
    if (targetSketch) {
        args.push(targetSketch);
    }
    
    // Archivo de salida (opcional)
    let outputPath;
    if (distOutput) {
        outputPath = path.join(outputDir, distOutput);
        args.push('--outfname=' + outputPath);
    }
    
    // Parámetros correctos para bindash dist
    args.push('--ithres=' + ithres);
    args.push('--mthres=' + mthres);
    args.push('--nneighbors=' + nneighbors);
    args.push('--nthreads=' + nthreads);
    args.push('--pthres=' + pthres);

    console.log(`🚀 Ejecutando: bindash ${args.join(' ')}`);
    
    const result = await runBindashCommand('bindash', args);
    
    return {
        outputPath: outputPath || 'stdout',
        command: `bindash ${args.join(' ')}`,
        stdout: result.stdout,
        stderr: result.stderr,
        distances: result.stdout // Las distancias se imprimen en stdout
    };
};

// Función para ejecutar modo completo
const executeCompleteMode = async (params, outputDir, jobId) => {
    const { 
        genomesDir, 
        filePattern = '*.fasta', 
        outputPrefix,
        kmerSize = '21',
        sketchSize = '32',
        bbits = '14',
        nthreads = '1'
    } = params;

    if (!genomesDir || !outputPrefix) {
        throw new Error('Se requieren genomesDir y outputPrefix para el modo completo');
    }

    // Resetear progreso
    updateProgress(0, 'Iniciando análisis BinDash...');

    const listFile = path.join(outputDir, `${outputPrefix}_genomes.txt`);
    const sketchFile = path.join(outputDir, `${outputPrefix}.sketch`);
    const distanceFile = path.join(outputDir, `${outputPrefix}_distances.txt`);

    // Convertir ruta relativa a absoluta si es necesario
    let absoluteGenomesDir = genomesDir;
    if (!path.isAbsolute(genomesDir)) {
        absoluteGenomesDir = path.resolve('/data', genomesDir.replace(/^\.\//, ''));
    }

    console.log(`📁 Directorio de genomas: ${absoluteGenomesDir}`);
    updateProgress(5, `Verificando directorio: ${absoluteGenomesDir}`);

    // Verificar que el directorio existe
    try {
        await fs.access(absoluteGenomesDir);
        updateProgress(10, 'Directorio verificado correctamente');
    } catch (error) {
        throw new Error(`El directorio de genomas no existe: ${absoluteGenomesDir}`);
    }

    // Paso 1: Crear lista de genomas
    updateProgress(15, 'Creando lista de genomas...');
    console.log(`📝 Paso 1: Creando lista de genomas`);
    const { spawn } = require('child_process');
    
    await new Promise((resolve, reject) => {
        const command = `find "${absoluteGenomesDir}" -name "${filePattern}" -type f > "${listFile}"`;
        console.log(`🔍 Ejecutando: ${command}`);
        
        const ls = spawn('sh', ['-c', command]);
        
        let stderr = '';
        ls.stderr.on('data', (data) => {
            stderr += data.toString();
        });
        
        ls.on('close', (code) => {
            if (code === 0) {
                console.log(`✅ Lista de genomas creada: ${listFile}`);
                updateProgress(25, 'Lista de genomas creada exitosamente');
                resolve();
            } else {
                console.error(`❌ Error en comando: ${command}`);
                console.error(`❌ stderr: ${stderr}`);
                reject(new Error(`Error creando lista de genomas: código ${code}, stderr: ${stderr}`));
            }
        });
    });

    // Verificar que se encontraron archivos
    const listContent = await fs.readFile(listFile, 'utf8');
    const genomeFiles = listContent.trim().split('\n').filter(line => line.length > 0);
    
    if (genomeFiles.length === 0) {
        throw new Error(`No se encontraron archivos con patrón "${filePattern}" en ${absoluteGenomesDir}`);
    }
    
    console.log(`📊 Encontrados ${genomeFiles.length} archivos de genomas`);
    updateProgress(30, `Encontrados ${genomeFiles.length} archivos de genomas`);

    // Paso 2: Crear sketch
    updateProgress(35, 'Iniciando creación de sketch...');
    console.log(`🧬 Paso 2: Creando sketch`);
    const sketchArgs = [
        'sketch',
        '--listfname=' + listFile,
        '--outfname=' + sketchFile,
        '--kmerlen=' + kmerSize,
        '--sketchsize64=' + sketchSize,
        '--bbits=' + bbits,
        '--nthreads=' + nthreads
    ];

    updateProgress(40, 'Ejecutando comando sketch...');
    const sketchResult = await runBindashCommand('bindash', sketchArgs);
    updateProgress(70, 'Sketch creado exitosamente');

    // Paso 3: Calcular distancias
    updateProgress(75, 'Iniciando cálculo de distancias...');
    console.log(`📊 Paso 3: Calculando distancias`);
    const distArgs = [
        'dist',
        sketchFile,
        '--outfname=' + distanceFile
    ];

    updateProgress(80, 'Ejecutando cálculo de distancias...');
    const distResult = await runBindashCommand('bindash', distArgs);
    updateProgress(95, 'Distancias calculadas exitosamente');

    updateProgress(100, 'Análisis BinDash completado exitosamente');

    return {
        outputPath: distanceFile,
        listFile,
        sketchFile,
        distanceFile,
        genomeCount: genomeFiles.length,
        genomeFiles: genomeFiles.slice(0, 10),
        commands: [
            `find "${absoluteGenomesDir}" -name "${filePattern}" -type f > "${listFile}"`,
            `bindash ${sketchArgs.join(' ')}`,
            `bindash ${distArgs.join(' ')}`
        ],
        sketchStdout: sketchResult.stdout,
        distStdout: distResult.stdout,
        stderr: sketchResult.stderr + '\n' + distResult.stderr
    };
};

// Ruta de ejemplo/demo
app.get('/demo', (req, res) => {
    res.json({
        message: 'Bindash Demo - Comandos de ejemplo',
        examples: [
            {
                description: 'Crear sketch de un genoma',
                command: 'POST /sketch',
                payload: {
                    inputFile: '/data/uploads/genome.fasta',
                    kmerSize: 21,
                    sketchSize: 1000
                }
            },
            {
                description: 'Comparar dos genomas',
                command: 'POST /compare',
                payload: {
                    files: ['/data/uploads/genome1.fasta', '/data/uploads/genome2.fasta'],
                    kmerSize: 21,
                    threshold: 0.1
                }
            },
            {
                description: 'Calcular matriz de distancias',
                command: 'POST /distance',
                payload: {
                    files: ['/data/uploads/genome1.fasta', '/data/uploads/genome2.fasta', '/data/uploads/genome3.fasta'],
                    kmerSize: 21,
                    outputFormat: 'phylip'
                }
            }
        ]
    });
});

// Función para actualizar progreso
const updateProgress = (progress, message) => {
    bindashProgress = progress;
    bindashLogs.push({
        timestamp: new Date().toISOString(),
        message: message,
        progress: progress
    });
    
    // Mantener solo los últimos 50 logs
    if (bindashLogs.length > 50) {
        bindashLogs = bindashLogs.slice(-50);
    }
    
    // Enviar a todos los clientes conectados
    progressClients.forEach(client => {
        try {
            client.write(`data: ${JSON.stringify({
                progress: progress,
                message: message,
                timestamp: new Date().toISOString()
            })}\n\n`);
        } catch (error) {
            console.error('Error enviando progreso:', error);
        }
    });
    
    console.log(`📊 Progreso: ${progress}% - ${message}`);
};

// Endpoint para Server-Sent Events (progreso en tiempo real)
app.get('/bindash-progress', (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    });

    // Agregar cliente a la lista
    progressClients.push(res);
    
    // Enviar estado actual
    res.write(`data: ${JSON.stringify({
        progress: bindashProgress,
        message: 'Conectado al sistema de progreso',
        timestamp: new Date().toISOString()
    })}\n\n`);

    // Limpiar cliente cuando se desconecte
    req.on('close', () => {
        progressClients = progressClients.filter(client => client !== res);
    });
});

// Middleware de manejo de errores
app.use((err, req, res, next) => {
    console.error('❌ Error no manejado:', err);
    res.status(500).json({ 
        error: 'Error interno del servidor',
        message: err.message 
    });
});

// Inicializar directorios necesarios
const initializeDirectories = async () => {
    const dirs = [
        '/data/bindash_uploads',
        '/data/bindash_results'
    ];

    for (const dir of dirs) {
        await createDirectoryIfNotExists(dir);
        console.log(`📁 Directorio creado/verificado: ${dir}`);
    }
};

// Iniciar servidor
const startServer = async () => {
    try {
        await initializeDirectories();

        app.listen(PORT, '0.0.0.0', () => {
            console.log(`
🧬 ================================
   BINDASH ANALYSIS SERVICE
🧬 ================================
🚀 Servidor ejecutándose en puerto ${PORT}
🌐 URL: http://localhost:${PORT}
📋 Health: http://localhost:${PORT}/health
📖 Info: http://localhost:${PORT}/info
🎯 Demo: http://localhost:${PORT}/demo
🧬 ================================
            `);
        });

    } catch (error) {
        console.error('❌ Error iniciando servidor:', error);
        process.exit(1);
    }
};

// Manejo de señales
process.on('SIGINT', () => {
    console.log('\n🛑 Cerrando servidor Bindash...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 Terminando servidor Bindash...');
    process.exit(0);
});

// Iniciar aplicación
startServer(); 