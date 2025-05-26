const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const storageService = require('./storage_service2');
const fs = require('fs-extra');

// Directorio temporal para almacenar archivos antes de moverlos
const TEMP_DIR = path.join(__dirname, 'tmp');
fs.ensureDirSync(TEMP_DIR);

// Configuración de multer para la carga de archivos
const upload = multer({ 
  dest: TEMP_DIR,
  limits: { fileSize: 1000 * 1024 * 1024 } // 1000MB límite
});

// Obtener la lista de archivos de una categoría y subcategoría
router.get('/files/:category/:subcategory', async (req, res) => {
  try {
    const { category, subcategory } = req.params;
    const files = await storageService.listFiles(category, subcategory);
    res.json({ success: true, data: files });
  } catch (error) {
    console.error('Error al listar archivos:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Subir un archivo a una categoría y subcategoría
router.post('/upload/:category/:subcategory', upload.single('file'), async (req, res) => {
  try {
    const { category, subcategory } = req.params;
    if (!req.file) {
      return res.status(400).json({ success: false, error: 'No se ha enviado ningún archivo' });
    }
    const filePath = await storageService.saveFile(req.file, category, subcategory);
    res.json({ 
      success: true, 
      message: 'Archivo subido correctamente',
      data: { filePath } 
    });
  } catch (error) {
    console.error('Error al subir archivo:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Subir múltiples archivos
router.post('/upload', upload.array('files'), async (req, res) => {
  try {
    const { category, subcategory } = req.body;
    
    if (!category || !subcategory) {
      return res.status(400).json({ 
        success: false, 
        error: 'Se requieren los parámetros category y subcategory' 
      });
    }
    
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ 
        success: false, 
        error: 'No se han enviado archivos' 
      });
    }
    
    const uploadedFiles = [];
    
    for (const file of req.files) {
      const filePath = await storageService.saveFile(file, category, subcategory);
      uploadedFiles.push({
        name: file.originalname,
        path: filePath,
        size: file.size
      });
    }
    
    res.json({ 
      success: true, 
      message: `${uploadedFiles.length} archivo(s) subido(s) correctamente`,
      data: { files: uploadedFiles } 
    });
  } catch (error) {
    console.error('Error al subir archivos:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Eliminar un archivo
router.delete('/files', async (req, res) => {
  try {
    const { filePath } = req.body;
    if (!filePath) {
      return res.status(400).json({ success: false, error: 'No se ha especificado la ruta del archivo' });
    }
    await storageService.deleteFile(filePath);
    res.json({ success: true, message: 'Archivo eliminado correctamente' });
  } catch (error) {
    console.error('Error al eliminar archivo:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Obtener información de un archivo
router.get('/file-info', async (req, res) => {
  try {
    const { filePath } = req.query;
    if (!filePath) {
      return res.status(400).json({ success: false, error: 'No se ha especificado la ruta del archivo' });
    }
    const fileInfo = await storageService.getFileInfo(filePath);
    res.json({ success: true, data: fileInfo });
  } catch (error) {
    console.error('Error al obtener información del archivo:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Crear un nuevo directorio
router.post('/create-folder', async (req, res) => {
  try {
    const { category, subcategory, folderName } = req.body;
    
    if (!category || !subcategory || !folderName) {
      return res.status(400).json({ 
        success: false, 
        error: 'Se requieren category, subcategory y folderName' 
      });
    }
    
    const folderPath = await storageService.createDirectory(category, subcategory, folderName);
    res.json({ 
      success: true, 
      message: 'Carpeta creada correctamente',
      data: { folderPath } 
    });
  } catch (error) {
    console.error('Error al crear carpeta:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Descargar un archivo
router.get('/download', async (req, res) => {
  try {
    const { path: filePath } = req.query;
    
    if (!filePath) {
      return res.status(400).json({ success: false, error: 'No se ha especificado la ruta del archivo' });
    }
    
    // Verificar si el archivo existe
    const exists = await fs.pathExists(filePath);
    if (!exists) {
      return res.status(404).json({ success: false, error: 'El archivo no existe' });
    }
    
    res.download(filePath);
  } catch (error) {
    console.error('Error al descargar archivo:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Obtener el contenido de un archivo
router.get('/file-content', async (req, res) => {
  try {
    const { path: filePath } = req.query;
    
    if (!filePath) {
      return res.status(400).json({ success: false, error: 'No se ha especificado la ruta del archivo' });
    }
    
    const content = await storageService.getFileContent(filePath);
    res.send(content);
  } catch (error) {
    console.error('Error al obtener contenido del archivo:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Crear un paquete de descarga para múltiples archivos
router.post('/download-multiple', async (req, res) => {
  try {
    const { files } = req.body;
    
    if (!files || !Array.isArray(files) || files.length === 0) {
      return res.status(400).json({ 
        success: false, 
        error: 'Se requiere un array de rutas de archivos' 
      });
    }
    
    const downloadId = await storageService.createDownloadBundle(files);
    res.json({ 
      success: true, 
      message: 'Bundle de descarga creado correctamente',
      downloadId 
    });
  } catch (error) {
    console.error('Error al crear bundle de descarga:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Descargar un ZIP previamente generado
router.get('/download-zip', async (req, res) => {
  try {
    const { id: downloadId } = req.query;
    
    if (!downloadId) {
      return res.status(400).json({ 
        success: false, 
        error: 'No se ha especificado el ID de descarga' 
      });
    }
    
    const zipPath = await storageService.getDownloadBundle(downloadId);
    res.download(zipPath, `descarga_${downloadId}.zip`);
  } catch (error) {
    console.error('Error al descargar ZIP:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Visualizar un archivo
router.get('/view', async (req, res) => {
  try {
    const { path: filePath } = req.query;
    
    if (!filePath) {
      return res.status(400).json({ success: false, error: 'No se ha especificado la ruta del archivo' });
    }
    
    const fileType = await storageService.getFileType(filePath);
    
    if (fileType.startsWith('image/')) {
      // Para imágenes, las enviamos directamente
      res.sendFile(filePath, { headers: { 'Content-Type': fileType } });
    } else {
      // Para otros tipos, redirigir a descarga
      res.redirect(`/download?path=${encodeURIComponent(filePath)}`);
    }
  } catch (error) {
    console.error('Error al visualizar archivo:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Obtener lista de categorías y subcategorías
router.get('/categories', async (req, res) => {
  try {
    const categories = await storageService.listCategories();
    res.json({ success: true, data: categories });
  } catch (error) {
    console.error('Error al listar categorías:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router; 