# FungiGT - Plataforma de Análisis Genómico para Hongos 🍄

**FungiGT** es una plataforma completa de análisis genómico especializada en hongos, que integra herramientas de adquisición, control de calidad, anotación genómica, análisis funcional y visualización en una arquitectura de microservicios containerizada.

## 🚀 Características Principales

### 🏗️ Arquitectura de Microservicios
- **Frontend Web** (Puerto 4005): Interfaz web moderna y responsiva
- **Servicio de Autenticación** (Puerto 4001): Gestión segura de usuarios
- **Gestor de Archivos** (Puerto 4002): Manejo centralizado de datos genómicos
- **Módulo de Visualización** (Puerto 4003): Gráficos interactivos y reportes
- **Control de Calidad** (Puerto 4004): Evaluación automática de secuencias
- **Adquisición de Datos** (Puerto 4006): Descarga automatizada desde NCBI

### 🧬 Herramientas de Análisis Integradas

#### Servicios Propios (Desarrollados)
- **Visualización**: Análisis estadístico y gráficos interactivos
- **Adquisición**: Cliente NCBI automatizado para descarga de genomas

#### Servicios Externos (Docker Hub)
- **BRAKER3** (`teambraker/braker3:latest`): Anotación automática de genes en genomas fúngicos
- **CheckM** (`nanozoo/checkm:latest`): Evaluación de completitud y contaminación genómica
- **EggNOG-mapper** (`quay.io/biocontainers/eggnog-mapper`): Análisis funcional y anotación ortóloga
- **BLAST** (`ncbi/blast:latest`): Análisis filogenético y búsqueda de homología

### 💾 Base de Datos
- **MongoDB 7.0**: Almacenamiento de metadatos, usuarios y resultados de análisis

## 📋 Requisitos del Sistema

### Software Requerido
- **Docker Desktop** (versión 20.10 o superior)
- **Docker Compose** (incluido con Docker Desktop)
- **Python 3.8+** (para scripts de instalación)
- **Git** (para clonar el repositorio)

### Recursos Recomendados
- **RAM**: 8GB mínimo, 16GB recomendado
- **Almacenamiento**: 50GB libres (los análisis genómicos requieren espacio considerable)
- **CPU**: 4 núcleos mínimo, 8 núcleos recomendado

## ⚡ Instalación Rápida

### 1. Clonar Repositorio
```bash
git clone https://github.com/tu-usuario/FungiGT.git
cd FungiGT
```

### 2. Instalación Automática
```bash
# Instalación completa paso a paso (evita errores de red de Docker)
python scripts/setup_fungigt.py
```

El script de instalación:
- ✅ Verifica Docker y dependencias
- ✅ Crea directorios necesarios automáticamente
- ✅ Limpia Docker para evitar conflictos
- ✅ Instala servicios uno por uno (evita RST_STREAM errors)
- ✅ Descarga herramientas externas de Docker Hub
- ✅ Verifica que todos los servicios funcionen
- ✅ Muestra resumen completo de instalación

### 3. Verificación
Una vez completada la instalación, el sistema estará disponible en:
- **Frontend**: http://localhost:4005
- **API Auth**: http://localhost:4001/health

## 🎮 Uso Diario

### Inicio Rápido
```bash
# Verificar estado de servicios
python scripts/quick_start.py status

# Iniciar todos los servicios
python scripts/quick_start.py start

# Detener servicios
python scripts/quick_start.py stop

# Reiniciar servicios
python scripts/quick_start.py restart
```

### Acceso a Herramientas Externas
```bash
# Ejecutar análisis con BRAKER3
docker exec -it fungigt-annotation bash

# Usar CheckM para evaluación de completitud
docker exec -it fungigt-checkm bash

# Análisis funcional con EggNOG
docker exec -it fungigt-eggnog bash

# Búsquedas BLAST
docker exec -it fungigt-blast bash
```

## 📁 Estructura de Directorios

```
FungiGT/
├── src/                          # Código fuente
│   ├── frontend/                 # Aplicación web React/Vue
│   ├── core/                     # Servicios principales
│   │   ├── auth/                 # Autenticación y autorización
│   │   └── database/             # Conexiones de base de datos
│   └── modules/                  # Módulos de análisis
│       ├── acquisition/          # Adquisición de datos NCBI
│       ├── file_manager/         # Gestión de archivos
│       ├── quality_control/      # Control de calidad
│       └── visualization/        # Visualización y reportes
├── infrastructure/               # Configuración de contenedores
│   └── docker/                   # Dockerfiles por servicio
├── data/                         # Datos y resultados
│   ├── braker_output/           # Resultados de anotación BRAKER3
│   ├── checkm_output/           # Evaluaciones de CheckM
│   ├── eggnog_output/           # Análisis funcional EggNOG
│   ├── blast_output/            # Resultados de BLAST
│   └── blast_db/                # Base de datos BLAST local
├── scripts/                     # Scripts de automatización
│   ├── setup_fungigt.py         # Instalador principal
│   ├── quick_start.py           # Gestión diaria
│   └── debug_installation.py    # Herramientas de depuración
└── docker-compose.yml          # Orquestación de contenedores
```

