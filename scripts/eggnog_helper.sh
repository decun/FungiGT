#!/bin/bash

# Script de Ayuda para eggNOG-mapper en FungiGT
# =============================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
CONTAINER_NAME="fungigt-eggnog-mapper"
EGGNOG_IMAGE="nanozoo/eggnog-mapper:2.1.9--4f2b6c0"
DATA_DIR="./data"
DB_DIR="$DATA_DIR/eggnog_db"
SERVICE_PORT="3001"

# Funciones
print_header() {
    echo -e "\n${BLUE}🧬 FungiGT - Gestor eggNOG-mapper${NC}"
    echo -e "${BLUE}=================================${NC}\n"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado o no está en PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker no está ejecutándose o no tienes permisos"
        exit 1
    fi
}

check_database() {
    print_status "Verificando base de datos eggNOG..."
    
    if [ ! -d "$DB_DIR" ]; then
        print_warning "Directorio de base de datos no existe: $DB_DIR"
        return 1
    fi
    
    # Archivos críticos de la base de datos
    critical_files=("eggnog.db" "eggnog_proteins.dmnd")
    files_found=0
    total_size=0
    
    for file in "${critical_files[@]}"; do
        file_path="$DB_DIR/$file"
        if [ -f "$file_path" ]; then
            files_found=$((files_found + 1))
            size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo 0)
            total_size=$((total_size + size))
        fi
    done
    
    if [ $files_found -eq ${#critical_files[@]} ]; then
        size_gb=$(echo "scale=2; $total_size / 1024 / 1024 / 1024" | bc 2>/dev/null || echo "N/A")
        print_status "✅ Base de datos completa (${size_gb} GB)"
        return 0
    else
        print_warning "❌ Base de datos incompleta ($files_found/${#critical_files[@]} archivos)"
        return 1
    fi
}

download_database() {
    print_status "Iniciando descarga de base de datos eggNOG..."
    
    # Crear directorio si no existe
    mkdir -p "$DB_DIR"
    
    print_warning "⚠️  ADVERTENCIA: La base de datos eggNOG ocupa ~2.9 GB"
    print_warning "    Tiempo estimado: 10-30 minutos"
    print_warning "    Requiere conexión estable a internet"
    
    echo ""
    read -p "¿Desea continuar? [s/N]: " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
        print_status "Descarga cancelada"
        return 0
    fi
    
    print_status "Descargando base de datos..."
    
    # Descargar usando el contenedor
    docker run --rm \
        -v "$(pwd)/$DB_DIR:/data/eggnog_db" \
        "$EGGNOG_IMAGE" \
        download_eggnog_data.py \
        --data_dir /data/eggnog_db \
        -y
    
    if [ $? -eq 0 ]; then
        print_status "✅ Base de datos descargada exitosamente"
        check_database
    else
        print_error "❌ Error descargando base de datos"
        return 1
    fi
}

pull_image() {
    print_status "Descargando imagen eggNOG-mapper..."
    docker pull "$EGGNOG_IMAGE"
}

start_service() {
    print_status "Iniciando servicio eggNOG-mapper..."
    
    # Verificar si el contenedor ya está ejecutándose
    if docker ps --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
        print_warning "El servicio ya está ejecutándose"
        return 0
    fi
    
    # Crear directorios necesarios
    mkdir -p "$DATA_DIR/eggnog_uploads"
    mkdir -p "$DATA_DIR/eggnog_results"
    mkdir -p "$DB_DIR"
    mkdir -p "./logs"
    
    # Iniciar servicio usando docker-compose
    if [ -f "infrastructure/docker/analysis/eggnog/docker-compose.yml" ]; then
        cd infrastructure/docker/analysis/eggnog
        docker-compose up -d
        cd - > /dev/null
        print_status "✅ Servicio iniciado con docker-compose"
    else
        print_error "Archivo docker-compose.yml no encontrado"
        return 1
    fi
}

stop_service() {
    print_status "Deteniendo servicio eggNOG-mapper..."
    
    if [ -f "infrastructure/docker/analysis/eggnog/docker-compose.yml" ]; then
        cd infrastructure/docker/analysis/eggnog
        docker-compose down
        cd - > /dev/null
        print_status "✅ Servicio detenido"
    else
        # Fallback: detener contenedor manualmente
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        print_status "✅ Servicio detenido (fallback)"
    fi
}

status_service() {
    print_status "Estado del servicio eggNOG-mapper:"
    
    # Verificar contenedor
    if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}🟢 Servicio: EJECUTÁNDOSE${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "$CONTAINER_NAME"
    else
        echo -e "${RED}🔴 Servicio: DETENIDO${NC}"
    fi
    
    # Verificar base de datos
    if check_database &>/dev/null; then
        echo -e "${GREEN}🟢 Base de datos: DISPONIBLE${NC}"
    else
        echo -e "${RED}🔴 Base de datos: NO DISPONIBLE${NC}"
    fi
    
    # Verificar puerto
    if command -v nc &> /dev/null; then
        if nc -z localhost "$SERVICE_PORT" 2>/dev/null; then
            echo -e "${GREEN}🟢 Puerto $SERVICE_PORT: ABIERTO${NC}"
        else
            echo -e "${RED}🔴 Puerto $SERVICE_PORT: CERRADO${NC}"
        fi
    fi
    
    # Verificar API
    if command -v curl &> /dev/null; then
        if curl -s "http://localhost:$SERVICE_PORT/health" &>/dev/null; then
            echo -e "${GREEN}🟢 API: RESPONDIENDO${NC}"
        else
            echo -e "${RED}🔴 API: NO RESPONDE${NC}"
        fi
    fi
}

test_analysis() {
    print_status "Ejecutando prueba de análisis..."
    
    # Verificar que el servicio esté ejecutándose
    if ! docker ps --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
        print_error "El servicio no está ejecutándose. Use: $0 start"
        return 1
    fi
    
    # Verificar base de datos
    if ! check_database &>/dev/null; then
        print_error "Base de datos no disponible. Use: $0 download-db"
        return 1
    fi
    
    print_status "✅ Servicio y base de datos listos para análisis"
    
    # Mostrar endpoints disponibles
    echo ""
    print_status "Endpoints disponibles:"
    echo "  • http://localhost:$SERVICE_PORT/health - Health check"
    echo "  • http://localhost:$SERVICE_PORT/info - Información del servicio"
    echo "  • http://localhost:$SERVICE_PORT/database/status - Estado de BD"
}

clean_data() {
    print_warning "Esta operación limpiará archivos temporales"
    
    echo ""
    read -p "¿Desea continuar? [s/N]: " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
        print_status "Operación cancelada"
        return 0
    fi
    
    # Limpiar archivos temporales
    find "$DATA_DIR/eggnog_uploads" -type f -name "*.tmp" -delete 2>/dev/null || true
    find "$DATA_DIR/eggnog_results" -type d -empty -delete 2>/dev/null || true
    
    print_status "✅ Archivos temporales limpiados"
}

show_help() {
    print_header
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponibles:"
    echo "  pull            Descargar imagen Docker de eggNOG-mapper"
    echo "  download-db     Descargar base de datos eggNOG (~2.9 GB)"
    echo "  check-db        Verificar estado de la base de datos"
    echo "  start           Iniciar servicio eggNOG-mapper"
    echo "  stop            Detener servicio eggNOG-mapper"
    echo "  restart         Reiniciar servicio eggNOG-mapper"
    echo "  status          Mostrar estado completo del servicio"
    echo "  test            Probar configuración y disponibilidad"
    echo "  clean           Limpiar archivos temporales"
    echo "  logs            Mostrar logs del servicio"
    echo "  help            Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 pull && $0 download-db && $0 start"
    echo "  $0 status"
    echo "  $0 test"
}

show_logs() {
    if docker ps --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
        print_status "Mostrando logs del servicio (Ctrl+C para salir)..."
        docker logs -f "$CONTAINER_NAME"
    else
        print_error "El servicio no está ejecutándose"
        return 1
    fi
}

# Main
main() {
    case "${1:-help}" in
        "pull")
            print_header
            check_docker
            pull_image
            ;;
        "download-db")
            print_header
            check_docker
            download_database
            ;;
        "check-db")
            print_header
            check_database
            ;;
        "start")
            print_header
            check_docker
            start_service
            ;;
        "stop")
            print_header
            check_docker
            stop_service
            ;;
        "restart")
            print_header
            check_docker
            stop_service
            sleep 2
            start_service
            ;;
        "status")
            print_header
            check_docker
            status_service
            ;;
        "test")
            print_header
            check_docker
            test_analysis
            ;;
        "clean")
            print_header
            clean_data
            ;;
        "logs")
            check_docker
            show_logs
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Comando desconocido: $1"
            show_help
            exit 1
            ;;
    esac
}

# Ejecutar
main "$@" 