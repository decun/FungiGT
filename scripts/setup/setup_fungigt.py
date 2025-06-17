#!/usr/bin/env python3
"""
FungiGT - Script de Autoinstalación Completa
===========================================

Este script automatiza completamente la instalación y configuración de FungiGT.
Ejecuta: python scripts/setup/setup_fungigt.py
"""

import os
import sys
import subprocess
import time
import platform
import json
import argparse
from pathlib import Path
import requests
import signal

# Colores para la consola
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    """Mostrar banner de FungiGT"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
███████╗██╗   ██╗███╗   ██╗ ██████╗ ██╗ ██████╗ ████████╗
██╔════╝██║   ██║████╗  ██║██╔════╝ ██║██╔════╝ ╚══██╔══╝
█████╗  ██║   ██║██╔██╗ ██║██║  ███╗██║██║  ███╗   ██║   
██╔══╝  ██║   ██║██║╚██╗██║██║   ██║██║██║   ██║   ██║   
██║     ╚██████╔╝██║ ╚████║╚██████╔╝██║╚██████╔╝   ██║   
╚═╝      ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝ ╚═════╝    ╚═╝   
{Colors.END}
{Colors.GREEN}🧬 Plataforma de Análisis Genómico para Hongos{Colors.END}
{Colors.YELLOW}🚀 Script de Autoinstalación v2.1{Colors.END}
{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
"""
    print(banner)

def log(level, message):
    """Logger con colores"""
    timestamp = time.strftime("%H:%M:%S")
    colors = {
        'INFO': Colors.CYAN,
        'SUCCESS': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'DEBUG': Colors.MAGENTA
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{Colors.WHITE}[{timestamp}]{Colors.END} {color}[{level}]{Colors.END} {message}")

def run_command(cmd, cwd=None, capture_output=False, timeout=300):
    """Ejecutar comando con manejo de errores mejorado"""
    if isinstance(cmd, str):
        cmd_str = cmd
        cmd = cmd.split()
    else:
        cmd_str = ' '.join(cmd)
    
    log('DEBUG', f"Ejecutando: {cmd_str}")
    
    try:
        if capture_output:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, cwd=cwd, timeout=timeout)
            return result.returncode == 0, None, None
    except subprocess.TimeoutExpired:
        log('ERROR', f"Comando excedió timeout de {timeout}s: {cmd_str}")
        return False, None, f"Timeout después de {timeout}s"
    except FileNotFoundError:
        log('ERROR', f"Comando no encontrado: {cmd[0]}")
        return False, None, f"Comando no encontrado: {cmd[0]}"
    except Exception as e:
        log('ERROR', f"Error ejecutando comando: {e}")
        return False, None, str(e)

def check_prerequisites():
    """Verificar prerrequisitos del sistema - VERSIÓN CORREGIDA PARA LINUX"""
    log('INFO', "Verificando prerrequisitos...")
    
    # Verificar Docker Engine (no Docker Desktop)
    success, stdout, stderr = run_command("docker --version", capture_output=True)
    if not success:
        log('ERROR', "Docker no está instalado o no está en el PATH")
        log('INFO', "En Ubuntu/Linux, instala Docker Engine con:")
        log('INFO', "  sudo apt update && sudo apt install docker.io docker-compose")
        log('INFO', "  sudo systemctl start docker")
        log('INFO', "  sudo usermod -aG docker $USER")
        return False
    
    log('SUCCESS', f"Docker encontrado: {stdout.strip()}")
    
    # Verificar Docker Compose (versión nueva o vieja)
    success_new, stdout_new, stderr_new = run_command("docker compose version", capture_output=True)
    success_old, stdout_old, stderr_old = run_command("docker-compose --version", capture_output=True)
    
    if not success_new and not success_old:
        log('ERROR', "Docker Compose no está disponible")
        log('INFO', "Instala Docker Compose con:")
        log('INFO', "  sudo apt install docker-compose")
        return False
    
    if success_new:
        log('SUCCESS', f"Docker Compose (nuevo) encontrado: {stdout_new.strip()}")
    else:
        log('SUCCESS', f"Docker Compose (clásico) encontrado: {stdout_old.strip()}")
    
    # Verificar que Docker daemon esté ejecutándose
    success, stdout, stderr = run_command("docker info", capture_output=True)
    if not success:
        log('ERROR', "Docker daemon no está ejecutándose")
        log('INFO', "Inicia Docker con:")
        log('INFO', "  sudo systemctl start docker")
        log('INFO', "  sudo systemctl enable docker  # Para inicio automático")
        
        # Verificar si es problema de permisos
        if "permission denied" in stderr.lower():
            log('WARNING', "Parece ser un problema de permisos")
            log('INFO', "Ejecuta estos comandos y reinicia tu sesión:")
            log('INFO', "  sudo usermod -aG docker $USER")
            log('INFO', "  newgrp docker")
        
        return False
    
    log('SUCCESS', "Docker daemon está ejecutándose correctamente")
    
    # Verificar permisos de Docker (sin sudo)
    success, stdout, stderr = run_command("docker ps", capture_output=True)
    if not success and "permission denied" in stderr.lower():
        log('WARNING', "Tu usuario no tiene permisos para usar Docker sin sudo")
        log('INFO', "Ejecuta estos comandos y reinicia tu sesión:")
        log('INFO', "  sudo usermod -aG docker $USER")
        log('INFO', "  newgrp docker")
        log('INFO', "O ejecuta el script con sudo (no recomendado)")
        return False
    
    log('SUCCESS', "Permisos de Docker correctos")
    
    # Verificar Python
    python_version = sys.version.split()[0]
    if sys.version_info < (3, 7):
        log('ERROR', f"Python 3.7+ requerido. Versión actual: {python_version}")
        return False
    
    log('SUCCESS', f"Python {python_version} encontrado")
    
    # Verificar conectividad de red para Docker
    success, stdout, stderr = run_command("docker run --rm hello-world", capture_output=True, timeout=60)
    if not success:
        log('WARNING', "Problema ejecutando contenedor de prueba")
        log('DEBUG', f"Error: {stderr}")
        # No es crítico, continuamos
    else:
        log('SUCCESS', "Docker puede ejecutar contenedores correctamente")
    
    log('SUCCESS', "🎉 Todos los prerrequisitos cumplidos")
    return True