## 🔧 Configuración Avanzada

### Variables de Entorno (.env)
```bash
# Puertos de servicios
FRONTEND_PORT=4005
AUTH_PORT=4001
FILE_MANAGER_PORT=4002
VISUALIZATION_PORT=4003
QUALITY_CONTROL_PORT=4004
ACQUISITION_PORT=4006

# Base de datos
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=admin123
MONGO_DATABASE=fungigt
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin

# Seguridad
JWT_SECRET=fungi-gt-secret-key-2024
NODE_ENV=development
```

### Servicios Personalizables

#### Adquisición de Datos
- Configurar credenciales NCBI
- Definir especies de interés
- Programar descargas automáticas

#### Control de Calidad
- Ajustar umbrales de calidad
- Integrar CheckM para evaluación
- Configurar filtros personalizados

#### Visualización
- Personalizar gráficos
- Configurar reportes automáticos
- Exportar resultados

## 🛠️ Desarrollo y Contribución

### Estructura de Desarrollo
```bash
# Desarrollo individual de servicios
docker-compose up -d mongodb  # Base de datos
docker-compose up -d auth     # Autenticación
docker-compose build frontend && docker-compose up -d frontend

# Logs en tiempo real
docker-compose logs -f <nombre_servicio>

# Acceso a contenedores
docker exec -it fungigt-<servicio> bash
```

### Agregar Nuevas Herramientas
1. Agregar servicio en `docker-compose.yml`
2. Crear Dockerfile si es necesario
3. Actualizar scripts de instalación
4. Integrar en interfaz web

## 📊 Monitoreo y Depuración

### Verificar Estado del Sistema
```bash
# Estado completo del sistema
python scripts/debug_installation.py

# Logs de servicios específicos
docker-compose logs <servicio>

# Uso de recursos
docker stats
```

### Solución de Problemas Comunes

#### Error RST_STREAM durante construcción
```bash
# El instalador automático ya maneja esto
python scripts/setup_fungigt.py
```

#### Servicios no inician
```bash
# Reinicio limpio
python scripts/quick_start.py stop
docker system prune -f
python scripts/setup_fungigt.py
```

#### Problemas de memoria
```bash
# Ajustar límites en docker-compose.yml
services:
  servicio:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 🧪 Flujo de Trabajo Típico

### 1. Adquisición de Datos
```bash
# Acceder al módulo de adquisición
curl http://localhost:4006/download -d '{"species": "Aspergillus fumigatus"}'
```

### 2. Control de Calidad
```bash
# Evaluar calidad con CheckM
docker exec -it fungigt-checkm checkm lineage_wf /data/genomes /data/checkm_output
```

### 3. Anotación Genómica
```bash
# Anotar genes con BRAKER3
docker exec -it fungigt-annotation braker.pl --species=fungi --genome=/data/genome.fasta
```

### 4. Análisis Funcional
```bash
# Análisis funcional con EggNOG
docker exec -it fungigt-eggnog emapper.py -i /data/proteins.fasta -o /data/eggnog_output
```

### 5. Análisis Filogenético
```bash
# Búsquedas BLAST
docker exec -it fungigt-blast blastp -query /data/query.fasta -db /blast/blastdb/nr
```

### 6. Visualización
- Acceder a http://localhost:4003 para gráficos interactivos
- Generar reportes automatizados
- Exportar resultados en múltiples formatos

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📞 Soporte

- **Issues**: GitHub Issues para reportar bugs
- **Documentación**: Wiki del proyecto
- **Contacto**: [email de contacto]

---

**FungiGT** - Potenciando la investigación en genómica de hongos con herramientas modernas y accesibles.

## Problemas Comunes

### Error "Command find requires authentication"
Si ves este error al registrarte/loguearte:

1. Verifica que existe el archivo `.env` en la raíz del proyecto
2. Asegúrate que tiene la variable: `MONGODB_URI=mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin`
3. El archivo debe estar en codificación UTF-8, no UTF-16
4. Reinicia los servicios: `docker compose -p fungigt restart auth`
