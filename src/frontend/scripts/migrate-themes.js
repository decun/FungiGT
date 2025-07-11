/**
 * Script de migración para aplicar el sistema de temas a todas las vistas de FungiGT
 * Uso: node migrate-themes.js
 */

const fs = require('fs');
const path = require('path');

// Mapeo de clases para migración
const classMapping = {
    // Backgrounds
    'bg-white': 'theme-bg-primary',
    'bg-gray-50': 'theme-bg-secondary',
    'bg-gray-100': 'theme-bg-tertiary',
    'bg-gray-200': 'theme-bg-tertiary',
    
    // Textos
    'text-gray-900': 'theme-text-primary',
    'text-gray-800': 'theme-text-primary',
    'text-gray-700': 'theme-text-secondary',
    'text-gray-600': 'theme-text-secondary',
    'text-gray-500': 'theme-text-muted',
    
    // Bordes
    'border-gray-300': 'theme-border',
    'border-gray-200': 'theme-border',
    
    // Sombras
    'shadow-sm': 'theme-shadow-light',
    'shadow': 'theme-shadow-light',
    'shadow-md': 'theme-shadow-medium',
    'shadow-lg': 'theme-shadow-dark',
    'shadow-xl': 'theme-shadow-dark'
};

// Rutas de archivos a migrar
const viewsPath = path.join(__dirname, '../views');
const partialsPath = path.join(viewsPath, 'partials');

/**
 * Migra un archivo EJS aplicando el sistema de temas
 */
function migrateFile(filePath) {
    try {
        console.log(`Migrando: ${filePath}`);
        
        let content = fs.readFileSync(filePath, 'utf8');
        let hasChanges = false;
        
        // 1. Agregar script de theme-manager si no existe
        if (!content.includes('theme-manager.js') && content.includes('</head>')) {
            content = content.replace(
                '</head>',
                '    <script src="/js/theme-manager.js"></script>\n</head>'
            );
            hasChanges = true;
        }
        
        // 2. Actualizar clase del body
        if (content.includes('<body') && !content.includes('theme-bg-primary')) {
            content = content.replace(
                /<body[^>]*class="([^"]*)"[^>]*>/,
                (match, classes) => {
                    const newClasses = classes.replace(/bg-[a-zA-Z0-9-]+/g, '')
                                             .replace(/text-[a-zA-Z0-9-]+/g, '')
                                             .trim();
                    return match.replace(`class="${classes}"`, 
                                       `class="theme-bg-primary theme-text-primary ${newClasses}"`);
                }
            );
            hasChanges = true;
        }
        
        // 3. Reemplazar clases según el mapeo
        Object.entries(classMapping).forEach(([oldClass, newClass]) => {
            const regex = new RegExp(`\\b${oldClass}\\b`, 'g');
            if (content.includes(oldClass)) {
                content = content.replace(regex, newClass);
                hasChanges = true;
            }
        });
        
        // 4. Convertir inputs a theme-input
        const inputRegex = /(<input[^>]*class="[^"]*?)("[^>]*>)/g;
        content = content.replace(inputRegex, (match, before, after) => {
            if (!before.includes('theme-input')) {
                hasChanges = true;
                return before + ' theme-input' + after;
            }
            return match;
        });
        
        // 5. Actualizar tarjetas comunes
        const cardRegex = /class="([^"]*)(bg-white[^"]*shadow[^"]*?)([^"]*)"/g;
        content = content.replace(cardRegex, (match, before, cardClasses, after) => {
            hasChanges = true;
            return `class="${before}theme-card${after}"`;
        });
        
        // 6. Actualizar glass-effect a theme-glass-effect
        if (content.includes('glass-effect')) {
            content = content.replace(/\bglass-effect\b/g, 'theme-glass-effect');
            hasChanges = true;
        }
        
        // 7. Actualizar nav-item-hover a theme-nav-hover
        if (content.includes('nav-item-hover')) {
            content = content.replace(/\bnav-item-hover\b/g, 'theme-nav-hover');
            hasChanges = true;
        }
        
        // Guardar cambios si los hay
        if (hasChanges) {
            fs.writeFileSync(filePath, content);
            console.log(`✅ Migrado: ${filePath}`);
        } else {
            console.log(`ℹ️  Sin cambios: ${filePath}`);
        }
        
    } catch (error) {
        console.error(`❌ Error migrando ${filePath}:`, error.message);
    }
}

/**
 * Migra recursivamente todos los archivos EJS en un directorio
 */
function migrateDirectory(dirPath) {
    try {
        const files = fs.readdirSync(dirPath);
        
        files.forEach(file => {
            const fullPath = path.join(dirPath, file);
            const stat = fs.statSync(fullPath);
            
            if (stat.isDirectory()) {
                migrateDirectory(fullPath);
            } else if (file.endsWith('.ejs')) {
                migrateFile(fullPath);
            }
        });
    } catch (error) {
        console.error(`❌ Error procesando directorio ${dirPath}:`, error.message);
    }
}

/**
 * Crea un backup de las vistas antes de migrar
 */
function createBackup() {
    const backupPath = path.join(__dirname, '../views-backup');
    const viewsPath = path.join(__dirname, '../views');
    
    try {
        if (fs.existsSync(backupPath)) {
            fs.rmSync(backupPath, { recursive: true, force: true });
        }
        
        fs.cpSync(viewsPath, backupPath, { recursive: true });
        console.log('📁 Backup creado en:', backupPath);
    } catch (error) {
        console.error('❌ Error creando backup:', error.message);
        process.exit(1);
    }
}

/**
 * Función principal
 */
function main() {
    console.log('🚀 Iniciando migración del sistema de temas...\n');
    
    // Crear backup
    createBackup();
    
    // Migrar archivos
    console.log('🔄 Migrando archivos...\n');
    migrateDirectory(viewsPath);
    
    console.log('\n✅ Migración completada!');
    console.log('\n📝 Pasos siguientes:');
    console.log('1. Revisar los archivos migrados');
    console.log('2. Probar la aplicación');
    console.log('3. Ajustar estilos específicos si es necesario');
    console.log('4. Eliminar el backup si todo funciona correctamente');
}

// Ejecutar solo si es llamado directamente
if (require.main === module) {
    main();
}

module.exports = { migrateFile, migrateDirectory, classMapping }; 