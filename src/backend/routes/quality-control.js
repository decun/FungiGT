const express = require('express');
const router = express.Router();
const { runCheckM } = require('../scripts/run_checkm');

/**
 * Ruta para ejecutar el análisis de CheckM
 * POST /api/quality-control/checkm
 */
router.post('/checkm', (req, res) => {
    const { inputPath, outputPath } = req.body;
    
    if (!inputPath || !outputPath) {
        return res.status(400).json({
            success: false,
            error: 'Se requieren las rutas de entrada y salida'
        });
    }
    
    // Iniciar el análisis de CheckM
    runCheckM(inputPath, outputPath, (error, result) => {
        if (error) {
            return res.status(500).json({
                success: false,
                error: error.message
            });
        }
        
        res.json({
            success: true,
            message: 'Análisis de CheckM iniciado correctamente',
            data: result
        });
    });
});

/**
 * Ruta para verificar el estado del análisis de CheckM
 * GET /api/quality-control/checkm/status
 */
router.get('/checkm/status', (req, res) => {
    const { outputPath } = req.query;
    
    if (!outputPath) {
        return res.status(400).json({
            success: false,
            error: 'Se requiere la ruta de salida para verificar el estado'
        });
    }
    
    // Verificar si existe el archivo de resultados en la carpeta de salida
    const fs = require('fs');
    const path = require('path');
    const resultsFile = path.join(outputPath, 'checkm.txt');
    
    if (fs.existsSync(resultsFile)) {
        return res.json({
            success: true,
            status: 'completed',
            message: 'El análisis de CheckM ha sido completado'
        });
    }
    
    // Verificar si el contenedor está ejecutándose
    const { exec } = require('child_process');
    exec('docker ps --filter "name=fungi_checkm" --format "{{.Names}}"', (error, stdout) => {
        if (error) {
            return res.status(500).json({
                success: false,
                error: 'Error al verificar el estado del contenedor'
            });
        }
        
        if (stdout.includes('fungi_checkm')) {
            return res.json({
                success: true,
                status: 'running',
                message: 'El análisis de CheckM está en ejecución'
            });
        }
        
        res.json({
            success: true,
            status: 'not_found',
            message: 'No se encontró ningún análisis de CheckM en ejecución'
        });
    });
});

module.exports = router; 