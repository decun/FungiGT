const express = require('express');
const { spawn } = require('child_process'); // Usamos spawn en lugar de exec para mayor seguridad
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra'); // Usamos fs-extra para más funcionalidades
const cors = require('cors');

const app = express();
const port = process.env.PORT || 4004; // Usar puerto desde variables de entorno o 4004 por defecto

// Almacenar el último proceso en ejecución y sus logs
let currentProcess = null;
let checkMProgress = 0;
let checkMLogs = [];

// CORS configuration para permitir solicitudes desde el frontend
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Configuración de multer para subir archivos con nombre original
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        const inputFolder = req.body.inputFolderPath; // Carpeta de destino especificada por el usuario

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
    limits: { fileSize: 500 * 1024 * 1024 } // 500MB máximo
});

// Función para validar parámetros
function validateParams(params) {
    const { workflowType, threads, inputFolderPath, outputFolderPath, fileExtension, flags } = params;
    
    // Verificar valores obligatorios
    if (!workflowType || !threads || !inputFolderPath || !outputFolderPath || !fileExtension) {
        return {
            valid: false,
            error: 'Faltan parámetros obligatorios'
        };
    }
    
    // Validar workflowType
    const validWorkflows = ['lineage_wf', 'taxonomy_wf', 'qa'];
    if (!validWorkflows.includes(workflowType)) {
        return {
            valid: false,
            error: 'Tipo de workflow no válido'
        };
    }
    
    // Validar threads (debe ser un número)
    if (isNaN(parseInt(threads)) || parseInt(threads) <= 0) {
        return {
            valid: false,
            error: 'El número de hilos debe ser un número positivo'
        };
    }
    
    // Validar extensión de archivo
    if (!/^[a-zA-Z0-9]+$/.test(fileExtension)) {
        return {
            valid: false,
            error: 'Extensión de archivo no válida'
        };
    }
    
    // Validar flags (opcional)
    if (flags) {
        const validFlags = ['--reduced_tree', '--quiet', '--tab_table'];
        const providedFlags = flags.split(' ').filter(Boolean);
        
        for (const flag of providedFlags) {
            if (!validFlags.includes(flag)) {
                return {
                    valid: false,
                    error: `Flag no válido: ${flag}`
                };
            }
        }
    }
    
    return { valid: true };
}

// Función para validar rutas
async function validatePaths(inputPath, outputPath) {
    try {
        // Verificar que las rutas existan o se puedan crear
        await fs.ensureDir(inputPath);
        await fs.ensureDir(outputPath);
        
        return { valid: true };
    } catch (error) {
        return {
            valid: false,
            error: `Error validando rutas: ${error.message}`
        };
    }
}

// Ruta para subir archivos .fna
app.post('/upload-checkm', upload.array('fnaFiles'), (req, res) => {
    if (!req.files || req.files.length === 0) {
        return res.status(400).json({ error: 'No se subieron archivos' });
    }

    console.log('Archivos subidos:', req.files.map(f => f.originalname));
    
    // Crear también el directorio de salida si se especificó
    if (req.body.outputFolderPath) {
        fs.ensureDirSync(req.body.outputFolderPath);
    }
    
    res.json({ 
        success: true,
        message: 'Archivos subidos con éxito', 
        files: req.files.map(f => ({ name: f.originalname, size: f.size }))
    });
});

// Ruta para ejecutar CheckM usando Docker
app.post('/execute-checkm', async (req, res) => {
    try {
        const { workflowType, threads, fileExtension, flags, inputFolderPath, outputFolderPath } = req.body;
        
        // Reiniciar logs y progreso para nueva ejecución
        checkMLogs = [];
        checkMProgress = 0;
        
        // Asegurarse de que las carpetas existen
        await fs.ensureDir(inputFolderPath);
        await fs.ensureDir(outputFolderPath);
        
        // Configurar argumentos para Docker
        const dockerArgs = [
            'run',
            '--rm',
            '-v', `${inputFolderPath}:/input`,
            '-v', `${outputFolderPath}:/output`,
            'nanozoo/checkm:latest',
            'checkm',
            workflowType,
            '-t', threads.toString(),
            '-x', fileExtension
        ];
        
        // Si hay flags, agregarlos
        if (flags) {
            flags.split(' ').filter(Boolean).forEach(flag => dockerArgs.push(flag));
        }
        
        // Agregar las rutas de entrada/salida dentro del contenedor
        dockerArgs.push('/input', '/output');
        
        console.log('Ejecutando Docker con:', dockerArgs.join(' '));
        
        // Ejecutar usando spawn
        currentProcess = spawn('docker', dockerArgs);
        
        let stdout = '';
        let stderr = '';
        
        // Capturar la salida estándar
        currentProcess.stdout.on('data', (data) => {
            const output = data.toString();
            stdout += output;
            checkMLogs.push({ type: 'stdout', text: output });
            updateProgressFromOutput(output);
        });
        
        // Capturar la salida de error (donde CheckM muestra su progreso)
        currentProcess.stderr.on('data', (data) => {
            const output = data.toString();
            stderr += output;
            checkMLogs.push({ type: 'stderr', text: output });
            updateProgressFromOutput(output);
        });
        
        currentProcess.on('close', (code) => {
            console.log(`Proceso CheckM terminado con código: ${code}`);
            
            // Establecer progreso al 100% solo cuando realmente termina
            checkMProgress = 100;
            checkMLogs.push({ 
                type: code === 0 ? 'success' : 'error', 
                text: code === 0 ? 'CheckM completado exitosamente' : `CheckM terminó con errores (código ${code})`
            });
            
            if (code !== 0) {
                console.error(`Docker process exited with code ${code}`);
                // No enviamos la respuesta aquí, ya la hemos enviado antes
            }
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ 
            success: false,
            error: `Error interno del servidor: ${error.message}` 
        });
    }
});

