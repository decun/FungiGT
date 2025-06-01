#!/usr/bin/env python3
"""
FungiGT - Script de Detención de Servicios
==========================================

Este script detiene todos los servicios de FungiGT de manera segura.
"""

import os
import sys
import subprocess
import argparse
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
        'ERROR': Colors.RED,
        'DEBUG': Colors.MAGENTA
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{Colors.WHITE}[{timestamp}]{Colors.END} {color}[{level}]{Colors.END} {message}")

def run_command(cmd, cwd=None, capture_output=False):
    """Ejecutar comando"""
    if isinstance(cmd, str):
        cmd_str = cmd
        cmd = cmd.split()
    else:
        cmd_str = ' '.join(cmd)
    
    log('DEBUG', f"Ejecutando: {cmd_str}")
    
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

def stop_services(remove_volumes=False, remove_images=False):
    """Detener servicios de FungiGT"""
    project_root = get_project_root()
    compose_file = project_root / "docker-compose.yml"
    
    if not compose_file.exists():
        log('ERROR', f"No se encuentra docker-compose.yml en {compose_file}")
        return False
    
    log('INFO', "Deteniendo servicios de FungiGT...")
    
    # Comando base para detener servicios
    cmd = [
        "docker", "compose", "-p", "fungigt",
        "-f", str(compose_file),
        "down", "--remove-orphans"
    ]
    
    # Agregar opciones adicionales
    if remove_volumes:
        cmd.append("--volumes")
        log('INFO', "Se eliminarán también los volúmenes de datos")
    
    if remove_images:
        cmd.append("--rmi")
        cmd.append("all")
        log('INFO', "Se eliminarán también las imágenes")
    
    # Ejecutar comando
    success, stdout, stderr = run_command(cmd, cwd=project_root, capture_output=True)
    
    if success:
        log('SUCCESS', "✅ Servicios detenidos exitosamente")
        if stdout:
            print(f"{Colors.WHITE}{stdout}{Colors.END}")
        return True
    else:
        log('ERROR', f"❌ Error deteniendo servicios: {stderr}")
        return False

def cleanup_docker_system():
    """Limpiar sistema Docker"""
    log('INFO', "Limpiando sistema Docker...")
    
    # Limpiar contenedores, redes, imágenes y caché
    success, _, _ = run_command("docker system prune -f", capture_output=True)
    
    if success:
        log('SUCCESS', "✅ Sistema Docker limpiado")
    else:
        log('WARNING', "⚠️ No se pudo limpiar completamente el sistema Docker")

def show_remaining_containers():
    """Mostrar contenedores que siguen ejecutándose"""
    log('INFO', "Verificando contenedores restantes...")
    
    success, stdout, stderr = run_command([
        "docker", "ps", "--filter", "name=fungigt"
    ], capture_output=True)
    
    if success and stdout.strip():
        lines = stdout.strip().split('\n')
        if len(lines) > 1:  # Más que solo el header
            log('WARNING', "⚠️ Algunos contenedores de FungiGT siguen ejecutándose:")
            print(f"{Colors.YELLOW}{stdout}{Colors.END}")
        else:
            log('SUCCESS', "✅ No hay contenedores de FungiGT ejecutándose")
    else:
        log('SUCCESS', "✅ No hay contenedores de FungiGT ejecutándose")

def force_stop_containers():
    """Forzar detención de contenedores específicos de FungiGT"""
    log('INFO', "Forzando detención de contenedores de FungiGT...")
    
    containers = [
        "fungigt-frontend",
        "fungigt-auth", 
        "fungigt-file-manager",
        "fungigt-visualization",
        "fungigt-quality-control",
        "fungigt-acquisition",
        "fungigt-annotation",
        "fungigt-mongodb"
    ]
    
    for container in containers:
        # Intentar detener
        success, _, _ = run_command(f"docker stop {container}", capture_output=True)
        if success:
            log('DEBUG', f"Contenedor {container} detenido")
        
        # Intentar eliminar
        success, _, _ = run_command(f"docker rm {container}", capture_output=True)
        if success:
            log('DEBUG', f"Contenedor {container} eliminado")

def print_banner():
    """Mostrar banner"""
    banner = f"""
{Colors.RED}{Colors.BOLD}
🛑 FungiGT - Detener Servicios
{Colors.END}
{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
"""
    print(banner)

def main():
    parser = argparse.ArgumentParser(description='Detener servicios de FungiGT')
    parser.add_argument('--remove-volumes', action='store_true',
                       help='Eliminar también los volúmenes de datos (⚠️ PELIGROSO)')
    parser.add_argument('--remove-images', action='store_true',
                       help='Eliminar también las imágenes Docker')
    parser.add_argument('--force', action='store_true',
                       help='Forzar detención de contenedores específicos')
    parser.add_argument('--cleanup', action='store_true',
                       help='Limpiar sistema Docker después de detener')
    args = parser.parse_args()
    
    print_banner()
    
    try:
        # Advertencia para operaciones destructivas
        if args.remove_volumes:
            log('WARNING', "⚠️ ADVERTENCIA: Se eliminarán TODOS los datos de la base de datos")
            confirm = input(f"{Colors.YELLOW}¿Estás seguro? Escribe 'SI' para continuar: {Colors.END}")
            if confirm.upper() != 'SI':
                log('INFO', "Operación cancelada")
                return 0
        
        # Detener servicios normalmente
        if not stop_services(args.remove_volumes, args.remove_images):
            if args.force:
                log('INFO', "Detención normal falló, intentando detención forzada...")
                force_stop_containers()
            else:
                log('ERROR', "❌ Error deteniendo servicios. Usa --force para forzar detención")
                return 1
        
        # Limpiar sistema si se solicita
        if args.cleanup:
            cleanup_docker_system()
        
        # Mostrar estado final
        show_remaining_containers()
        
        log('SUCCESS', "🎉 Detención completada")
        
        # Mostrar comandos para reiniciar
        print(f"\n{Colors.CYAN}🔄 Para reiniciar FungiGT:{Colors.END}")
        print(f"  {Colors.WHITE}python scripts/setup/setup_fungigt.py{Colors.END}")
        print(f"  {Colors.WHITE}python scripts/setup/setup_fungigt.py --restart{Colors.END}")
        
        return 0
        
    except KeyboardInterrupt:
        log('WARNING', "🛑 Operación interrumpida por el usuario")
        return 1
    except Exception as e:
        log('ERROR', f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())