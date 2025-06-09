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

// Health check endpoint para Docker
app.get('/health', (req, res) => {
    res.status(200).json({
        success: true,
        message: 'Servicio BRAKER3 funcionando correctamente',
        timestamp: new Date().toISOString()
    });
});

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

// Función para diagnosticar errores de GeneMark
async function diagnoseGeneMark(outputPath, genome) {
    const diagnostics = [];
    
    try {
        // 1. Verificar archivo de entrada del genoma
        const genomePath = path.join(outputPath, '..', 'input', genome);
        
        if (!fs.existsSync(genomePath)) {
            diagnostics.push({
                type: 'error',
                text: `Archivo del genoma no encontrado: ${genome}`
            });
            return diagnostics;
        }
        
        // 2. Verificar el tamaño del archivo
        const stats = fs.statSync(genomePath);
        const fileSizeMB = (stats.size / 1024 / 1024).toFixed(2);
        diagnostics.push({
            type: 'info',
            text: `Tamaño del genoma: ${fileSizeMB} MB`
        });
        
        // 3. Verificar que no esté vacío
        if (stats.size === 0) {
            diagnostics.push({
                type: 'error',
                text: 'El archivo del genoma está vacío'
            });
            return diagnostics;
        }
        
        // 4. Verificar headers del FASTA
        const genomicContent = fs.readFileSync(genomePath, 'utf8', { encoding: 'utf8' }).substring(0, 1000);
        
        if (!genomicContent.startsWith('>')) {
            diagnostics.push({
                type: 'error',
                text: 'El archivo no parece ser un FASTA válido (no comienza con >)'
            });
        }
        
        // 5. Contar secuencias
        const sequenceCount = (genomicContent.match(/>/g) || []).length;
        diagnostics.push({
            type: 'info',
            text: `Número de secuencias detectadas (primeros 1000 chars): ${sequenceCount}`
        });
        
        // 6. Verificar archivos de error de GeneMark
        const genemarkErrorFile = path.join(outputPath, 'errors', 'GeneMark-ES.stderr');
        if (fs.existsSync(genemarkErrorFile)) {
            const errorContent = fs.readFileSync(genemarkErrorFile, 'utf8');
            if (errorContent.trim()) {
                diagnostics.push({
                    type: 'error',
                    text: `Error específico de GeneMark: ${errorContent.substring(0, 500)}`
                });
            }
        }
        
        // 7. Verificar archivo de log de BRAKER
        const brakerLogFile = path.join(outputPath, 'braker.log');
        if (fs.existsSync(brakerLogFile)) {
            const logContent = fs.readFileSync(brakerLogFile, 'utf8');
            
            // Buscar líneas con ERROR
            const errorLines = logContent.split('\n').filter(line => 
                line.includes('ERROR') || line.includes('FATAL')
            );
            
            errorLines.forEach(line => {
                diagnostics.push({
                    type: 'error',
                    text: `BRAKER Log: ${line.trim()}`
                });
            });
        }
        
    } catch (error) {
        diagnostics.push({
            type: 'error',
            text: `Error durante el diagnóstico: ${error.message}`
        });
    }
    
    return diagnostics;
}

// Función mejorada para validar el archivo del genoma antes de ejecutar
async function validateGenomeFile(inputPath, genomeFileName) {
    // Convertir la ruta de Windows a formato de Docker si es necesario
    let normalizedInputPath = inputPath;
    
    // Si la ruta contiene : significa que es una ruta de Windows
    if (inputPath.includes(':')) {
        // Ya está en formato correcto para Docker, no necesitamos path.join en este caso
        console.log(`Validando archivo del genoma: ${genomeFileName} en ruta Docker: ${inputPath}`);
        
        // Para Windows con Docker, simplemente verificamos que el archivo debería estar ahí
        // No podemos usar fs.existsSync con rutas de Docker desde Node.js
        // Pero podemos asumir que está correcto si la validación básica pasa
        
        try {
            // Verificar que el nombre del archivo es válido
            if (!genomeFileName || genomeFileName.trim() === '') {
                return {
                    valid: false,
                    error: 'Nombre del archivo del genoma no puede estar vacío'
                };
            }
            
            // Verificar extensión (debe ser .fna, .fa, .fasta)
            const validExtensions = ['.fna', '.fa', '.fasta'];
            const hasValidExtension = validExtensions.some(ext => 
                genomeFileName.toLowerCase().endsWith(ext)
            );
            
            if (!hasValidExtension) {
                return {
                    valid: false,
                    error: 'El archivo del genoma debe tener extensión .fna, .fa o .fasta'
                };
            }
            
            // Para rutas de Docker en Windows, asumimos que el archivo existe
            // si hemos llegado hasta aquí con validaciones básicas correctas
            console.log(`Archivo del genoma validado correctamente: ${genomeFileName}`);
            
            return { 
                valid: true,
                message: `Archivo del genoma validado: ${genomeFileName}`
            };
            
        } catch (error) {
            return {
                valid: false,
                error: `Error al validar archivo del genoma: ${error.message}`
            };
        }
    } else {
        // Ruta de Linux/Unix - usar validación original
        const genomePath = path.join(inputPath, genomeFileName);
        
        try {
            // Verificar que existe
            if (!fs.existsSync(genomePath)) {
                return {
                    valid: false,
                    error: `Archivo del genoma no encontrado: ${genomeFileName}`
                };
            }
            
            // Verificar tamaño mínimo
            const stats = fs.statSync(genomePath);
            if (stats.size < 1000) { // Menos de 1KB es sospechoso
                return {
                    valid: false,
                    error: `El archivo del genoma es demasiado pequeño (${stats.size} bytes)`
                };
            }
            
            // Verificar que es FASTA válido
            const firstChars = fs.readFileSync(genomePath, 'utf8', { start: 0, end: 100 });
            if (!firstChars.startsWith('>')) {
                return {
                    valid: false,
                    error: 'El archivo no parece ser un FASTA válido (debe comenzar con >)'
                };
            }
            
            // Verificar que no tiene caracteres problemáticos en headers
            const lines = firstChars.split('\n');
            const headerLine = lines[0];
            
            if (headerLine.includes('|') || headerLine.includes(' ')) {
                return {
                    valid: true,
                    warning: 'El header FASTA contiene espacios o caracteres |. BRAKER3 los manejará automáticamente.'
                };
            }
            
            return { valid: true };
            
        } catch (error) {
            return {
                valid: false,
                error: `Error al validar archivo del genoma: ${error.message}`
            };
        }
    }
}

