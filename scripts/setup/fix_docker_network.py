#!/usr/bin/env python3
"""
FungiGT - Solucionador de Problemas de Red Docker
================================================

Script para solucionar errores comunes de red de Docker, especialmente
el error "stream terminated by RST_STREAM with error code: INTERNAL_ERROR"
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
        'ERROR': Colors.RED,
        'DEBUG': Colors.MAGENTA
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{Colors.WHITE}[{timestamp}]{Colors.END} {color}[{level}]{Colors.END} {message}")

def run_command(cmd, cwd=None, capture_output=False, check=False):
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
        if check:
            log('ERROR', f"Error ejecutando comando: {e}")
        return False, None, str(e)

def print_banner():
    """Banner del solucionador"""
    banner = f"""
{Colors.YELLOW}{Colors.BOLD}
🔧 FungiGT - Solucionador de Problemas Docker
{Colors.END}
{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
"""
    print(banner)

def check_docker_resources():
    """Verificar recursos de Docker"""
    log('INFO', "Verificando recursos de Docker...")
    
    success, stdout, stderr = run_command("docker system df", capture_output=True)
    if success:
        log('INFO', "Uso de espacio Docker:")
        print(f"{Colors.WHITE}{stdout}{Colors.END}")
    
    return True

def cleanup_docker_build_cache():
    """Limpiar caché de construcción de Docker"""
    log('INFO', "Limpiando caché de construcción de Docker...")
    
    # Limpiar buildx cache
    run_command("docker buildx prune -f", capture_output=True)
    
    # Limpiar builder cache
    run_command("docker builder prune -f", capture_output=True)
    
    # Limpiar system cache
    run_command("docker system prune -f", capture_output=True)
    
    log('SUCCESS', "✅ Caché de Docker limpiado")

def restart_docker_desktop():
    """Instruir al usuario para reiniciar Docker Desktop"""
    log('WARNING', "🔄 Se recomienda reiniciar Docker Desktop")
    print(f"""
{Colors.YELLOW}Para reiniciar Docker Desktop:{Colors.END}
1. {Colors.WHITE}Haz clic derecho en el ícono de Docker en la bandeja del sistema{Colors.END}
2. {Colors.WHITE}Selecciona "Restart Docker Desktop"{Colors.END}
3. {Colors.WHITE}Espera a que Docker se reinicie completamente{Colors.END}

{Colors.CYAN}O usa PowerShell como administrador:{Colors.END}
{Colors.WHITE}Restart-Service -Name "com.docker.service"{Colors.END}
""")

def increase_docker_resources():
    """Instruir sobre cómo aumentar recursos de Docker"""
    log('INFO', "Verificando configuración de recursos...")
    print(f"""
{Colors.YELLOW}Para aumentar recursos de Docker Desktop:{Colors.END}

1. {Colors.WHITE}Abre Docker Desktop{Colors.END}
2. {Colors.WHITE}Ve a Settings (⚙️) > Resources{Colors.END}
3. {Colors.WHITE}Aumenta la memoria RAM a al menos 4GB{Colors.END}
4. {Colors.WHITE}Aumenta el espacio en disco si es necesario{Colors.END}
5. {Colors.WHITE}Haz clic en "Apply & Restart"{Colors.END}

{Colors.CYAN}Configuración recomendada:{Colors.END}
- {Colors.WHITE}Memory: 4GB+{Colors.END}
- {Colors.WHITE}CPU: 2+ cores{Colors.END}
- {Colors.WHITE}Disk: 10GB+ libres{Colors.END}
""")

def check_network_connectivity():
    """Verificar conectividad de red"""
    log('INFO', "Verificando conectividad de red...")
    
    # Verificar conectividad con Docker Hub
    success, _, _ = run_command("docker pull hello-world", capture_output=True)
    if success:
        log('SUCCESS', "✅ Conectividad con Docker Hub OK")
        # Limpiar imagen de prueba
        run_command("docker rmi hello-world", capture_output=True)
    else:
        log('ERROR', "❌ Problemas de conectividad con Docker Hub")
        log('INFO', "Verifica tu conexión a internet y firewall")

def fix_dns_issues():
    """Solucionar problemas de DNS"""
    log('INFO', "Aplicando soluciones de DNS...")
    
    print(f"""
{Colors.YELLOW}Soluciones para problemas de DNS:{Colors.END}

1. {Colors.WHITE}Configurar DNS en Docker Desktop:{Colors.END}
   - Settings > Docker Engine
   - Agregar: {Colors.CYAN}"dns": ["8.8.8.8", "8.8.4.4"]{Colors.END}

2. {Colors.WHITE}Reiniciar adaptador de red:{Colors.END}
   {Colors.CYAN}ipconfig /flushdns{Colors.END}
   {Colors.CYAN}ipconfig /release{Colors.END}
   {Colors.CYAN}ipconfig /renew{Colors.END}

3. {Colors.WHITE}Verificar proxy/VPN si aplica{Colors.END}
""")

def alternative_build_strategy():
    """Estrategia alternativa de construcción"""
    log('INFO', "Estrategia alternativa para construcción...")
    
    print(f"""
{Colors.GREEN}Estrategia de construcción paso a paso:{Colors.END}

{Colors.CYAN}1. Construir solo un servicio a la vez:{Colors.END}
{Colors.WHITE}docker compose -p fungigt build auth{Colors.END}
{Colors.WHITE}docker compose -p fungigt build file-manager{Colors.END}

{Colors.CYAN}2. Usar construcción sin caché:{Colors.END}
{Colors.WHITE}docker compose -p fungigt build --no-cache file-manager{Colors.END}

{Colors.CYAN}3. Construir con más memoria:{Colors.END}
{Colors.WHITE}docker compose -p fungigt build --memory=2g file-manager{Colors.END}

{Colors.CYAN}4. Si persiste, usar imágenes base simples:{Colors.END}
{Colors.WHITE}# Editar Dockerfile para usar alpine en lugar de ubuntu{Colors.END}
""")

def run_quick_fix():
    """Ejecutar solución rápida automática"""
    log('INFO', "Ejecutando solución rápida automática...")
    
    # 1. Limpiar caché
    cleanup_docker_build_cache()
    
    # 2. Verificar espacio
    check_docker_resources()
    
    # 3. Verificar conectividad
    check_network_connectivity()
    
    log('SUCCESS', "✅ Solución rápida completada")

def manual_build_services():
    """Construcción manual paso a paso"""
    log('INFO', "Iniciando construcción manual paso a paso...")
    
    project_root = Path(__file__).parent.parent.parent.absolute()
    services = ["auth", "file-manager", "frontend", "visualization", "quality-control", "acquisition"]
    
    for service in services:
        print(f"\n{Colors.CYAN}Construyendo {service}...{Colors.END}")
        
        success, stdout, stderr = run_command([
            "docker", "compose", "-p", "fungigt",
            "-f", str(project_root / "docker-compose.yml"),
            "build", service
        ], cwd=project_root, capture_output=True)
        
        if success:
            log('SUCCESS', f"✅ {service} construido exitosamente")
        else:
            log('ERROR', f"❌ Error construyendo {service}")
            if stderr:
                print(f"{Colors.RED}{stderr}{Colors.END}")
            
            user_input = input(f"{Colors.YELLOW}¿Continuar con el siguiente servicio? (s/N): {Colors.END}")
            if user_input.lower() != 's':
                break

def main():
    print_banner()
    
    print(f"""
{Colors.CYAN}Selecciona una opción:{Colors.END}

{Colors.WHITE}1.{Colors.END} Solución rápida automática
{Colors.WHITE}2.{Colors.END} Limpiar caché de Docker
{Colors.WHITE}3.{Colors.END} Verificar recursos de Docker
{Colors.WHITE}4.{Colors.END} Mostrar cómo aumentar recursos
{Colors.WHITE}5.{Colors.END} Verificar conectividad de red
{Colors.WHITE}6.{Colors.END} Solucionar problemas de DNS
{Colors.WHITE}7.{Colors.END} Estrategia de construcción alternativa
{Colors.WHITE}8.{Colors.END} Construcción manual paso a paso
{Colors.WHITE}9.{Colors.END} Instrucciones para reiniciar Docker
{Colors.WHITE}0.{Colors.END} Salir
""")
    
    try:
        choice = input(f"{Colors.YELLOW}Selecciona una opción (1-9, 0 para salir): {Colors.END}")
        
        if choice == "1":
            run_quick_fix()
        elif choice == "2":
            cleanup_docker_build_cache()
        elif choice == "3":
            check_docker_resources()
        elif choice == "4":
            increase_docker_resources()
        elif choice == "5":
            check_network_connectivity()
        elif choice == "6":
            fix_dns_issues()
        elif choice == "7":
            alternative_build_strategy()
        elif choice == "8":
            manual_build_services()
        elif choice == "9":
            restart_docker_desktop()
        elif choice == "0":
            log('INFO', "Saliendo...")
            return 0
        else:
            log('ERROR', "Opción no válida")
            return 1
            
        print(f"\n{Colors.GREEN}Después de aplicar las soluciones, intenta:{Colors.END}")
        print(f"{Colors.WHITE}python scripts/setup/setup_fungigt.py --restart{Colors.END}")
        
        return 0
        
    except KeyboardInterrupt:
        log('WARNING', "🛑 Operación interrumpida")
        return 1
    except Exception as e:
        log('ERROR', f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 