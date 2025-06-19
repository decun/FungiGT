# eggNOG-mapper para FungiGT

Este módulo proporciona análisis funcional de proteínas utilizando eggNOG-mapper en un entorno Dockerizado.

## 🧬 Características

- **Análisis funcional completo**: Anotación de proteínas con ontología GO, KEGG, COG
- **Gestión inteligente de BD**: Descarga automática de base de datos solo cuando es necesaria
- **Interfaz web integrada**: Control desde el frontend de FungiGT
- **Contenedor nanozoo**: Usa la imagen oficial `nanozoo/eggnog-mapper:2.1.9--4f2b6c0`
- **Streaming de progreso**: Monitoreo en tiempo real del análisis

## 📋 Requisitos

- Docker instalado y ejecutándose
- Python 3.7+ (para scripts de gestión)
- Node.js 16+ (para el servidor API)
- ~3 GB de espacio libre (base de datos eggNOG)

## 🚀 Instalación Rápida

### 1. Instalar dependencias del módulo
```bash
cd src/modules/analysis/eggnog
npm install
```

### 2. Preparar base de datos (opcional)
```bash
# Opción A: Usar script de Python
python scripts/eggnog_db_manager.py --download

# Opción B: Usar script Bash
./scripts/eggnog_helper.sh download-db

# Opción C: Descarga automática desde la interfaz web
```

### 3. Iniciar servicio
```bash
# Usando docker-compose
cd infrastructure/docker/analysis/eggnog
docker-compose up -d

# O usando el script de ayuda
./scripts/eggnog_helper.sh start
```

## 🔧 Configuración

### Variables de Entorno

- `PORT`: Puerto del servicio (default: 3001)
- `NODE_ENV`: Entorno de ejecución (production/development)
- `EGGNOG_IMAGE`: Imagen Docker de eggNOG-mapper

### Directorios de Datos

```
data/
├── eggnog_db/          # Base de datos eggNOG (~2.9 GB)
├── eggnog_uploads/     # Archivos subidos
└── eggnog_results/     # Resultados de análisis
```

## 📊 Uso

### Desde la Interfaz Web

1. Ir a **Analizador Funcional** → **eggNOG-mapper**
2. Verificar estado de base de datos
3. Descargar BD si es necesario (confirmación automática)
4. Configurar parámetros de análisis
5. Ejecutar análisis

### Desde API REST

#### Verificar estado de BD
```bash
curl http://localhost:3001/database/status
```

#### Descargar base de datos
```bash
curl -X POST http://localhost:3001/database/download \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

#### Ejecutar análisis
```bash
curl -X POST http://localhost:3001/run-eggnog \
  -H "Content-Type: application/json" \
  -d '{
    "proteinFilePath": "/data/input/proteins.faa",
    "outputName": "analysis_result",
    "taxScope": "2759",
    "cpu": 4
  }'
```

### Usando Scripts de Ayuda

#### Script Python (completo)
```bash
# Verificar estado
python scripts/eggnog_db_manager.py --check

# Información detallada
python scripts/eggnog_db_manager.py --info

# Descargar BD con confirmación
python scripts/eggnog_db_manager.py --download

# Descargar BD sin confirmación
python scripts/eggnog_db_manager.py --force

# Limpiar archivos temporales
python scripts/eggnog_db_manager.py --clean
```

#### Script Bash (servicio)
```bash
# Estado del servicio
./scripts/eggnog_helper.sh status

# Iniciar todo desde cero
./scripts/eggnog_helper.sh pull
./scripts/eggnog_helper.sh download-db
./scripts/eggnog_helper.sh start

# Probar configuración
./scripts/eggnog_helper.sh test

