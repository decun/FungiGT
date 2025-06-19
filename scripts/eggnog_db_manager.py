#!/usr/bin/env python3
"""
Script de Gestión de Base de Datos eggNOG para FungiGT
====================================================

Este script proporciona funcionalidades para:
- Verificar el estado de la base de datos eggNOG
- Descargar la base de datos con confirmación del usuario
- Gestionar el almacenamiento y limpieza
- Mostrar estadísticas de uso

Uso:
    python eggnog_db_manager.py --check        # Verificar estado
    python eggnog_db_manager.py --download     # Descargar con confirmación
    python eggnog_db_manager.py --force        # Descargar sin confirmación
    python eggnog_db_manager.py --clean        # Limpiar archivos temporales
    python eggnog_db_manager.py --info         # Mostrar información detallada
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import shutil

class EggNOGDatabaseManager:
    def __init__(self, data_dir='./data/eggnog_db'):
        self.data_dir = Path(data_dir).resolve()
        self.container_image = 'nanozoo/eggnog-mapper:2.1.9--4f2b6c0'
        self.required_files = [
            'eggnog.db',
            'eggnog_proteins.dmnd',
            'pfam.hmm',
            'pfam.hmm.h3f',
            'pfam.hmm.h3i',
            'pfam.hmm.h3m',
            'pfam.hmm.h3p'
        ]
        
    def check_docker(self):
        """Verificar que Docker esté disponible"""
        try:
            subprocess.run(['docker', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_database_status(self):
        """Obtener estado actual de la base de datos"""
        if not self.data_dir.exists():
            return {
                'status': 'not_found',
                'files_found': 0,
                'total_files': len(self.required_files),
                'size_gb': 0,
                'last_modified': None
            }
        
        files_found = 0
        total_size = 0
        last_modified = None
        
        for file_name in self.required_files:
            file_path = self.data_dir / file_name
            if file_path.exists():
                files_found += 1
                stat = file_path.stat()
                total_size += stat.st_size
                if last_modified is None or stat.st_mtime > last_modified:
                    last_modified = stat.st_mtime
        
        if files_found == len(self.required_files):
            status = 'complete'
        elif files_found > 0:
            status = 'partial'
        else:
            status = 'empty'
        
        return {
            'status': status,
            'files_found': files_found,
            'total_files': len(self.required_files),
            'size_gb': total_size / (1024**3),
            'last_modified': datetime.fromtimestamp(last_modified).isoformat() if last_modified else None
        }
    
    def print_status(self):
        """Mostrar estado de la base de datos"""
        status = self.get_database_status()
        
        print("\n" + "="*60)
        print("🧬 ESTADO DE BASE DE DATOS eggNOG-mapper")
        print("="*60)
        
        if status['status'] == 'complete':
            print(f"✅ Estado: COMPLETA")
            print(f"📁 Ubicación: {self.data_dir}")
            print(f"📊 Archivos: {status['files_found']}/{status['total_files']}")
            print(f"💾 Tamaño: {status['size_gb']:.2f} GB")
            if status['last_modified']:
                print(f"🕐 Última modificación: {status['last_modified']}")
        elif status['status'] == 'partial':
            print(f"⚠️  Estado: PARCIAL ({status['files_found']}/{status['total_files']} archivos)")
            print(f"📁 Ubicación: {self.data_dir}")
            print(f"💾 Tamaño actual: {status['size_gb']:.2f} GB")
            print(f"🔄 Recomendación: Ejecutar descarga completa")
        elif status['status'] == 'empty':
            print(f"📂 Estado: DIRECTORIO VACÍO")
            print(f"📁 Ubicación: {self.data_dir}")
        else:
            print(f"❌ Estado: NO ENCONTRADA")
            print(f"📁 Ubicación esperada: {self.data_dir}")
        
        print("="*60)
    
    def confirm_download(self):
        """Solicitar confirmación para descarga"""
        print("\n" + "⚠️ "*20)
        print("CONFIRMACIÓN DE DESCARGA DE BASE DE DATOS eggNOG")
        print("⚠️ "*20)
        print()
        print("📋 INFORMACIÓN IMPORTANTE:")
        print("   • Tamaño estimado: ~2.9 GB")
        print("   • Tiempo estimado: 10-30 minutos")
        print("   • Requiere conexión a internet estable")
        print("   • Se descargará en:", self.data_dir)
        print()
        print("🔍 ARCHIVOS QUE SE DESCARGARÁN:")
        for file_name in self.required_files:
            print(f"   • {file_name}")
        print()
        
        while True:
            response = input("¿Desea continuar con la descarga? [s/N]: ").strip().lower()
            if response in ['s', 'si', 'sí', 'y', 'yes']:
                return True
            elif response in ['n', 'no', ''] or not response:
                return False
            else:
                print("Por favor, responda 's' para sí o 'n' para no.")
    
    def download_database(self, force=False):
        """Descargar base de datos eggNOG"""
        if not self.check_docker():
            print("❌ Error: Docker no está disponible. Por favor, instale Docker primero.")
            return False
        
        status = self.get_database_status()
        
        if status['status'] == 'complete' and not force:
            print("✅ La base de datos ya está completa.")
            print(f"📊 Archivos: {status['files_found']}/{status['total_files']}")
            print(f"💾 Tamaño: {status['size_gb']:.2f} GB")
            return True
        
        if not force and not self.confirm_download():
            print("❌ Descarga cancelada por el usuario.")
            return False
        
        # Crear directorio si no existe
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📥 Iniciando descarga de base de datos eggNOG...")
        print(f"📁 Directorio destino: {self.data_dir}")
        
        try:
            # Comando para descargar la base de datos
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{self.data_dir}:/data/eggnog_db',
                self.container_image,
                'download_eggnog_data.py',
                '--data_dir', '/data/eggnog_db',
                '-y'  # Confirmar automáticamente
            ]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("⏳ Por favor, espere. Esto puede tardar varios minutos...")
            
            # Ejecutar comando con output en tiempo real
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Mostrar output en tiempo real
            for line in process.stdout:
                print(f"📝 {line.rstrip()}")
            
            process.wait()
            
            if process.returncode == 0:
                print("\n✅ Descarga completada exitosamente!")
                self.print_status()
                return True
            else:
                print(f"\n❌ Error en la descarga (código: {process.returncode})")
                return False
                
        except Exception as e:
            print(f"❌ Error ejecutando descarga: {e}")
            return False
    
    def clean_temporary_files(self):
        """Limpiar archivos temporales"""
        temp_extensions = ['.tmp', '.temp', '.download', '.partial']
        cleaned_files = []
        
        if self.data_dir.exists():
            for file_path in self.data_dir.rglob('*'):
                if file_path.is_file():
                    if any(file_path.name.endswith(ext) for ext in temp_extensions):
                        try:
                            file_path.unlink()
                            cleaned_files.append(file_path.name)
                        except Exception as e:
                            print(f"⚠️  No se pudo eliminar {file_path.name}: {e}")
        
        if cleaned_files:
            print(f"🧹 Archivos temporales eliminados: {len(cleaned_files)}")
            for file_name in cleaned_files:
                print(f"   • {file_name}")
        else:
            print("✨ No se encontraron archivos temporales para limpiar")
    
    def get_detailed_info(self):
        """Obtener información detallada"""
        status = self.get_database_status()
        
        info = {
            'container_image': self.container_image,
            'data_directory': str(self.data_dir),
            'docker_available': self.check_docker(),
            'database_status': status,
            'required_files': self.required_files,
            'timestamp': datetime.now().isoformat()
        }
        
        if status['status'] == 'complete':
            # Obtener información detallada de cada archivo
            file_details = {}
            for file_name in self.required_files:
                file_path = self.data_dir / file_name
                if file_path.exists():
                    stat = file_path.stat()
                    file_details[file_name] = {
                        'size_mb': stat.st_size / (1024**2),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
            info['file_details'] = file_details
        
        return info
    
    def print_detailed_info(self):
        """Mostrar información detallada"""
        info = self.get_detailed_info()
        
        print("\n" + "="*80)
        print("🔍 INFORMACIÓN DETALLADA - eggNOG Database Manager")
        print("="*80)
        
        print(f"🐳 Imagen Docker: {info['container_image']}")
        print(f"📁 Directorio de datos: {info['data_directory']}")
        print(f"🔧 Docker disponible: {'✅ Sí' if info['docker_available'] else '❌ No'}")
        print(f"⏰ Timestamp: {info['timestamp']}")
        
        print(f"\n📊 ESTADO DE BASE DE DATOS:")
        status = info['database_status']
        print(f"   Estado: {status['status'].upper()}")
        print(f"   Archivos encontrados: {status['files_found']}/{status['total_files']}")
        print(f"   Tamaño total: {status['size_gb']:.2f} GB")
        
        if 'file_details' in info:
            print(f"\n📋 DETALLES DE ARCHIVOS:")
            for file_name, details in info['file_details'].items():
                print(f"   • {file_name}")
                print(f"     - Tamaño: {details['size_mb']:.2f} MB")
                print(f"     - Modificado: {details['modified']}")
        
        print("\n🎯 ARCHIVOS REQUERIDOS:")
        for file_name in info['required_files']:
            file_path = Path(info['data_directory']) / file_name
            exists = file_path.exists()
            print(f"   {'✅' if exists else '❌'} {file_name}")
        
        print("="*80)

def main():
    parser = argparse.ArgumentParser(
        description='Gestor de Base de Datos eggNOG para FungiGT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python %(prog)s --check                    # Verificar estado
  python %(prog)s --download                 # Descargar con confirmación
  python %(prog)s --force                    # Descargar sin confirmación
  python %(prog)s --clean                    # Limpiar archivos temporales
  python %(prog)s --info                     # Información detallada
  python %(prog)s --data-dir /path/to/db     # Usar directorio personalizado
        """
    )
    
    parser.add_argument('--check', action='store_true',
                       help='Verificar estado de la base de datos')
    parser.add_argument('--download', action='store_true',
                       help='Descargar base de datos (con confirmación)')
    parser.add_argument('--force', action='store_true',
                       help='Descargar sin confirmación')
    parser.add_argument('--clean', action='store_true',
                       help='Limpiar archivos temporales')
    parser.add_argument('--info', action='store_true',
                       help='Mostrar información detallada')
    parser.add_argument('--data-dir', default='./data/eggnog_db',
                       help='Directorio de la base de datos (default: ./data/eggnog_db)')
    parser.add_argument('--json', action='store_true',
                       help='Salida en formato JSON')
    
    args = parser.parse_args()
    
    if not any([args.check, args.download, args.force, args.clean, args.info]):
        parser.print_help()
        return
    
    manager = EggNOGDatabaseManager(args.data_dir)
    
    try:
        if args.info:
            if args.json:
                info = manager.get_detailed_info()
                print(json.dumps(info, indent=2))
            else:
                manager.print_detailed_info()
        
        elif args.check:
            if args.json:
                status = manager.get_database_status()
                print(json.dumps(status, indent=2))
            else:
                manager.print_status()
        
        elif args.clean:
            manager.clean_temporary_files()
        
        elif args.download or args.force:
            success = manager.download_database(force=args.force)
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 