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

def stop_services():
    """Detener todos los servicios de FungiGT."""
    print("Deteniendo todos los servicios de FungiGT...")
    run_command([
        "docker", "compose",
        "-p", "fungigt",
        "-f", "docker-compose.yml",
        "down"
    ])

def main():
    parser = argparse.ArgumentParser(description='Detener los servicios de FungiGT.')
    parser.add_argument('--remove-volumes', action='store_true',
                      help='Eliminar también los volúmenes de datos')
    args = parser.parse_args()

    if args.remove_volumes:
        print("ADVERTENCIA: Se eliminarán todos los volúmenes de datos!")
        confirm = input("¿Estás seguro? (s/N): ").lower()
        if confirm == 's':
            print("Deteniendo servicios y eliminando volúmenes...")
            run_command([
                "docker", "compose",
                "-p", "fungigt",
                "-f", "docker-compose.yml",
                "down", "-v"
            ])
        else:
            print("Operación cancelada. Los volúmenes se conservarán.")
            stop_services()
    else:
        stop_services()
    
    print("Todos los servicios de FungiGT han sido detenidos correctamente.")

if __name__ == "__main__":
    main()