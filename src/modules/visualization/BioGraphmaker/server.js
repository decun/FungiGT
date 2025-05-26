const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const app = express();
const port = 5000;

// Configurar CORS - ACTUALIZADO para incluir puerto 4005
app.use(cors({
    origin: [
        'http://localhost:4000', 
        'http://localhost:3000', 
        'http://localhost:4005',  // ← AGREGADO
        'http://localhost:4200'   // ← AGREGADO para LIDA
    ],
    methods: ['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization', 'Accept'],
    credentials: true,
    exposedHeaders: ['Content-Type', 'Content-Disposition'],
    optionsSuccessStatus: 200 // Para navegadores legacy
}));

// Middleware adicional para manejar preflight requests
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', req.headers.origin);
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');
    res.header('Access-Control-Allow-Credentials', 'true');
    
    if (req.method === 'OPTIONS') {
        res.sendStatus(200);
    } else {
        next();
    }
});

// Configurar multer para el manejo de archivos
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        const uploadDir = path.join(__dirname, 'graph_maker', 'uploads');
        if (!fs.existsSync(uploadDir)){
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: function (req, file, cb) {
        cb(null, file.originalname);
    }
});

const upload = multer({ storage: storage });

// Middleware para servir archivos estáticos con headers CORS
app.use('/graphs', express.static(path.join(__dirname, 'graph_maker', 'output'), {
    setHeaders: (res, filePath) => {
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
        res.setHeader('Access-Control-Allow-Credentials', 'true');
        
        if (filePath.endsWith('.png')) {
            res.setHeader('Content-Type', 'image/png');
            res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
            res.setHeader('Pragma', 'no-cache');
            res.setHeader('Expires', '0');
        }
    }
}));

// Ruta raíz
app.get('/', (req, res) => {
    res.json({ status: 'Server is running' });
});

// Endpoint para limpiar uploads
app.post('/clear_uploads', (req, res) => {
    const uploadsDir = path.join(__dirname, 'graph_maker', 'uploads');
    if (fs.existsSync(uploadsDir)) {
        fs.readdirSync(uploadsDir).forEach(file => {
            const filePath = path.join(uploadsDir, file);
            try {
                fs.unlinkSync(filePath);
            } catch (error) {
                console.error(`Error al eliminar ${filePath}:`, error);
            }
        });
    }
    res.json({ status: 'success', message: 'Uploads cleared successfully' });
});

