#!/usr/bin/env python3
"""
install.py

Script de instalación inicial para FungiGT.
"""

import os
import subprocess
import argparse
import sys

def run_command(cmd, cwd=None):
    """Ejecutar un comando de shell e imprimirlo."""
    print("Ejecutando:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def check_docker():
    """Verificar que Docker esté instalado y funcionando."""
    print("Verificando instalación de Docker...")
    try:
        run_command(["docker", "--version"])
        run_command(["docker", "compose", "--version"])
        print("Docker y Docker Compose están instalados correctamente.")
        return True
    except:
        print("ERROR: Docker no está instalado o no está en el PATH.")
        print("Por favor, instala Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False

def create_directories():
    """Crear directorios necesarios para los datos."""
    # Obtener la ruta a la raíz del proyecto (2 niveles arriba del script)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    
    dirs = ["data/uploads", "data/processed", "data/results"]
    for d in dirs:
        dir_path = os.path.join(project_root, d)
        if not os.path.exists(dir_path):
            print(f"Creando directorio: {d}")
            os.makedirs(dir_path)

def build_images():
    """Construir las imágenes de Docker para todos los servicios."""
    print("Construyendo imágenes de Docker para FungiGT...")
    
    # Obtener la ruta a la raíz del proyecto (2 niveles arriba del script)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    
    # Ruta completa al archivo docker-compose.yml
    compose_file = os.path.join(project_root, "docker-compose.yml")
    
    # Verificar que el archivo existe
    if not os.path.exists(compose_file):
        print(f"ERROR: No se encuentra el archivo {compose_file}")
        return False
    
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", compose_file,
        "build"
    ], cwd=project_root)
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Instalación inicial de FungiGT")
    args = parser.parse_args()

    print("=== Instalando FungiGT ===")
    
    if not check_docker():
        return

    create_directories()
    
    if build_images():
        print("\n=== Instalación completada ===")
        print("Para iniciar los servicios ejecuta: python scripts/setup/start_services.py")
    else:
        print("\n=== ERROR: La instalación no se completó correctamente ===")

if __name__ == "__main__":
    main() 