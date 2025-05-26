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
const PORT = process.env.PORT || 3002;

// Configurar CORS y middlewares
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Directorio base para almacenamiento de datos
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, '../../../../data');
const GENOMES_DIR = path.join(DATA_DIR, 'raw/genomes');
const TEMP_DIR = path.join(__dirname, 'tmp');

// Función para normalizar rutas Windows para Docker
function normalizePathForDocker(windowsPath) {
    // Obtener la ruta relativa desde DATA_DIR
    const relativePath = path.relative(DATA_DIR, windowsPath);
    // Convertir a formato Docker usando forward slash
    return `/data/${relativePath.replace(/\\/g, '/')}`;
}

// Asegurar que los directorios existan
fs.ensureDirSync(GENOMES_DIR);
fs.ensureDirSync(TEMP_DIR);

// Nombre de la imagen Docker NCBI
const DOCKER_IMAGE_NAME = 'ncbi-datasets:latest';

// Configuración de Multer para cargar archivos .txt
const upload = multer({ dest: TEMP_DIR });

// Ruta para verificar que el servicio está funcionando
app.get('/', (req, res) => {
    res.json({ 
        message: 'Servicio de adquisición de datos genómicos FungiGT funcionando correctamente',
        version: '1.0.0'
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
        fs.ensureDirSync(GENOMES_DIR);
        fs.ensureDirSync(downloadDir);
        
        console.log(`Creado directorio base para descarga: ${downloadDir}`);

        if (accessionNumbers.length > 0) {
            for (const accession of accessionNumbers) {
                const outputDir = path.join(downloadDir, accession);
                fs.ensureDirSync(outputDir);
                console.log(`Creado directorio para accession: ${outputDir}`);
                
                let command = `docker run --rm -v "${DATA_DIR}:/data" ncbi-datasets download genome accession ${accession}`;
                console.log('Ejecutando comando:', command);

                await execCommand(command);

                const downloadedZip = path.join(DATA_DIR, 'ncbi_dataset.zip');
                const finalZip = path.join(outputDir, `${accession}_genome.zip`);
                if (fs.existsSync(downloadedZip)) {
                    fs.renameSync(downloadedZip, finalZip);
                    downloadResults.push({ accession, status: 'success', files: [finalZip], zipFile: `${accession}_genome.zip` });
                } else {
                    downloadResults.push({ accession, status: 'failed', error: 'No se descargaron archivos' });
                }
            }
        }

        if (taxonNames.length > 0) {
            for (const taxon of taxonNames) {
                const sanitizedTaxon = taxon.replace(/[^a-zA-Z0-9_]/g, '_');
                const outputDir = path.join(downloadDir, sanitizedTaxon);
                fs.ensureDirSync(outputDir);
                console.log(`Creado directorio para taxon: ${outputDir}`);
                
                // Construir comando usando Docker con la sintaxis básica
                let command = `docker run --rm -v "${DATA_DIR}:/data" ${DOCKER_IMAGE_NAME} datasets download genome taxon "${taxon}"`;

                // Ejecuta el comando
                await execCommand(command);
                // El archivo se llamará ncbi_dataset.zip en DATA_DIR
                const downloadedZip = path.join(outputDir, 'ncbi_dataset.zip');
                const finalZip = path.join(outputDir, `${sanitizedTaxon}_genome.zip`);
                if (fs.existsSync(downloadedZip)) {
                    fs.renameSync(downloadedZip, finalZip);
                    downloadResults.push({ taxon, status: 'success', files: [finalZip], zipFile: `${sanitizedTaxon}_genome.zip` });
                } else {
                    downloadResults.push({ taxon, status: 'failed', error: 'No se descargaron archivos' });
                }
            }
        }

        // Modo de ejemplo/prueba
        if (downloadMode === 'example') {
            // Usar un accession conocido como ejemplo de prueba
            const exampleAccession = 'GCA_000001405.29'; // Genoma humano (hg38)
            const outputDir = path.join(downloadDir, exampleAccession);
            fs.ensureDirSync(outputDir);
            console.log(`Creado directorio para ejemplo: ${outputDir}`);
            
            // Construir comando usando Docker con la sintaxis básica
            let command = `docker run --rm -v "${DATA_DIR}:/data" ${DOCKER_IMAGE_NAME} datasets download genome accession ${exampleAccession}`;

            // Ejecuta el comando
            await execCommand(command);
            // El archivo se llamará ncbi_dataset.zip en DATA_DIR
            const downloadedZip = path.join(outputDir, 'ncbi_dataset.zip');
            const finalZip = path.join(outputDir, `${exampleAccession}_example_genome.zip`);
            if (fs.existsSync(downloadedZip)) {
                fs.renameSync(downloadedZip, finalZip);
                downloadResults.push({ 
                    accession: exampleAccession, 
                    status: 'success', 
                    files: [finalZip],
                    zipFile: finalZip,
                    isExample: true
                });
            } else {
                downloadResults.push({ 
                    accession: exampleAccession, 
                    status: 'failed', 
                    error: 'No se descargaron archivos', 
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
            console.error('Detalles del error:', downloadResults || error);
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

// Función para ejecutar un comando y esperar el resultado
function execCommand(command) {
    return new Promise((resolve, reject) => {
        exec(command, { maxBuffer: 1024 * 1024 * 10 }, (error, stdout, stderr) => {
            if (error) {
                return reject(error);
            }
            if (stderr) {
                console.warn('Advertencias:', stderr);
            }
            resolve(stdout);
        });
    });
}

// Iniciar el servidor
app.listen(PORT, () => {
    console.log(`Servicio de adquisición de datos genómicos ejecutándose en http://localhost:${PORT}`);
});