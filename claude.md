# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# FungiGT - Plataforma de Análisis Genómico de Hongos

## Descripción General

FungiGT es una plataforma completa de análisis genómico especializada en hongos, implementada como una arquitectura de microservicios usando Docker. La plataforma integra múltiples herramientas bioinformáticas y proporciona una interfaz web unificada para análisis genómicos end-to-end.

## Arquitectura del Sistema

### Tecnologías Principales
- **Backend**: Node.js con Express, Python Flask
- **Frontend**: EJS templates, JavaScript vanilla
- **Base de Datos**: MongoDB 4.4
- **Containerización**: Docker & Docker Compose
- **AI/ML**: Anthropic Claude API para análisis inteligente

### Microservicios (17 contenedores)

#### Servicios Core
1. **MongoDB** (`fungigt-mongodb`) - Puerto 27017
   - Base de datos principal del sistema
   - Autenticación configurada
   - Volumen persistente para datos

2. **Auth Service** (`fungigt-auth`) - Puerto 4001
   - Servicio de autenticación y autorización
   - JWT tokens para sesiones
   - Middleware de autenticación

3. **Frontend** (`fungigt-frontend`) - Puerto 4005
   - Interfaz web principal
   - Dashboard unificado
   - Integración con todos los servicios

4. **File Manager** (`fungigt-file-manager`) - Puerto 4002
   - Gestión centralizada de archivos
   - Upload/download de datasets
   - Navegación de resultados

#### Servicios de Análisis

5. **Visualization Server** (`fungigt-visualization-server`) - Puerto 4003
   - Servidor Python Flask para visualizaciones
   - Gráficos interactivos (matplotlib, seaborn)
   - Soporte para múltiples tipos de datos genómicos

6. **Quality Control** (`fungigt-quality-control`) - Puerto 4004
   - Control de calidad con CheckM
   - Evaluación de completitud genómica
   - Detección de contaminación

7. **Acquisition** (`fungigt-acquisition`) - Puerto 4006
   - Descarga de datos NCBI
   - CLI personalizado para datasets públicos
   - Automatización de adquisición

8. **BinDash Analysis** (`fungigt-bindash-analysis`) - Puerto 4007
   - Análisis filogenético rápido
   - Matrices de distancia genómica
   - Dendrogramas automáticos

#### Servicios de Anotación

9. **BRAKER3 Server** (`fungigt-braker3-server`) - Puerto 3004
   - API para anotación genómica
   - Orquestación de BRAKER3
   - Gestión de trabajos asíncronos

10. **BRAKER3 Tool** (`fungigt-annotation`)
    - Contenedor BRAKER3 oficial (teambraker/braker3:latest)
    - Anotación automática de genes
    - Perfiles: solo con `--profile tools`

11. **eggNOG-mapper** (`fungigt-eggnog-mapper`) - Puerto 3002
    - Anotación funcional de proteínas
    - API personalizada sobre nanozoo/eggnog-mapper
    - Análisis COG, GO, KEGG

12. **Funannotate Server** (`fungigt-funannotate-server`) - Puerto 3005
    - API para anotación genómica completa con Funannotate
    - Workflows: predict, annotate, compare
    - Especializada en genómica fúngica

#### Servicios Especializados

13. **CheckM Tool** (`fungigt-checkm`)
    - Herramienta CheckM oficial (nanozoo/checkm:latest)
    - Evaluación de calidad genómica
    - Perfiles: solo con `--profile tools`

14. **BLAST Tool** (`fungigt-blast`)
    - NCBI BLAST oficial (ncbi/blast:latest)
    - Análisis de homología
    - Bases de datos personalizables

15. **Funannotate Tool** (`fungigt-funannotate`)
    - Herramienta Funannotate oficial (nextgenusfs/funannotate:latest)
    - Anotación genómica completa para hongos
    - Perfiles: solo con `--profile tools`

16. **Dr. Fungito AI Agent** (`fungigt-drfungito-agent`) - Puerto 4009
    - Agente de IA especializado en genómica
    - Análisis automático de imágenes/gráficos
    - Generación de reportes inteligentes
    - Powered by Anthropic Claude


## Características Principales

### Pipeline Completo de Análisis
1. **Adquisición** → Descarga de genomas NCBI
2. **Control de Calidad** → Evaluación con CheckM
3. **Anotación** → Genes (BRAKER3) y funciones (eggNOG)
4. **Análisis Filogenético** → Distancias con BinDash
5. **Visualización** → Gráficos interactivos
6. **Interpretación IA** → Análisis automático con Dr. Fungito

