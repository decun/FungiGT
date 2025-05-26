/**
 * Servicio para la adquisición de datos genómicos
 * Utiliza el contenedor Docker ensemblorg/datasets-cli
 */
const fs = require('fs-extra');
const path = require('path');
const { exec } = require('child_process');
const { v4: uuidv4 } = require('uuid');

// Directorio base para almacenamiento de datos
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, '../../../../data');
const GENOMES_DIR = path.join(DATA_DIR, 'raw/genomes');

/**
 * Clase que gestiona la adquisición de datos genómicos
 */
class AcquisitionService {
  constructor() {
    // Asegurar que los directorios necesarios existan
    this.ensureDirectories();
  }

  /**
   * Crear directorios necesarios si no existen
   */
  async ensureDirectories() {
    try {
      await fs.ensureDir(GENOMES_DIR);
      console.log('Directorios de adquisición creados correctamente');
    } catch (error) {
      console.error('Error al crear directorios de adquisición:', error);
    }
  }

  /**
   * Descargar genoma por número de accesión usando datasets-cli
   * @param {String} accessionNumber - Número de accesión
   * @param {Array} includeOptions - Opciones a incluir (genome, protein, etc.)
   * @param {String} assemblyLevel - Nivel de ensamblaje
   * @returns {Promise<Object>} - Información de la descarga
   */
  downloadGenomeByAccession(accessionNumber, includeOptions = ['genome'], assemblyLevel = '') {
    return new Promise((resolve, reject) => {
      // Generar ID único para la descarga
      const downloadId = uuidv4();
      const downloadDir = path.join(GENOMES_DIR, downloadId);
      
      // Crear directorio para la descarga
      fs.ensureDirSync(downloadDir);
      
      // Construir comando para datasets-cli
      let command = `docker run --rm -v ${DATA_DIR}:/data ensemblorg/datasets-cli download genome accession ${accessionNumber}`;
      
      // Agregar opciones
      if (includeOptions && includeOptions.length > 0) {
        command += ` --include ${includeOptions.join(',')}`;
      }
      
      // Agregar nivel de ensamblaje si se especifica
      if (assemblyLevel) {
        command += ` --assembly-level ${assemblyLevel}`;
      }
      
      // Especificar directorio de salida
      command += ` --output-dir /data/raw/genomes/${downloadId}`;
      
      console.log(`Ejecutando comando: ${command}`);
      
      // Ejecutar comando
      exec(command, (error, stdout, stderr) => {
        if (error) {
          console.error(`Error al ejecutar comando: ${error.message}`);
          return reject({
            success: false,
            error: error.message,
            stderr: stderr
          });
        }
        
        if (stderr) {
          console.warn(`Advertencia del comando: ${stderr}`);
        }
        
        console.log(`Salida del comando: ${stdout}`);
        
        // Verificar si la descarga fue exitosa
        fs.readdir(downloadDir, (err, files) => {
          if (err || files.length === 0) {
            return reject({
              success: false,
              error: 'No se descargaron archivos',
              stderr: stderr
            });
          }
          
          // Retornar información de la descarga
          resolve({
            success: true,
            downloadId: downloadId,
            downloadDir: downloadDir,
            files: files,
            stdout: stdout
          });
        });
      });
    });
  }

  /**
   * Descargar genoma por nombre de taxón
   * @param {String} taxonName - Nombre del taxón
   * @param {Array} includeOptions - Opciones a incluir
   * @param {String} assemblyLevel - Nivel de ensamblaje
   * @returns {Promise<Object>} - Información de la descarga
   */
  downloadGenomeByTaxon(taxonName, includeOptions = ['genome'], assemblyLevel = '') {
    return new Promise((resolve, reject) => {
      const downloadId = uuidv4();
      const downloadDir = path.join(GENOMES_DIR, downloadId);
      
      fs.ensureDirSync(downloadDir);
      
      let command = `docker run --rm -v ${DATA_DIR}:/data ensemblorg/datasets-cli download genome taxon ${taxonName}`;
      
      if (includeOptions && includeOptions.length > 0) {
        command += ` --include ${includeOptions.join(',')}`;
      }
      
      if (assemblyLevel) {
        command += ` --assembly-level ${assemblyLevel}`;
      }
      
      command += ` --output-dir /data/raw/genomes/${downloadId}`;
      
      console.log(`Ejecutando comando: ${command}`);
      
      exec(command, (error, stdout, stderr) => {
        if (error) {
          console.error(`Error al ejecutar comando: ${error.message}`);
          return reject({
            success: false,
            error: error.message,
            stderr: stderr
          });
        }
        
        if (stderr) {
          console.warn(`Advertencia del comando: ${stderr}`);
        }
        
        console.log(`Salida del comando: ${stdout}`);
        
        fs.readdir(downloadDir, (err, files) => {
          if (err || files.length === 0) {
            return reject({
              success: false,
              error: 'No se descargaron archivos',
              stderr: stderr
            });
          }
          
          resolve({
            success: true,
            downloadId: downloadId,
            downloadDir: downloadDir,
            files: files,
            stdout: stdout
          });
        });
      });
    });
  }

  /**
   * Descargar múltiples genomas desde un archivo
   * @param {String} filePath - Ruta al archivo con números de accesión
   * @param {Array} includeOptions - Opciones a incluir
   * @param {String} assemblyLevel - Nivel de ensamblaje
   * @returns {Promise<Object>} - Información de la descarga
   */
  downloadGenomesFromFile(filePath, includeOptions = ['genome'], assemblyLevel = '') {
    return new Promise((resolve, reject) => {
      // Leer el archivo
      fs.readFile(filePath, 'utf8', async (err, data) => {
        if (err) {
          return reject({
            success: false,
            error: `Error al leer el archivo: ${err.message}`
          });
        }
        
        // Obtener accesiones del archivo (una por línea)
        const accessions = data.split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0);
        
        if (accessions.length === 0) {
          return reject({
            success: false,
            error: 'El archivo no contiene números de accesión'
          });
        }
        
        // Crear directorio para la descarga
        const downloadId = uuidv4();
        const downloadDir = path.join(GENOMES_DIR, downloadId);
        fs.ensureDirSync(downloadDir);
        
        try {
          // Descargar cada genoma
          const results = [];
          for (const accession of accessions) {
            try {
              const result = await this.downloadGenomeByAccession(
                accession, 
                includeOptions, 
                assemblyLevel
              );
              results.push({
                accession,
                success: true,
                downloadId: result.downloadId
              });
            } catch (err) {
              results.push({
                accession,
                success: false,
                error: err.message || 'Error desconocido'
              });
            }
          }
          
          resolve({
            success: true,
            downloadId,
            downloads: results
          });
        } catch (error) {
          reject({
            success: false,
            error: `Error durante la descarga: ${error.message}`
          });
        }
      });
    });
  }
}

module.exports = new AcquisitionService(); 