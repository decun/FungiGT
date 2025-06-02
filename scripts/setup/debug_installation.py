#!/usr/bin/env python3
"""
FungiGT - Debug de Instalación
==============================

Script para debuggear instalaciones parciales y gestionar el estado de FungiGT.
Ayuda a entender qué se mantiene, qué se limpia y cómo debuggear efectivamente.
"""

import os
import sys
import subprocess
import time
import json
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

def run_command(cmd, cwd=None, capture_output=True):
    """Ejecutar comando"""
    try:
        if isinstance(cmd, str):
            cmd = cmd.split()
        result = subprocess.run(cmd, cwd=cwd, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, None, str(e)

def print_banner():
    """Banner de debugging"""
    banner = f"""
{Colors.MAGENTA}{Colors.BOLD}
🔍 FungiGT - Debug de Instalación
{Colors.END}
{Colors.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}
"""
    print(banner)

def get_project_root():
    """Obtener la ruta raíz del proyecto"""
    return Path(__file__).parent.parent.parent.absolute()

def check_installation_state():
    """Verificar estado actual de la instalación"""
    log('INFO', "Verificando estado de la instalación...")
    
    project_root = get_project_root()
    state = {
        'directories': {},
        'docker_images': {},
        'docker_containers': {},
        'docker_volumes': {},
        'config_files': {}
    }
    
    # Verificar directorios
    dirs_to_check = [
        "data", "data/raw", "data/uploads", "data/results", 
        "logs", "tmp", "src", "scripts", "infrastructure"
    ]
    
    for dir_path in dirs_to_check:
        full_path = project_root / dir_path
        state['directories'][dir_path] = {
            'exists': full_path.exists(),
            'is_dir': full_path.is_dir() if full_path.exists() else False,
            'size_items': len(list(full_path.iterdir())) if full_path.exists() and full_path.is_dir() else 0
        }
    
    # Verificar archivos de configuración
    config_files = [".env", "docker-compose.yml", "scripts/mongo-init/init-db.js"]
    
    for file_path in config_files:
        full_path = project_root / file_path
        state['config_files'][file_path] = {
            'exists': full_path.exists(),
            'size_bytes': full_path.stat().st_size if full_path.exists() else 0
        }
    
    # Verificar imágenes Docker
    success, stdout, stderr = run_command("docker images --format json")
    if success:
        for line in stdout.strip().split('\n'):
            if line:
                try:
                    image_info = json.loads(line)
                    if 'fungigt' in image_info.get('Repository', '') or 'fungigt' in image_info.get('Tag', ''):
                        state['docker_images'][image_info['Repository']] = {
                            'tag': image_info['Tag'],
                            'size': image_info['Size'],
                            'created': image_info['CreatedAt']
                        }
                except:
                    pass
    
    # Verificar contenedores Docker
    success, stdout, stderr = run_command("docker ps -a --filter name=fungigt --format json")
    if success:
        for line in stdout.strip().split('\n'):
            if line:
                try:
                    container_info = json.loads(line)
                    state['docker_containers'][container_info['Names']] = {
                        'status': container_info['State'],
                        'image': container_info['Image'],
                        'ports': container_info.get('Ports', '')
                    }
                except:
                    pass
    
    # Verificar volúmenes Docker
    success, stdout, stderr = run_command("docker volume ls --filter name=fungigt --format json")
    if success:
        for line in stdout.strip().split('\n'):
            if line:
                try:
                    volume_info = json.loads(line)
                    state['docker_volumes'][volume_info['Name']] = {
                        'driver': volume_info['Driver'],
                        'mountpoint': volume_info.get('Mountpoint', 'N/A')
                    }
                except:
                    pass
    
    return state

def show_installation_state(state):
    """Mostrar estado detallado de la instalación"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}📊 Estado de la Instalación:{Colors.END}")
    
    # Directorios
    print(f"\n{Colors.YELLOW}📁 Directorios:{Colors.END}")
    for dir_path, info in state['directories'].items():
        status = "✅" if info['exists'] else "❌"
        items = f"({info['size_items']} items)" if info['exists'] else ""
        print(f"  {status} {dir_path} {items}")
    
    # Archivos de configuración
    print(f"\n{Colors.YELLOW}⚙️ Archivos de Configuración:{Colors.END}")
    for file_path, info in state['config_files'].items():
        status = "✅" if info['exists'] else "❌"
        size = f"({info['size_bytes']} bytes)" if info['exists'] else ""
        print(f"  {status} {file_path} {size}")
    
    # Imágenes Docker
    print(f"\n{Colors.YELLOW}🐳 Imágenes Docker:{Colors.END}")
    if state['docker_images']:
        for repo, info in state['docker_images'].items():
            print(f"  ✅ {repo}:{info['tag']} - {info['size']}")
    else:
        print(f"  {Colors.RED}❌ No hay imágenes de FungiGT construidas{Colors.END}")
    
    # Contenedores Docker
    print(f"\n{Colors.YELLOW}📦 Contenedores Docker:{Colors.END}")
    if state['docker_containers']:
        for name, info in state['docker_containers'].items():
            status_color = Colors.GREEN if info['status'] == 'running' else Colors.RED
            print(f"  {status_color}{info['status'].upper()}{Colors.END} {name} - {info['image']}")
    else:
        print(f"  {Colors.RED}❌ No hay contenedores de FungiGT{Colors.END}")
    
    # Volúmenes Docker
    print(f"\n{Colors.YELLOW}💾 Volúmenes Docker:{Colors.END}")
    if state['docker_volumes']:
        for name, info in state['docker_volumes'].items():
            print(f"  ✅ {name} - {info['driver']}")
    else:
        print(f"  {Colors.RED}❌ No hay volúmenes de FungiGT{Colors.END}")

def analyze_partial_installation(state):
    """Analizar instalación parcial y dar recomendaciones"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}🔍 Análisis de Instalación Parcial:{Colors.END}")
    
    # Verificar qué servicios están construidos
    built_services = []
    failed_services = []
    
    # Mapeo de servicios esperados a nombres de imágenes
    service_mappings = {
        "auth": ["fungigt-auth", "auth"],
        "frontend": ["fungigt-frontend", "frontend"],
        "file-manager": ["fungigt-file-manager", "fungigt-backend", "file-manager", "backend"],
        "visualization": ["fungigt-visualization", "visualization"],
        "quality-control": ["fungigt-quality-control", "quality-control"],
        "acquisition": ["fungigt-acquisition", "acquisition"]
    }
    
    for service, possible_names in service_mappings.items():
        service_found = False
        for repo in state['docker_images'].keys():
            for possible_name in possible_names:
                if possible_name in repo.lower():
                    built_services.append(service)
                    service_found = True
                    break
            if service_found:
                break
        if not service_found:
            failed_services.append(service)
    
    print(f"\n{Colors.GREEN}✅ Servicios Construidos ({len(built_services)}/{len(service_mappings)}):{Colors.END}")
    for service in built_services:
        # Mostrar qué imagen corresponde a cada servicio
        for repo in state['docker_images'].keys():
            for possible_name in service_mappings[service]:
                if possible_name in repo.lower():
                    print(f"  ✅ {service} → {repo}")
                    break
            else:
                continue
            break
    
    if failed_services:
        print(f"\n{Colors.RED}❌ Servicios Faltantes ({len(failed_services)}/{len(service_mappings)}):{Colors.END}")
        for service in failed_services:
            print(f"  ❌ {service}")
    
    # Recomendaciones mejoradas
    print(f"\n{Colors.YELLOW}💡 Recomendaciones:{Colors.END}")
    
    if len(built_services) >= 3:
        print(f"  📊 Puedes ejecutar FungiGT con servicios construidos:")
        services_to_start = built_services[:4]  # Limitar a 4 servicios para evitar sobrecarga
        print(f"  {Colors.WHITE}docker compose -p fungigt up -d {' '.join(services_to_start)}{Colors.END}")
        
        if len(built_services) >= 4:
            print(f"  🎉 ¡Excelente! Tienes {len(built_services)} servicios construidos - suficientes para una instalación funcional")
    
    if failed_services:
        print(f"  🔧 Para construir servicios faltantes uno por uno:")
        for service in failed_services[:2]:  # Mostrar solo los primeros 2
            print(f"  {Colors.WHITE}docker compose -p fungigt build {service}{Colors.END}")
        
        if len(failed_services) > 2:
            print(f"  📝 O construir todos los faltantes: {Colors.WHITE}docker compose -p fungigt build {' '.join(failed_services)}{Colors.END}")
    
    if len(state['docker_volumes']) > 0:
        print(f"  ⚠️ Los datos en volúmenes se mantienen entre reinstalaciones")
        print(f"  🗑️ Para limpiar datos: {Colors.WHITE}python scripts/setup/stop_services.py --remove-volumes{Colors.END}")
    
    # Sugerencia para servicios casi completos
    if len(built_services) >= 4:
        print(f"\n{Colors.GREEN}🚀 Estado Excelente:{Colors.END}")
        print(f"  ✨ Tienes suficientes servicios para ejecutar FungiGT")
        print(f"  🔄 Intenta iniciar los servicios: {Colors.WHITE}python scripts/setup/quick_start.py{Colors.END}")

