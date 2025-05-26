const fs = require('fs-extra');
const path = require('path');
const archiver = require('archiver');

const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, '../../../data');

class StorageService {
  constructor() {
    this.createDirectories();
    this.downloadBundles = {}; // Para almacenar referencias a los paquetes de descarga
  }

  async createDirectories() {
    try {
      await fs.ensureDir(path.join(DATA_DIR, 'raw/genomes'));
      await fs.ensureDir(path.join(DATA_DIR, 'intermediate/quality_filtered'));
      await fs.ensureDir(path.join(DATA_DIR, 'intermediate/annotated'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/quality_control'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/annotation'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/analysis/blastn'));
      await fs.ensureDir(path.join(DATA_DIR, 'results/analysis/eggnog'));
      await fs.ensureDir(path.join(DATA_DIR, 'visualizations'));
      // Directorio para almacenar descargas temporales
      await fs.ensureDir(path.join(DATA_DIR, 'downloads'));
      
      console.log('Directorios creados correctamente');
    } catch (error) {
      console.error('Error al crear directorios:', error);
    }
  }

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

  async listFiles(category, subcategory) {
    try {
      const targetDir = path.join(DATA_DIR, category, subcategory);
      await fs.ensureDir(targetDir);
      const files = await fs.readdir(targetDir);
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

  async deleteFile(filePath) {
    try {
      await fs.remove(filePath);
      return true;
    } catch (error) {
      console.error('Error al eliminar archivo:', error);
      throw error;
    }
  }

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
        
        // Configurar el evento para cuando finalice la compresión
        output.on('close', () => {
          console.log(`Archivo ZIP creado: ${zipPath}`);
          console.log(`Tamaño total: ${archive.pointer()} bytes`);
        });
        
        // Configurar eventos de error
        archive.on('error', (err) => {
          throw err;
        });
        
        // Pipe el contenido al archivo
        archive.pipe(output);
        
        // Añadir archivos al ZIP
        for (const filePath of downloadedFiles) {
          const fileName = path.basename(filePath);
          archive.file(filePath, { name: fileName });
        }
        
        // Finalizar el archivo
        await archive.finalize();
        
        return {
          success: true,
          zipPath: zipPath,
          fileName: zipFilename
        };
      } else if (downloadedFiles.length === 1) {
        // Si solo hay un archivo, devolverlo directamente
        return {
          success: true,
          filePath: downloadedFiles[0],
          fileName: path.basename(downloadedFiles[0])
        };
      } else {
        throw new Error('No se proporcionaron archivos para comprimir');
      }
    } catch (error) {
      console.error('Error al comprimir archivos:', error);
      throw error;
    }
  }

  async createDirectory(category, subcategory, folderName) {
    try {
      const targetDir = path.join(DATA_DIR, category, subcategory, folderName);
      await fs.ensureDir(targetDir);
      return targetDir;
    } catch (error) {
      console.error('Error al crear directorio:', error);
      throw error;
    }
  }

  async listCategories() {
    try {
      const categories = [
        { name: 'raw', subcategories: ['genomes'] },
        { name: 'intermediate', subcategories: ['quality_filtered', 'annotated'] },
        { name: 'results', subcategories: ['quality_control', 'annotation', 'analysis/blastn', 'analysis/eggnog'] },
        { name: 'visualizations', subcategories: [] }
      ];
      
      // Verificar si los directorios existen y crear los que falten
      for (const category of categories) {
        await fs.ensureDir(path.join(DATA_DIR, category.name));
        for (const subcategory of category.subcategories) {
          await fs.ensureDir(path.join(DATA_DIR, category.name, subcategory));
        }
      }
      
      return categories;
    } catch (error) {
      console.error('Error al listar categorías:', error);
      throw error;
    }
  }

  getDataDir() {
    return DATA_DIR;
  }
  
  /**
   * Obtener el contenido de un archivo
   * @param {String} filePath - Ruta del archivo
   * @returns {Promise<String>} - Contenido del archivo
   */
  async getFileContent(filePath) {
    try {
      // Comprobar si es un archivo binario
      const isBinary = this.isBinaryFile(filePath);
      if (isBinary) {
        return "Este es un archivo binario y no se puede mostrar como texto. Por favor, descárgalo para verlo.";
      }
      
      const content = await fs.readFile(filePath, 'utf8');
      return content;
    } catch (error) {
      console.error('Error al leer contenido del archivo:', error);
      throw error;
    }
  }
  
  /**
   * Verificar si un archivo es binario
   * @param {String} filePath - Ruta del archivo
   * @returns {Boolean} - true si es binario, false si es texto
   */
  isBinaryFile(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const binaryExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.zip', '.gz', '.tar', '.bam', '.exe'];
    return binaryExtensions.includes(ext);
  }
  
  /**
   * Crear un paquete de descarga para múltiples archivos
   * @param {Array<String>} filePaths - Array de rutas de archivos
   * @returns {Promise<String>} - ID único para la descarga
   */
  async createDownloadBundle(filePaths) {
    try {
      const downloadId = Date.now().toString();
      const downloadDir = path.join(DATA_DIR, 'downloads');
      await fs.ensureDir(downloadDir);
      
      const zipFilename = `download_${downloadId}.zip`;
      const zipPath = path.join(downloadDir, zipFilename);
      
      const output = fs.createWriteStream(zipPath);
      const archive = archiver('zip', { zlib: { level: 9 } });
      
      // Configurar evento de finalización
      await new Promise((resolve, reject) => {
        output.on('close', () => {
          resolve();
        });
        
        archive.on('error', (err) => {
          reject(err);
        });
        
        archive.pipe(output);
        
        // Añadir cada archivo al ZIP
        for (const filePath of filePaths) {
          // Usar solo el nombre de archivo para la estructura del ZIP
          const fileName = path.basename(filePath);
          archive.file(filePath, { name: fileName });
        }
        
        archive.finalize();
      });
      
      // Guardar en memoria el ID de descarga y su ruta para acceso posterior
      this.downloadBundles[downloadId] = zipPath;
      
      // Configurar limpieza automática después de 1 hora
      setTimeout(() => {
        if (this.downloadBundles[downloadId]) {
          fs.remove(zipPath).catch(err => console.error('Error al eliminar ZIP temporal:', err));
          delete this.downloadBundles[downloadId];
        }
      }, 3600000); // 1 hora
      
      return downloadId;
    } catch (error) {
      console.error('Error al crear bundle de descarga:', error);
      throw error;
    }
  }
  
  /**
   * Obtener la ruta del archivo ZIP para una descarga
   * @param {String} downloadId - ID de la descarga
   * @returns {Promise<String>} - Ruta del archivo ZIP
   */
  async getDownloadBundle(downloadId) {
    try {
      if (!this.downloadBundles || !this.downloadBundles[downloadId]) {
        throw new Error('ID de descarga no válido o expirado');
      }
      
      return this.downloadBundles[downloadId];
    } catch (error) {
      console.error('Error al obtener bundle de descarga:', error);
      throw error;
    }
  }
  
  /**
   * Determinar el tipo MIME de un archivo
   * @param {String} filePath - Ruta del archivo
   * @returns {Promise<String>} - Tipo MIME
   */
  async getFileType(filePath) {
    try {
      const ext = path.extname(filePath).toLowerCase();
      
      // Mapeo básico de extensiones a tipos MIME
      const mimeTypes = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.tsv': 'text/tab-separated-values',
        '.fna': 'text/plain',
        '.faa': 'text/plain',
        '.gff': 'text/plain',
        '.gbk': 'text/plain'
      };
      
      return mimeTypes[ext] || 'application/octet-stream';
    } catch (error) {
      console.error('Error al determinar tipo de archivo:', error);
      throw error;
    }
  }
}

