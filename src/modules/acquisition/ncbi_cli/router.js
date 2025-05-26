/**
 * Router para la API de adquisición de datos genómicos
 */
const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');
const acquisitionService = require('./service');

// Configuración de multer para la subida de archivos
const upload = multer({ 
  dest: path.join(__dirname, 'tmp'),
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB límite
});

// Crear directorio temporal
fs.ensureDirSync(path.join(__dirname, 'tmp'));

/**
 * Descargar genoma por número de accesión
 */
router.post('/download-genome/accession', async (req, res) => {
  try {
    const { accessionNumber, includeOptions, assemblyLevel } = req.body;
    
    if (!accessionNumber) {
      return res.status(400).json({ 
        success: false, 
        error: 'Número de accesión requerido' 
      });
    }
    
    const result = await acquisitionService.downloadGenomeByAccession(
      accessionNumber,
      includeOptions || ['genome'],
      assemblyLevel
    );
    
    res.json(result);
  } catch (error) {
    console.error('Error al descargar genoma por accesión:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || 'Error interno del servidor' 
    });
  }
});

/**
 * Descargar genoma por nombre de taxón
 */
router.post('/download-genome/taxon', async (req, res) => {
  try {
    const { taxonName, includeOptions, assemblyLevel } = req.body;
    
    if (!taxonName) {
      return res.status(400).json({ 
        success: false, 
        error: 'Nombre de taxón requerido' 
      });
    }
    
    const result = await acquisitionService.downloadGenomeByTaxon(
      taxonName,
      includeOptions || ['genome'],
      assemblyLevel
    );
    
    res.json(result);
  } catch (error) {
    console.error('Error al descargar genoma por taxón:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || 'Error interno del servidor' 
    });
  }
});

/**
 * Descargar genomas desde archivo
 */
router.post('/download-genomes/file', upload.single('accessionFile'), async (req, res) => {
  try {
    const { includeOptions, assemblyLevel } = req.body;
    
    if (!req.file) {
      return res.status(400).json({ 
        success: false, 
        error: 'Archivo requerido' 
      });
    }
    
    const result = await acquisitionService.downloadGenomesFromFile(
      req.file.path,
      includeOptions || ['genome'],
      assemblyLevel
    );
    
    // Eliminar archivo temporal
    fs.removeSync(req.file.path);
    
    res.json(result);
  } catch (error) {
    console.error('Error al descargar genomas desde archivo:', error);
    
    // Eliminar archivo temporal en caso de error
    if (req.file && req.file.path) {
      fs.removeSync(req.file.path);
    }
    
    res.status(500).json({ 
      success: false, 
      error: error.message || 'Error interno del servidor' 
    });
  }
});

/**
 * Endpoint unificado para descargar genomas
 */
router.post('/download-genomes', upload.single('accessionFile'), async (req, res) => {
  try {
    const { 
      downloadMode, 
      accessionNumber, 
      taxonName, 
      includeOptions, 
      assemblyLevel 
    } = req.body;
    
    let result;
    
    switch (downloadMode) {
      case 'accession':
        if (!accessionNumber) {
          return res.status(400).json({ 
            success: false, 
            error: 'Número de accesión requerido' 
          });
        }
        result = await acquisitionService.downloadGenomeByAccession(
          accessionNumber,
          includeOptions || ['genome'],
          assemblyLevel
        );
        break;
        
      case 'taxon':
        if (!taxonName) {
          return res.status(400).json({ 
            success: false, 
            error: 'Nombre de taxón requerido' 
          });
        }
        result = await acquisitionService.downloadGenomeByTaxon(
          taxonName,
          includeOptions || ['genome'],
          assemblyLevel
        );
        break;
        
      case 'automated':
        if (!req.file) {
          return res.status(400).json({ 
            success: false, 
            error: 'Archivo requerido' 
          });
        }
        result = await acquisitionService.downloadGenomesFromFile(
          req.file.path,
          includeOptions || ['genome'],
          assemblyLevel
        );
        break;
        
      default:
        return res.status(400).json({ 
          success: false, 
          error: 'Modo de descarga no válido' 
        });
    }
    
    // Eliminar archivo temporal si existe
    if (req.file && req.file.path) {
      fs.removeSync(req.file.path);
    }
    
    // Proporcionar enlace de descarga
    const downloadLink = `/api/genomes/${result.downloadId}`;
    
    res.json({
      ...result,
      downloadLink
    });
  } catch (error) {
    console.error('Error al descargar genomas:', error);
    
    // Eliminar archivo temporal en caso de error
    if (req.file && req.file.path) {
      fs.removeSync(req.file.path);
    }
    
    res.status(500).json({ 
      success: false, 
      error: error.message || 'Error interno del servidor' 
    });
  }
});

/**
 * Obtener lista de descargas
 */
router.get('/genomes', async (req, res) => {
  try {
    const genomeDir = path.join(process.env.DATA_DIR || path.join(__dirname, '../../../../data'), 'raw/genomes');
    const dirs = await fs.readdir(genomeDir);
    
    const downloads = await Promise.all(
      dirs.map(async (dir) => {
        const dirPath = path.join(genomeDir, dir);
        const stats = await fs.stat(dirPath);
        
        if (!stats.isDirectory()) {
          return null;
        }
        
        const files = await fs.readdir(dirPath);
        
        return {
          id: dir,
          path: dirPath,
          files: files.length,
          created: stats.birthtime
        };
      })
    );
    
    res.json({
      success: true,
      data: downloads.filter(Boolean)
    });
  } catch (error) {
    console.error('Error al obtener lista de descargas:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || 'Error interno del servidor' 
    });
  }
});

/**
 * Servir archivos descargados
 */
router.get('/genomes/:downloadId', async (req, res) => {
  try {
    const { downloadId } = req.params;
    const downloadDir = path.join(
      process.env.DATA_DIR || path.join(__dirname, '../../../../data'),
      'raw/genomes',
      downloadId
    );
    
    // Verificar si existe el directorio
    const exists = await fs.pathExists(downloadDir);
    if (!exists) {
      return res.status(404).json({ 
        success: false, 
        error: 'Descarga no encontrada' 
      });
    }
    
    // Obtener listado de archivos
    const files = await fs.readdir(downloadDir);
    
    if (files.length === 0) {
      return res.status(404).json({ 
        success: false, 
        error: 'No hay archivos disponibles para esta descarga' 
      });
    }
    
    // Si hay un archivo zip, enviarlo
    const zipFile = files.find(file => file.endsWith('.zip'));
    if (zipFile) {
      return res.download(path.join(downloadDir, zipFile));
    }
    
    // Si hay archivos pero no zip, crear un archivo con la lista
    const fileListPath = path.join(downloadDir, 'files.json');
    await fs.writeJson(fileListPath, { files });
    
    res.json({
      success: true,
      data: {
        downloadId,
        files
      }
    });
  } catch (error) {
    console.error('Error al servir archivos descargados:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || 'Error interno del servidor' 
    });
  }
});

module.exports = router; 