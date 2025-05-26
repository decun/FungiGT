/**
 * Script para configurar la estructura de directorios de datos
 */
const fs = require('fs-extra');
const path = require('path');

const DATA_DIR = path.join(__dirname, '../../../data');

async function setupDataDirectory() {
    try {
        console.log('Configurando estructura de directorios...');
        console.log('Directorio base:', DATA_DIR);
        
        // Crear directorios principales
        const directories = [
            'raw/genomes',
            'intermediate/quality_filtered',
            'intermediate/annotated',
            'results/quality_control',
            'results/annotation',
            'results/analysis/blastn',
            'results/analysis/eggnog',
            'visualizations',
            'downloads'
        ];
        
        for (const dir of directories) {
            const fullPath = path.join(DATA_DIR, dir);
            await fs.ensureDir(fullPath);
            console.log(`✓ Creado: ${dir}`);
        }
        
        // Crear algunos archivos de ejemplo para probar
        const exampleFile = path.join(DATA_DIR, 'README.txt');
        if (!fs.existsSync(exampleFile)) {
            await fs.writeFile(exampleFile, 
                'Directorio de datos de FungiGT\n' +
                'Este directorio contiene todos los archivos del proyecto.\n' +
                '\n' +
                'Estructura:\n' +
                '- raw/: Datos sin procesar\n' +
                '- intermediate/: Datos procesados intermedios\n' +
                '- results/: Resultados finales\n' +
                '- visualizations/: Gráficos y visualizaciones\n'
            );
            console.log('✓ Creado archivo README.txt');
        }
        
        console.log('\n✅ Estructura de directorios configurada correctamente');
        console.log(`📁 Directorio base: ${DATA_DIR}`);
        
    } catch (error) {
        console.error('❌ Error al configurar directorios:', error);
    }
}

setupDataDirectory(); 