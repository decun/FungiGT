const express = require('express');
const { spawn, exec } = require('child_process');
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');
const cors = require('cors');
const os = require('os');
const archiver = require('archiver');

const app = express();
const port = 3004;

// Almacenar los trabajos de BRAKER3 en ejecución y sus logs
const runningJobs = {};
let currentProcess = null;
let braker3Progress = 0;
let braker3Logs = [];
let currentJobId = null;

// CORS configuration para permitir solicitudes desde el frontend
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Función para convertir rutas de Windows a formato Docker
const convertPath = (p) => {
    return p.replace(/\\/g, '/');
};

// Configuración de multer para subir archivos con nombre original
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        const inputFolder = req.body.inputFolderPath || 'data/raw/genomes/braker3';

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

// Función para validar parámetros de BRAKER3
function validateBraker3Params(params) {
    console.log("Validando parámetros:", JSON.stringify(params, null, 2));
    
    // Extraer parámetros con diferentes nombres posibles
    const species = params.species;
    const genome = params.genome;
    const threads = params.threads;
    
    // Manejar las diferentes versiones de nombres de parámetros
    const inputFolder = params.inputFolder || params.inputFolderPath;
    const outputFolder = params.outputFolder || params.outputFolderPath;
    
    console.log("Parámetros extraídos:", { species, genome, threads, inputFolder, outputFolder });
    
    // Verificar valores obligatorios
    if (!species || !genome || !threads || !inputFolder || !outputFolder) {
        const missing = [];
        if (!species) missing.push('species');
        if (!genome) missing.push('genome');
        if (!threads) missing.push('threads');
        if (!inputFolder) missing.push('inputFolder/inputFolderPath');
        if (!outputFolder) missing.push('outputFolder/outputFolderPath');
        
        return {
            valid: false,
            error: `Faltan parámetros obligatorios para BRAKER3: ${missing.join(', ')}`
        };
    }
    
    // Validar threads (debe ser un número)
    if (isNaN(parseInt(threads)) || parseInt(threads) <= 0) {
        return {
            valid: false,
            error: 'El número de hilos debe ser un número positivo'
        };
    }
    
    return { 
        valid: true,
        // Devolver valores normalizados
        inputFolderPath: inputFolder,
        outputFolderPath: outputFolder,
        species,
        genome,
        threads
    };
}

// Función para validar rutas
async function validatePaths(inputPath, outputPath) {
    console.log("Validando rutas:", { inputPath, outputPath });
    
    try {
        // Verificar que las rutas existan o se puedan crear
        await fs.ensureDir(inputPath);
        await fs.ensureDir(outputPath);
        
        return { valid: true };
    } catch (error) {
        console.error("Error al validar rutas:", error);
        return {
            valid: false,
            error: `Error validando rutas: ${error.message}`
        };
    }
}

// Función para actualizar el progreso basado en la salida de BRAKER3
function updateBraker3ProgressFromOutput(output) {
    // Analizar el texto para identificar patrones de progreso de BRAKER3
    
    // Fase: Iniciando BRAKER3
    if (output.includes('BRAKER PIPELINE STARTED')) {
        braker3Progress = 5;
        braker3Logs.push({ type: 'info', text: 'Pipeline BRAKER3 iniciado' });
    }
    
    // Fase: Preparación del genoma
    else if (output.includes('Preparing genome') || output.includes('softmasking')) {
        braker3Progress = 10;
        braker3Logs.push({ type: 'info', text: 'Preparando genoma y aplicando softmasking' });
    }
    
    // Fase: GeneMark-EX
    else if (output.includes('GeneMark-EX') || output.includes('Starting GeneMark')) {
        braker3Progress = 20;
        braker3Logs.push({ type: 'info', text: 'Ejecutando GeneMark-EX para predicción inicial de genes' });
    }
    
    // Fase: Entrenamiento de AUGUSTUS
    else if (output.includes('Training AUGUSTUS') || output.includes('augustus training')) {
        braker3Progress = 40;
        braker3Logs.push({ type: 'info', text: 'Entrenando modelo AUGUSTUS (puede tardar)' });
    }
    
    // Fase: Predicción con AUGUSTUS
    else if (output.includes('Running AUGUSTUS') || output.includes('augustus prediction')) {
        braker3Progress = 60;
        braker3Logs.push({ type: 'info', text: 'Ejecutando predicción de genes con AUGUSTUS' });
    }
    
    // Fase: Integración de evidencias
    else if (output.includes('Integrating') || output.includes('evidence integration')) {
        braker3Progress = 75;
        braker3Logs.push({ type: 'info', text: 'Integrando evidencias y refinando predicciones' });
    }
    
    // Fase: Generación de archivos finales
    else if (output.includes('Writing') && (output.includes('.gff') || output.includes('.gtf'))) {
        braker3Progress = 85;
        braker3Logs.push({ type: 'info', text: 'Generando archivos de anotación finales' });
    }
    
    // Fase: Estadísticas finales
    else if (output.includes('Statistics') || output.includes('Summary')) {
        braker3Progress = 95;
        braker3Logs.push({ type: 'info', text: 'Generando estadísticas y resumen final' });
    }
    
    // Fase: Completado
    else if (output.includes('BRAKER PIPELINE FINISHED') || output.includes('braker.pl finished')) {
        braker3Progress = 100;
        braker3Logs.push({ type: 'success', text: 'Pipeline BRAKER3 completado exitosamente' });
    }
    
    // Capturar errores específicos
    else if (output.includes('ERROR') || output.includes('FATAL')) {
        braker3Logs.push({ type: 'error', text: output.trim() });
    }
    
    // Capturar warnings
    else if (output.includes('WARNING') || output.includes('WARN')) {
        braker3Logs.push({ type: 'warning', text: output.trim() });
    }
    
    // Capturar información general importante
    else if (output.includes('INFO') || output.includes('Processing')) {
        braker3Logs.push({ type: 'info', text: output.trim() });
    }
    
    console.log(`Progreso BRAKER3: ${braker3Progress}%`);
}