def get_project_root():
    """Obtener la ruta raíz del proyecto"""
    return Path(__file__).parent.parent.parent.absolute()

def create_directories():
    """Crear estructura de directorios necesaria"""
    log('INFO', "Creando directorios necesarios...")
    
    project_root = get_project_root()
    dirs = [
        "data/raw/genomes",
        "data/processed",
        "data/uploads", 
        "data/results",
        "data/downloads",
        "data/references",
        "data/intermediate",
        "data/visualizations",
        "logs",
        "tmp"
    ]
    
    for dir_path in dirs:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        log('DEBUG', f"Directorio creado: {dir_path}")
    
    log('SUCCESS', "Estructura de directorios creada")

def create_essential_files():
    """Crear archivos esenciales para los servicios"""
    log('INFO', "Creando archivos esenciales para servicios...")
    
    project_root = get_project_root()
    
    # ===== ARCHIVO DE CONEXIÓN A BASE DE DATOS PARA AUTH =====
    auth_db_dir = project_root / "src/core/auth/database"
    auth_db_dir.mkdir(parents=True, exist_ok=True)
    
    connection_file = auth_db_dir / "connection.js"
    
    if not connection_file.exists():
        log('INFO', "Creando archivo de conexión a MongoDB para auth...")
        
        connection_content = '''const mongoose = require('mongoose');

class DatabaseConnection {
    constructor() {
        this.isConnected = false;
        this.maxRetries = 5;
        this.retryDelay = 5000; // 5 segundos
    }

    async connect() {
        if (this.isConnected) {
            console.log('📦 Base de datos ya conectada');
            return;
        }

        const mongoUri = process.env.MONGODB_URI || 'mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin';
        
        console.log('🔄 Conectando a MongoDB...');
        console.log(`📍 URI: ${mongoUri.replace(/\\/\\/.*@/, '//***:***@')}`); // Ocultar credenciales en logs

        let retries = 0;
        
        while (retries < this.maxRetries) {
            try {
                await mongoose.connect(mongoUri, {
                    serverSelectionTimeoutMS: 10000, // 10 segundos
                    connectTimeoutMS: 10000,
                    socketTimeoutMS: 45000,
                    maxPoolSize: 10,
                    retryWrites: true,
                    w: 'majority'
                });

                this.isConnected = true;
                console.log('✅ Conectado exitosamente a MongoDB');
                
                // Configurar eventos de conexión
                this.setupConnectionEvents();
                
                return;
            } catch (error) {
                retries++;
                console.error(`❌ Error conectando a MongoDB (intento ${retries}/${this.maxRetries}):`, error.message);
                
                if (retries < this.maxRetries) {
                    console.log(`⏳ Reintentando en ${this.retryDelay/1000} segundos...`);
                    await this.delay(this.retryDelay);
                } else {
                    console.error('💥 Máximo número de reintentos alcanzado');
                    throw error;
                }
            }
        }
    }

    setupConnectionEvents() {
        mongoose.connection.on('error', (error) => {
            console.error('❌ Error de conexión MongoDB:', error);
            this.isConnected = false;
        });

        mongoose.connection.on('disconnected', () => {
            console.warn('⚠️ Desconectado de MongoDB');
            this.isConnected = false;
        });

        mongoose.connection.on('reconnected', () => {
            console.log('🔄 Reconectado a MongoDB');
            this.isConnected = true;
        });

        // Cerrar conexión cuando la aplicación se cierra
        process.on('SIGINT', async () => {
            console.log('🛑 Cerrando conexión a MongoDB...');
            await mongoose.connection.close();
            process.exit(0);
        });
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async disconnect() {
        if (this.isConnected) {
            await mongoose.connection.close();
            this.isConnected = false;
            console.log('🔌 Desconectado de MongoDB');
        }
    }

    getStatus() {
        return {
            connected: this.isConnected,
            readyState: mongoose.connection.readyState,
            host: mongoose.connection.host,
            port: mongoose.connection.port,
            name: mongoose.connection.name
        };
    }
}

// Exportar instancia singleton
const dbConnection = new DatabaseConnection();
module.exports = dbConnection;
'''
        
        with open(connection_file, 'w', encoding='utf-8') as f:
            f.write(connection_content)
        
        log('SUCCESS', f"✅ Archivo de conexión MongoDB creado: {connection_file.relative_to(project_root)}")
    else:
        log('DEBUG', "Archivo de conexión MongoDB ya existe")
    
    # ===== ARCHIVO .DOCKERIGNORE PARA OPTIMIZAR BUILDS =====
    dockerignore_file = project_root / ".dockerignore"
    if not dockerignore_file.exists():
        log('INFO', "Creando archivo .dockerignore...")
        
        dockerignore_content = '''# Archivos de desarrollo
node_modules
npm-debug.log*
.env.local
.env.development.local
.env.test.local
.env.production.local

# Archivos temporales
.tmp/
tmp/
logs/
*.log

# Archivos de datos (demasiado grandes)
data/raw/
data/processed/
data/uploads/
data/downloads/

# Git
.git/
.gitignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Documentación
docs/
README.md
*.md
'''
        
        with open(dockerignore_file, 'w', encoding='utf-8') as f:
            f.write(dockerignore_content)
        
        log('SUCCESS', "✅ Archivo .dockerignore creado")
    else:
        log('DEBUG', "Archivo .dockerignore ya existe")
    
    log('SUCCESS', "🎉 Archivos esenciales creados correctamente")

