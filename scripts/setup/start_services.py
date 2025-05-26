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

def run_command(cmd, cwd=None):
    """Ejecutar un comando de shell e imprimirlo."""
    print("Ejecutando:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

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
        "down"
    ], cwd=project_root)

def build_images():
    """Construir las imágenes de Docker para todos los servicios."""
    print("Construyendo imágenes de Docker para FungiGT...")
    project_root = get_project_root()
    compose_file = os.path.join(project_root, "docker-compose.yml")
    
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", compose_file,
        "build"
    ], cwd=project_root)

def start_services(profile=None):
    """Iniciar todos los servicios de FungiGT."""
    print("Iniciando servicios de FungiGT...")
    project_root = get_project_root()
    compose_file = os.path.join(project_root, "docker-compose.yml")
    
    cmd = ["docker", "compose", "-p", "fungigt"]
    if profile and profile != "all":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", compose_file, "up", "-d"])
    run_command(cmd, cwd=project_root)

def main():
    parser = argparse.ArgumentParser(description='Iniciar los servicios de FungiGT.')
    parser.add_argument('--profile', choices=['all', 'frontend', 'backend', 'modules', 'acquisition', 'quality', 'analysis', 'annotation'], default='all',
                      help='Perfil a usar para Docker Compose (default: all)')
    parser.add_argument('--rebuild', action='store_true',
                      help='Reconstruir las imágenes antes de iniciar los servicios')
    args = parser.parse_args()

    # Detener contenedores existentes
    stop_existing_containers()
    
    # Reconstruir imágenes si se solicita
    if args.rebuild:
        build_images()
    
    # Iniciar los servicios
    start_services(args.profile)
    
    print("Todos los servicios de FungiGT han sido iniciados correctamente.")
    print("Puedes acceder al frontend en: http://localhost:4005")

if __name__ == "__main__":
    main()