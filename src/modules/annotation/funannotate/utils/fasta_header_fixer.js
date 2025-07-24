const fs = require('fs-extra');
const path = require('path');
const readline = require('readline');

/**
 * Utilidad para arreglar headers de archivos FASTA que son demasiado largos para Funannotate
 * Funannotate requiere headers de máximo 16 caracteres
 */

class FastaHeaderFixer {
    constructor() {
        this.maxHeaderLength = 16;
        this.processedHeaders = 0;
        this.sequenceLines = 0;
    }

    /**
     * Verifica si un archivo FASTA tiene headers problemáticos
     * @param {string} filePath - Ruta al archivo FASTA
     * @returns {Promise<Object>} - {needsFix: boolean, problematicHeaders: Array}
     */
    async checkHeaders(filePath) {
        return new Promise((resolve, reject) => {
            const problematicHeaders = [];
            const fileStream = fs.createReadStream(filePath);
            const rl = readline.createInterface({
                input: fileStream,
                crlfDelay: Infinity
            });

            let lineCount = 0;

            rl.on('line', (line) => {
                lineCount++;
                if (line.startsWith('>')) {
                    const header = line.substring(1); // Remover '>'
                    const headerId = header.split(/\s+/)[0]; // Tomar solo el ID antes del primer espacio
                    
                    // Marcar como problemático si:
                    // 1. El ID es más largo que 16 caracteres, O
                    // 2. El header contiene espacios (descripción adicional) que Funannotate podría no manejar bien
                    const hasDescription = header.includes(' ');
                    const idTooLong = headerId.length > this.maxHeaderLength;
                    
                    if (idTooLong || hasDescription) {
                        problematicHeaders.push({
                            line: lineCount,
                            original: line,
                            headerId: headerId,
                            length: headerId.length,
                            hasDescription: hasDescription,
                            reason: idTooLong ? 'ID too long' : 'Has description'
                        });
                    }
                }
            });

            rl.on('close', () => {
                resolve({
                    needsFix: problematicHeaders.length > 0,
                    problematicHeaders: problematicHeaders,
                    totalProblematic: problematicHeaders.length
                });
            });

            rl.on('error', (error) => {
                reject(error);
            });
        });
    }

    /**
     * Arregla los headers de un archivo FASTA
     * @param {string} inputPath - Archivo FASTA original
     * @param {string} outputPath - Archivo FASTA con headers arreglados
     * @returns {Promise<Object>} - Estadísticas del procesamiento
     */
    async fixHeaders(inputPath, outputPath) {
        return new Promise((resolve, reject) => {
            const inputStream = fs.createReadStream(inputPath);
            const outputStream = fs.createWriteStream(outputPath);
            const rl = readline.createInterface({
                input: inputStream,
                crlfDelay: Infinity
            });

            this.processedHeaders = 0;
            this.sequenceLines = 0;
            const headerMappings = [];

            rl.on('line', (line) => {
                if (line.startsWith('>')) {
                    // Es un header
                    this.processedHeaders++;
                    const originalHeader = line;
                    const headerContent = line.substring(1); // Remover '>'
                    const parts = headerContent.split(/\s+/);
                    
                    if (parts.length > 0) {
                        let newHeaderId = parts[0];
                        
                        // Si el header es muy largo, truncarlo
                        if (newHeaderId.length > this.maxHeaderLength) {
                            newHeaderId = newHeaderId.substring(0, this.maxHeaderLength);
                        }
                        
                        const newHeader = `>${newHeaderId}`;
                        
                        // Guardar mapping para logging
                        headerMappings.push({
                            original: originalHeader,
                            new: newHeader,
                            truncated: newHeaderId.length < parts[0].length
                        });
                        
                        outputStream.write(newHeader + '\n');
                    } else {
                        // Header vacío, usar un ID genérico
                        const genericId = `seq_${this.processedHeaders}`;
                        outputStream.write(`>${genericId}\n`);
                        headerMappings.push({
                            original: originalHeader,
                            new: `>${genericId}`,
                            truncated: true
                        });
                    }
                } else {
                    // Es secuencia
                    if (line.trim().length > 0) {
                        this.sequenceLines++;
                    }
                    outputStream.write(line + '\n');
                }
            });

            rl.on('close', () => {
                outputStream.end();
                resolve({
                    success: true,
                    inputFile: inputPath,
                    outputFile: outputPath,
                    headersProcessed: this.processedHeaders,
                    sequenceLines: this.sequenceLines,
                    headerMappings: headerMappings,
                    truncatedHeaders: headerMappings.filter(h => h.truncated).length
                });
            });

            rl.on('error', (error) => {
                outputStream.destroy();
                reject(error);
            });

            outputStream.on('error', (error) => {
                reject(error);
            });
        });
    }

    /**
     * Genera un nombre de archivo para la versión arreglada
     * @param {string} originalPath - Ruta del archivo original
     * @returns {string} - Ruta del archivo arreglado
     */
    generateFixedFileName(originalPath) {
        const dir = path.dirname(originalPath);
        const name = path.basename(originalPath, path.extname(originalPath));
        const ext = path.extname(originalPath);
        return path.join(dir, `${name}_fixed${ext}`);
    }

    /**
     * Proceso completo: verifica y arregla si es necesario
     * @param {string} filePath - Archivo FASTA a procesar
     * @param {boolean} forcefix - Forzar arreglo aunque no sea necesario
     * @returns {Promise<Object>} - Resultado del procesamiento
     */
    async processFile(filePath, forceFix = false) {
        try {
            console.log(`🔍 Verificando headers en: ${filePath}`);
            
            // Verificar si el archivo existe
            if (!await fs.pathExists(filePath)) {
                throw new Error(`Archivo no encontrado: ${filePath}`);
            }

            // Verificar si necesita arreglo
            const checkResult = await this.checkHeaders(filePath);
            
            if (!checkResult.needsFix && !forceFix) {
                console.log(`✅ Headers OK: El archivo no necesita corrección`);
                return {
                    needsFix: false,
                    processedFile: filePath, // Usar el archivo original
                    originalFile: filePath,
                    stats: {
                        headersProcessed: 0,
                        truncatedHeaders: 0
                    }
                };
            }

            console.log(`🔧 Encontrados ${checkResult.totalProblematic} headers problemáticos`);
            
            // Mostrar algunos ejemplos
            if (checkResult.problematicHeaders.length > 0) {
                console.log('📋 Primeros headers problemáticos:');
                checkResult.problematicHeaders.slice(0, 5).forEach((header, index) => {
                    console.log(`  ${index + 1}. ${header.original.substring(0, 50)}... (${header.length} chars)`);
                });
            }

            // Generar nombre para archivo arreglado
            const fixedFilePath = this.generateFixedFileName(filePath);
            
            console.log(`🛠️ Arreglando headers...`);
            const fixResult = await this.fixHeaders(filePath, fixedFilePath);
            
            console.log(`✅ Headers arreglados exitosamente:`);
            console.log(`   📊 Headers procesados: ${fixResult.headersProcessed}`);
            console.log(`   ✂️ Headers truncados: ${fixResult.truncatedHeaders}`);
            console.log(`   🧬 Líneas de secuencia: ${fixResult.sequenceLines}`);
            console.log(`   📁 Archivo generado: ${fixedFilePath}`);

            return {
                needsFix: true,
                processedFile: fixedFilePath,
                originalFile: filePath,
                stats: fixResult
            };

        } catch (error) {
            console.error(`❌ Error procesando archivo FASTA: ${error.message}`);
            throw error;
        }
    }
}

module.exports = FastaHeaderFixer;