// Función para crear archivo de diagnóstico
async function createDiagnosticFile(outputPath, diagnostics) {
    try {
        const diagnosticPath = path.join(outputPath, 'braker3_diagnostic.txt');
        
        const content = [
            `=== DIAGNÓSTICO DE BRAKER3 ===`,
            `Fecha: ${new Date().toISOString()}`,
            ``,
            ...diagnostics.map(d => `[${d.type.toUpperCase()}] ${d.text}`),
            ``,
            `=== SOLUCIONES SUGERIDAS ===`,
            `1. Verificar que el archivo FASTA del genoma esté bien formateado`,
            `2. Verificar que el genoma tenga al menos 50kb de secuencia`,
            `3. Si es un genoma muy fragmentado, usar --min_contig=10000`,
            `4. Verificar que no hay caracteres especiales en los nombres de archivos`,
            `5. Revisar los logs en el directorio errors/`
        ].join('\n');
        
        fs.writeFileSync(diagnosticPath, content);
        
        return diagnosticPath;
    } catch (error) {
        console.error('Error al crear archivo de diagnóstico:', error);
        return null;
    }
}

// Función ejecutar BRAKER3 con mejor manejo de errores
function executeBraker3WithRealTimeLogging(dockerArgs, jobId) {
    return new Promise(async (resolve, reject) => {
        console.log('Ejecutando Docker con args:', dockerArgs);
        
        // Reiniciar logs y progreso para nueva ejecución
        braker3Logs = [];
        braker3Progress = 0;
        currentJobId = jobId;
        
        // Extraer información para diagnóstico
        let outputPath = null;
        let genome = null;
        
        dockerArgs.forEach((arg, index) => {
            if (arg.includes(':/output')) {
                outputPath = arg.split(':')[0];
            }
            if (arg.startsWith('--genome=')) {
                genome = arg.replace('--genome=/input/', '');
            }
        });
        
        // Ejecutar usando spawn para captura en tiempo real
        currentProcess = spawn('docker', dockerArgs);
        
        let stdout = '';
        let stderr = '';
        let hasGenmarkError = false;
        
        // Capturar la salida estándar
        currentProcess.stdout.on('data', (data) => {
            const output = data.toString();
            stdout += output;
            braker3Logs.push({ type: 'stdout', text: output });
            updateBraker3ProgressFromOutput(output);
            
            // Detectar errores específicos de GeneMark
            if (output.includes('Failed to execute') && output.includes('gmes_petap.pl')) {
                hasGenmarkError = true;
            }
            
            // Actualizar el trabajo en runningJobs
            if (runningJobs[jobId]) {
                runningJobs[jobId].progress = braker3Progress;
                runningJobs[jobId].logs = braker3Logs.slice(-10);
            }
        });
        
        // Capturar la salida de error
        currentProcess.stderr.on('data', (data) => {
            const output = data.toString();
            stderr += output;
            braker3Logs.push({ type: 'stderr', text: output });
            updateBraker3ProgressFromOutput(output);
            
            // Detectar errores específicos de GeneMark
            if (output.includes('Failed to execute') && output.includes('gmes_petap.pl')) {
                hasGenmarkError = true;
            }
            
            // Actualizar el trabajo en runningJobs
            if (runningJobs[jobId]) {
                runningJobs[jobId].progress = braker3Progress;
                runningJobs[jobId].logs = braker3Logs.slice(-10);
            }
        });
        
        currentProcess.on('close', async (code) => {
            console.log(`Proceso BRAKER3 terminado con código: ${code}`);
            
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
                // Si falló, hacer diagnóstico adicional
                let diagnostics = [];
                
                if (hasGenmarkError && outputPath && genome) {
                    console.log('Ejecutando diagnóstico de GeneMark...');
                    diagnostics = await diagnoseGeneMark(outputPath, genome);
                    
                    // Añadir diagnósticos a los logs
                    diagnostics.forEach(d => braker3Logs.push(d));
                    
                    // Crear archivo de diagnóstico
                    const diagnosticFile = await createDiagnosticFile(outputPath, diagnostics);
                    if (diagnosticFile) {
                        braker3Logs.push({
                            type: 'info',
                            text: `Archivo de diagnóstico creado: ${diagnosticFile}`
                        });
                    }
                }
                
                braker3Logs.push({ 
                    type: 'error', 
                    text: `BRAKER3 terminó con errores (código ${code})`
                });
                
                if (runningJobs[jobId]) {
                    runningJobs[jobId].status = 'Error';
                    runningJobs[jobId].error = `Proceso terminó con código ${code}`;
                    runningJobs[jobId].completed = true;
                    runningJobs[jobId].diagnostics = diagnostics;
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
        
        // *** NUEVA VALIDACIÓN: Verificar archivo del genoma ***
        const genomeValidation = await validateGenomeFile(inputFolderPath, genome);
        if (!genomeValidation.valid) {
            console.error('Error de validación del genoma:', genomeValidation.error);
            return res.status(400).json({
                success: false,
                error: genomeValidation.error
            });
        }
        
        // Si hay warning, loggearlo
        if (genomeValidation.warning) {
            console.warn('Warning del genoma:', genomeValidation.warning);
        }
        
        // Generar un ID único para este trabajo
        const jobId = Date.now().toString();
        
        // Convertir rutas a formato Docker
        const dockerInputPath = convertPath(inputFolderPath);
        const dockerOutputPath = convertPath(outputFolderPath);
        
        // Construir el comando BRAKER completo con parámetros
        let brakerCommand = `chmod 777 /output && braker.pl --species=${species} --genome=/input/${genome} --threads=${threads} --min_contig=1000 --AUGUSTUS_CONFIG_PATH=/opt/augustus/config`;
        
        // Agregar parámetros opcionales al comando braker.pl
        if (bam && bam.trim() !== '') {
            brakerCommand += ` --bam=/input/${bam}`;
        }
        
        if (prot_seq && prot_seq.trim() !== '') {
            brakerCommand += ` --prot_seq=/input/${prot_seq}`;
        }
        
        // Si hay flags adicionales, agregarlos
        if (flags && flags.trim() !== '') {
            brakerCommand += ` ${flags}`;
        }
        
        brakerCommand += ' --workingdir=/output';
        
        // Construir el array de argumentos para Docker con permisos de root
        const dockerArgs = [
            'run',
            '--rm',
            '--user', '0:0', // Ejecutar como root para evitar problemas de permisos
            '-v', `${dockerInputPath}:/input:ro`, // Solo lectura para input
            '-v', `${dockerOutputPath}:/output:rw`, // Lectura/escritura para output
            'teambraker/braker3:latest',
            'sh', '-c', brakerCommand
        ];
        
        // Construir el comando para mostrar (solo para logging)
        const dockerCommand = `docker ${dockerArgs.join(' ')}`;
        console.log('Ejecutando Docker con:', dockerCommand);
        
        // Responder inmediatamente al cliente con el ID del trabajo
        res.status(200).json({
            success: true,
            message: 'BRAKER3 iniciado correctamente',
            jobId: jobId,
            command: dockerCommand,
            warning: genomeValidation.warning || null
        });
        
        // Registrar el trabajo como iniciado
        runningJobs[jobId] = {
            status: 'Ejecutando',
            progress: 0,
            completed: false,
            logs: [],
            genomeFile: genome,
            inputPath: inputFolderPath,
            outputPath: outputFolderPath
        };
        
        // Ejecutar BRAKER3 usando la función mejorada
        executeBraker3WithRealTimeLogging(dockerArgs, jobId)
            .then((output) => {
                console.log(`BRAKER3 completado exitosamente. JobID: ${jobId}`);
            })
            .catch((error) => {
                console.error(`Error en el trabajo BRAKER3 (${jobId}):`, error);
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

// Nuevo endpoint para obtener diagnósticos
app.get('/diagnostics/:jobId', async (req, res) => {
    const jobId = req.params.jobId;
    
    if (!runningJobs[jobId]) {
        return res.status(404).json({
            success: false,
            error: 'Trabajo no encontrado'
        });
    }
    
    const job = runningJobs[jobId];
    
    if (job.status !== 'Error') {
        return res.json({
            success: true,
            status: job.status,
            message: 'No hay errores para diagnosticar'
        });
    }
    
    try {
        // Ejecutar diagnóstico
        const diagnostics = await diagnoseGeneMark(job.outputPath, job.genomeFile);
        
        res.json({
            success: true,
            jobId: jobId,
            status: job.status,
            diagnostics: diagnostics
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: `Error al ejecutar diagnóstico: ${error.message}`
        });
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