### Funcionalidades Avanzadas
- **Gestión de Archivos**: Sistema centralizado para datasets
- **Visualizaciones**: Matrices de calor, dendrogramas, gráficos estadísticos
- **IA Integrada**: Interpretación automática de resultados
- **Arquitectura Escalable**: Microservicios independientes
- **Persistencia**: Volúmenes Docker para datos y resultados

## Estructura de Puertos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| Frontend | 4005 | Interfaz web principal |
| Auth | 4001 | Autenticación |
| File Manager | 4002 | Gestión de archivos |
| Visualization | 4003 | Servidor de visualización |
| Quality Control | 4004 | Control de calidad |
| Acquisition | 4006 | Adquisición NCBI |
| BinDash | 4007 | Análisis filogenético |
| BRAKER3 API | 3004 | Anotación genómica |
| eggNOG API | 3002 | Anotación funcional |
| Funannotate API | 3005 | Anotación completa |
| Dr. Fungito | 4009 | Agente de IA |
| MongoDB | 27017 | Base de datos |

## Configuración de Red
- **Red**: `fungigt-network` (bridge)
- **Comunicación interna**: Por nombres de contenedor
- **Healthchecks**: Configurados para todos los servicios críticos

## Volúmenes Persistentes
- `fungigt-mongodb-data`: Datos de MongoDB
- `fungigt-data`: Datos de aplicación compartidos
- `./data`: Bind mount para resultados y datasets

## Variables de Entorno Principales
```bash
NODE_ENV=development
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=admin123
JWT_SECRET=fungi-gt-secret-key-2024
ANTHROPIC_API_KEY=<your-key>
FRONTEND_PORT=4005
AUTH_PORT=4001
```

## Comandos de Desarrollo Esenciales

### Instalación Inicial (Primera Vez)
```bash
python scripts/setup/setup_fungigt.py
```

### Desarrollo Diario (Inicio Rápido)
```bash
python scripts/setup/quick_start.py
```

### Detener Servicios
```bash
python scripts/setup/stop_services.py
```

### Solucionar Problemas de Red Docker
```bash
python scripts/setup/fix_docker_network.py
```

### Comandos Docker Compose
```bash
# Inicio completo con project name
docker-compose -p fungigt up -d

# Solo servicios web (sin herramientas pesadas)
docker-compose -p fungigt --profile web up -d

# Con todas las herramientas bioinformáticas
docker-compose -p fungigt --profile tools up -d

# Logs de servicio específico
docker-compose -p fungigt logs -f <service-name>

# Reconstruir servicios
docker-compose -p fungigt build --no-cache <service-name>

# Ver estado de servicios
docker-compose -p fungigt ps

# Parar todos los servicios
docker-compose -p fungigt down
```

### Comandos de Desarrollo por Servicio
```bash
# Frontend (Node.js + EJS)
cd src/frontend
npm run start    # usa nodemon para hot reload
npm test         # placeholder, no hay tests implementados

# Auth Service (Node.js + JWT)
cd src/core/auth
npm run dev      # desarrollo con nodemon
npm start        # producción
npm test         # placeholder, no hay tests implementados

# Servicios de análisis (patrón similar)
cd src/modules/<service>
npm run dev      # desarrollo con nodemon
npm start        # producción

# Servicios Python (visualización)
cd src/modules/visualization
pip install -r requirements.txt
python app.py    # Flask development server
```

### Debugging y Monitoreo
```bash
# Ver logs en tiempo real
docker-compose -p fungigt logs -f

# Inspeccionar contenedor específico
docker exec -it fungigt-<service-name> /bin/sh

# Ver estado de red
docker network ls | grep fungigt
docker network inspect fungigt-network

# Verificar estado de base de datos
docker exec -it fungigt-mongodb mongo -u admin -p admin123 --authenticationDatabase admin
```

## Casos de Uso Típicos

1. **Análisis de Genoma Individual**:
   - Upload → Quality Control → Annotation → Visualization

2. **Estudio Filogenético**:
   - Múltiples genomas → BinDash → Dendrogramas → Interpretación IA

3. **Anotación Funcional**:
   - Proteomas → eggNOG-mapper → Análisis GO/KEGG → Reportes

4. **Control de Calidad Masivo**:
   - Datasets → CheckM → Evaluación automática → Filtrado

## Dependencias del Sistema
- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM mínimo (16GB recomendado)
- 50GB espacio en disco para datos
- Conexión a internet para herramientas externas

