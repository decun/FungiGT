/**
 * Servidor para el servicio de adquisición de datos genómicos
 */
const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const cors = require('cors');
const fs = require('fs-extra');
const multer = require('multer');
const readline = require('readline');

const app = express();
const PORT = process.env.PORT || 4006;

// Configurar CORS y middlewares
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Directorio base para almacenamiento de datos
const DATA_DIR = process.env.DATA_DIR || '/data';
const GENOMES_DIR = path.join(DATA_DIR, 'raw/genomes');
const TEMP_DIR = path.join(__dirname, 'tmp');

// Asegurar que los directorios existan
fs.ensureDirSync(GENOMES_DIR);
fs.ensureDirSync(TEMP_DIR);

// Configuración de Multer para cargar archivos .txt
const upload = multer({ dest: TEMP_DIR });

// Ruta para verificar que el servicio está funcionando
app.get('/', (req, res) => {
    res.json({ 
        message: 'Servicio de adquisición de datos genómicos FungiGT funcionando correctamente',
        version: '2.0.0-fixed'
    });
});

// Ruta para health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK',
        service: 'FungiGT Acquisition Service',
        timestamp: new Date().toISOString()
    });
});

// Ruta para manejar las descargas desde el NCBI
app.post('/api/download-genomes', upload.single('accessionFile'), async (req, res) => {
    try {
        const { downloadMode, accessionNumber, taxonName, includeOptions, assemblyLevel } = req.body;
        console.log('Solicitud recibida:', { downloadMode, accessionNumber, taxonName, includeOptions, assemblyLevel });

        let accessionNumbers = [];
        let taxonNames = [];
        if (downloadMode === 'accession' && accessionNumber) {
            accessionNumbers.push(accessionNumber.trim());
        } else if (downloadMode === 'taxon' && taxonName) {
            taxonNames.push(taxonName.trim());
        } else if (downloadMode === 'automated') {
            if (!req.file) {
                return res.status(400).json({ error: 'Archivo .txt con accesiones es requerido.' });
            }

            const fileStream = fs.createReadStream(req.file.path);
            const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });

            for await (const line of rl) {
                if (line.trim()) {
                    accessionNumbers.push(line.trim());
                }
            }

            if (accessionNumbers.length === 0) {
                return res.status(400).json({ error: 'El archivo está vacío.' });
            }
        }

        const downloadResults = [];
        const optionsArray = Array.isArray(includeOptions) ? includeOptions : [includeOptions].filter(Boolean);
        
        // Crear un ID único para esta descarga
        const downloadId = Date.now().toString();
        const downloadDir = path.join(GENOMES_DIR, downloadId);
        
        // Asegurar que los directorios existan
        fs.ensureDirSync(downloadDir);
        console.log(`Creado directorio base para descarga: ${downloadDir}`);

        if (accessionNumbers.length > 0) {
            for (const accession of accessionNumbers) {
                const outputDir = path.join(downloadDir, accession);
                fs.ensureDirSync(outputDir);
                console.log(`Creado directorio para accession: ${outputDir}`);
                
                // ✅ CAMBIO CRÍTICO: usar CLI directamente, NO Docker dentro de Docker
                const zipFileName = `${accession}_genome.zip`;
                let command = `cd "${outputDir}" && datasets download genome accession ${accession} --filename ${zipFileName}`;
                console.log('🚀 Ejecutando comando:', command);

                try {
                    const result = await execCommand(command);
                    console.log('✅ Comando ejecutado exitosamente');
                    console.log('📤 Stdout:', result);
                    
                    const finalZip = path.join(outputDir, zipFileName);
                    console.log(`🔍 Buscando archivo ZIP en: ${finalZip}`);
                    
                    // Debug: ver qué archivos se crearon
                    const filesInDir = fs.readdirSync(outputDir);
                    console.log('📂 Archivos en directorio:', filesInDir);
                    
                    if (fs.existsSync(finalZip)) {
                        const stats = fs.statSync(finalZip);
                        console.log(`✅ ¡ZIP encontrado! Tamaño: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);
                        
                        downloadResults.push({ 
                            accession, 
                            status: 'success', 
                            files: [finalZip], 
                            zipFile: zipFileName,
                            size: stats.size
                        });
                    } else {
                        // Buscar cualquier archivo .zip
                        const zipFiles = filesInDir.filter(file => file.endsWith('.zip'));
                        console.log(`🗜️ Archivos ZIP encontrados: ${zipFiles}`);
                        
                        if (zipFiles.length > 0) {
                            const foundZip = path.join(outputDir, zipFiles[0]);
                            const targetZip = path.join(outputDir, zipFileName);
                            fs.renameSync(foundZip, targetZip);
                            console.log(`✅ Archivo renombrado: ${zipFiles[0]} -> ${zipFileName}`);
                            
                            downloadResults.push({ 
                                accession, 
                                status: 'success', 
                                files: [targetZip], 
                                zipFile: zipFileName
                            });
                        } else {
                            console.log('❌ No se encontraron archivos ZIP');
                            downloadResults.push({ 
                                accession, 
                                status: 'failed', 
                                error: 'No se descargaron archivos',
                                filesFound: filesInDir
                            });
                        }
                    }
                } catch (commandError) {
                    console.error('❌ Error en comando:', commandError.message);
                    downloadResults.push({ 
                        accession, 
                        status: 'failed', 
                        error: `Error: ${commandError.message}`
                    });
                }
            }
        }

        if (taxonNames.length > 0) {
            for (const taxon of taxonNames) {
                const sanitizedTaxon = taxon.replace(/[^a-zA-Z0-9_]/g, '_');
                const outputDir = path.join(downloadDir, sanitizedTaxon);
                fs.ensureDirSync(outputDir);
                console.log(`Creado directorio para taxon: ${outputDir}`);
                
                const zipFileName = `${sanitizedTaxon}_genome.zip`;
                let command = `cd "${outputDir}" && datasets download genome taxon "${taxon}" --filename ${zipFileName}`;
                console.log('🚀 Ejecutando comando:', command);

                try {
                    const result = await execCommand(command);
                    console.log('✅ Comando de taxón ejecutado exitosamente');
                    
                    const finalZip = path.join(outputDir, zipFileName);
                    if (fs.existsSync(finalZip)) {
                        downloadResults.push({ 
                            taxon, 
                            status: 'success', 
                            files: [finalZip], 
                            zipFile: zipFileName 
                        });
                    } else {
                        const files = fs.readdirSync(outputDir);
                        const zipFiles = files.filter(file => file.endsWith('.zip'));
                        
                        if (zipFiles.length > 0) {
                            const foundZip = path.join(outputDir, zipFiles[0]);
                            const renamedZip = path.join(outputDir, zipFileName);
                            fs.renameSync(foundZip, renamedZip);
                            
                            downloadResults.push({ 
                                taxon, 
                                status: 'success', 
                                files: [renamedZip], 
                                zipFile: zipFileName
                            });
                        } else {
                            downloadResults.push({ 
                                taxon, 
                                status: 'failed', 
                                error: 'No se encontró archivo ZIP',
                                filesFound: files
                            });
                        }
                    }
                } catch (commandError) {
                    console.error('❌ Error ejecutando comando de taxón:', commandError);
                    downloadResults.push({ 
                        taxon, 
                        status: 'failed', 
                        error: `Error en comando: ${commandError.message}` 
                    });
                }
            }
        }

        // Modo de ejemplo/prueba
        if (downloadMode === 'example') {
            const exampleAccession = 'GCF_000005825.2'; // E. coli K-12
            const outputDir = path.join(downloadDir, exampleAccession);
            fs.ensureDirSync(outputDir);
            console.log(`Creado directorio para ejemplo: ${outputDir}`);
            
            const zipFileName = `${exampleAccession}_example_genome.zip`;
            let command = `cd "${outputDir}" && datasets download genome accession ${exampleAccession} --filename ${zipFileName}`;
            console.log('🚀 Ejecutando comando de ejemplo:', command);

            try {
                const result = await execCommand(command);
                console.log('✅ Comando de ejemplo ejecutado exitosamente');
                
                const finalZip = path.join(outputDir, zipFileName);
                if (fs.existsSync(finalZip)) {
                    downloadResults.push({ 
                        accession: exampleAccession, 
                        status: 'success', 
                        files: [finalZip],
                        zipFile: zipFileName,
                        isExample: true
                    });
                } else {
                    const files = fs.readdirSync(outputDir);
                    const zipFiles = files.filter(file => file.endsWith('.zip'));
                    
                    if (zipFiles.length > 0) {
                        const foundZip = path.join(outputDir, zipFiles[0]);
                        const renamedZip = path.join(outputDir, zipFileName);
                        fs.renameSync(foundZip, renamedZip);
                        
                        downloadResults.push({ 
                            accession: exampleAccession, 
                            status: 'success', 
                            files: [renamedZip],
                            zipFile: zipFileName,
                            isExample: true
                        });
                    } else {
                        downloadResults.push({ 
                            accession: exampleAccession, 
                            status: 'failed', 
                            error: 'No se encontró archivo ZIP de ejemplo',
                            filesFound: files,
                            isExample: true 
                        });
                    }
                }
            } catch (commandError) {
                console.error('❌ Error ejecutando comando de ejemplo:', commandError);
                downloadResults.push({ 
                    accession: exampleAccession, 
                    status: 'failed', 
                    error: `Error en comando: ${commandError.message}`, 
                    isExample: true 
                });
            }
        }

        // Eliminar archivo temporal si existe
        if (req.file && req.file.path) {
            fs.removeSync(req.file.path);
        }

        // Verificar resultados
        const successfulDownloads = downloadResults.filter(result => result.status === 'success');
        if (successfulDownloads.length === 0) {
            console.error('Detalles del error:', downloadResults);
            return res.status(500).json({ 
                success: false,
                error: 'No se pudo completar ninguna descarga.',
                details: downloadResults 
            });
        }

        // Proporcionar enlace de descarga
        const downloadLink = `/genomes/${downloadId}`;
        res.json({
            success: true,
            downloadId,
            results: downloadResults,
            downloadLink
        });
    } catch (error) {
        console.error('Error procesando la solicitud:', error);
        if (req.file && req.file.path) {
            fs.removeSync(req.file.path);
        }
        res.status(500).json({ 
            success: false,
            error: 'Error interno en el servidor: ' + error.message 
        });
    }
});

// Ruta para descargar archivos
app.get('/api/download-file/:downloadId/:accession/:filename', (req, res) => {
    try {
        const { downloadId, accession, filename } = req.params;
        const filePath = path.join(GENOMES_DIR, downloadId, accession, filename);
        
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ 
                success: false, 
                error: 'Archivo no encontrado' 
            });
        }
        
        res.download(filePath);
    } catch (error) {
        console.error('Error enviando archivo:', error);
        res.status(500).json({ 
            success: false, 
            error: 'Error enviando archivo: ' + error.message 
        });
    }
});

// Ruta para listar descargas disponibles
app.get('/api/downloads', (req, res) => {
    try {
        const downloads = [];
        const downloadDirs = fs.readdirSync(GENOMES_DIR);
        
        downloadDirs.forEach(downloadId => {
            const downloadPath = path.join(GENOMES_DIR, downloadId);
            if (fs.statSync(downloadPath).isDirectory()) {
                const items = fs.readdirSync(downloadPath);
                downloads.push({
                    downloadId,
                    timestamp: parseInt(downloadId),
                    items: items.length
                });
            }
        });
        
        downloads.sort((a, b) => b.timestamp - a.timestamp);
        
        res.json({
            success: true,
            downloads: downloads
        });
        
    } catch (error) {
        console.error('❌ Error listando descargas:', error);
        res.status(500).json({ 
            success: false, 
            error: 'Error listando descargas: ' + error.message 
        });
    }
});

// Función para ejecutar un comando y esperar el resultado - CON MÁS DEBUG
function execCommand(command) {
    return new Promise((resolve, reject) => {
        console.log('🔄 Iniciando comando:', command);
        exec(command, { 
            maxBuffer: 1024 * 1024 * 100, // 100MB buffer
            timeout: 300000, // 5 minutos
            cwd: DATA_DIR // Ejecutar desde el directorio de datos
        }, (error, stdout, stderr) => {
            console.log('✅ Comando completado');
            
            if (stdout) {
                console.log('📤 Stdout:');
                console.log(stdout);
            }
            
            if (stderr) {
                console.log('⚠️ Stderr:');
                console.log(stderr);
            }
            
            if (error) {
                console.error('❌ Error en comando:');
                console.error('  - Código:', error.code);
                console.error('  - Señal:', error.signal);
                console.error('  - Mensaje:', error.message);
                return reject(error);
            }
            
            resolve(stdout);
        });
    });
}

// Iniciar el servidor
app.listen(PORT, () => {
    console.log('=================================');
    console.log('🚀 SERVICIO DE ADQUISICIÓN INICIADO');
    console.log(`📡 Puerto: ${PORT}`);
    console.log(`📁 Directorio datos: ${DATA_DIR}`);
    console.log(`🧬 Directorio genomas: ${GENOMES_DIR}`);
    console.log(`🌐 Health check: http://localhost:${PORT}/health`);
    console.log('=================================');
});

// Manejo de errores no capturados
process.on('uncaughtException', (error) => {
    console.error('💥 Error no capturado:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('💥 Promesa rechazada no manejada:', reason);
});

module.exports = app;