#!/usr/bin/env python3
"""
start_services.py

Este script inicia todos los servicios de FungiGT usando Docker Compose.
Maneja dependencias y puede continuar aunque algunos servicios fallen.
Soporta profiles para servicios de herramientas bioinformáticas.
"""

import os
import subprocess
import time
import argparse
import sys
from pathlib import Path

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(level, message):
    """Logger con colores"""
    colors = {
        'INFO': Colors.CYAN,
        'SUCCESS': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{color}[{level}]{Colors.END} {message}")

def run_command(cmd, cwd=None, capture_output=True):
    """Ejecutar comando con manejo de errores"""
    try:
        if capture_output:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, cwd=cwd, timeout=180)
            return result.returncode == 0, None, None
    except subprocess.TimeoutExpired:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, str(e)

def get_project_root():
    """Obtener la ruta a la raíz del proyecto."""
    return Path(__file__).parent.parent.parent.absolute()

def check_service_running(service_name):
    """Verificar si un servicio está ejecutándose"""
    project_root = get_project_root()
    success, stdout, stderr = run_command([
        "docker", "compose", "-p", "fungigt", "ps", service_name
    ], cwd=project_root)
    
    if success and stdout:
        return "running" in stdout.lower() or "up" in stdout.lower()
    return False

def start_service_individual(service_name, max_retries=2, use_tools_profile=False):
    """Iniciar un servicio individual con reintentos"""
    project_root = get_project_root()
    
    for attempt in range(max_retries):
        log('INFO', f"🚀 Iniciando {service_name} (intento {attempt + 1}/{max_retries})")
        
        cmd = [
            "docker", "compose", "-p", "fungigt",
            "-f", str(project_root / "docker-compose.yml")
        ]
        
        # Agregar profile si es necesario
        if use_tools_profile:
            cmd.extend(["--profile", "tools"])
        
        cmd.extend(["up", "-d", service_name])
        
        success, stdout, stderr = run_command(cmd, cwd=project_root)
        
        if success:
            # Esperar un poco y verificar estado
            time.sleep(5)
            if check_service_running(service_name):
                log('SUCCESS', f"✅ {service_name} iniciado correctamente")
                return True
            else:
                log('WARNING', f"⚠️ {service_name} no responde correctamente")
        else:
            log('WARNING', f"❌ Error iniciando {service_name}: {stderr}")
            if attempt < max_retries - 1:
                log('INFO', f"⏳ Reintentando en 5 segundos...")
                time.sleep(5)
    
    log('ERROR', f"💥 No se pudo iniciar {service_name} después de {max_retries} intentos")
    return False

def start_services_ordered(services_to_start=None, skip_failed=True, include_tools=False):
    """Iniciar servicios en orden de dependencia"""
    # Servicios principales (ACTUALIZADO - incluir file-manager)
    main_services = [
        "mongodb",           # Base de datos primero
        "auth",             # Autenticación
        "file-manager",     # Gestor de archivos (MOVIDO AQUÍ TEMPRANO)
        "frontend",         # Frontend principal
        "visualization",    # Visualización
        "quality-control",  # Control de calidad
        "acquisition",      # Adquisición de datos
    ]
    
    # Servicios de herramientas bioinformáticas
    tool_services = [
        "annotation",        # BRAKER3
        "checkm",           # CheckM
        "functional-analysis", # EggNOG
        "phylogeny"         # BLAST
    ]
    
    # Si no se especifican servicios, usar configuración por defecto (ACTUALIZADO)
    if services_to_start is None:
        # AHORA incluye file-manager por defecto
        services_to_start = main_services.copy()
        if include_tools:
            services_to_start.extend(tool_services)
    
    log('INFO', f"🎯 Iniciando servicios: {', '.join(services_to_start)}")
    
    successful_services = []
    failed_services = []
    
    for service in services_to_start:
        use_tools_profile = service in tool_services
        
        if start_service_individual(service, use_tools_profile=use_tools_profile):
            successful_services.append(service)
        else:
            failed_services.append(service)
            if not skip_failed:
                log('ERROR', f"💥 Deteniendo debido a fallo en {service}")
                return False, successful_services, failed_services
    
    return len(failed_services) == 0, successful_services, failed_services

