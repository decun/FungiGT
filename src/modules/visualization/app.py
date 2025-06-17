#!/usr/bin/env python3
"""
Servidor Principal de Visualización para FungiGT
===============================================

Servidor Flask que integra múltiples visualizadores especializados para
diferentes tipos de archivos genómicos y bioinformáticos.

Visualizadores disponibles:
- BinDashVisualizer: Análisis genómico comparativo
- AnnotationsVisualizer: Anotaciones funcionales
- HMMERVisualizer: Dominios proteicos
- SeedOrthologsVisualizer: Análisis filogenético
- QualityControlVisualizer: Métricas de calidad
- PhylogenyVisualizer: Árboles filogenéticos
"""

import os
import sys
import json
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

# Importar visualizadores especializados
sys.path.append(str(Path(__file__).parent))
from visualizers.bindash_visualizer import BinDashVisualizer
from visualizers.base_visualizer import BaseVisualizer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración CORS
CORS(app, origins=[
    'http://localhost:4005',
    'http://localhost:3000', 
    'http://localhost:4000',
    'http://localhost:4001'
], supports_credentials=True)

# Configuración de directorios
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'outputs'
TEMP_DIR = BASE_DIR / 'temp'

# Crear directorios si no existen
for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuración de archivos permitidos por tipo
FILE_TYPE_CONFIGS = {
    'bindash': {
        'extensions': ['.txt', '.tsv', '.csv', '.out', '.distances'],
        'visualizer_class': BinDashVisualizer,
        'description': 'Análisis genómico comparativo con BinDash'
    },
    'annotations': {
        'extensions': ['.annotations', '.emapper.annotations', '.eggnog'],
        'visualizer_class': None,  # TODO: Implementar
        'description': 'Anotaciones funcionales de genes'
    },
    'hmmer': {
        'extensions': ['.txt', '.out', '.analyze.txt', '.domtblout'],
        'visualizer_class': None,  # TODO: Implementar
        'description': 'Análisis de dominios proteicos con HMMER'
    },
    'seed_orthologs': {
        'extensions': ['.seed_orthologs', '.orthologs'],
        'visualizer_class': None,  # TODO: Implementar
        'description': 'Análisis de ortólogos y filogenética'
    },
    'quality_control': {
        'extensions': ['.qc', '.quality', '.stats'],
        'visualizer_class': None,  # TODO: Implementar
        'description': 'Métricas de calidad genómica'
    }
}

def detect_file_type(file_path: Path) -> Optional[str]:
    """
    Detectar automáticamente el tipo de archivo genómico.
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tipo de archivo detectado o None si no se reconoce
    """
    # Detectar por extensión
    suffix = file_path.suffix.lower()
    
    for file_type, config in FILE_TYPE_CONFIGS.items():
        if suffix in config['extensions']:
            return file_type
    
    # Detectar por contenido
    try:
        with open(file_path, 'r') as f:
            content = f.read(1000)  # Leer primeras líneas
            
        # Detectar BinDash por contenido
        if any(keyword in content.lower() for keyword in ['query', 'target', 'mutation_distance', 'jaccard']):
            return 'bindash'
            
        # Detectar anotaciones por contenido
        if any(keyword in content.lower() for keyword in ['go:', 'kegg:', 'pfam:', 'cog']):
            return 'annotations'
            
        # Detectar HMMER por contenido
        if any(keyword in content.lower() for keyword in ['domain', 'evalue', 'bitscore']):
            return 'hmmer'
            
    except Exception:
        pass
    
    return None

def get_visualizer(file_type: str, output_dir: Path) -> Optional[BaseVisualizer]:
    """
    Obtener instancia del visualizador apropiado.
    
    Args:
        file_type: Tipo de archivo
        output_dir: Directorio de salida
        
    Returns:
        Instancia del visualizador o None si no está disponible
    """
    config = FILE_TYPE_CONFIGS.get(file_type)
    if not config or not config['visualizer_class']:
        return None
    
    return config['visualizer_class'](output_dir)

