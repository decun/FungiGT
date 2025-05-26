#!/usr/bin/env python3
"""
stop_services.py

Este script detiene todos los servicios de FungiGT que están corriendo en Docker.
"""

import os
import subprocess
import argparse

def run_command(cmd, cwd=None):
    """Ejecutar un comando de shell e imprimirlo."""
    print("Ejecutando:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def get_project_root():
    """Obtener la ruta a la raíz del proyecto."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def stop_services():
    """Detener todos los servicios de FungiGT."""
    print("Deteniendo todos los servicios de FungiGT...")
    project_root = get_project_root()
    compose_file = os.path.join(project_root, "docker-compose.yml")
    
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", compose_file,
        "down"
    ], cwd=project_root)

def main():
    parser = argparse.ArgumentParser(description='Detener los servicios de FungiGT.')
    parser.add_argument('--remove-volumes', action='store_true',
                      help='Eliminar también los volúmenes de datos')
    args = parser.parse_args()

    project_root = get_project_root()
    compose_file = os.path.join(project_root, "docker-compose.yml")

    if args.remove_volumes:
        print("ADVERTENCIA: Se eliminarán todos los volúmenes de datos!")
        confirm = input("¿Estás seguro? (s/N): ").lower()
        if confirm == 's':
            print("Deteniendo servicios y eliminando volúmenes...")
            run_command([
                "docker", "compose",
                "-p", "fungigt",
                "-f", compose_file,
                "down", "-v"
            ], cwd=project_root)
        else:
            print("Operación cancelada. Los volúmenes se conservarán.")
            stop_services()
    else:
        stop_services()
    
    print("Todos los servicios de FungiGT han sido detenidos correctamente.")

if __name__ == "__main__":
    main()