def what_gets_cleaned():
    """Explicar qué se limpia y qué se mantiene"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}🧹 Gestión de Limpieza:{Colors.END}")
    
    print(f"\n{Colors.GREEN}✅ Se MANTIENE automáticamente:{Colors.END}")
    print(f"  📁 Directorios de datos (/data)")
    print(f"  📁 Código fuente (/src)")
    print(f"  📁 Scripts (/scripts)")
    print(f"  📁 Configuración (/infrastructure)")
    print(f"  💾 Volúmenes Docker (datos de DB)")
    print(f"  ⚙️ Archivos .env generados")
    
    print(f"\n{Colors.YELLOW}🔄 Se LIMPIA automáticamente con --restart:{Colors.END}")
    print(f"  🐳 Contenedores Docker activos")
    print(f"  🗑️ Imágenes Docker huérfanas")
    print(f"  🔌 Redes Docker no utilizadas")
    print(f"  💾 Volúmenes Docker (solo con --remove-volumes)")
    
    print(f"\n{Colors.RED}⚠️ Se BORRA solo manualmente:{Colors.END}")
    print(f"  🗂️ Datos de usuario (/data)")
    print(f"  📊 Resultados de análisis")
    print(f"  🔐 Configuraciones personalizadas")

def debug_specific_service():
    """Debug de un servicio específico"""
    print(f"\n{Colors.CYAN}Servicios disponibles:{Colors.END}")
    services = ["auth", "frontend", "file-manager", "visualization", "quality-control", "acquisition"]
    
    for i, service in enumerate(services, 1):
        print(f"  {i}. {service}")
    
    try:
        choice = input(f"\n{Colors.YELLOW}Selecciona un servicio para debuggear (1-{len(services)}): {Colors.END}")
        service_idx = int(choice) - 1
        
        if 0 <= service_idx < len(services):
            service = services[service_idx]
            debug_service_details(service)
        else:
            log('ERROR', "Selección inválida")
    except (ValueError, KeyboardInterrupt):
        log('INFO', "Operación cancelada")

def debug_service_details(service_name):
    """Debug detallado de un servicio específico"""
    log('INFO', f"Debuggeando servicio: {service_name}")
    
    project_root = get_project_root()
    
    # Verificar Dockerfile
    dockerfile_paths = [
        f"infrastructure/docker/{service_name}/Dockerfile",
        f"infrastructure/docker/{service_name.replace('-', '_')}/Dockerfile",
        f"src/modules/{service_name}/Dockerfile",
        f"src/modules/{service_name.replace('-', '_')}/Dockerfile"
    ]
    
    dockerfile_found = None
    for path in dockerfile_paths:
        full_path = project_root / path
        if full_path.exists():
            dockerfile_found = path
            break
    
    print(f"\n{Colors.YELLOW}📄 Dockerfile:{Colors.END}")
    if dockerfile_found:
        print(f"  ✅ Encontrado: {dockerfile_found}")
        
        # Intentar construir solo este servicio
        print(f"\n{Colors.YELLOW}🔨 Intentando construcción individual:{Colors.END}")
        success, stdout, stderr = run_command([
            "docker", "compose", "-p", "fungigt",
            "-f", str(project_root / "docker-compose.yml"),
            "build", service_name
        ], cwd=project_root)
        
        if success:
            log('SUCCESS', f"✅ {service_name} se construyó exitosamente")
        else:
            log('ERROR', f"❌ Error construyendo {service_name}")
            if stderr:
                print(f"{Colors.RED}Error details:{Colors.END}")
                print(stderr[:500] + "..." if len(stderr) > 500 else stderr)
    else:
        print(f"  ❌ No se encontró Dockerfile para {service_name}")

def show_debug_commands():
    """Mostrar comandos útiles para debugging"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}🛠️ Comandos de Debugging:{Colors.END}")
    
    commands = [
        ("Ver estado de contenedores", "docker compose -p fungigt ps"),
        ("Ver logs de servicios", "docker compose -p fungigt logs -f"),
        ("Ver logs de un servicio", "docker compose -p fungigt logs [servicio]"),
        ("Ver imágenes construidas", "docker images | grep fungigt"),
        ("Ver volúmenes", "docker volume ls | grep fungigt"),
        ("Ver uso de espacio Docker", "docker system df"),
        ("Construir servicio individual", "docker compose -p fungigt build [servicio]"),
        ("Iniciar servicios específicos", "docker compose -p fungigt up -d [servicio1] [servicio2]"),
        ("Ejecutar bash en contenedor", "docker exec -it [contenedor] bash"),
        ("Ver configuración docker-compose", "docker compose -p fungigt config")
    ]
    
    for description, command in commands:
        print(f"\n{Colors.YELLOW}{description}:{Colors.END}")
        print(f"  {Colors.WHITE}{command}{Colors.END}")