def create_fallback_visualization(file_path: Path, output_dir: Path, file_type: str) -> Dict[str, Any]:
    """
    Crear visualización básica cuando no hay visualizador especializado.
    
    Args:
        file_path: Ruta al archivo
        output_dir: Directorio de salida
        file_type: Tipo de archivo
        
    Returns:
        Resultado de visualización básica
    """
    import matplotlib.pyplot as plt
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 
                f'📊 Archivo Genómico Cargado\n\n'
                f'Tipo: {file_type.upper()}\n'
                f'Archivo: {file_path.name}\n'
                f'Líneas: {len(lines)}\n'
                f'Tamaño: {file_path.stat().st_size / 1024:.1f} KB\n\n'
                f'⚠️ Visualizador especializado en desarrollo',
                ha='center', va='center', fontsize=14,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')
        plt.title(f'Archivo {file_type.upper()} - En Desarrollo', fontsize=16, fontweight='bold')
        
        graph_path = output_dir / f'fallback_{file_type}.png'
        plt.savefig(graph_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'graphs': [f"/graphs/{graph_path.relative_to(OUTPUT_DIR)}"],
            'stats': {
                'file_type': file_type,
                'lines_count': len(lines),
                'file_size_kb': file_path.stat().st_size / 1024
            },
            'data_summary': {
                'total_rows': len(lines),
                'file_type': file_type,
                'status': 'visualizer_in_development'
            },
            'message': f'Visualizador para {file_type} en desarrollo'
        }
        
    except Exception as e:
        logger.error(f"Error creando visualización fallback: {e}")
        return {
            'graphs': [],
            'stats': {},
            'data_summary': {},
            'error': str(e)
        }

def clean_old_files():
    """Limpiar archivos temporales antiguos (más de 4 horas para mejor caching)"""
    import time
    current_time = time.time()
    
    for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
        if directory.exists():
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 14400:  # 4 horas (mejorado de 2 horas)
                        try:
                            file_path.unlink()
                            logger.info(f"Archivo eliminado: {file_path}")
                        except Exception as e:
                            logger.error(f"Error eliminando {file_path}: {e}")

# ========== RUTAS PRINCIPALES ==========

@app.route('/')
def index():
    """Ruta principal del servidor de visualización"""
    return jsonify({
        'service': 'FungiGT Multi-Genomic Visualization Server',
        'version': '2.0.0',
        'status': 'running',
        'supported_file_types': {
            file_type: {
                'extensions': config['extensions'],
                'description': config['description'],
                'available': config['visualizer_class'] is not None
            }
            for file_type, config in FILE_TYPE_CONFIGS.items()
        },
        'endpoints': [
            'GET / - Estado del servidor',
            'POST /process-file - Procesar cualquier archivo genómico (auto-detección)',
            'POST /process-bindash - Procesar archivos BinDash específicamente',
            'GET /graphs/<path> - Servir gráficos generados',
            'POST /cleanup - Limpiar archivos temporales',
            'GET /supported-types - Ver tipos de archivos soportados'
        ]
    })

@app.route('/health')
def health_check():
    """Health check del servidor"""
    return jsonify({
        'status': 'healthy',
        'service': 'multi-genomic-visualization',
        'timestamp': datetime.now().isoformat(),
        'available_visualizers': [
            file_type for file_type, config in FILE_TYPE_CONFIGS.items()
            if config['visualizer_class'] is not None
        ]
    })

@app.route('/supported-types')
def supported_types():
    """Listar tipos de archivos soportados"""
    return jsonify({
        'supported_types': FILE_TYPE_CONFIGS,
        'auto_detection': True,
        'fallback_visualization': True
    })

# ========== PROCESAMIENTO UNIVERSAL DE ARCHIVOS ==========