# Ver logs en tiempo real
./scripts/eggnog_helper.sh logs
```

## ⚙️ Parámetros de eggNOG-mapper

### Básicos
- **Input file** (`-i`): Archivo FASTA de proteínas
- **Output name** (`-o`): Nombre base para archivos de salida
- **Tax scope** (`--tax_scope`): Alcance taxonómico (2759 para eucariotas)
- **CPUs** (`--cpu`): Número de procesadores a usar

### Avanzados
- **Data type** (`--itype`): proteins, CDS, genome, metagenome
- **Search mode** (`-m`): diamond, mmseqs, hmmer
- **E-value** (`--evalue`): Umbral de significancia
- **Gene prediction** (`--genepred`): search, prodigal

### Opciones de Salida
- **No comments** (`--no_file_comments`): Sin comentarios en archivos
- **Resume** (`--resume`): Continuar análisis interrumpido
- **Override** (`--override`): Sobrescribir archivos existentes

## 📁 Archivos de Salida

eggNOG-mapper genera varios archivos de resultados:

- `*.emapper.annotations`: Anotaciones principales (formato tabular)
- `*.emapper.seed_orthologs`: Ortólogos semilla identificados
- `*.emapper.hits`: Hits de búsqueda de secuencias

### Formato de Anotaciones

Las anotaciones incluyen:
- **GO terms**: Ontología genética
- **KEGG pathways**: Rutas metabólicas
- **COG categories**: Clusters de genes ortólogos
- **Pfam domains**: Dominios proteicos
- **EC numbers**: Números de enzimas

## 🔍 Monitoreo y Debugging

### Health Checks
```bash
# Estado del servicio
curl http://localhost:3001/health

# Información del servicio
curl http://localhost:3001/info
```

### Logs
```bash
# Logs del contenedor
docker logs fungigt-eggnog-mapper -f

# O usando el script
./scripts/eggnog_helper.sh logs
```

### Archivos de Log
- `logs/error.log`: Errores del servicio
- `logs/combined.log`: Logs completos

## ⚠️ Consideraciones Importantes

### Base de Datos
- **Tamaño**: ~2.9 GB comprimida, ~4+ GB descomprimida
- **Tiempo de descarga**: 10-30 minutos según conexión
- **Actualización**: Se puede actualizar ejecutando descarga nuevamente
- **Ubicación**: `data/eggnog_db/`

### Rendimiento
- **Memoria RAM**: Mínimo 4 GB recomendado
- **CPU**: Más cores = análisis más rápido
- **Almacenamiento**: SSD recomendado para mejor I/O

### Limitaciones
- Solo archivos de proteínas en formato FASTA
- Análisis secuencial (no paralelo por trabajos)
- Requiere conexión a internet para descarga inicial

## 🐛 Solución de Problemas

### Error: Base de datos no encontrada
```bash
# Verificar estado
python scripts/eggnog_db_manager.py --check

# Descargar si falta
./scripts/eggnog_helper.sh download-db
```

### Error: Contenedor no inicia
```bash
# Verificar Docker
docker info

# Revisar puertos
sudo netstat -tulpn | grep 3001

# Limpiar y reiniciar
./scripts/eggnog_helper.sh stop
./scripts/eggnog_helper.sh start
```

### Error: Análisis falla
```bash
# Verificar logs
./scripts/eggnog_helper.sh logs

# Verificar archivo de entrada
ls -la /path/to/input/file.faa

# Probar configuración
./scripts/eggnog_helper.sh test
```

## 📖 Referencias

- [eggNOG-mapper Documentation](https://github.com/eggnogdb/eggnog-mapper)
- [eggNOG Database](http://eggnog5.embl.de/)
- [Nanozoo Container](https://hub.docker.com/r/nanozoo/eggnog-mapper)

## 🤝 Contribuir

Para reportar bugs o sugerir mejoras:
1. Ejecutar `./scripts/eggnog_helper.sh test` 
2. Adjuntar logs relevantes
3. Describir el problema o mejora propuesta

---

**FungiGT Team** - Análisis genómico especializado en hongos 🍄 