def cleanup_previous_installation():
    """Limpiar instalación previa"""
    log('INFO', "Limpiando instalación previa...")
    
    project_root = get_project_root()
    
    # Detener contenedores existentes
    run_command([
        "docker", "compose", "-p", "fungigt", 
        "-f", str(project_root / "docker-compose.yml"),
        "down", "--remove-orphans", "--volumes"
    ], cwd=project_root)
    
    # Limpiar imágenes huérfanas
    run_command("docker system prune -f", capture_output=True)
    
    log('SUCCESS', "Limpieza completada")

def build_service_with_retry(service_name, max_retries=3):
    """Construir servicio individual con reintentos"""
    project_root = get_project_root()
    
    for attempt in range(max_retries):
        log('INFO', f"Construyendo {service_name} (intento {attempt + 1}/{max_retries})")
        
        success, _, stderr = run_command([
            "docker", "compose", "-p", "fungigt",
            "-f", str(project_root / "docker-compose.yml"),
            "build", "--no-cache", service_name
        ], cwd=project_root, capture_output=True, timeout=600)
        
        if success:
            log('SUCCESS', f"✅ {service_name} construido exitosamente")
            return True
        else:
            log('WARNING', f"❌ Fallo construyendo {service_name}")
            if stderr:
                log('DEBUG', f"Error: {stderr}")
            
            if attempt < max_retries - 1:
                log('INFO', f"Reintentando en 10 segundos...")
                time.sleep(10)
    
    log('ERROR', f"❌ Falló la construcción de {service_name} después de {max_retries} intentos")
    return False

def build_all_services():
    """Construir todos los servicios en orden de dependencia"""
    log('INFO', "Iniciando construcción de servicios...")
    
    # Orden de construcción basado en dependencias
    services = [
        "auth",
        "file-manager", 
        "frontend",
        "visualization",
        "quality-control",
        "acquisition",
        "bindash-analysis"
    ]
    
    failed_services = []
    
    for service in services:
        if not build_service_with_retry(service):
            failed_services.append(service)
    
    if failed_services:
        log('ERROR', f"❌ Servicios que fallaron: {', '.join(failed_services)}")
        return False
    
    log('SUCCESS', "🎉 Todos los servicios construidos exitosamente")
    return True

