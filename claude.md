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

### Microservicios (15 contenedores)

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

#### Servicios Especializados

12. **CheckM Tool** (`fungigt-checkm`)
    - Herramienta CheckM oficial (nanozoo/checkm:latest)
    - Evaluación de calidad genómica
    - Perfiles: solo con `--profile tools`

13. **BLAST Tool** (`fungigt-blast`)
    - NCBI BLAST oficial (ncbi/blast:latest)
    - Análisis de homología
    - Bases de datos personalizables

14. **Dr. Fungito AI Agent** (`fungigt-drfungito-agent`) - Puerto 4009
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

### Comandos Docker Compose Avanzados
```bash
# Inicio completo
docker-compose up -d

# Solo servicios web (sin herramientas pesadas)
docker-compose up -d --profile web

# Con todas las herramientas bioinformáticas
docker-compose --profile tools up -d

# Logs de servicio específico
docker-compose -p fungigt logs -f <service-name>

# Reconstruir servicios
docker-compose build --no-cache <service-name>
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