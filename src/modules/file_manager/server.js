/**
 * Servidor para el servicio de gestión de archivos FungiGT
 */
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');
const cors = require('cors');

// Inicializar aplicación Express
const app = express();
const PORT = process.env.PORT || 4002;

// Configuración del directorio de datos
const DATA_DIR = path.join(__dirname, '../../../data');

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configuración de multer para subida de archivos
const upload = multer({
    dest: path.join(__dirname, 'temp'),
    limits: { fileSize: 1000 * 1024 * 1024 } // 1GB límite
});

// Asegurar que existen los directorios necesarios
fs.ensureDirSync(DATA_DIR);
fs.ensureDirSync(path.join(__dirname, 'temp'));

// ==================== FUNCIONES AUXILIARES ====================

// Función para obtener información de archivos
function getFileInfo(filePath) {
    const stats = fs.statSync(filePath);
    const name = path.basename(filePath);
    
    return {
        name: name,
        path: filePath,
        size: stats.size,
        modified: stats.mtime,
        isDirectory: stats.isDirectory()
    };
}

// Función para validar rutas (seguridad)
function isValidPath(requestedPath) {
    const fullPath = path.join(DATA_DIR, requestedPath || '');
    const normalizedPath = path.normalize(fullPath);
    return normalizedPath.startsWith(DATA_DIR);
}

// ==================== ENDPOINTS DEL EXPLORADOR DE ARCHIVOS ====================