@app.route('/process-file', methods=['POST'])
def process_file():
    """
    Endpoint universal para procesar cualquier tipo de archivo genómico.
    Detecta automáticamente el tipo y usa el visualizador apropiado.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        # Guardar archivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_path = UPLOAD_DIR / f"{timestamp}_{filename}"
        file.save(upload_path)
        
        # Detectar tipo de archivo
        file_type = detect_file_type(upload_path)
        if not file_type:
            upload_path.unlink()
            return jsonify({'error': 'Tipo de archivo no reconocido'}), 400
        
        logger.info(f"📁 Archivo detectado como: {file_type}")
        
        # Crear directorio de salida
        output_dir = OUTPUT_DIR / f"{file_type}_{timestamp}"
        output_dir.mkdir(exist_ok=True)
        
        # Obtener visualizador apropiado
        visualizer = get_visualizer(file_type, output_dir)
        
        if visualizer:
            # Usar visualizador especializado
            result = visualizer.process_file(upload_path)
            # Convertir rutas absolutas a URLs relativas
            if 'graphs' in result:
                graphs_urls = []
                for graph_path in result['graphs']:
                    if isinstance(graph_path, str):
                        graph_file = Path(graph_path)
                        if graph_file.exists():
                            relative_path = graph_file.relative_to(OUTPUT_DIR)
                            graphs_urls.append(f"/graphs/{relative_path}")
                result['graphs'] = graphs_urls
        else:
            # Usar visualización fallback
            result = create_fallback_visualization(upload_path, output_dir, file_type)
        
        # Limpiar archivo temporal
        upload_path.unlink()
        
        return jsonify({
            'message': f'Archivo {file_type} procesado exitosamente',
            'file_type': file_type,
            'visualizer': result.get('visualizer', f'{file_type}_fallback'),
            **result
        })
        
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process-bindash', methods=['POST'])
def process_bindash():
    """Endpoint específico para archivos BinDash (compatibilidad)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        # Guardar archivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_path = UPLOAD_DIR / f"bindash_{timestamp}_{filename}"
        file.save(upload_path)
        
        # Crear directorio de salida
        output_dir = OUTPUT_DIR / f"bindash_{timestamp}"
        output_dir.mkdir(exist_ok=True)
        
        # Usar visualizador BinDash
        visualizer = BinDashVisualizer(output_dir)
        result = visualizer.process_file(upload_path)
        
        # Convertir rutas a URLs relativas
        if 'graphs' in result:
            graphs_urls = []
            for graph_path in result['graphs']:
                if isinstance(graph_path, str):
                    graph_file = Path(graph_path)
                    if graph_file.exists():
                        relative_path = graph_file.relative_to(OUTPUT_DIR)
                        graphs_urls.append(f"/graphs/{relative_path}")
            result['graphs'] = graphs_urls
        
        # Limpiar archivo temporal
        upload_path.unlink()
        
        return jsonify({
            'message': 'Archivo BinDash procesado exitosamente',
            'file_type': 'bindash',
            **result
        })
        
    except Exception as e:
        logger.error(f"Error procesando BinDash: {e}")
        return jsonify({'error': str(e)}), 500

# ========== RUTAS DE SERVICIO ==========

@app.route('/graphs/<path:filename>')
def serve_graph(filename):
    """Servir archivos de gráficos"""
    try:
        return send_from_directory(OUTPUT_DIR, filename)
    except Exception as e:
        logger.error(f"Error sirviendo gráfico {filename}: {e}")
        return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Limpiar archivos temporales"""
    try:
        clean_old_files()
        return jsonify({'message': 'Limpieza completada'})
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_uploads', methods=['POST'])
def clear_uploads():
    """Limpiar directorio uploads completamente"""
    try:
        # Verificar autorización básica
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != 'Bearer tu_token_secreto':
            return jsonify({'error': 'No autorizado'}), 401
        
        # Limpiar directorio uploads
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
        
        return jsonify({'status': 'success', 'message': 'Directorio uploads limpiado'})
        
    except Exception as e:
        logger.error(f"Error limpiando uploads: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ========== INICIALIZACIÓN ==========

if __name__ == '__main__':
    logger.info("🧬 Iniciando Servidor Multi-Genómico de Visualización FungiGT...")
    logger.info(f"📁 Directorio uploads: {UPLOAD_DIR}")
    logger.info(f"📊 Directorio outputs: {OUTPUT_DIR}")
    
    # Mostrar visualizadores disponibles
    available = [ft for ft, config in FILE_TYPE_CONFIGS.items() if config['visualizer_class']]
    in_development = [ft for ft, config in FILE_TYPE_CONFIGS.items() if not config['visualizer_class']]
    
    logger.info(f"✅ Visualizadores disponibles: {', '.join(available)}")
    logger.info(f"🚧 En desarrollo: {', '.join(in_development)}")
    logger.info("🚀 Servidor disponible en http://localhost:4003")
    
    # Limpiar archivos al iniciar
    clean_old_files()
    
    app.run(host='0.0.0.0', port=4003, debug=True) 