#!/usr/bin/env python3
"""
check_structure.py

Verifica la estructura del proyecto FungiGT y muestra información útil.
"""

import os
import sys
import json

def get_project_root():
    """Obtener la ruta a la raíz del proyecto."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def check_file(path, description):
    """Verificar si un archivo existe y mostrar información."""
    if os.path.exists(path):
        print(f"✅ {description} encontrado: {path}")
        return True
    else:
        print(f"❌ {description} NO encontrado: {path}")
        return False

def check_directory(path, description):
    """Verificar si un directorio existe y mostrar información."""
    if os.path.exists(path) and os.path.isdir(path):
        print(f"✅ {description} encontrado: {path}")
        return True
    else:
        print(f"❌ {description} NO encontrado: {path}")
        return False

def main():
    project_root = get_project_root()
    print(f"Raíz del proyecto: {project_root}")
    
    # Verificar archivos principales
    check_file(os.path.join(project_root, "docker-compose.yml"), "Archivo docker-compose.yml")
    check_file(os.path.join(project_root, ".env"), "Archivo .env")
    
    # Verificar directorios principales
    backend_dir = os.path.join(project_root, "src", "backend")
    frontend_dir = os.path.join(project_root, "src", "frontend")
    auth_dir = os.path.join(project_root, "src", "core", "auth")
    
    check_directory(backend_dir, "Directorio backend")
    check_directory(frontend_dir, "Directorio frontend")
    check_directory(auth_dir, "Directorio auth")
    
    # Verificar package.json en cada directorio
    check_file(os.path.join(backend_dir, "package.json"), "package.json de backend")
    check_file(os.path.join(frontend_dir, "package.json"), "package.json de frontend")
    check_file(os.path.join(auth_dir, "package.json"), "package.json de auth")
    
    # Verificar Dockerfiles
    check_file(os.path.join(project_root, "infrastructure", "docker", "backend", "Dockerfile"), "Dockerfile de backend")
    check_file(os.path.join(project_root, "infrastructure", "docker", "frontend", "Dockerfile"), "Dockerfile de frontend")
    check_file(os.path.join(project_root, "infrastructure", "docker", "auth", "Dockerfile"), "Dockerfile de auth")

if __name__ == "__main__":
    main() 