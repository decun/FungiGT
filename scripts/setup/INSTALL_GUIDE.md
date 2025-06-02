# 🚀 Guía de Instalación FungiGT v2.0

## 📋 Resumen del Sistema de Autoinstalación

FungiGT ahora incluye un **sistema de autoinstalación completo** que maneja toda la configuración y despliegue con comandos simples.

## 🎯 Comandos Principales

### 🆕 Primera Instalación
```bash
python scripts/setup/setup_fungigt.py
```

### ⚡ Inicio Rápido (uso diario)
```bash
python scripts/setup/quick_start.py
```

### 🛑 Detener Servicios
```bash
python scripts/setup/stop_services.py
```

### 🔧 Solucionador de Problemas Docker
```bash
python scripts/setup/fix_docker_network.py
```

## 🔧 Opciones Avanzadas

### Reinstalación Completa
```bash
python scripts/setup/setup_fungigt.py --clean --rebuild
```

### Solo Iniciar (sin construir)
```bash
python scripts/setup/setup_fungigt.py --skip-build
```

### Detener con Limpieza de Datos
```bash
python scripts/setup/stop_services.py --remove-volumes --cleanup
```

## 📁 Archivos del Sistema

### Scripts Principales
- `setup_fungigt.py` - **Script maestro de autoinstalación**
- `quick_start.py` - Inicio rápido para uso diario
- `stop_services.py` - Detención controlada de servicios
- `fix_docker_network.py` - **🆕 Solucionador de problemas Docker**
- `requirements.txt` - Dependencias Python

### Configuración
- `docker-compose.yml` - Configuración de servicios actualizada
- `scripts/mongo-init/init-db.js` - Inicialización de MongoDB
- `.env` - Variables de entorno (auto-generado)

## 🌟 Características del Nuevo Sistema

### ✅ Verificación Automática
- Verifica Docker y Docker Compose
- Valida versiones de Python
- Comprueba puertos disponibles

### 🏗️ Construcción Inteligente
- Construye servicios en orden de dependencia
- Reintentos automáticos en caso de fallo
- Logs detallados con colores

### 🔍 Monitoreo de Estado
- Health checks para todos los servicios
- Verificación de conectividad
- Estado en tiempo real

### 🎨 Interfaz Mejorada
- Banners coloridos y informativos
- Logs con timestamps y niveles
- Información clara de acceso

### 🛠️ Solucionador de Problemas Integrado
- Diagnóstico automático de errores de Docker
- Limpieza de caché y recursos
- Soluciones paso a paso para errores comunes

## 🗄️ Servicios Incluidos

| Servicio | Puerto | Función | Estado |
|----------|--------|---------|--------|
| MongoDB | 27017 | Base de datos | ✅ Automático |
| Auth | 4001 | Autenticación JWT | ✅ Automático |
| File Manager | 4002 | Gestión de archivos | ✅ Automático |
| Visualization | 4003 | Gráficos | ✅ Automático |
| Quality Control | 4004 | CheckM | ✅ Automático |
| Frontend | 4005 | Interfaz web | ✅ Automático |
| Acquisition | 4006 | Descarga NCBI | ✅ Automático |
| BRAKER3 | - | Anotación | ✅ Automático |

## 🔐 Configuración de Seguridad

### Usuario Admin por Defecto
- **Email**: admin@fungigt.com
- **Password**: admin123
- **Rol**: Administrador completo

### Variables de Entorno Seguras
```env
JWT_SECRET=fungi-gt-secret-key-2024-auto-generated
SESSION_SECRET=fungi-gt-session-secret-2024
MONGO_ROOT_PASSWORD=admin123
```

## 📊 Estructura de Datos

### Directorios Autocreados
```
data/
├── raw/genomes/      # Genomas descargados de NCBI
├── processed/        # Datos procesados
├── uploads/          # Archivos subidos por usuarios
├── results/          # Resultados de análisis
├── downloads/        # Descargas temporales
├── references/       # Genomas de referencia
├── intermediate/     # Archivos de trabajo
└── visualizations/   # Gráficos generados
```

## 🛠️ Solución de Problemas Comunes

### ⚡ Solucionador Automático
Si experimentas errores durante la instalación:
```bash
python scripts/setup/fix_docker_network.py
```

### Error: Docker no encontrado
```bash
# Verificar instalación
docker --version
docker compose version

# Si falla, instalar Docker Desktop
# https://www.docker.com/products/docker-desktop
```

### Error: RST_STREAM con INTERNAL_ERROR
```bash
# 🆕 Usar el solucionador automático
python scripts/setup/fix_docker_network.py

# Selecciona opción 1: Solución rápida automática
```

### Error: Puerto ocupado
```bash
# Verificar qué proceso usa el puerto
netstat -tulpn | grep :4005

# Detener servicios previos
python scripts/setup/stop_services.py --force
```

### Error: Falta de memoria
```bash
# Aumentar memoria asignada a Docker Desktop
# Docker Desktop > Settings > Resources > Memory > 4GB+

# O usar el solucionador:
python scripts/setup/fix_docker_network.py
# Selecciona opción 4: Mostrar cómo aumentar recursos
```

### Error: Construcción fallida
```bash
# Limpiar caché de Docker
python scripts/setup/fix_docker_network.py
# Selecciona opción 2: Limpiar caché de Docker

# O manualmente:
docker system prune -f
docker builder prune -f

# Reinstalar completamente
python scripts/setup/setup_fungigt.py --clean
```

### Construcción Individual de Servicios
Si fallan servicios específicos:
```bash
# Construcción manual paso a paso
python scripts/setup/fix_docker_network.py
# Selecciona opción 8: Construcción manual paso a paso

# O comandos individuales:
docker compose -p fungigt build auth
docker compose -p fungigt build file-manager
docker compose -p fungigt build frontend
```

### Problemas de Red/DNS
```bash
# Solucionar DNS automáticamente
python scripts/setup/fix_docker_network.py
# Selecciona opción 6: Solucionar problemas de DNS

# Verificar conectividad
python scripts/setup/fix_docker_network.py  
# Selecciona opción 5: Verificar conectividad de red
```

## 📝 Logs y Debugging

### Ver logs en tiempo real
```bash
docker compose -p fungigt logs -f
```

### Ver logs de un servicio específico
```bash
docker compose -p fungigt logs frontend
docker compose -p fungigt logs auth
```

### Verificar estado de contenedores
```bash
docker compose -p fungigt ps
```

## 🔄 Flujo de Trabajo Recomendado

### Desarrollo Diario
1. `python scripts/setup/quick_start.py` - Iniciar
2. Trabajar en tu código
3. `python scripts/setup/stop_services.py` - Detener

### Actualización de Código
1. `python scripts/setup/stop_services.py`
2. Actualizar código
3. `python scripts/setup/setup_fungigt.py --restart`

### Limpieza Periódica
```bash
# Cada semana
python scripts/setup/stop_services.py --cleanup

# Cada mes (cuidado: elimina datos)
python scripts/setup/stop_services.py --remove-volumes
```

## 📞 Soporte

### Si algo falla:
1. Revisa los logs: `docker compose -p fungigt logs -f`
2. Intenta reinstalar: `python scripts/setup/setup_fungigt.py --clean`
3. Verifica Docker: `docker info`
4. Consulta la documentación en `docs/`

### Para reportar problemas:
- Incluye la salida de los scripts
- Especifica tu sistema operativo
- Indica la versión de Docker

---

**¡FungiGT v2.0 está listo para hacer el análisis genómico más fácil que nunca!** 🍄🧬✨ 