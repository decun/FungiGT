#!/usr/bin/env python3
"""
Clase Base para Visualizadores Genómicos de FungiGT
===================================================

Clase abstracta que define la interfaz común para todos los visualizadores
especializados de diferentes tipos de archivos genómicos.
"""

import os
import json
import logging
import tempfile
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend no interactivo
import matplotlib.pyplot as plt
import seaborn as sns

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar estilo de matplotlib
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class BaseVisualizer(ABC):
    """
    Clase base abstracta para todos los visualizadores genómicos.
    
    Define la interfaz común y funcionalidades básicas que todos los
    visualizadores especializados deben implementar.
    """
    
    def __init__(self, output_dir: Path, config: Optional[Dict] = None):
        """
        Inicializar visualizador base.
        
        Args:
            output_dir: Directorio donde guardar los gráficos generados
            config: Configuración específica del visualizador
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = config or {}
        self.temp_dir = self.output_dir / 'temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        # Configuración por defecto
        self.default_figsize = (12, 8)
        self.default_dpi = 300
        self.default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        logger.info(f"✅ {self.__class__.__name__} inicializado con directorio: {output_dir}")
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Retornar lista de extensiones de archivo soportadas.
        
        Returns:
            Lista de extensiones (ej: ['.txt', '.tsv', '.csv'])
        """
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """
        Validar que el archivo sea compatible con este visualizador.
        
        Args:
            file_path: Ruta al archivo a validar
            
        Returns:
            True si el archivo es válido, False en caso contrario
        """
        pass
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """
        Parsear archivo y convertir a DataFrame.
        
        Args:
            file_path: Ruta al archivo a parsear
            
        Returns:
            DataFrame con los datos parseados
        """
        pass
    
    @abstractmethod
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """
        Generar todas las visualizaciones para los datos.
        
        Args:
            data: DataFrame con los datos parseados
            
        Returns:
            Lista de rutas a los archivos de gráficos generados
        """
        pass
    
    @abstractmethod
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generar estadísticas descriptivas de los datos.
        
        Args:
            data: DataFrame con los datos
            
        Returns:
            Diccionario con estadísticas
        """
        pass
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Método principal para procesar un archivo completo.
        
        Args:
            file_path: Ruta al archivo a procesar
            
        Returns:
            Diccionario con resultados del procesamiento
        """
        try:
            logger.info(f"🔍 Procesando archivo: {file_path.name}")
            
            # Validar archivo
            if not self.validate_file(file_path):
                raise ValueError(f"Archivo no válido para {self.__class__.__name__}")
            
            # Parsear datos
            data = self.parse_file(file_path)
            logger.info(f"📊 Datos parseados: {len(data)} filas")
            
            if data.empty:
                raise ValueError("No se encontraron datos válidos en el archivo")
            
            # Generar visualizaciones
            graphs = self.generate_visualizations(data)
            logger.info(f"📈 Generados {len(graphs)} gráficos")
            
            # Generar estadísticas
            stats = self.generate_statistics(data)
            
            # Generar resumen de datos
            data_summary = self.generate_data_summary(data)
            
            return {
                'graphs': graphs,
                'stats': stats,
                'data_summary': data_summary,
                'visualizer': self.__class__.__name__,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando archivo: {e}")
            return self.create_error_visualization(file_path, str(e))
    
    def generate_data_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generar resumen básico de los datos.
        
        Args:
            data: DataFrame con los datos
            
        Returns:
            Diccionario con resumen de datos
        """
        return {
            'total_rows': len(data),
            'total_columns': len(data.columns),
            'columns': list(data.columns),
            'data_types': {col: str(dtype) for col, dtype in data.dtypes.items()},
            'missing_values': data.isnull().sum().to_dict(),
            'memory_usage': f"{data.memory_usage(deep=True).sum() / 1024:.2f} KB"
        }
    
    def create_error_visualization(self, file_path: Path, error_msg: str) -> Dict[str, Any]:
        """
        Crear visualización de error cuando falla el procesamiento.
        
        Args:
            file_path: Ruta al archivo que causó el error
            error_msg: Mensaje de error
            
        Returns:
            Diccionario con visualización de error
        """
        try:
            plt.figure(figsize=self.default_figsize)
            plt.text(0.5, 0.5, 
                    f'❌ Error procesando archivo\n\n'
                    f'Archivo: {file_path.name}\n'
                    f'Visualizador: {self.__class__.__name__}\n'
                    f'Error: {error_msg}',
                    ha='center', va='center', fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightcoral", alpha=0.8))
            plt.xlim(0, 1)
            plt.ylim(0, 1)
            plt.axis('off')
            plt.title(f'Error en {self.__class__.__name__}', fontsize=16, fontweight='bold')
            
            error_path = self.output_dir / f'error_{self.__class__.__name__.lower()}.png'
            plt.savefig(error_path, dpi=self.default_dpi, bbox_inches='tight')
            plt.close()
            
            return {
                'graphs': [str(error_path)],
                'stats': {},
                'data_summary': {},
                'error': error_msg,
                'visualizer': self.__class__.__name__,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creando visualización de error: {e}")
            return {
                'graphs': [],
                'stats': {},
                'data_summary': {},
                'error': f"Error crítico: {error_msg}",
                'visualizer': self.__class__.__name__,
                'timestamp': datetime.now().isoformat()
            }
    
    def save_figure(self, filename: str, fig: Optional[plt.Figure] = None) -> str:
        """
        Guardar figura de matplotlib con configuración estándar.
        
        Args:
            filename: Nombre del archivo (sin extensión)
            fig: Figura de matplotlib (usa plt.gcf() si no se proporciona)
            
        Returns:
            Ruta al archivo guardado
        """
        if fig is None:
            fig = plt.gcf()
        
        file_path = self.output_dir / f"{filename}.png"
        fig.savefig(file_path, dpi=self.default_dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        return str(file_path)
    
    def create_basic_plot(self, title: str, message: str, color: str = "lightblue") -> str:
        """
        Crear gráfico básico con mensaje de información.
        
        Args:
            title: Título del gráfico
            message: Mensaje a mostrar
            color: Color de fondo del mensaje
            
        Returns:
            Ruta al archivo generado
        """
        plt.figure(figsize=self.default_figsize)
        plt.text(0.5, 0.5, message,
                ha='center', va='center', fontsize=14,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color))
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')
        plt.title(title, fontsize=16, fontweight='bold')
        
        return self.save_figure(f'basic_{self.__class__.__name__.lower()}')
    
    def cleanup_temp_files(self):
        """Limpiar archivos temporales."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(exist_ok=True)
            logger.info("🧹 Archivos temporales limpiados")
        except Exception as e:
            logger.warning(f"Error limpiando archivos temporales: {e}")
    
    def __del__(self):
        """Destructor - limpiar recursos."""
        try:
            self.cleanup_temp_files()
        except:
            pass  # Evitar errores en destructor 