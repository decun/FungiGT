const express = require('express');
const router = express.Router();
const axios = require('axios');
const uuid = require('uuid');
const fs = require('fs');
const path = require('path');

// Carpeta de descargas
const DOWNLOAD_FOLDER = path.join(__dirname, '../downloads');

function ensureAuthenticated(req, res, next) {
  if (req.session.userId) {
    return next();
  }
  res.redirect('/auth/login');
}

router.get('/', (req, res) => {
  res.render('database', { 
    title: 'NCBI Datasets Genome Downloader',
    apiEndpoint: 'http://localhost:3002/api' // Apuntar al servicio de adquisición
  });
});
//router.get('/', ensureAuthenticated, (req, res) => {
//  res.render('annotator');
//});
// Ruta para iniciar la descarga
router.get('/start_download', ensureAuthenticated, (req, res) => {
  const accession = req.query.accession;
  const annotationTypes = req.query.annotation_type;

  if (!accession) {
    return res.status(400).json({ error: 'Se requiere el número de accesión' });
  }

  if (!annotationTypes || annotationTypes.length === 0) {
    return res.status(400).json({ error: 'Se requiere al menos un tipo de anotación' });
  }

  const downloadId = uuid.v4();
  downloads[downloadId] = { status: 'starting', progress: 0 };

  // Descargar en un hilo separado
  downloadGenome(accession, annotationTypes, downloadId);

  res.json({ download_id: downloadId });
});

// Ruta para obtener el estado de la descarga
router.get('/download_status/:downloadId', ensureAuthenticated, (req, res) => {
  const downloadId = req.params.downloadId;
  if (!downloads[downloadId]) {
    return res.status(404).json({ error: 'ID de descarga inválido' });
  }

  res.json(downloads[downloadId]);
});

// Ruta para descargar el archivo
router.get('/download_file/:downloadId', ensureAuthenticated, (req, res) => {
  const downloadId = req.params.downloadId;
  if (!downloads[downloadId] || downloads[downloadId].status !== 'completed') {
    return res.status(404).json({ error: 'El archivo no está listo para descargar' });
  }

  const filePath = downloads[downloadId].filePath;
  res.download(filePath);
});

// Función para gestionar la descarga del genoma
async function downloadGenome(accession, annotationTypes, downloadId) {
  try {
    const baseUrl = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha/genome/accession";
    const downloadUrl = `${baseUrl}/${accession}/download`;
    const fileName = `${accession}_genome.zip`;
    const filePath = path.join(DOWNLOAD_FOLDER, fileName);

    const response = await axios.get(downloadUrl, {
      params: {
        include_annotation_type: annotationTypes, // Pasar los tipos de anotación seleccionados
      },
      responseType: 'stream'
    });

    const totalSize = parseInt(response.headers['content-length'], 10);
    const writer = fs.createWriteStream(filePath);

    let downloaded = 0;
    downloads[downloadId].status = 'downloading';
    downloads[downloadId].progress = 0;

    response.data.on('data', (chunk) => {
      writer.write(chunk);
      downloaded += chunk.length;
      downloads[downloadId].progress = ((downloaded / totalSize) * 100).toFixed(2);
    });

    response.data.on('end', () => {
      writer.end();
      downloads[downloadId] = { status: 'completed', progress: 100, filePath };
    });

    response.data.on('error', (err) => {
      downloads[downloadId] = { status: 'failed', error: err.message };
      writer.end(); // Asegurarse de cerrar el archivo incluso en caso de error
    });

  } catch (err) {
    downloads[downloadId] = { status: 'failed', error: err.message };
  }
}

module.exports = router;