// Función para ejecutar BRAKER3 usando spawn para captura en tiempo real
function executeBraker3WithRealTimeLogging(dockerArgs, jobId) {
    return new Promise((resolve, reject) => {
        console.log('Ejecutando Docker con args:', dockerArgs);
        
        // Reiniciar logs y progreso para nueva ejecución
        braker3Logs = [];
        braker3Progress = 0;
        currentJobId = jobId;
        
        // Ejecutar usando spawn para captura en tiempo real
        currentProcess = spawn('docker', dockerArgs);
        
        let stdout = '';
        let stderr = '';
        
        // Capturar la salida estándar
        currentProcess.stdout.on('data', (data) => {
            const output = data.toString();
            stdout += output;
            braker3Logs.push({ type: 'stdout', text: output });
            updateBraker3ProgressFromOutput(output);
            
            // Actualizar el trabajo en runningJobs
            if (runningJobs[jobId]) {
                runningJobs[jobId].progress = braker3Progress;
                runningJobs[jobId].logs = braker3Logs.slice(-10); // Últimos 10 logs
            }
        });
        
        // Capturar la salida de error (donde BRAKER3 muestra mucha información)
        currentProcess.stderr.on('data', (data) => {
            const output = data.toString();
            stderr += output;
            braker3Logs.push({ type: 'stderr', text: output });
            updateBraker3ProgressFromOutput(output);
            
            // Actualizar el trabajo en runningJobs
            if (runningJobs[jobId]) {
                runningJobs[jobId].progress = braker3Progress;
                runningJobs[jobId].logs = braker3Logs.slice(-10); // Últimos 10 logs
            }
        });
        
        currentProcess.on('close', (code) => {
            console.log(`Proceso BRAKER3 terminado con código: ${code}`);
            
            // Establecer progreso al 100% solo cuando realmente termina exitosamente
            if (code === 0) {
                braker3Progress = 100;
                braker3Logs.push({ 
                    type: 'success', 
                    text: 'BRAKER3 completado exitosamente'
                });
                
                if (runningJobs[jobId]) {
                    runningJobs[jobId].status = 'Completado';
                    runningJobs[jobId].progress = 100;
                    runningJobs[jobId].completed = true;
                    runningJobs[jobId].output = stdout;
                }
                
                resolve(stdout);
            } else {
                braker3Logs.push({ 
                    type: 'error', 
                    text: `BRAKER3 terminó con errores (código ${code})`
                });
                
                if (runningJobs[jobId]) {
                    runningJobs[jobId].status = 'Error';
                    runningJobs[jobId].error = `Proceso terminó con código ${code}`;
                    runningJobs[jobId].completed = true;
                }
                
                reject(new Error(`Proceso terminó con código ${code}: ${stderr}`));
            }
            
            currentProcess = null;
            currentJobId = null;
        });
        
        currentProcess.on('error', (error) => {
            console.error('Error al ejecutar proceso BRAKER3:', error);
            braker3Logs.push({ 
                type: 'error', 
                text: `Error al ejecutar proceso: ${error.message}`
            });
            
            if (runningJobs[jobId]) {
                runningJobs[jobId].status = 'Error';
                runningJobs[jobId].error = error.message;
                runningJobs[jobId].completed = true;
            }
            
            reject(error);
        });
    });
}