## Arquitectura de Desarrollo
- **Bind Mounts**: Código fuente montado para desarrollo
- **Hot Reload**: Nodemon en servicios Node.js
- **Logs Centralizados**: `./logs` para debugging
- **Health Checks**: Monitoreo automático de servicios

## Especialización en Hongos
- Herramientas optimizadas para genómica fúngica
- Bases de datos especializadas
- Workflows específicos para especies de hongos
- Análisis comparativo inter-especies
- Dr. Fungito entrenado en literatura micológica

## Estructura de Directorios Clave

```
data/                         # Datos persistentes
├── raw/genomes/             # Genomas descargados de NCBI
├── results/                 # Resultados de análisis
├── uploads/                 # Archivos subidos por usuarios
├── visualizations/          # Gráficos generados
├── eggnog_results/          # Anotaciones funcionales
├── bindash_results/         # Análisis filogenético
└── checkm_output/           # Control de calidad

src/
├── frontend/                # Interfaz web (Node.js/Express/EJS)
├── core/auth/              # Servicio de autenticación
└── modules/                # Servicios de análisis
    ├── file_manager/       # Gestión de archivos
    ├── visualization/      # Servidor Python Flask
    ├── acquisition/        # Cliente NCBI
    ├── quality_control/    # Integración CheckM
    ├── analysis/           # bindash, eggnog
    └── ai_agent/           # Dr. Fungito (Claude AI)
```

## APIs Principales


### Autenticación (Puerto 4001)
- `POST /auth/register` - Registro de usuarios
- `POST /auth/login` - Login con JWT
- `GET /auth/profile` - Perfil de usuario

### Frontend (Puerto 4005)
- `GET /` - Página principal
- `GET /database` - Gestión de datos
- `GET /annotator` - Anotación genómica
- `GET /analyzer` - Análisis comparativo
- `GET /visualizer` - Visualizaciones

## Desarrollo y Debugging

### Hot Reload
- Servicios Node.js usan `nodemon` para auto-reload
- Cambios en código se reflejan automáticamente
- Logs centralizados en `./logs/`

### Base de Datos
- MongoDB con autenticación (admin/admin123)
- Conexión: `mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin`
- Inicialización automática con `scripts/mongo-init/init-db.js`

### Health Checks
- Todos los servicios exponen endpoint `/health`
- Monitoreo automático con Docker Compose
- Reinicio automático en caso de fallo

### Variables de Entorno Críticas
```bash
ANTHROPIC_API_KEY=<claude-api-key>    # Para Dr. Fungito AI
JWT_SECRET=fungi-gt-secret-key-2024   # Autenticación
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin
```

## Arquitectura de Comunicación
- Red interna: `fungigt-network` (bridge)
- Servicios se comunican por nombre de contenedor
- Puertos expuestos solo para desarrollo/debugging
- Balanceador de carga interno para escalabilidad

## Stack Tecnológico Detallado

### Servicios Node.js
**Dependencias Principales:**
- Express 4.18+ (framework web)
- Mongoose 6.9+ / MongoDB 6.8+ (base de datos)
- JWT (jsonwebtoken 9.0+) + bcryptjs 2.4+ (autenticación)
- EJS templates (frontend)
- Multer (manejo de archivos)
- Nodemon (desarrollo con hot reload)

### Servicios Python
**Dependencias Principales:**
- Flask 2.0+ (framework web)
- Matplotlib 3.5+, Seaborn 0.11+, Plotly 5.0+ (visualización)
- Pandas 1.3+, NumPy (análisis de datos)
- BioPython 1.79+ (procesamiento bioinformático)
- DNA Features Viewer 3.1+ (visualización genómica)

### Base de Datos
- MongoDB 4.4 con autenticación
- Conexiones con pooling y retry logic
- Colecciones: usuarios, proyectos, análisis, resultados

### Herramientas Bioinformáticas Externas
- BRAKER3 (teambraker/braker3:latest)
- CheckM (nanozoo/checkm:latest)
- eggNOG-mapper (nanozoo/eggnog-mapper)
- BLAST (ncbi/blast:latest)

## Notas de Desarrollo Importantes

### Testing
- **Estado actual**: No hay tests unitarios implementados
- **Recomendación**: Usar Jest para Node.js, pytest para Python
- **Comandos**: `npm test` actualmente devuelve placeholder

### Linting y Formateo
- **Estado actual**: No hay configuración de ESLint/Prettier
- **Recomendación**: Configurar ESLint + Prettier para consistencia

### Hot Reload y Desarrollo
- Todos los servicios Node.js usan `nodemon` para auto-reload
- Bind mounts configurados para desarrollo en tiempo real
- Variables de entorno separadas para desarrollo/producción 