// Ruta para obtener el progreso actual mediante SSE (Server-Sent Events)
app.get('/checkm-progress-stream', (req, res) => {
    // Configurar headers para SSE
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    });
    
    // Enviar el progreso actual inmediatamente
    sendProgress(res);
    
    // Crear un intervalo para enviar actualizaciones cada segundo
    const progressInterval = setInterval(() => {
        sendProgress(res);
    }, 1000);
    
    // Limpiar el intervalo cuando se cierra la conexión
    req.on('close', () => {
        clearInterval(progressInterval);
    });
});

// Ruta para obtener el progreso actual (para compatibilidad)
app.get('/checkm-progress', (req, res) => {
    res.json({ 
        success: true, 
        progress: `${checkMProgress}%`,
        logs: checkMLogs.slice(-10) // Enviar los últimos 10 logs
    });
});

// Función para enviar el progreso actual al cliente
function sendProgress(res) {
    // Enviar solo los logs más recientes e importantes
    const filteredLogs = checkMLogs
        .filter(log => log.type !== 'stderr' || log.text.includes('CheckM'))
        .slice(-5); // Últimos 5 logs importantes
    
    const data = {
        progress: checkMProgress,
        logs: filteredLogs
    };
    
    res.write(`data: ${JSON.stringify(data)}\n\n`);
}

// Función mejorada para actualizar el progreso basado en la salida de CheckM
function updateProgressFromOutput(output) {
    // Analizar el texto para identificar patrones de progreso de manera más eficiente
    
    // Fase: Iniciando CheckM
    if (output.includes('[CheckM - tree]')) {
        checkMProgress = 5;
        checkMLogs.push({ type: 'info', text: 'Iniciando análisis: Colocando genomas en árbol de referencia' });
    }
    
    // Fase: Identificando genes marcadores
    else if (output.includes('Identifying marker genes')) {
        checkMProgress = 10;
        checkMLogs.push({ type: 'info', text: 'Identificando genes marcadores en genomas' });
    }
    
    // Fase: Extracción de HMMs - actualizar solo en incrementos del 10%
    else if (output.includes('Extracting') && output.includes('HMMs')) {
        const match = output.match(/Finished extracting (\d+) of (\d+) \(([0-9.]+)%\) HMMs/);
        if (match && match[3]) {
            const extractionProgress = parseFloat(match[3]);
            // Solo actualizar en incrementos significativos para reducir logs
            if (extractionProgress % 10 < 1 || extractionProgress > 95) {
                checkMProgress = 15 + Math.floor(extractionProgress * 0.15);
                checkMLogs.push({ 
                    type: 'progress', 
                    text: `Extrayendo HMMs: ${match[1]} de ${match[2]} (${match[3]}%)`
                });
            }
        }
    }
    
    // Fase: Alineamiento de genes marcadores - actualizar solo en incrementos del 10%
    else if (output.includes('Aligning') && output.includes('marker genes')) {
        const match = output.match(/Finished aligning (\d+) of (\d+) \(([0-9.]+)%\) marker genes/);
        if (match && match[3]) {
            const alignmentProgress = parseFloat(match[3]);
            // Solo actualizar en incrementos significativos
            if (alignmentProgress % 10 < 1 || alignmentProgress > 95) {
                checkMProgress = 30 + Math.floor(alignmentProgress * 0.2);
                checkMLogs.push({ 
                    type: 'progress', 
                    text: `Alineando genes marcadores: ${match[1]} de ${match[2]} (${match[3]}%)`
                });
            }
        }
    }
    
    // Fase: Colocación en árbol
    else if (output.includes('Placing') && output.includes('bins into the genome tree')) {
        checkMProgress = 50;
        checkMLogs.push({ type: 'info', text: 'Colocando genomas en árbol filogenético (puede tardar)' });
    }
    
    // Fase: Current stage (tiempo transcurrido)
    else if (output.includes('Current stage:')) {
        const timeMatch = output.match(/Current stage: ([0-9:\.]+)/);
        if (timeMatch) {
            checkMLogs.push({ type: 'time', text: `Tiempo de ejecución: ${timeMatch[1]}` });
        }
    }
    
    // Fase: Conjuntos de marcadores específicos de linaje
    else if (output.includes('[CheckM - lineage_set]')) {
        checkMProgress = 70;
        checkMLogs.push({ type: 'info', text: 'Inferencia de conjuntos de marcadores específicos de linaje' });
    }
    
    // Fase: Análisis final
    else if (output.includes('[CheckM - analyze]')) {
        checkMProgress = 80;
        checkMLogs.push({ type: 'info', text: 'Fase final: Identificando genes marcadores en genomas' });
    }
    
    // Fase: qa
    else if (output.includes('[CheckM - qa]')) {
        checkMProgress = 90;
        checkMLogs.push({ type: 'info', text: 'Realizando control de calidad y evaluación final' });
    }
    
    // Fase: Terminado (estas líneas suelen aparecer al final)
    else if (output.includes('...done.') || 
             output.includes('Results written to') || 
             output.includes('Output table written to')) {
        checkMProgress = 99; // No ponemos 100 hasta que realmente termine el proceso
        checkMLogs.push({ type: 'success', text: 'Análisis completado, generando resultados' });
    }
    
    console.log(`Progreso actual: ${checkMProgress}%`);
}

