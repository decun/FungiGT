#!/usr/bin/env python3
"""
FungiGT - Inicio Rápido
=======================

Script para iniciar rápidamente FungiGT (para usuarios que ya lo tienen instalado)
Ejecuta: python scripts/setup/quick_start.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path

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

def log(level, message):
    """Logger con colores"""
    timestamp = time.strftime("%H:%M:%S")
    colors = {
        'INFO': Colors.CYAN,
        'SUCCESS': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{Colors.WHITE}[{timestamp}]{Colors.END} {color}[{level}]{Colors.END} {message}")

def run_command(cmd, cwd=None, capture_output=False):
    """Ejecutar comando"""
    try:
        if capture_output:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, cwd=cwd)
            return result.returncode == 0, None, None
    except Exception as e:
        log('ERROR', f"Error ejecutando comando: {e}")
        return False, None, str(e)

def get_project_root():
    """Obtener la ruta raíz del proyecto"""
    return Path(__file__).parent.parent.parent.absolute()

def check_docker():
    """Verificar que Docker esté disponible"""
    success, _, _ = run_command(["docker", "info"], capture_output=True)
    return success

def start_services():
    """Iniciar servicios de FungiGT"""
    project_root = get_project_root()
    compose_file = project_root / "docker-compose.yml"
    
    if not compose_file.exists():
        log('ERROR', f"No se encuentra docker-compose.yml. Ejecuta primero: python scripts/setup/setup_fungigt.py")
        return False
    
    log('INFO', "Iniciando servicios de FungiGT...")
    
    success, _, stderr = run_command([
        "docker", "compose", "-p", "fungigt",
        "-f", str(compose_file),
        "up", "-d"
    ], cwd=project_root, capture_output=True)
    
    if success:
        log('SUCCESS', "✅ Servicios iniciados")
        return True
    else:
        log('ERROR', f"❌ Error iniciando servicios: {stderr}")
        return False

def show_status():
    """Mostrar estado de servicios"""
    project_root = get_project_root()
    
    success, stdout, _ = run_command([
        "docker", "compose", "-p", "fungigt", "ps"
    ], cwd=project_root, capture_output=True)
    
    if success and stdout:
        print(f"\n{Colors.CYAN}📊 Estado de los servicios:{Colors.END}")
        print(f"{Colors.WHITE}{stdout}{Colors.END}")

def show_access_info():
    """Mostrar información de acceso"""
    urls = [
        ("🌐 Frontend Principal", "http://localhost:4005"),
        ("🔐 Autenticación", "http://localhost:4001/health"),
        ("📁 Gestión de Archivos", "http://localhost:4002/health"),
        ("📊 Visualización", "http://localhost:4003/health"),
        ("🔍 Control de Calidad", "http://localhost:4004/health"),
        ("📥 Adquisición de Datos", "http://localhost:4006")
    ]
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 FungiGT está ejecutándose!{Colors.END}")
    print(f"{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
    print(f"{Colors.CYAN}📋 URLs de Acceso:{Colors.END}")
    
    for name, url in urls:
        print(f"  {name}: {Colors.BLUE}{url}{Colors.END}")
    
    print(f"\n{Colors.YELLOW}👤 Credenciales por defecto:{Colors.END}")
    print(f"  Email: {Colors.WHITE}admin@fungigt.com{Colors.END}")
    print(f"  Password: {Colors.WHITE}admin123{Colors.END}")

def print_banner():
    """Banner de inicio rápido"""
    banner = f"""
{Colors.GREEN}{Colors.BOLD}
⚡ FungiGT - Inicio Rápido
{Colors.END}
{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
"""
    print(banner)

def main():
    print_banner()
    
    try:
        # Verificar Docker
        if not check_docker():
            log('ERROR', "Docker no está ejecutándose. Inicia Docker Desktop.")
            return 1
        
        # Iniciar servicios
        if not start_services():
            log('ERROR', "❌ Error iniciando servicios")
            log('INFO', "💡 Intenta ejecutar: python scripts/setup/setup_fungigt.py")
            return 1
        
        # Esperar un momento para que los servicios se inicien
        log('INFO', "Esperando que los servicios se inicien...")
        time.sleep(10)
        
        # Mostrar estado y acceso
        show_status()
        show_access_info()
        
        print(f"\n{Colors.MAGENTA}🛠️ Comandos útiles:{Colors.END}")
        print(f"  Ver logs: {Colors.WHITE}docker compose -p fungigt logs -f{Colors.END}")
        print(f"  Detener: {Colors.WHITE}python scripts/setup/stop_services.py{Colors.END}")
        print(f"  Reinstalar: {Colors.WHITE}python scripts/setup/setup_fungigt.py --clean{Colors.END}")
        
        return 0
        
    except KeyboardInterrupt:
        log('WARNING', "🛑 Operación interrumpida")
        return 1
    except Exception as e:
        log('ERROR', f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 