// Listar archivos y carpetas
app.get('/files', (req, res) => {
    try {
        const requestedPath = req.query.path || '';
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const fullPath = path.join(DATA_DIR, requestedPath);
        
        if (!fs.existsSync(fullPath)) {
            return res.status(404).json({
                success: false,
                error: 'La ruta no existe'
            });
        }
        
        if (!fs.statSync(fullPath).isDirectory()) {
            return res.status(400).json({
                success: false,
                error: 'La ruta no es un directorio'
            });
        }
        
        const items = fs.readdirSync(fullPath);
        const files = items.map(item => {
            const itemPath = path.join(fullPath, item);
            return getFileInfo(itemPath);
        });
        
        res.json({
            success: true,
            files: files,
            currentPath: requestedPath
        });
        
    } catch (error) {
        console.error('Error al listar archivos:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Crear carpeta
app.post('/create-folder', (req, res) => {
    try {
        const { path: requestedPath, name } = req.body;
        
        if (!name || !name.trim()) {
            return res.status(400).json({
                success: false,
                error: 'Nombre de carpeta requerido'
            });
        }
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const folderName = name.trim();
        const parentPath = path.join(DATA_DIR, requestedPath || '');
        const newFolderPath = path.join(parentPath, folderName);
        
        if (fs.existsSync(newFolderPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ya existe una carpeta con ese nombre'
            });
        }
        
        fs.ensureDirSync(newFolderPath);
        
        res.json({
            success: true,
            message: 'Carpeta creada correctamente'
        });
        
    } catch (error) {
        console.error('Error al crear carpeta:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Subir archivos
app.post('/upload', upload.array('files'), (req, res) => {
    try {
        const requestedPath = req.body.path || '';
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        if (!req.files || req.files.length === 0) {
            return res.status(400).json({
                success: false,
                error: 'No se enviaron archivos'
            });
        }
        
        const targetDir = path.join(DATA_DIR, requestedPath);
        fs.ensureDirSync(targetDir);
        
        const uploadedFiles = [];
        
        for (const file of req.files) {
            const targetPath = path.join(targetDir, file.originalname);
            fs.moveSync(file.path, targetPath);
            uploadedFiles.push(file.originalname);
        }
        
        res.json({
            success: true,
            message: `${uploadedFiles.length} archivo(s) subido(s) correctamente`,
            files: uploadedFiles
        });
        
    } catch (error) {
        console.error('Error al subir archivos:', error);
        
        // Limpiar archivos temporales en caso de error
        if (req.files) {
            req.files.forEach(file => {
                if (fs.existsSync(file.path)) {
                    fs.removeSync(file.path);
                }
            });
        }
        
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Ver contenido de archivo
app.get('/file-content', (req, res) => {
    try {
        const requestedPath = req.query.path;
        
        if (!requestedPath) {
            return res.status(400).json({
                success: false,
                error: 'Ruta de archivo requerida'
            });
        }
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const filePath = path.join(DATA_DIR, requestedPath);
        
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Archivo no encontrado'
            });
        }
        
        if (fs.statSync(filePath).isDirectory()) {
            return res.status(400).json({
                success: false,
                error: 'La ruta es un directorio, no un archivo'
            });
        }
        
        // Limitar el tamaño del archivo para vista previa (10MB)
        const stats = fs.statSync(filePath);
        if (stats.size > 10 * 1024 * 1024) {
            return res.status(400).json({
                success: false,
                error: 'Archivo demasiado grande para vista previa'
            });
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        
        // Limitar las líneas mostradas para archivos muy largos
        const lines = content.split('\n');
        if (lines.length > 1000) {
            const truncatedContent = lines.slice(0, 1000).join('\n') + 
                '\n\n... (archivo truncado, mostrando solo las primeras 1000 líneas)';
            res.send(truncatedContent);
        } else {
            res.send(content);
        }
        
    } catch (error) {
        console.error('Error al leer archivo:', error);
        res.status(500).send('Error al leer el archivo: ' + error.message);
    }
});

// Ver imagen
app.get('/view', (req, res) => {
    try {
        const requestedPath = req.query.path;
        
        if (!requestedPath) {
            return res.status(400).json({
                success: false,
                error: 'Ruta de archivo requerida'
            });
        }
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const filePath = path.join(DATA_DIR, requestedPath);
        
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Archivo no encontrado'
            });
        }
        
        res.sendFile(filePath);
        
    } catch (error) {
        console.error('Error al servir archivo:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Descargar archivo
app.get('/download', (req, res) => {
    try {
        const requestedPath = req.query.path;
        
        if (!requestedPath) {
            return res.status(400).json({
                success: false,
                error: 'Ruta de archivo requerida'
            });
        }
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const filePath = path.join(DATA_DIR, requestedPath);
        
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Archivo no encontrado'
            });
        }
        
        const fileName = path.basename(filePath);
        const stats = fs.statSync(filePath);
        
        // Configurar headers
        res.setHeader('Content-Type', 'application/octet-stream');
        res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
        res.setHeader('Content-Length', stats.size);
        
        // Crear stream de lectura y manejar errores
        const fileStream = fs.createReadStream(filePath);
        
        fileStream.on('error', (error) => {
            console.error(`Error en stream de archivo ${filePath}:`, error);
            
            // Solo enviar el error si la respuesta no ha sido enviada aún
            if (!res.headersSent) {
                res.status(500).json({
                    success: false,
                    error: 'Error al leer el archivo'
                });
            }
        });
        
        // Manejar eventos de cierre y terminación
        res.on('close', () => {
            fileStream.destroy();
        });
        
        // Piping optimizado
        fileStream.pipe(res);
        
    } catch (error) {
        console.error('Error al descargar archivo:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Eliminar archivo o carpeta
app.delete('/delete', (req, res) => {
    try {
        const requestedPath = req.body.path;
        
        if (!requestedPath) {
            return res.status(400).json({
                success: false,
                error: 'Ruta requerida'
            });
        }
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const fullPath = path.join(DATA_DIR, requestedPath);
        
        if (!fs.existsSync(fullPath)) {
            return res.status(404).json({
                success: false,
                error: 'Archivo o carpeta no encontrado'
            });
        }
        
        fs.removeSync(fullPath);
        
        res.json({
            success: true,
            message: 'Eliminado correctamente'
        });
        
    } catch (error) {
        console.error('Error al eliminar:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// ==================== ENDPOINTS LEGACY (para compatibilidad) ====================

// Ruta de prueba para verificar que el servicio está funcionando
app.get('/', (req, res) => {
  res.json({ 
    message: 'Servicio de gestión de archivos FungiGT funcionando correctamente',
        version: '2.0.0',
        dataDir: DATA_DIR
  });
});

// Endpoint legacy para compatibilidad con otras partes del sistema
app.get('/api/files/:category/:subcategory', (req, res) => {
    try {
        const { category, subcategory } = req.params;
        const requestedPath = path.join(category, subcategory);
        
        if (!isValidPath(requestedPath)) {
            return res.status(400).json({
                success: false,
                error: 'Ruta no válida'
            });
        }
        
        const fullPath = path.join(DATA_DIR, requestedPath);
        
        if (!fs.existsSync(fullPath)) {
            return res.status(404).json({
                success: false,
                error: 'La ruta no existe'
            });
        }
        
        const items = fs.readdirSync(fullPath);
        const files = items.map(item => {
            const itemPath = path.join(fullPath, item);
            return getFileInfo(itemPath);
        });
        
        res.json({
            success: true,
            data: files
        });
        
    } catch (error) {
        console.error('Error al listar archivos (legacy):', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Endpoint de health check (NUEVO)
app.get('/health', (req, res) => {
    res.status(200).json({
        status: 'OK',
        service: 'FungiGT File Manager',
        version: '2.0.0',
        timestamp: new Date().toISOString(),
        dataDir: DATA_DIR
    });
});

// Iniciar servidor (ACTUALIZADO)
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Servicio de gestión de archivos ejecutándose en el puerto ${PORT}`);
    console.log(`Directorio de datos: ${DATA_DIR}`);
    console.log(`Health check disponible en: http://localhost:${PORT}/health`);
});

// Manejo de errores no capturados
process.on('uncaughtException', (error) => {
    console.error('Error no capturado:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Promesa rechazada no manejada:', reason);
});

module.exports = app; 