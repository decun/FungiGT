const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const storageService = require('./storage_service');


const upload = multer({ 
  dest: path.join(__dirname, 'tmp'),
  limits: { fileSize: 1000 * 1024 * 1024 } // 1000MB límite
});

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

module.exports = router;