// Ruta para subir archivos para BRAKER3
app.post('/upload', upload.array('fnaFiles'), (req, res) => {
    if (!req.files || req.files.length === 0) {
        return res.status(400).json({ 
            success: false,
            error: 'No se subieron archivos' 
        });
    }

    console.log('Archivos subidos para BRAKER3:', req.files.map(f => f.originalname));
    
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

// Ruta para ejecutar BRAKER3
app.post('/execute-braker3', async (req, res) => {
    try {
        console.log('Parámetros recibidos en execute-braker3:', JSON.stringify(req.body, null, 2));
        
        // Validar parámetros
        const validationResult = validateBraker3Params(req.body);
        
        if (!validationResult.valid) {
            console.error('Error de validación:', validationResult.error);
            return res.status(400).json({
                success: false,
                error: validationResult.error
            });
        }
        
        // Usar los valores validados
        const { species, genome, threads, inputFolderPath, outputFolderPath } = validationResult;
        const { bam, prot_seq, flags } = req.body;
        
        // Validar rutas
        const pathsValidation = await validatePaths(inputFolderPath, outputFolderPath);
        if (!pathsValidation.valid) {
            console.error('Error de validación de rutas:', pathsValidation.error);
            return res.status(400).json({
                success: false,
                error: pathsValidation.error
            });
        }
        
        // Generar un ID único para este trabajo
        const jobId = Date.now().toString();
        
        // Convertir rutas a formato Docker
        const dockerInputPath = convertPath(inputFolderPath);
        const dockerOutputPath = convertPath(outputFolderPath);
        
        // Construir el array de argumentos para Docker
        const dockerArgs = [
            'run',
            '--rm',
            '-v', `${dockerInputPath}:/input`,
            '-v', `${dockerOutputPath}:/output`,
            'teambraker/braker3:latest',
            'braker.pl',
            `--species=${species}`,
            `--genome=/input/${genome}`,
            `--threads=${threads}`
        ];
        
        // Agregar parámetros opcionales
        if (bam && bam.trim() !== '') {
            dockerArgs.push(`--bam=/input/${bam}`);
        }
        
        if (prot_seq && prot_seq.trim() !== '') {
            dockerArgs.push(`--prot_seq=/input/${prot_seq}`);
        }
        
        // Si hay flags, agregarlos
        if (flags && flags.trim() !== '') {
            flags.split(' ').filter(Boolean).forEach(flag => dockerArgs.push(flag));
        }
        
        // Agregar el directorio de trabajo
        dockerArgs.push('--workingdir=/output');
        
        // Construir el comando para mostrar (solo para logging)
        const dockerCommand = `docker ${dockerArgs.join(' ')}`;
        console.log('Ejecutando Docker con:', dockerCommand);
        
        // Responder inmediatamente al cliente con el ID del trabajo
        res.status(200).json({
            success: true,
            message: 'BRAKER3 iniciado correctamente',
            jobId: jobId,
            command: dockerCommand
        });
        
        // Registrar el trabajo como iniciado
        runningJobs[jobId] = {
            status: 'Ejecutando',
            progress: 0,
            completed: false,
            logs: []
        };
        
        // Ejecutar BRAKER3 usando executeBraker3WithRealTimeLogging
        executeBraker3WithRealTimeLogging(dockerArgs, jobId)
            .then((output) => {
                console.log(`BRAKER3 completado exitosamente. JobID: ${jobId}`);
                // El estado ya se actualiza dentro de la función
            })
            .catch((error) => {
                console.error(`Error en el trabajo BRAKER3 (${jobId}):`, error);
                // El estado ya se actualiza dentro de la función
            });
    } catch (error) {
        console.error('Error al ejecutar BRAKER3:', error);
        
        res.status(500).json({ 
            success: false,
            error: `Error al ejecutar BRAKER3: ${error.message}` 
        });
    }
});

// Ruta para verificar el progreso de un trabajo
app.get('/progress', (req, res) => {
    const jobId = req.query.id;
    
    if (!jobId || !runningJobs[jobId]) {
        return res.status(404).json({
            success: false,
            error: 'Trabajo no encontrado'
        });
    }
    
    // Devolver el estado actual del trabajo
    res.json({
        success: true,
        ...runningJobs[jobId]
    });
});

// Ruta para obtener el progreso actual mediante SSE (Server-Sent Events)
app.get('/braker3-progress-stream', (req, res) => {
    // Configurar headers para SSE
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    });
    
    // Enviar el progreso actual inmediatamente
    sendBraker3Progress(res);
    
    // Crear un intervalo para enviar actualizaciones cada segundo
    const progressInterval = setInterval(() => {
        sendBraker3Progress(res);
    }, 1000);
    
    // Limpiar el intervalo cuando se cierra la conexión
    req.on('close', () => {
        clearInterval(progressInterval);
    });
});