def main():
    print_banner()
    
    print(f"""
{Colors.CYAN}Selecciona una opción de debugging:{Colors.END}

{Colors.WHITE}1.{Colors.END} Ver estado completo de la instalación
{Colors.WHITE}2.{Colors.END} Analizar instalación parcial
{Colors.WHITE}3.{Colors.END} Explicar qué se limpia/mantiene
{Colors.WHITE}4.{Colors.END} Debug de servicio específico
{Colors.WHITE}5.{Colors.END} Mostrar comandos de debugging
{Colors.WHITE}6.{Colors.END} Ver estado resumido
{Colors.WHITE}0.{Colors.END} Salir
""")
    
    try:
        choice = input(f"{Colors.YELLOW}Selecciona una opción (0-6): {Colors.END}")
        
        if choice == "1":
            state = check_installation_state()
            show_installation_state(state)
            analyze_partial_installation(state)
        elif choice == "2":
            state = check_installation_state()
            analyze_partial_installation(state)
        elif choice == "3":
            what_gets_cleaned()
        elif choice == "4":
            debug_specific_service()
        elif choice == "5":
            show_debug_commands()
        elif choice == "6":
            state = check_installation_state()
            # Resumen rápido
            total_dirs = len([d for d in state['directories'].values() if d['exists']])
            total_images = len(state['docker_images'])
            total_containers = len(state['docker_containers'])
            
            print(f"\n{Colors.GREEN}📊 Resumen: {total_dirs} dirs, {total_images} imágenes, {total_containers} contenedores{Colors.END}")
        elif choice == "0":
            log('INFO', "Saliendo...")
            return 0
        else:
            log('ERROR', "Opción no válida")
            return 1
        
        print(f"\n{Colors.GREEN}💡 Consejos adicionales:{Colors.END}")
        print(f"  - Los directorios /data se mantienen siempre")
        print(f"  - Las imágenes Docker se mantienen hasta limpieza manual")
        print(f"  - Usa --restart para instalación incremental")
        print(f"  - Usa --clean para empezar completamente desde cero")
        
        return 0
        
    except KeyboardInterrupt:
        log('WARNING', "🛑 Operación interrumpida")
        return 1
    except Exception as e:
        log('ERROR', f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 