// Función para mover genomas que pasan el control de calidad
async function movePassingGenomes(checkMOutputPath, qualityThreshold = 90) {
    try {
        // Leer el archivo de resultados de CheckM (por ejemplo, quality_summary.tsv)
        const summaryPath = path.join(checkMOutputPath, 'quality_summary.tsv');
        const summaryContent = await fs.readFile(summaryPath, 'utf8');
        const lines = summaryContent.split('\n').filter(Boolean);
        
        // Analizar cada línea para identificar genomas que pasan el umbral
        for (let i = 1; i < lines.length; i++) { // Empezar en 1 para saltar el encabezado
            const columns = lines[i].split('\t');
            const genomeName = columns[0];
            const completeness = parseFloat(columns[1]);
            const contamination = parseFloat(columns[2]);
            
            // Calcular calidad (completeness - 5*contamination)
            const quality = completeness - (5 * contamination);
            
            if (quality >= qualityThreshold) {
                // Mover el archivo a quality_filtered
                const sourceFile = path.join(storageService.getDataDir(), 'raw/genomes', `${genomeName}.fna`);
                const targetFile = path.join(storageService.getDataDir(), 'intermediate/quality_filtered', `${genomeName}.fna`);
                
                await fs.copy(sourceFile, targetFile);
                console.log(`Genoma ${genomeName} pasó el control de calidad y fue copiado a quality_filtered`);
            }
        }
        
        return { success: true, message: 'Genomas filtrados por calidad correctamente' };
    } catch (error) {
        console.error('Error al mover genomas filtrados:', error);
        return { success: false, error: error.message };
    }
}

module.exports = new StorageService(); 