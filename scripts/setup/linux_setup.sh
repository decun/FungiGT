#!/bin/bash

# Script de configuración específica para Linux - FungiGT
# Este script prepara el sistema Linux para ejecutar FungiGT

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🐧 FungiGT - Configuración para Linux${NC}"
echo "======================================"

# Función para logging
log() {
    local level=$1
    local message=$2
    case $level in
        "INFO")
            echo -e "${CYAN}[INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
    esac
}

# Verificar si el usuario está en el grupo docker
check_docker_group() {
    log "INFO" "Verificando permisos Docker..."
    
    if groups $USER | grep &>/dev/null '\bdocker\b'; then
        log "SUCCESS" "Usuario '$USER' está en el grupo 'docker'"
        return 0
    else
        log "WARNING" "Usuario '$USER' NO está en el grupo 'docker'"
        return 1
    fi
}

# Agregar usuario al grupo docker
add_user_to_docker() {
    log "INFO" "Agregando usuario '$USER' al grupo 'docker'..."
    
    if command -v sudo &> /dev/null; then
        sudo usermod -aG docker $USER
        log "SUCCESS" "Usuario agregado al grupo 'docker'"
        log "WARNING" "IMPORTANTE: Debes reiniciar tu sesión para que los cambios tomen efecto"
        log "INFO" "Puedes hacer: logout/login o ejecutar: newgrp docker"
        return 0
    else
        log "ERROR" "sudo no está disponible. Ejecuta manualmente:"
        log "INFO" "  usermod -aG docker $USER"
        return 1
    fi
}

# Verificar Docker instalado
check_docker_installed() {
    log "INFO" "Verificando instalación de Docker..."
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        log "SUCCESS" "Docker encontrado: $DOCKER_VERSION"
        return 0
    else
        log "ERROR" "Docker no está instalado"
        return 1
    fi
}

# Verificar Docker Compose
check_docker_compose() {
    log "INFO" "Verificando Docker Compose..."
    
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        log "SUCCESS" "Docker Compose encontrado: $COMPOSE_VERSION"
        return 0
    else
        log "ERROR" "Docker Compose no está disponible"
        return 1
    fi
}

# Verificar Docker daemon corriendo
check_docker_running() {
    log "INFO" "Verificando Docker daemon..."
    
    if docker info &> /dev/null; then
        log "SUCCESS" "Docker daemon está ejecutándose"
        return 0
    else
        log "ERROR" "Docker daemon no está ejecutándose"
        log "INFO" "Inicia Docker con: sudo systemctl start docker"
        return 1
    fi
}

# Crear directorios necesarios con permisos correctos
setup_directories() {
    log "INFO" "Configurando directorios..."
    
    local dirs=(
        "data/raw/genomes"
        "data/processed"
        "data/uploads"
        "data/results"
        "data/downloads"
        "data/references"
        "data/intermediate"
        "data/visualizations"
        "logs"
        "tmp"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        # Asegurar permisos correctos para el usuario actual
        chown -R $USER:$USER "$dir" 2>/dev/null || true
        chmod -R 755 "$dir" 2>/dev/null || true
    done
    
    log "SUCCESS" "Directorios configurados"
}

# Configurar variables de entorno
setup_env_vars() {
    log "INFO" "Configurando variables de entorno Linux..."
    
    # Obtener UID y GID del usuario actual
    USER_UID=$(id -u)
    USER_GID=$(id -g)
    
    # Obtener GID del grupo docker
    DOCKER_GID=$(getent group docker | cut -d: -f3 2>/dev/null || echo "999")
    
    log "INFO" "Usuario actual: UID=$USER_UID, GID=$USER_GID"
    log "INFO" "Grupo Docker: GID=$DOCKER_GID"
    
    # Exportar variables para sesión actual
    export DOCKER_USER="$USER_UID:$USER_GID"
    export DOCKER_GROUP="$DOCKER_GID"
    
    log "SUCCESS" "Variables configuradas temporalmente"
    log "INFO" "Para configuración permanente, ejecuta setup_fungigt.py"
}

# Verificar permisos del socket Docker
check_docker_socket() {
    log "INFO" "Verificando permisos del socket Docker..."
    
    if [ -S /var/run/docker.sock ]; then
        local socket_group=$(stat -c %G /var/run/docker.sock)
        log "INFO" "Socket Docker pertenece al grupo: $socket_group"
        
        if groups $USER | grep &>/dev/null "\b$socket_group\b"; then
            log "SUCCESS" "Permisos del socket Docker OK"
            return 0
        else
            log "WARNING" "Usuario no tiene acceso al socket Docker"
            return 1
        fi
    else
        log "ERROR" "Socket Docker no encontrado en /var/run/docker.sock"
        return 1
    fi
}

# Función principal
main() {
    echo
    log "INFO" "Iniciando configuración para Linux..."
    echo
    
    # Verificaciones básicas
    if ! check_docker_installed; then
        log "ERROR" "Docker debe estar instalado. Visita: https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    if ! check_docker_compose; then
        log "ERROR" "Docker Compose no disponible"
        exit 1
    fi
    
    if ! check_docker_running; then
        log "WARNING" "Docker daemon no está corriendo"
        log "INFO" "Intentando iniciar Docker..."
        if command -v sudo &> /dev/null; then
            sudo systemctl start docker || log "ERROR" "No se pudo iniciar Docker"
        fi
    fi
    
    # Verificar y configurar permisos
    if ! check_docker_group; then
        log "WARNING" "Se necesita agregar usuario al grupo docker"
        read -p "¿Agregar usuario '$USER' al grupo docker? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            add_user_to_docker
        else
            log "INFO" "Configuración manual requerida"
        fi
    fi
    
    if ! check_docker_socket; then
        log "WARNING" "Problemas con permisos del socket Docker"
    fi
    
    # Configurar directorios y variables
    setup_directories
    setup_env_vars
    
    echo
    log "SUCCESS" "🎉 Configuración Linux completada"
    echo
    log "INFO" "📋 Próximos pasos:"
    log "INFO" "  1. Si agregaste usuario al grupo docker, reinicia tu sesión"
    log "INFO" "  2. Ejecuta: python scripts/setup/setup_fungigt.py"
    log "INFO" "  3. Para iniciar servicios: python scripts/setup/start_services.py"
    echo
}

# Ejecutar si se llama directamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 