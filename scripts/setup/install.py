#!/usr/bin/env python3
"""
install.py

Este script realiza la instalación inicial del proyecto FungiGT,
preparando todos los componentes para su ejecución con Docker.
"""

import os
import subprocess
import argparse
import sys
import platform

def run_command(cmd, cwd=None):
    """Ejecutar un comando de shell e imprimirlo."""
    print("Ejecutando:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def check_docker_installed():
    """Verificar si Docker está instalado en el sistema."""
    try:
        run_command(["docker", "--version"])
        run_command(["docker", "compose", "--version"])
        print("Docker y Docker Compose están instalados correctamente.")
        return True
    except Exception as e:
        print("Error: Docker o Docker Compose no están instalados correctamente.")
        print("Por favor, instala Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False

def build_images():
    """Construir todas las imágenes de Docker para el proyecto."""
    print("Construyendo imágenes de Docker para FungiGT...")
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", "docker-compose.yml",
        "build"
    ])

def create_data_directories():
    """Crear directorios de datos necesarios si no existen."""
    data_dirs = [
        "data/uploads",
        "data/processed",
        "data/results"
    ]
    
    for directory in data_dirs:
        if not os.path.exists(directory):
            print(f"Creando directorio: {directory}")
            os.makedirs(directory)

def main():
    parser = argparse.ArgumentParser(description='Instalar y configurar FungiGT.')
    parser.add_argument('--skip-docker-check', action='store_true',
                      help='Omitir la verificación de Docker')
    args = parser.parse_args()

    print("=== Instalando FungiGT ===")
    
    # Verificar instalación de Docker
    if not args.skip_docker_check:
        if not check_docker_installed():
            return
    
    # Crear directorios de datos
    create_data_directories()
    
    # Construir imágenes
    build_images()
    
    print("\n=== Instalación completada correctamente ===")
    print("Para iniciar los servicios, ejecuta: python scripts/setup/start_services.py")
    print("Para detener los servicios, ejecuta: python scripts/setup/stop_services.py")

if __name__ == "__main__":
    main() 