// Ruta para obtener archivos
app.get('/download-file/:filename', (req, res) => {
    const { filename } = req.params;
    const { path } = req.query;
    
    if (!path) {
        return res.status(400).json({ 
            success: false,
            error: 'No se especificó la ruta del archivo' 
        });
    }
    
    // Sanitizar la ruta
    const sanitizedPath = path.replace(/[;&|`${}[\]\\\/"'*?~<>^]/g, '');
    const filePath = `${sanitizedPath}/${filename}`;
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ 
            success: false,
            error: 'Archivo no encontrado' 
        });
    }
    
    res.download(filePath);
});

// Agregar un endpoint de salud para Docker healthcheck
app.get('/health', (req, res) => {
    res.json({ 
        success: true, 
        message: 'Servicio CheckM funcionando correctamente',
        service: 'quality-control-checkm',
        port: port
    });
});

// Agregar un endpoint para cancelar el proceso actual
app.post('/cancel-checkm', (req, res) => {
    if (currentProcess) {
        console.log('Cancelando proceso CheckM actual');
        
        // En Windows usamos taskkill para asegurar que se termina el proceso y sus hijos
        const killProcess = spawn('taskkill', ['/pid', currentProcess.pid, '/f', '/t']);
        
        killProcess.on('close', (code) => {
            console.log(`Proceso terminado con código: ${code}`);
            checkMProgress = 0;
            checkMLogs.push({ type: 'error', text: 'Proceso cancelado por el usuario' });
            currentProcess = null;
            res.json({ success: true, message: 'Proceso cancelado correctamente' });
        });
    } else {
        res.json({ success: false, message: 'No hay proceso activo para cancelar' });
    }
});

// Iniciar el servidor
app.listen(port, () => {
    console.log(`🔬 Servidor CheckM (Quality Control) ejecutándose en http://localhost:${port}`);
    console.log(`📊 Endpoints disponibles:`);
    console.log(`   - GET /health - Estado del servicio`);
    console.log(`   - POST /upload-checkm - Subir archivos genómicos`);
    console.log(`   - POST /execute-checkm - Ejecutar análisis CheckM`);
    console.log(`   - GET /checkm-progress - Obtener progreso actual`);
    console.log(`   - GET /checkm-progress-stream - Stream de progreso (SSE)`);
    console.log(`   - POST /cancel-checkm - Cancelar proceso actual`);
});

// También manejar la terminación del servidor
process.on('SIGINT', () => {
    if (currentProcess) {
        console.log('Terminando proceso CheckM antes de cerrar el servidor');
        try {
            // En Windows
            spawn('taskkill', ['/pid', currentProcess.pid, '/f', '/t']);
        } catch (error) {
            console.error('Error al terminar proceso:', error);
        }
    }
    process.exit(0);
});