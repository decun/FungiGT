
const fs = require('fs-extra');
const path = require('path');
const archiver = require('archiver');

// Directorio base para almacenamiento de datos (configurado mediante variables de entorno)
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, '../../../data');

/**
 * Clase que gestiona el almacenamiento de archivos
 */
class StorageService {
  constructor() {
    // Asegurar que los directorios necesarios existan
    this.createDirectories();
  }

  /**
   * Crear directorios necesarios si no existen
   */
  async createDirectories() {
    try {
      // Crear directorios principales
      await fs.ensureDir(path.join(DATA_DIR, 'raw/genomes'));
      await fs.ensureDir(path.join(DATA_DIR, 'intermediate/quality_filtered'));
      await fs.ensureDir(path.join(DATA_DIR, 'intermediate/annotated'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/quality_control'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/annotation'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/analysis/blastn'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/analysis/eggnog'));
      await fs.ensureDir(path.join(DATA_DIR, 'visualizations'));
      
      console.log('Directorios creados correctamente');
    } catch (error) {
      console.error('Error al crear directorios:', error);
    }
  }

  /**
   * Guardar un archivo en la ubicación especificada
   * @param {Object} file - Archivo a guardar (objeto de Multer)
   * @param {String} category - Categoría del archivo (raw, intermediate, results)
   * @param {String} subcategory - Subcategoría (genomes, quality_filtered, etc.)
   * @returns {Promise<String>} - Ruta del archivo guardado
   */
  async saveFile(file, category, subcategory) {
    try {
      const targetDir = path.join(DATA_DIR, category, subcategory);
      await fs.ensureDir(targetDir);
      
      const filePath = path.join(targetDir, file.originalname);
      await fs.move(file.path, filePath, { overwrite: true });
      
      return filePath;
    } catch (error) {
      console.error('Error al guardar archivo:', error);
      throw error;
    }
  }

  /**
   * Listar archivos en un directorio específico
   * @param {String} category - Categoría del archivo
   * @param {String} subcategory - Subcategoría
   * @returns {Promise<Array>} - Lista de archivos
   */
  async listFiles(category, subcategory) {
    try {
      const targetDir = path.join(DATA_DIR, category, subcategory);
      await fs.ensureDir(targetDir);
      
      const files = await fs.readdir(targetDir);
      
      // Obtener información de cada archivo
      const fileDetails = await Promise.all(
        files.map(async (filename) => {
          const filePath = path.join(targetDir, filename);
          const stats = await fs.stat(filePath);
          
          return {
            name: filename,
            path: filePath,
            size: stats.size,
            created: stats.birthtime,
            modified: stats.mtime,
            isDirectory: stats.isDirectory()
          };
        })
      );
      
      return fileDetails;
    } catch (error) {
      console.error('Error al listar archivos:', error);
      throw error;
    }
  }

  /**
   * Eliminar un archivo
   * @param {String} filePath - Ruta del archivo a eliminar
   * @returns {Promise<Boolean>} - Resultado de la operación
   */
  async deleteFile(filePath) {
    try {
      await fs.remove(filePath);
      return true;
    } catch (error) {
      console.error('Error al eliminar archivo:', error);
      throw error;
    }
  }

  /**
   * Obtener información de un archivo
   * @param {String} filePath - Ruta del archivo
   * @returns {Promise<Object>} - Información del archivo
   */
  async getFileInfo(filePath) {
    try {
      const stats = await fs.stat(filePath);
      
      return {
        name: path.basename(filePath),
        path: filePath,
        size: stats.size,
        created: stats.birthtime,
        modified: stats.mtime,
        isDirectory: stats.isDirectory()
      };
    } catch (error) {
      console.error('Error al obtener información del archivo:', error);
      throw error;
    }
  }

  async compressFiles(downloadedFiles, downloadId) {
    try {
      const downloadDir = path.join(DATA_DIR, 'raw/genomes', downloadId);
      fs.ensureDirSync(downloadDir);

      if (downloadedFiles.length > 1) {
        const zipFilename = `all_genomes_${downloadId}.zip`;
        const zipPath = path.join(downloadDir, zipFilename);
        const output = fs.createWriteStream(zipPath);
        const archive = archiver('zip', { zlib: { level: 9 } });

        // ... resto del código de compresión
      }
    } catch (error) {
      console.error('Error al comprimir archivos:', error);
      throw error;
    }
  }
}

module.exports = new StorageService();