def show_services_status():
    """Mostrar estado de todos los servicios"""
    project_root = get_project_root()
    
    log('INFO', "📊 Estado de servicios de FungiGT:")
    
    # Mostrar servicios principales
    success, stdout, stderr = run_command([
        "docker", "compose", "-p", "fungigt", "ps"
    ], cwd=project_root)
    
    if success and stdout:
        print(f"\n{Colors.WHITE}=== SERVICIOS PRINCIPALES ==={Colors.END}")
        print(f"{Colors.WHITE}{stdout}{Colors.END}")
    
    # Mostrar servicios de herramientas si existen
    success, stdout, stderr = run_command([
        "docker", "compose", "-p", "fungigt", "--profile", "tools", "ps"
    ], cwd=project_root)
    
    if success and stdout and "fungigt-" in stdout:
        print(f"\n{Colors.WHITE}=== HERRAMIENTAS BIOINFORMÁTICAS ==={Colors.END}")
        print(f"{Colors.WHITE}{stdout}{Colors.END}")
    
    # URLs de acceso
    urls = [
        ("🌐 Frontend Principal", "http://localhost:4005", "frontend"),
        ("🔐 Autenticación", "http://localhost:4001/health", "auth"),
        ("📊 Visualización", "http://localhost:4003/health", "visualization"),
        ("🔍 Control de Calidad", "http://localhost:4004/health", "quality-control"),
        ("📥 Adquisición", "http://localhost:4006", "acquisition"),
        ("📁 Gestor de Archivos", "http://localhost:4002/health", "file-manager"),
    ]
    
    print(f"\n{Colors.CYAN}📋 URLs de Acceso (solo servicios activos):{Colors.END}")
    for name, url, service in urls:
        if check_service_running(service):
            print(f"  ✅ {name}: {Colors.BLUE}{url}{Colors.END}")
        else:
            print(f"  ❌ {name}: {Colors.RED}No disponible{Colors.END}")

def main():
    parser = argparse.ArgumentParser(description='Iniciar los servicios de FungiGT.')
    parser.add_argument('--all', action='store_true',
                      help='Iniciar TODOS los servicios incluyendo file-manager')
    parser.add_argument('--tools', action='store_true',
                      help='Incluir herramientas bioinformáticas (BRAKER3, CheckM, EggNOG, BLAST)')
    parser.add_argument('--essential', action='store_true',
                      help='Solo servicios esenciales (mongodb, auth, frontend)')
    parser.add_argument('--services', nargs='+',
                      help='Servicios específicos a iniciar')
    parser.add_argument('--stop-on-fail', action='store_true',
                      help='Detener si algún servicio falla (por defecto continúa)')
    args = parser.parse_args()

    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print("   FUNGIGT - INICIAR SERVICIOS")
    print("=" * 60)
    print(f"{Colors.END}")

    # Determinar qué servicios iniciar
    if args.services:
        services_to_start = args.services
        include_tools = any(s in ["annotation", "checkm", "functional-analysis", "phylogeny"] for s in args.services)
    elif args.essential:
        services_to_start = ["mongodb", "auth", "frontend"]
        include_tools = False
    elif args.all:
        services_to_start = None  # Usará todos los servicios principales
        include_tools = args.tools
    else:
        # Por defecto: servicios principales INCLUYENDO file-manager
        services_to_start = ["mongodb", "auth", "file-manager", "frontend", "visualization", "quality-control", "acquisition"]
        include_tools = args.tools
    
    # Iniciar servicios
    try:
        success, successful, failed = start_services_ordered(
            services_to_start, 
            skip_failed=not args.stop_on_fail,
            include_tools=include_tools
        )
        
        # Mostrar resumen
        print(f"\n{Colors.YELLOW}📋 Resumen de Inicio:{Colors.END}")
        print(f"✅ Servicios exitosos: {len(successful)} → {', '.join(successful)}")
        if failed:
            print(f"❌ Servicios fallidos: {len(failed)} → {', '.join(failed)}")
        
        # Mostrar estado actual
        show_services_status()
        
        if successful:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡FungiGT iniciado!{Colors.END}")
            print(f"{Colors.CYAN}👉 Accede al frontend en: {Colors.BLUE}http://localhost:4005{Colors.END}")
            
            if include_tools:
                print(f"\n{Colors.YELLOW}🧬 Herramientas bioinformáticas disponibles:{Colors.END}")
                tools_info = [
                    "🧬 BRAKER3: Anotación automática de genes",
                    "🔍 CheckM: Evaluación de completitud genómica",
                    "📊 EggNOG: Análisis funcional",
                    "🧬 BLAST: Análisis filogenético"
                ]
                for tool in tools_info:
                    print(f"  {tool}")
        else:
            print(f"\n{Colors.RED}💥 No se pudo iniciar ningún servicio{Colors.END}")
            return 1
        
        return 0 if success else 2  # 2 = éxito parcial
        
    except KeyboardInterrupt:
        log('WARNING', "⚠️ Operación cancelada por el usuario")
        return 1

if __name__ == "__main__":
    sys.exit(main())