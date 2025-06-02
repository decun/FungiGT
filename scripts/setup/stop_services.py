#!/usr/bin/env python3
"""
Script para detener todos los servicios de FungiGT
"""

import subprocess
import sys
from pathlib import Path

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(level, message):
    """Logger con colores"""
    colors = {
        'INFO': Colors.CYAN,
        'SUCCESS': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{color}[{level}]{Colors.END} {message}")

def run_command(cmd, cwd=None):
    """Ejecutar comando"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def stop_services():
    """Detener todos los servicios de FungiGT"""
    log('INFO', "🛑 Deteniendo servicios de FungiGT...")
    
    project_root = Path(__file__).parent.parent.parent
    
    # Detener servicios
    success, stdout, stderr = run_command([
        "docker", "compose", "-p", "fungigt",
        "-f", str(project_root / "docker-compose.yml"),
        "down"
    ], cwd=project_root)
    
    if success:
        log('SUCCESS', "✅ Servicios detenidos exitosamente")
    else:
        log('ERROR', f"❌ Error deteniendo servicios: {stderr}")
        return False
    
    # Mostrar estado
    success, stdout, stderr = run_command([
        "docker", "compose", "-p", "fungigt", "ps"
    ], cwd=project_root)
    
    if stdout.strip():
        print(f"\n{Colors.YELLOW}Estado de servicios:{Colors.END}")
        print(stdout)
    else:
        log('SUCCESS', "🎉 Todos los servicios han sido detenidos")
    
    return True

def main():
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 50)
    print("   FUNGIGT - DETENER SERVICIOS")
    print("=" * 50)
    print(f"{Colors.END}")
    
    try:
        if stop_services():
            log('SUCCESS', "🚀 Operación completada")
            return 0
        else:
            log('ERROR', "💥 Operación falló")
            return 1
    except KeyboardInterrupt:
        log('WARNING', "⚠️ Operación cancelada")
        return 1

if __name__ == "__main__":
    sys.exit(main())