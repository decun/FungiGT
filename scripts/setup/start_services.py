#!/usr/bin/env python3
"""
start_services.py

Este script inicia todos los servicios de FungiGT usando Docker Compose.
"""

import os
import subprocess
import time
import argparse
import platform
import sys

def run_command(cmd, cwd=None, check=True):
    """Ejecutar un comando de shell e imprimirlo."""
    print("Ejecutando:", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=cwd, check=check)
        return True
    except subprocess.CalledProcessError as e:
        if check:
            print(f"ERROR: {e}")
            return False
        raise

def get_project_root():
    """Obtener la ruta a la raíz del proyecto."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def stop_existing_containers():
    """Detener y eliminar contenedores existentes para nuestro proyecto ('fungigt')."""
    print("Deteniendo y eliminando contenedores existentes para el proyecto 'fungigt'...")
    project_root = get_project_root()
    compose_file = os.path.join(project_root, "docker-compose.yml")
    
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", compose_file,
        "down", "--remove-orphans"
    ], cwd=project_root, check=False)

def start_services_unified():
    """Iniciar todos los servicios usando un único docker-compose.yml."""
    print("Iniciando todos los servicios desde el docker-compose.yml principal...")
    project_root = get_project_root()
    compose_file = os.path.join(project_root, "docker-compose.yml")
    
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", compose_file,
        "up", "-d"
    ], cwd=project_root)

def main():
    parser = argparse.ArgumentParser(description='Iniciar los servicios de FungiGT.')
    parser.add_argument('--rebuild', action='store_true',
                      help='Reconstruir las imágenes antes de iniciar los servicios')
    args = parser.parse_args()

    # Detener contenedores existentes
    stop_existing_containers()
    
    # Reconstruir imágenes si se solicita
    if args.rebuild:
        project_root = get_project_root()
        compose_file = os.path.join(project_root, "docker-compose.yml")
        run_command([
            "docker", "compose",
            "-p", "fungigt",
            "-f", compose_file,
            "build"
        ], cwd=project_root)
    
    # Iniciar todos los servicios usando un único docker-compose
    start_services_unified()
    
    print("Todos los servicios de FungiGT han sido iniciados correctamente.")
    print("Puedes acceder al frontend en: http://localhost:4005")

if __name__ == "__main__":
    main()