// Ruta para obtener el progreso actual (para compatibilidad)
app.get('/braker3-progress', (req, res) => {
    res.json({ 
        success: true, 
        progress: `${braker3Progress}%`,
        logs: braker3Logs.slice(-10) // Enviar los últimos 10 logs
    });
});

// Función para enviar el progreso actual al cliente
function sendBraker3Progress(res) {
    // Enviar solo los logs más recientes e importantes
    const filteredLogs = braker3Logs
        .filter(log => log.type !== 'stderr' || log.text.includes('BRAKER') || log.text.includes('GeneMark') || log.text.includes('AUGUSTUS'))
        .slice(-5); // Últimos 5 logs importantes
    
    const data = {
        progress: braker3Progress,
        logs: filteredLogs,
        jobId: currentJobId
    };
    
    res.write(`data: ${JSON.stringify(data)}\n\n`);
}

// Ruta para servir resultados
app.get('/results', (req, res) => {
    const path = req.query.path;
    
    if (!path) {
        return res.status(400).json({
            success: false,
            error: 'Falta el parámetro path'
        });
    }
    
    try {
        // Verificar que la ruta existe
        if (!fs.existsSync(path)) {
            return res.status(404).json({
                success: false,
                error: 'La ruta especificada no existe'
            });
        }
        
        // Obtener la lista de archivos en la ruta
        const files = fs.readdirSync(path);
        
        res.json({
            success: true,
            path: path,
            files: files
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: `Error al leer el directorio: ${error.message}`
        });
    }
});

// Ruta para descargar archivos
app.get('/download', (req, res) => {
    const filePath = req.query.path;
    
    if (!filePath) {
        return res.status(400).json({
            success: false,
            error: 'Falta el parámetro path'
        });
    }
    
    try {
        // Verificar que la ruta existe
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'La ruta especificada no existe'
            });
        }
        
        // Si es un directorio, comprimirlo
        if (fs.statSync(filePath).isDirectory()) {
            const zipFileName = `braker3_results_${Date.now()}.zip`;
            const zipPath = require('path').join(os.tmpdir(), zipFileName);
            
            const output = fs.createWriteStream(zipPath);
            const archive = archiver('zip', {
                zlib: { level: 9 }
            });
            
            output.on('close', () => {
                res.download(zipPath, zipFileName, (err) => {
                    if (err) {
                        console.error('Error al enviar el archivo:', err);
                    }
                    // Eliminar el archivo temporal después de enviarlo
                    fs.unlinkSync(zipPath);
                });
            });
            
            archive.pipe(output);
            archive.directory(filePath, false);
            archive.finalize();
        } else {
            // Es un archivo, descargarlo directamente
            res.download(filePath);
        }
    } catch (error) {
        res.status(500).json({
            success: false,
            error: `Error al preparar la descarga: ${error.message}`
        });
    }
});

// Endpoint para cancelar el proceso actual de BRAKER3
app.post('/cancel-braker3', (req, res) => {
    if (currentProcess) {
        console.log('Cancelando proceso BRAKER3 actual');
        
        // En Windows usamos taskkill para asegurar que se termina el proceso y sus hijos
        const killProcess = spawn('taskkill', ['/pid', currentProcess.pid, '/f', '/t']);
        
        killProcess.on('close', (code) => {
            console.log(`Proceso BRAKER3 terminado con código: ${code}`);
            braker3Progress = 0;
            braker3Logs.push({ type: 'error', text: 'Proceso cancelado por el usuario' });
            
            // Actualizar el trabajo actual si existe
            if (currentJobId && runningJobs[currentJobId]) {
                runningJobs[currentJobId].status = 'Cancelado';
                runningJobs[currentJobId].completed = true;
                runningJobs[currentJobId].error = 'Proceso cancelado por el usuario';
            }
            
            currentProcess = null;
            currentJobId = null;
            res.json({ success: true, message: 'Proceso BRAKER3 cancelado correctamente' });
        });
    } else {
        res.json({ success: false, message: 'No hay proceso BRAKER3 activo para cancelar' });
    }
});

// Iniciar el servidor
app.listen(port, () => {
    console.log(`Servidor de BRAKER3 ejecutándose en http://localhost:${port}`);
});

// También manejar la terminación del servidor
process.on('SIGINT', () => {
    console.log('Cerrando el servidor de BRAKER3...');
    
    // Terminar proceso BRAKER3 activo si existe
    if (currentProcess) {
        console.log('Terminando proceso BRAKER3 antes de cerrar el servidor');
        try {
            // En Windows
            spawn('taskkill', ['/pid', currentProcess.pid, '/f', '/t']);
        } catch (error) {
            console.error('Error al terminar proceso BRAKER3:', error);
        }
    }
    
    process.exit(0);
}); 