def wait_for_service_health(service_name, port, timeout=120):
    """Esperar a que un servicio esté saludable"""
    log('INFO', f"Esperando que {service_name} esté listo...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                log('SUCCESS', f"✅ {service_name} está listo")
                return True
        except:
            pass
        
        time.sleep(5)
    
    log('WARNING', f"⚠️ {service_name} no respondió en {timeout}s")
    return False

def start_services():
    """Iniciar todos los servicios"""
    log('INFO', "Iniciando servicios...")
    
    project_root = get_project_root()
    
    # Iniciar servicios
    success, _, stderr = run_command([
        "docker", "compose", "-p", "fungigt",
        "-f", str(project_root / "docker-compose.yml"),
        "up", "-d"
    ], cwd=project_root, capture_output=True, timeout=300)
    
    if not success:
        log('ERROR', f"Error iniciando servicios: {stderr}")
        return False
    
    log('SUCCESS', "Servicios iniciados")
    
    # Esperar a que los servicios estén listos
    services_to_check = [
        ("mongodb", 27017),
        ("auth", 4001),
        ("file-manager", 4002),
        ("visualization", 4003), 
        ("quality-control", 4004),
        ("frontend", 4005),
        ("acquisition", 4006),
        ("bindash-analysis", 4007)
    ]
    
    log('INFO', "Verificando estado de servicios...")
    for service, port in services_to_check:
        if service == "mongodb":
            # MongoDB no tiene endpoint /health, verificar de otra manera
            time.sleep(10)
            continue
        wait_for_service_health(service, port)
    
    return True

def show_service_status():
    """Mostrar estado de todos los servicios"""
    log('INFO', "Estado de los servicios:")
    
    project_root = get_project_root()
    
    success, stdout, stderr = run_command([
        "docker", "compose", "-p", "fungigt",
        "-f", str(project_root / "docker-compose.yml"),
        "ps"
    ], cwd=project_root, capture_output=True)
    
    if success and stdout:
        print(f"{Colors.WHITE}{stdout}{Colors.END}")
    
    # URLs de acceso
    urls = [
        ("🌐 Frontend Principal", "http://localhost:4005"),
        ("🔐 Servicio de Autenticación", "http://localhost:4001/health"),
        ("📁 Gestor de Archivos", "http://localhost:4002/health"),
        ("📊 Visualización", "http://localhost:4003/health"),
        ("🔍 Control de Calidad", "http://localhost:4004/health"),
        ("📥 Adquisición de Datos", "http://localhost:4006"),
        ("🧬 Análisis Bindash", "http://localhost:4007/health"),
        ("🗄️ MongoDB", "mongodb://localhost:27017/fungigt")
    ]
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 FungiGT instalado exitosamente!{Colors.END}")
    print(f"{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
    print(f"{Colors.CYAN}📋 URLs de Acceso:{Colors.END}")
    
    for name, url in urls:
        print(f"  {name}: {Colors.BLUE}{url}{Colors.END}")
    
    print(f"\n{Colors.YELLOW}👤 Credenciales por defecto:{Colors.END}")
    print(f"  Email: {Colors.WHITE}admin@fungigt.com{Colors.END}")
    print(f"  Password: {Colors.WHITE}admin123{Colors.END}")
    
    print(f"\n{Colors.MAGENTA}🛠️ Comandos útiles:{Colors.END}")
    print(f"  Ver logs: {Colors.WHITE}docker compose -p fungigt logs -f{Colors.END}")
    print(f"  Detener: {Colors.WHITE}python scripts/setup/stop_services.py{Colors.END}")
    print(f"  Reiniciar: {Colors.WHITE}python scripts/setup/setup_fungigt.py --restart{Colors.END}")

def create_env_file():
    """Crear archivo .env con configuraciones por defecto"""
    log('INFO', "Creando archivo de configuración...")
    
    project_root = get_project_root()
    env_file = project_root / ".env"
    
    # Detectar sistema operativo y configurar variables específicas
    system = platform.system().lower()
    log('INFO', f"Sistema operativo detectado: {system}")
    
    # Configurar variables específicas para Linux
    docker_user = "1000:1000"  # Por defecto
    docker_group = "999"       # Por defecto
    
    if system == "linux":
        log('INFO', "Configurando variables específicas para Linux...")
        try:
            # Obtener UID y GID del usuario actual
            import pwd
            import grp
            uid = os.getuid()
            gid = os.getgid()
            docker_user = f"{uid}:{gid}"
            log('DEBUG', f"Usuario actual: UID={uid}, GID={gid}")
            
            # Intentar obtener el GID del grupo docker
            try:
                docker_grp = grp.getgrnam('docker')
                docker_group = str(docker_grp.gr_gid)
                log('DEBUG', f"Grupo docker encontrado: GID={docker_group}")
            except KeyError:
                log('WARNING', "Grupo 'docker' no encontrado, usando GID por defecto")
                docker_group = "999"
        except Exception as e:
            log('WARNING', f"Error obteniendo información del usuario: {e}")
    
    env_content = f"""# Configuración de FungiGT
# Sistema operativo: {system}

# Puertos de servicios
FRONTEND_PORT=4005
AUTH_PORT=4001

# Base de datos MongoDB
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=admin123
MONGO_DATABASE=fungigt
MONGODB_URI=mongodb://mongodb:27017/fungigt

# Autenticación
JWT_SECRET=fungi-gt-secret-key-2024-auto-generated
SESSION_SECRET=fungi-gt-session-secret-2024

# Entorno
NODE_ENV=development

# Data directory
DATA_DIR=./data

# Configuración específica para Docker (Linux)
DOCKER_USER={docker_user}
DOCKER_GROUP={docker_group}

# Variables de compatibilidad
COMPOSE_CONVERT_WINDOWS_PATHS=1
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    log('SUCCESS', f"Archivo .env creado para {system}")
    
    # Mostrar información específica de Linux
    if system == "linux":
        log('INFO', "📋 Información para Linux:")
        log('INFO', f"  • Usuario Docker: {docker_user}")
        log('INFO', f"  • Grupo Docker: {docker_group}")
        log('INFO', "  • Asegúrate de que tu usuario esté en el grupo 'docker':")
        log('INFO', "    sudo usermod -aG docker $USER")
        log('INFO', "    (reinicia la sesión después de este comando)")

def handle_interrupt(signum, frame):
    """Manejar interrupción del usuario"""
    print(f"\n{Colors.YELLOW}🛑 Instalación interrumpida por el usuario{Colors.END}")
    log('INFO', "Limpiando...")
    cleanup_previous_installation()
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='FungiGT - Script de Autoinstalación')
    parser.add_argument('--restart', action='store_true', help='Reiniciar servicios existentes')
    parser.add_argument('--clean', action='store_true', help='Limpieza completa antes de instalar')
    parser.add_argument('--skip-build', action='store_true', help='Saltar construcción de imágenes')
    parser.add_argument('--start-services', action='store_true', help='Iniciar servicios después de construir (por defecto NO)')
    parser.add_argument('--prepare-only', action='store_true', help='Solo preparar archivos y construir, no iniciar servicios')
    args = parser.parse_args()
    
    # Manejar Ctrl+C
    signal.signal(signal.SIGINT, handle_interrupt)
    
    print_banner()
    
    try:
        # Verificar prerrequisitos
        if not check_prerequisites():
            log('ERROR', "❌ Prerrequisitos no cumplidos")
            return 1
        
        # Crear directorios
        create_directories()
        
        # Crear archivos esenciales (NUEVO - incluye database/connection.js)
        create_essential_files()
        
        # Crear archivo .env
        create_env_file()
        
        # Limpieza opcional
        if args.clean or args.restart:
            cleanup_previous_installation()
        
        # Construir servicios
        if not args.skip_build:
            if not build_all_services():
                log('ERROR', "❌ Error en la construcción de servicios")
                return 1
        
        # Solo iniciar servicios si se solicita explícitamente
        if args.start_services and not args.prepare_only:
            log('INFO', "Iniciando servicios...")
            if not start_services():
                log('ERROR', "❌ Error iniciando servicios")
                return 1
            # Mostrar estado
            show_service_status()
        else:
            log('SUCCESS', "🎉 Preparación completada exitosamente")
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ FungiGT preparado correctamente{Colors.END}")
            print(f"{Colors.CYAN}📋 Para iniciar servicios, ejecuta:{Colors.END}")
            print(f"  {Colors.WHITE}python scripts/setup/start_services.py{Colors.END}")
            print(f"\n{Colors.CYAN}📋 O ejecuta servicios individuales:{Colors.END}")
            print(f"  {Colors.WHITE}docker compose -p fungigt up -d mongodb auth frontend{Colors.END}")
        
        return 0
        
    except KeyboardInterrupt:
        handle_interrupt(None, None)
    except Exception as e:
        log('ERROR', f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 