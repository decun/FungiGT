const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Ejecuta el análisis de CheckM a través de Docker Compose
 * @param {string} inputPath - Ruta de la carpeta de entrada con los genomas
 * @param {string} outputPath - Ruta de la carpeta de salida para los resultados
 * @param {Function} callback - Función callback para manejar la respuesta
 */
function runCheckM(inputPath, outputPath, callback) {
    // Validar que las rutas existan
    if (!fs.existsSync(inputPath)) {
        return callback(new Error('La carpeta de entrada no existe'));
    }
    
    // Crear la carpeta de salida si no existe
    if (!fs.existsSync(outputPath)) {
        fs.mkdirSync(outputPath, { recursive: true });
    }
    
    // Modificar el docker-compose.yml temporalmente con las rutas específicas
    const tempComposeFile = path.join(__dirname, 'temp-checkm-compose.yml');
    const composeContent = `version: '3.8'
services:
  checkm:
    image: nanozoo/checkm:latest
    container_name: fungi_checkm
    volumes:
      - "${inputPath}:/input"
      - "${outputPath}:/output"
    command: >
      checkm lineage_wf -t 4 --pplacer_threads 4 -x fna /input /output
    restart: "no"`;
    
    fs.writeFileSync(tempComposeFile, composeContent);
    
    // Ejecutar docker-compose
    const command = `docker-compose -f ${tempComposeFile} up --build`;
    
    console.log(`Ejecutando CheckM con comando: ${command}`);
    
    exec(command, (error, stdout, stderr) => {
        // Eliminar el archivo temporal
        if (fs.existsSync(tempComposeFile)) {
            fs.unlinkSync(tempComposeFile);
        }
        
        if (error) {
            console.error(`Error al ejecutar CheckM: ${error.message}`);
            return callback(error);
        }
        
        console.log(`Salida de CheckM: ${stdout}`);
        
        if (stderr) {
            console.warn(`Advertencias de CheckM: ${stderr}`);
        }
        
        callback(null, { success: true, message: 'Análisis de CheckM completado con éxito' });
    });
}

module.exports = { runCheckM }; 