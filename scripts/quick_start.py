#!/usr/bin/env python3
"""
Script de inicio rápido para FungiGT
Para uso diario cuando ya está instalado
"""

import subprocess
import time
import sys
from pathlib import Path

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    OKCYAN = '\033[96m'

def print_success(message: str):
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")

def print_warning(message: str):
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")

def print_error(message: str):
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")

def run_command(cmd: str) -> bool:
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def check_services_status():
    """Verifica el estado de todos los servicios"""
    print(f"\n{Colors.BOLD}=== Estado de Servicios FungiGT ==={Colors.ENDC}")
    
    try:
        result = subprocess.run("docker-compose ps", shell=True, capture_output=True, text=True)
        output = result.stdout
        
        services = {
            'mongodb': 'Base de datos MongoDB',
            'auth': 'Servicio de autenticación',
            'frontend': 'Interfaz web',
            'file-manager': 'Gestor de archivos',
            'visualization': 'Módulo de visualización',
            'quality-control': 'Control de calidad',
            'acquisition': 'Adquisición de datos',
            'annotation': 'BRAKER3 - Anotación genómica',
            'checkm': 'CheckM - Evaluación de completitud',
            'functional-analysis': 'EggNOG - Análisis funcional',
            'phylogeny': 'BLAST - Análisis filogenético'
        }
        
        running_count = 0
        total_count = len(services)
        
        for service, description in services.items():
            if service in output:
                if "Up" in output or "running" in output or "healthy" in output:
                    print_success(f"{description}")
                    running_count += 1
                else:
                    print_error(f"{description} - No ejecutándose")
            else:
                print_warning(f"{description} - No encontrado")
        
        print(f"\n{Colors.BOLD}Servicios activos: {running_count}/{total_count}{Colors.ENDC}")
        
        if running_count == total_count:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 Todos los servicios están funcionando correctamente{Colors.ENDC}")
            return True
        else:
            print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️ Algunos servicios no están funcionando{Colors.ENDC}")
            return False
            
    except Exception as e:
        print_error(f"Error verificando servicios: {e}")
        return False

def start_services():
    """Inicia todos los servicios"""
    print(f"\n{Colors.BOLD}=== Iniciando FungiGT ==={Colors.ENDC}")
    
    if run_command("docker-compose up -d"):
        print_success("Servicios iniciados correctamente")
        time.sleep(10)  # Esperar a que se estabilicen
        return check_services_status()
    else:
        print_error("Error iniciando servicios")
        return False

def stop_services():
    """Detiene todos los servicios"""
    print(f"\n{Colors.BOLD}=== Deteniendo FungiGT ==={Colors.ENDC}")
    
    if run_command("docker-compose down"):
        print_success("Servicios detenidos correctamente")
        return True
    else:
        print_error("Error deteniendo servicios")
        return False

def show_access_info():
    """Muestra información de acceso"""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}=== Información de Acceso ==={Colors.ENDC}")
    print(f"{Colors.OKCYAN}🌐 Servicios Web:{Colors.ENDC}")
    print(f"  • Frontend Principal: http://localhost:4005")
    print(f"  • Auth Service: http://localhost:4001")
    print(f"  • File Manager: http://localhost:4002")
    print(f"  • Visualization: http://localhost:4003")
    print(f"  • Quality Control: http://localhost:4004")
    print(f"  • Acquisition: http://localhost:4006")
    
    print(f"\n{Colors.OKCYAN}🔬 Herramientas de Análisis:{Colors.ENDC}")
    print(f"  • BRAKER3: docker exec -it fungigt-annotation bash")
    print(f"  • CheckM: docker exec -it fungigt-checkm bash")
    print(f"  • EggNOG: docker exec -it fungigt-eggnog bash")
    print(f"  • BLAST: docker exec -it fungigt-blast bash")
    
    print(f"\n{Colors.OKCYAN}📁 Directorios de Datos:{Colors.ENDC}")
    print(f"  • Datos principales: ./data/")
    print(f"  • Resultados BRAKER3: ./data/braker_output/")
    print(f"  • Resultados CheckM: ./data/checkm_output/")
    print(f"  • Resultados EggNOG: ./data/eggnog_output/")
    print(f"  • Resultados BLAST: ./data/blast_output/")

def main():
    """Función principal"""
    print(f"{Colors.BOLD}")
    print("=" * 50)
    print("   FUNGIGT - INICIO RÁPIDO")
    print("   Plataforma de Análisis Genómico")
    print("=" * 50)
    print(f"{Colors.ENDC}")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "start":
            if start_services():
                show_access_info()
        elif command == "stop":
            stop_services()
        elif command == "status":
            if check_services_status():
                show_access_info()
        elif command == "restart":
            stop_services()
            time.sleep(5)
            if start_services():
                show_access_info()
        else:
            print_error(f"Comando no reconocido: {command}")
            print("Comandos disponibles: start, stop, status, restart")
    else:
        # Verificar estado actual
        status_ok = check_services_status()
        
        if not status_ok:
            print(f"\n{Colors.WARNING}¿Quieres iniciar los servicios? (y/n): {Colors.ENDC}", end="")
            response = input().lower()
            if response in ['y', 'yes', 's', 'si']:
                if start_services():
                    show_access_info()
        else:
            show_access_info()

if __name__ == "__main__":
    main() 