// Endpoint para procesar archivos de anotaciones
app.post('/process-annotations', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No se subió ningún archivo' });
    }

    const timestamp = Date.now();
    const outputDir = path.join(__dirname, 'graph_maker', 'output', `annotations_${timestamp}`);
    if (!fs.existsSync(outputDir)){
        fs.mkdirSync(outputDir, { recursive: true });
    }

    // Usar la ruta correcta del script en PythonScripts
    const scriptPath = path.join(__dirname, 'PythonScripts', 'process_annotations.py');
    const command = `python "${scriptPath}" "${req.file.path}" "${outputDir}"`;
    
    console.log('Ejecutando comando:', command);
    
    exec(command, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error: ${error}`);
            console.error(`stderr: ${stderr}`);
            return res.status(500).json({ error: error.message });
        }

        console.log(`stdout: ${stdout}`);
        
        const graphs = fs.readdirSync(outputDir)
            .filter(file => file.endsWith('.png'))
            .map(file => `/graphs/annotations_${timestamp}/${file}`);

        res.json({ 
            message: 'Procesamiento completado',
            graphs: graphs
        });
    });
});

// Endpoint para procesar datos HMMER
app.post('/process-hmmer', upload.single('file'), (req, res) => {
    // Asegurar que la respuesta sea JSON
    res.setHeader('Content-Type', 'application/json');

    if (!req.file) {
        return res.status(400).json({ error: 'No se subió ningún archivo' });
    }

    const timestamp = Date.now();
    const outputDir = path.join(__dirname, 'graph_maker', 'output', `hmmer_${timestamp}`);
    
    try {
        if (!fs.existsSync(outputDir)){
            fs.mkdirSync(outputDir, { recursive: true });
        }

        // Usar la ruta correcta del script en PythonScripts
        const scriptPath = path.join(__dirname, 'PythonScripts', 'process_hmmer_data.py');
        if (!fs.existsSync(scriptPath)) {
            return res.status(500).json({ 
                error: 'Script de procesamiento no encontrado' 
            });
        }

        const command = process.platform === 'win32' 
            ? `python "${scriptPath}" "${req.file.path}" "${outputDir}"`
            : `python3 "${scriptPath}" "${req.file.path}" "${outputDir}"`;

        console.log('Ejecutando comando:', command);

        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error('Error al ejecutar script:', error);
                console.error('stderr:', stderr);
                return res.status(500).json({ 
                    error: 'Error al procesar el archivo',
                    details: stderr 
                });
            }

            console.log(`stdout: ${stdout}`);

            const graphs = fs.readdirSync(outputDir)
                .filter(file => file.endsWith('.png'))
                .map(file => `/graphs/hmmer_${timestamp}/${file}`);

            if (graphs.length === 0) {
                return res.status(500).json({ 
                    error: 'No se encontraron gráficos generados' 
                });
            }

            res.json({ 
                message: 'Procesamiento completado',
                graphs: graphs
            });
        });
    } catch (error) {
        console.error('Error inesperado:', error);
        res.status(500).json({ 
            error: 'Error interno del servidor',
            details: error.message 
        });
    }
});

// Endpoint para limpiar archivos temporales
app.post('/cleanup', (req, res) => {
    const outputDir = path.join(__dirname, 'graph_maker', 'output');
    const uploadsDir = path.join(__dirname, 'graph_maker', 'uploads');

    // Limpiar directorio de salida
    if (fs.existsSync(outputDir)) {
        fs.readdirSync(outputDir).forEach(file => {
            const filePath = path.join(outputDir, file);
            fs.rmSync(filePath, { recursive: true, force: true });
        });
    }

    // Limpiar directorio de uploads
    if (fs.existsSync(uploadsDir)) {
        fs.readdirSync(uploadsDir).forEach(file => {
            const filePath = path.join(uploadsDir, file);
            fs.unlinkSync(filePath);
        });
    }

    res.json({ message: 'Limpieza completada' });
});

// Endpoint para procesar archivos seed_orthologs
app.post('/process-seed-orthologs', upload.single('file'), (req, res) => {
    // Asegurar que la respuesta sea JSON
    res.setHeader('Content-Type', 'application/json');

    if (!req.file) {
        return res.status(400).json({ error: 'No se subió ningún archivo' });
    }

    const timestamp = Date.now();
    const outputDir = path.join(__dirname, 'graph_maker', 'output', `seed_orthologs_${timestamp}`);
    
    try {
        if (!fs.existsSync(outputDir)){
            fs.mkdirSync(outputDir, { recursive: true });
        }

        // Usar la ruta correcta del script en PythonScripts
        const scriptPath = path.join(__dirname, 'PythonScripts', 'process_seed_orthologs.py');
        if (!fs.existsSync(scriptPath)) {
            return res.status(500).json({ 
                error: 'Script de procesamiento no encontrado' 
            });
        }

        const command = process.platform === 'win32' 
            ? `python "${scriptPath}" "${req.file.path}" "${outputDir}"`
            : `python3 "${scriptPath}" "${req.file.path}" "${outputDir}"`;
        
        console.log('Ejecutando comando:', command);

        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error de ejecución: ${error}`);
                console.error(`stderr: ${stderr}`);
                return res.status(500).json({ 
                    error: 'Error al procesar el archivo',
                    details: error.message
                });
            }

            console.log(`stdout: ${stdout}`);

            if (!fs.existsSync(outputDir)) {
                return res.status(500).json({ 
                    error: 'No se generaron gráficos' 
                });
            }

            const graphs = fs.readdirSync(outputDir)
                .filter(file => file.endsWith('.png'))
                .map(file => `/graphs/seed_orthologs_${timestamp}/${file}`);

            if (graphs.length === 0) {
                return res.status(500).json({ 
                    error: 'No se encontraron gráficos generados' 
                });
            }

            res.json({ 
                message: 'Procesamiento completado',
                graphs: graphs
            });
        });
    } catch (error) {
        console.error('Error inesperado:', error);
        res.status(500).json({ 
            error: 'Error interno del servidor',
            details: error.message 
        });
    }
});

app.listen(port, () => {
    console.log(`Servidor corriendo en http://localhost:${port}`);
    console.log(`CORS configurado para puertos: 3000, 4000, 4005, 4200`);
});