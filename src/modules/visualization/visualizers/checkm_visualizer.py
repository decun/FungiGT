#!/usr/bin/env python3
"""
Visualizador CheckM para FungiGT
===============================

Visualizador especializado para archivos de resultados CheckM,
incluyendo análisis de calidad genómica, completitud, contaminación,
y estadísticas de genomas.

Tipos de archivos soportados:
- Resultados QA (.tsv)  
- Análisis de linaje (.tsv)
- Estadísticas de bins (.tsv)
- Archivos FASTA (.fna, .fasta, .fa)
- Archivos de marcadores (.marker_stats)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from .base_visualizer import BaseVisualizer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intentar importar BioPython para análisis FASTA
try:
    from Bio import SeqIO
    from Bio.SeqUtils import gc_fraction
    BIOPYTHON_AVAILABLE = True
    logger.info("✅ BioPython disponible para análisis FASTA")
except ImportError:
    BIOPYTHON_AVAILABLE = False
    logger.warning("⚠️ BioPython no disponible - análisis FASTA limitado")

class CheckMVisualizer(BaseVisualizer):
    """
    Visualizador especializado para resultados CheckM.
    
    Genera múltiples tipos de gráficos y análisis estadísticos
    para evaluación de calidad genómica.
    """
    
    def __init__(self, output_dir: Path, config: Optional[Dict] = None):
        """
        Inicializar visualizador CheckM.
        
        Args:
            output_dir: Directorio de salida para gráficos
            config: Configuración adicional
        """
        super().__init__(output_dir, config)
        
        # Configuración específica de CheckM
        self.quality_thresholds = {
            'high_quality': {'completeness': 90, 'contamination': 5},
            'medium_quality': {'completeness': 70, 'contamination': 10},
            'low_quality': {'completeness': 50, 'contamination': 15}
        }
        
        # Colores para calidad
        self.quality_colors = {
            'high': '#2E8B57',      # Verde oscuro
            'medium': '#FFD700',    # Dorado  
            'low': '#FF6347',       # Rojo tomate
            'very_low': '#8B0000'   # Rojo oscuro
        }
        
        logger.info("🔬 CheckMVisualizer inicializado correctamente")
    
    def get_supported_extensions(self) -> List[str]:
        """Extensiones de archivo soportadas."""
        return ['.tsv', '.txt', '.csv', '.qa', '.stats', '.fna', '.fasta', '.fa', '.marker_stats']
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validar que el archivo sea compatible con CheckM.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            True si es válido, False en caso contrario
        """
        try:
            if not file_path.exists():
                return False
            
            # Verificar extensión
            if file_path.suffix.lower() not in self.get_supported_extensions():
                return False
            
            # Verificar contenido para archivos de texto
            if file_path.suffix.lower() in ['.tsv', '.txt', '.csv']:
                with open(file_path, 'r') as f:
                    first_line = f.readline().lower()
                    # Buscar patrones típicos de CheckM
                    checkm_patterns = [
                        'bin id', 'completeness', 'contamination', 
                        'lineage', 'marker', 'gc', 'genome size'
                    ]
                    return any(pattern in first_line for pattern in checkm_patterns)
            
            # Para archivos FASTA, verificar formato
            elif file_path.suffix.lower() in ['.fna', '.fasta', '.fa']:
                with open(file_path, 'r') as f:
                    first_line = f.readline().strip()
                    return first_line.startswith('>')
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando archivo: {e}")
            return False
    
    def detect_file_type(self, file_path: Path) -> str:
        """
        Detectar el tipo específico de archivo CheckM.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Tipo de archivo detectado
        """
        filename = file_path.name.lower()
        
        # Detección por nombre de archivo
        if 'qa' in filename and ('.tsv' in filename or '.txt' in filename):
            return 'qa_results'
        elif 'lineage' in filename:
            return 'lineage_analysis'
        elif 'bin' in filename and 'stats' in filename:
            return 'bin_stats'
        elif 'marker' in filename:
            return 'marker_stats'
        elif filename.endswith(('.fna', '.fasta', '.fa')):
            return 'fasta_analysis'
        
        # Detección por contenido
        try:
            with open(file_path, 'r') as f:
                header = f.readline().lower()
                
            if 'completeness' in header and 'contamination' in header:
                return 'qa_results'
            elif 'lineage' in header:
                return 'lineage_analysis'
            elif 'marker' in header:
                return 'marker_stats'
            elif header.startswith('>'):
                return 'fasta_analysis'
                
        except Exception:
            pass
        
        return 'general_checkm'
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """
        Parsear archivo CheckM según su tipo.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            DataFrame con datos parseados
        """
        file_type = self.detect_file_type(file_path)
        logger.info(f"📊 Parseando archivo tipo: {file_type}")
        
        if file_type == 'fasta_analysis':
            return self._parse_fasta_file(file_path)
        elif file_type in ['qa_results', 'lineage_analysis', 'bin_stats', 'marker_stats']:
            return self._parse_tabular_file(file_path)
        else:
            return self._parse_general_file(file_path)
    
    def _parse_fasta_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo FASTA."""
        if not BIOPYTHON_AVAILABLE:
            raise ValueError("BioPython requerido para análisis FASTA")
        
        sequences = []
        try:
            for record in SeqIO.parse(file_path, "fasta"):
                seq_data = {
                    'sequence_id': record.id,
                    'description': record.description,
                    'length': len(record.seq),
                    'gc_content': gc_fraction(record.seq) * 100
                }
                
                # Calcular estadísticas adicionales
                seq_str = str(record.seq).upper()
                seq_data.update({
                    'n_count': seq_str.count('N'),
                    'n_percentage': (seq_str.count('N') / len(seq_str)) * 100,
                    'at_content': ((seq_str.count('A') + seq_str.count('T')) / len(seq_str)) * 100
                })
                
                sequences.append(seq_data)
            
            return pd.DataFrame(sequences)
            
        except Exception as e:
            raise ValueError(f"Error parseando FASTA: {e}")
    
    def _parse_tabular_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo tabular (TSV/CSV)."""
        try:
            # Detectar separador
            with open(file_path, 'r') as f:
                first_line = f.readline()
                if '\t' in first_line:
                    sep = '\t'
                elif ',' in first_line:
                    sep = ','
                else:
                    sep = '\s+'  # Espacios múltiples
            
            df = pd.read_csv(file_path, sep=sep, comment='#', low_memory=False)
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Convertir columnas numéricas
            numeric_columns = ['completeness', 'contamination', 'strain_heterogeneity', 
                             'genome_size', 'gc_content', 'coding_density', 'translation_table',
                             'n50_contigs', 'mean_contig_length', 'longest_contig']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo tabular: {e}")
    
    def _parse_general_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo general."""
        try:
            return self._parse_tabular_file(file_path)
        except:
            # Fallback para archivos con formato no estándar
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            return pd.DataFrame({
                'line_number': range(1, len(lines) + 1),
                'content': [line.strip() for line in lines]
            })
    
    def classify_genome_quality(self, completeness: float, contamination: float) -> str:
        """
        Clasificar calidad del genoma basado en métricas CheckM.
        
        Args:
            completeness: Porcentaje de completitud
            contamination: Porcentaje de contaminación
            
        Returns:
            Clasificación de calidad
        """
        if completeness >= self.quality_thresholds['high_quality']['completeness'] and \
           contamination <= self.quality_thresholds['high_quality']['contamination']:
            return 'high'
        elif completeness >= self.quality_thresholds['medium_quality']['completeness'] and \
             contamination <= self.quality_thresholds['medium_quality']['contamination']:
            return 'medium'
        elif completeness >= self.quality_thresholds['low_quality']['completeness'] and \
             contamination <= self.quality_thresholds['low_quality']['contamination']:
            return 'low'
        else:
            return 'very_low'
    
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """
        Generar todas las visualizaciones para CheckM.
        
        Args:
            data: DataFrame con datos CheckM
            
        Returns:
            Lista de rutas a gráficos generados
        """
        graphs = []
        file_type = self.detect_file_type(Path('dummy'))  # Detectar por contenido de data
        
        try:
            if 'completeness' in data.columns and 'contamination' in data.columns:
                # Gráficos de calidad
                graphs.extend(self._plot_quality_assessment(data))
                graphs.extend(self._plot_quality_distribution(data))
                graphs.extend(self._plot_quality_scatter(data))
                
                # Si hay más columnas, generar análisis adicionales
                if len(data.columns) > 3:
                    graphs.extend(self._plot_correlation_analysis(data))
                    graphs.extend(self._plot_pca_analysis(data))
            
            elif 'sequence_id' in data.columns and 'length' in data.columns:
                # Análisis FASTA
                graphs.extend(self._plot_sequence_analysis(data))
                graphs.extend(self._plot_gc_analysis(data))
            
            else:
                # Análisis general
                graphs.extend(self._plot_general_statistics(data))
            
            logger.info(f"✅ Generados {len(graphs)} gráficos")
            return graphs
            
        except Exception as e:
            logger.error(f"Error generando visualizaciones: {e}")
            return [self.create_basic_plot("Error en Visualización", str(e), "lightcoral")]
    
    def _plot_quality_assessment(self, data: pd.DataFrame) -> List[str]:
        """Crear gráfico principal de evaluación de calidad."""
        graphs = []
        
        try:
            # Clasificar genomas por calidad
            data['quality'] = data.apply(
                lambda row: self.classify_genome_quality(row['completeness'], row['contamination']),
                axis=1
            )
            
            plt.figure(figsize=(14, 10))
            
            # Subplot 1: Scatter plot principal
            plt.subplot(2, 2, 1)
            
            for quality in ['high', 'medium', 'low', 'very_low']:
                subset = data[data['quality'] == quality]
                if len(subset) > 0:
                    plt.scatter(subset['contamination'], subset['completeness'],
                              c=self.quality_colors[quality], label=f'{quality.replace("_", " ").title()} Quality',
                              alpha=0.7, s=60, edgecolors='black', linewidth=0.5)
            
            # Líneas de referencia
            plt.axhline(y=90, color='green', linestyle='--', alpha=0.5, label='High Quality (>90%)')
            plt.axhline(y=70, color='orange', linestyle='--', alpha=0.5, label='Medium Quality (>70%)')
            plt.axvline(x=5, color='red', linestyle='--', alpha=0.5, label='High Contamination (>5%)')
            plt.axvline(x=10, color='darkred', linestyle='--', alpha=0.5, label='Very High Contamination (>10%)')
            
            plt.xlabel('Contaminación (%)')
            plt.ylabel('Completitud (%)')
            plt.title('Evaluación de Calidad CheckM')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True, alpha=0.3)
            
            # Subplot 2: Distribución de calidad
            plt.subplot(2, 2, 2)
            quality_counts = data['quality'].value_counts()
            colors = [self.quality_colors[q] for q in quality_counts.index]
            plt.pie(quality_counts.values, labels=quality_counts.index, colors=colors, autopct='%1.1f%%')
            plt.title('Distribución de Calidad de Genomas')
            
            # Subplot 3: Histograma de completitud
            plt.subplot(2, 2, 3)
            plt.hist(data['completeness'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            plt.axvline(x=data['completeness'].mean(), color='red', linestyle='--', label=f'Media: {data["completeness"].mean():.1f}%')
            plt.xlabel('Completitud (%)')
            plt.ylabel('Frecuencia')
            plt.title('Distribución de Completitud')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Subplot 4: Histograma de contaminación
            plt.subplot(2, 2, 4)
            plt.hist(data['contamination'], bins=20, alpha=0.7, color='lightcoral', edgecolor='black')
            plt.axvline(x=data['contamination'].mean(), color='red', linestyle='--', label=f'Media: {data["contamination"].mean():.1f}%')
            plt.xlabel('Contaminación (%)')
            plt.ylabel('Frecuencia')
            plt.title('Distribución de Contaminación')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            graphs.append(self.save_figure('quality_assessment'))
            
        except Exception as e:
            logger.error(f"Error en gráfico de calidad: {e}")
        
        return graphs
    
    def _plot_quality_distribution(self, data: pd.DataFrame) -> List[str]:
        """Crear gráficos de distribución de calidad."""
        graphs = []
        
        try:
            plt.figure(figsize=(15, 5))
            
            # Box plot de completitud por calidad
            plt.subplot(1, 3, 1)
            data['quality'] = data.apply(
                lambda row: self.classify_genome_quality(row['completeness'], row['contamination']),
                axis=1
            )
            
            quality_order = ['very_low', 'low', 'medium', 'high']
            box_data = [data[data['quality'] == q]['completeness'].values for q in quality_order if q in data['quality'].values]
            box_labels = [q.replace('_', ' ').title() for q in quality_order if q in data['quality'].values]
            
            plt.boxplot(box_data, labels=box_labels)
            plt.ylabel('Completitud (%)')
            plt.title('Completitud por Calidad')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            
            # Box plot de contaminación por calidad
            plt.subplot(1, 3, 2)
            box_data = [data[data['quality'] == q]['contamination'].values for q in quality_order if q in data['quality'].values]
            
            plt.boxplot(box_data, labels=box_labels)
            plt.ylabel('Contaminación (%)')
            plt.title('Contaminación por Calidad')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            
            # Violin plot combinado
            plt.subplot(1, 3, 3)
            for i, quality in enumerate(quality_order):
                if quality in data['quality'].values:
                    subset = data[data['quality'] == quality]
                    plt.scatter([i+1]*len(subset), subset['completeness'] - subset['contamination'],
                              c=self.quality_colors[quality], alpha=0.6, s=40)
            
            plt.xticks(range(1, len(box_labels)+1), box_labels, rotation=45)
            plt.ylabel('Completitud - Contaminación')
            plt.title('Índice de Calidad Neta')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            graphs.append(self.save_figure('quality_distribution'))
            
        except Exception as e:
            logger.error(f"Error en distribución de calidad: {e}")
        
        return graphs
    
    def _plot_quality_scatter(self, data: pd.DataFrame) -> List[str]:
        """Crear gráficos de dispersión avanzados."""
        graphs = []
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            
            # Scatter con densidad
            ax1 = axes[0, 0]
            scatter = ax1.scatter(data['contamination'], data['completeness'], 
                                c=data['completeness'], cmap='RdYlGn', 
                                s=60, alpha=0.7, edgecolors='black', linewidth=0.5)
            ax1.set_xlabel('Contaminación (%)')
            ax1.set_ylabel('Completitud (%)')
            ax1.set_title('Calidad con Mapa de Color')
            plt.colorbar(scatter, ax=ax1, label='Completitud (%)')
            ax1.grid(True, alpha=0.3)
            
            # Hexbin plot
            ax2 = axes[0, 1]
            hb = ax2.hexbin(data['contamination'], data['completeness'], 
                           gridsize=15, cmap='Blues', alpha=0.7)
            ax2.set_xlabel('Contaminación (%)')
            ax2.set_ylabel('Completitud (%)')
            ax2.set_title('Densidad de Genomas')
            plt.colorbar(hb, ax=ax2, label='Frecuencia')
            
            # Scatter con tamaño de genoma (si disponible)
            ax3 = axes[1, 0]
            if 'genome_size' in data.columns:
                scatter = ax3.scatter(data['contamination'], data['completeness'],
                                    s=data['genome_size']/10000, alpha=0.6,
                                    c='purple', edgecolors='black', linewidth=0.5)
                ax3.set_title('Calidad vs Tamaño de Genoma')
            else:
                ax3.scatter(data['contamination'], data['completeness'], alpha=0.6)
                ax3.set_title('Gráfico de Calidad Estándar')
            
            ax3.set_xlabel('Contaminación (%)')
            ax3.set_ylabel('Completitud (%)')
            ax3.grid(True, alpha=0.3)
            
            # Gráfico de contorno
            ax4 = axes[1, 1]
            try:
                from scipy.stats import gaussian_kde
                x = data['contamination'].values
                y = data['completeness'].values
                
                # Crear grilla
                xi = np.linspace(x.min(), x.max(), 30)
                yi = np.linspace(y.min(), y.max(), 30)
                xi, yi = np.meshgrid(xi, yi)
                
                # Calcular densidad
                kde = gaussian_kde(np.vstack([x, y]))
                zi = kde(np.vstack([xi.flatten(), yi.flatten()]))
                zi = zi.reshape(xi.shape)
                
                ax4.contour(xi, yi, zi, levels=5, colors='black', alpha=0.5)
                ax4.contourf(xi, yi, zi, levels=10, cmap='Blues', alpha=0.7)
                ax4.scatter(x, y, s=20, c='red', alpha=0.5)
                
            except ImportError:
                ax4.scatter(data['contamination'], data['completeness'], alpha=0.6)
            
            ax4.set_xlabel('Contaminación (%)')
            ax4.set_ylabel('Completitud (%)')
            ax4.set_title('Contornos de Densidad')
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            graphs.append(self.save_figure('quality_scatter_advanced'))
            
        except Exception as e:
            logger.error(f"Error en scatter avanzado: {e}")
        
        return graphs
    
    def _plot_correlation_analysis(self, data: pd.DataFrame) -> List[str]:
        """Crear análisis de correlación entre variables."""
        graphs = []
        
        try:
            # Seleccionar columnas numéricas
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_columns) < 2:
                return graphs
            
            plt.figure(figsize=(12, 10))
            
            # Matriz de correlación
            corr_matrix = data[numeric_columns].corr()
            
            # Heatmap de correlación
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
            sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='RdBu_r', 
                       center=0, square=True, fmt='.2f', cbar_kws={'shrink': 0.8})
            
            plt.title('Matriz de Correlación - Variables CheckM')
            plt.tight_layout()
            graphs.append(self.save_figure('correlation_matrix'))
            
            # Pairplot si hay pocas variables
            if len(numeric_columns) <= 6:
                plt.figure(figsize=(15, 15))
                
                # Crear pairplot manual
                n_vars = len(numeric_columns)
                fig, axes = plt.subplots(n_vars, n_vars, figsize=(15, 15))
                
                for i, var1 in enumerate(numeric_columns):
                    for j, var2 in enumerate(numeric_columns):
                        ax = axes[i, j]
                        
                        if i == j:
                            # Diagonal: histograma
                            ax.hist(data[var1], bins=20, alpha=0.7, color='skyblue')
                            ax.set_ylabel('Frecuencia')
                        else:
                            # Off-diagonal: scatter plot
                            ax.scatter(data[var2], data[var1], alpha=0.6, s=20)
                            
                            # Línea de regresión
                            try:
                                z = np.polyfit(data[var2].dropna(), data[var1].dropna(), 1)
                                p = np.poly1d(z)
                                ax.plot(data[var2], p(data[var2]), "r--", alpha=0.8)
                            except:
                                pass
                        
                        if i == n_vars - 1:
                            ax.set_xlabel(var2)
                        if j == 0:
                            ax.set_ylabel(var1)
                        
                        ax.grid(True, alpha=0.3)
                
                plt.suptitle('Análisis Pairwise de Variables CheckM')
                plt.tight_layout()
                graphs.append(self.save_figure('pairplot_analysis'))
            
        except Exception as e:
            logger.error(f"Error en análisis de correlación: {e}")
        
        return graphs
    
    def _plot_pca_analysis(self, data: pd.DataFrame) -> List[str]:
        """Crear análisis de componentes principales."""
        graphs = []
        
        try:
            # Seleccionar columnas numéricas
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_columns) < 3:
                return graphs
            
            # Preparar datos para PCA
            pca_data = data[numeric_columns].dropna()
            
            if len(pca_data) < 3:
                return graphs
            
            # Estandarizar datos
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(pca_data)
            
            # Aplicar PCA
            pca = PCA()
            pca_result = pca.fit_transform(scaled_data)
            
            plt.figure(figsize=(15, 5))
            
            # Varianza explicada
            plt.subplot(1, 3, 1)
            plt.plot(range(1, len(pca.explained_variance_ratio_) + 1), 
                    pca.explained_variance_ratio_, 'bo-')
            plt.xlabel('Componente Principal')
            plt.ylabel('Varianza Explicada')
            plt.title('Varianza Explicada por Componente')
            plt.grid(True, alpha=0.3)
            
            # Varianza acumulada
            plt.subplot(1, 3, 2)
            plt.plot(range(1, len(pca.explained_variance_ratio_) + 1), 
                    np.cumsum(pca.explained_variance_ratio_), 'ro-')
            plt.xlabel('Componente Principal')
            plt.ylabel('Varianza Acumulada')
            plt.title('Varianza Acumulada')
            plt.axhline(y=0.95, color='gray', linestyle='--', label='95%')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Biplot PC1 vs PC2
            plt.subplot(1, 3, 3)
            plt.scatter(pca_result[:, 0], pca_result[:, 1], alpha=0.6, s=40)
            plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} varianza)')
            plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} varianza)')
            plt.title('Biplot PC1 vs PC2')
            plt.grid(True, alpha=0.3)
            
            # Agregar vectores de variables (loadings)
            loadings = pca.components_[:2].T
            for i, var in enumerate(numeric_columns):
                plt.arrow(0, 0, loadings[i, 0]*3, loadings[i, 1]*3, 
                         head_width=0.1, head_length=0.1, fc='red', ec='red', alpha=0.7)
                plt.text(loadings[i, 0]*3.2, loadings[i, 1]*3.2, var, 
                        fontsize=8, ha='center', va='center')
            
            plt.tight_layout()
            graphs.append(self.save_figure('pca_analysis'))
            
        except Exception as e:
            logger.error(f"Error en análisis PCA: {e}")
        
        return graphs
    
    def _plot_sequence_analysis(self, data: pd.DataFrame) -> List[str]:
        """Crear análisis de secuencias FASTA."""
        graphs = []
        
        try:
            plt.figure(figsize=(15, 10))
            
            # Distribución de longitudes
            plt.subplot(2, 3, 1)
            plt.hist(data['length'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
            plt.axvline(x=data['length'].mean(), color='red', linestyle='--', 
                       label=f'Media: {data["length"].mean():.0f} bp')
            plt.xlabel('Longitud (bp)')
            plt.ylabel('Frecuencia')
            plt.title('Distribución de Longitudes')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Log-scale de longitudes
            plt.subplot(2, 3, 2)
            plt.hist(np.log10(data['length']), bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
            plt.xlabel('Log10(Longitud)')
            plt.ylabel('Frecuencia')
            plt.title('Distribución Log de Longitudes')
            plt.grid(True, alpha=0.3)
            
            # Contenido GC
            plt.subplot(2, 3, 3)
            plt.hist(data['gc_content'], bins=30, alpha=0.7, color='orange', edgecolor='black')
            plt.axvline(x=data['gc_content'].mean(), color='red', linestyle='--',
                       label=f'Media: {data["gc_content"].mean():.1f}%')
            plt.xlabel('Contenido GC (%)')
            plt.ylabel('Frecuencia')
            plt.title('Distribución de Contenido GC')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Longitud vs GC
            plt.subplot(2, 3, 4)
            plt.scatter(data['length'], data['gc_content'], alpha=0.6, s=30)
            plt.xlabel('Longitud (bp)')
            plt.ylabel('Contenido GC (%)')
            plt.title('Longitud vs Contenido GC')
            plt.grid(True, alpha=0.3)
            
            # Contenido N (si disponible)
            if 'n_percentage' in data.columns:
                plt.subplot(2, 3, 5)
                plt.hist(data['n_percentage'], bins=20, alpha=0.7, color='red', edgecolor='black')
                plt.xlabel('Porcentaje de Ns (%)')
                plt.ylabel('Frecuencia')
                plt.title('Distribución de Contenido N')
                plt.grid(True, alpha=0.3)
            
            # Estadísticas generales
            plt.subplot(2, 3, 6)
            stats_text = f"""Estadísticas Generales:
            
Total secuencias: {len(data):,}
Longitud total: {data['length'].sum():,} bp
Longitud media: {data['length'].mean():.0f} bp
Longitud mediana: {data['length'].median():.0f} bp
GC medio: {data['gc_content'].mean():.1f}%
N50: {self._calculate_n50(data['length'].tolist()):.0f} bp"""
            
            plt.text(0.05, 0.95, stats_text, transform=plt.gca().transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
            plt.axis('off')
            plt.title('Resumen Estadístico')
            
            plt.tight_layout()
            graphs.append(self.save_figure('sequence_analysis'))
            
        except Exception as e:
            logger.error(f"Error en análisis de secuencias: {e}")
        
        return graphs
    
    def _plot_gc_analysis(self, data: pd.DataFrame) -> List[str]:
        """Análisis detallado de contenido GC."""
        graphs = []
        
        try:
            plt.figure(figsize=(12, 8))
            
            # GC vs AT content
            plt.subplot(2, 2, 1)
            if 'at_content' in data.columns:
                plt.scatter(data['gc_content'], data['at_content'], alpha=0.6)
                plt.xlabel('Contenido GC (%)')
                plt.ylabel('Contenido AT (%)')
                plt.title('GC vs AT Content')
                # Línea diagonal esperada
                plt.plot([0, 100], [100, 0], 'r--', alpha=0.5, label='GC + AT = 100%')
                plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Distribución normal de GC
            plt.subplot(2, 2, 2)
            mu, sigma = stats.norm.fit(data['gc_content'])
            n, bins, patches = plt.hist(data['gc_content'], bins=30, density=True, 
                                       alpha=0.7, color='green', edgecolor='black')
            
            # Curva normal ajustada
            x = np.linspace(data['gc_content'].min(), data['gc_content'].max(), 100)
            plt.plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, 
                    label=f'Normal (μ={mu:.1f}, σ={sigma:.1f})')
            plt.xlabel('Contenido GC (%)')
            plt.ylabel('Densidad')
            plt.title('Ajuste Normal del Contenido GC')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Box plot por rangos de longitud
            plt.subplot(2, 2, 3)
            data['length_category'] = pd.cut(data['length'], bins=5, labels=['Muy Corto', 'Corto', 'Medio', 'Largo', 'Muy Largo'])
            
            box_data = [data[data['length_category'] == cat]['gc_content'].dropna().values 
                       for cat in data['length_category'].cat.categories]
            plt.boxplot(box_data, labels=data['length_category'].cat.categories)
            plt.ylabel('Contenido GC (%)')
            plt.title('GC por Categoría de Longitud')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            
            # QQ-plot para normalidad
            plt.subplot(2, 2, 4)
            stats.probplot(data['gc_content'], dist="norm", plot=plt)
            plt.title('Q-Q Plot - Normalidad del GC')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            graphs.append(self.save_figure('gc_analysis'))
            
        except Exception as e:
            logger.error(f"Error en análisis GC: {e}")
        
        return graphs
    
    def _plot_general_statistics(self, data: pd.DataFrame) -> List[str]:
        """Crear gráficos estadísticos generales."""
        graphs = []
        
        try:
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_columns) == 0:
                return [self.create_basic_plot("Sin Datos Numéricos", 
                                             "No se encontraron columnas numéricas para analizar")]
            
            n_cols = min(3, len(numeric_columns))
            n_rows = (len(numeric_columns) + n_cols - 1) // n_cols
            
            plt.figure(figsize=(5*n_cols, 4*n_rows))
            
            for i, col in enumerate(numeric_columns):
                plt.subplot(n_rows, n_cols, i+1)
                
                # Remover valores NaN
                clean_data = data[col].dropna()
                
                if len(clean_data) > 0:
                    plt.hist(clean_data, bins=min(20, len(clean_data)//2 + 1), 
                            alpha=0.7, edgecolor='black')
                    plt.axvline(x=clean_data.mean(), color='red', linestyle='--',
                               label=f'Media: {clean_data.mean():.2f}')
                    plt.xlabel(col)
                    plt.ylabel('Frecuencia')
                    plt.title(f'Distribución de {col}')
                    plt.legend()
                    plt.grid(True, alpha=0.3)
                else:
                    plt.text(0.5, 0.5, 'Sin datos', ha='center', va='center')
                    plt.title(f'{col} - Sin datos')
            
            plt.tight_layout()
            graphs.append(self.save_figure('general_statistics'))
            
        except Exception as e:
            logger.error(f"Error en estadísticas generales: {e}")
        
        return graphs
    
    def _calculate_n50(self, lengths: List[int]) -> int:
        """Calcular N50 de una lista de longitudes."""
        sorted_lengths = sorted(lengths, reverse=True)
        total_length = sum(sorted_lengths)
        target = total_length * 0.5
        
        cumsum = 0
        for length in sorted_lengths:
            cumsum += length
            if cumsum >= target:
                return length
        
        return 0
    
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generar estadísticas comprehensivas para CheckM.
        
        Args:
            data: DataFrame con datos CheckM
            
        Returns:
            Diccionario con estadísticas
        """
        stats = {}
        
        try:
            # Estadísticas básicas
            stats['basic'] = {
                'total_genomes': len(data),
                'total_columns': len(data.columns),
                'columns': list(data.columns)
            }
            
            # Estadísticas de calidad si están disponibles
            if 'completeness' in data.columns and 'contamination' in data.columns:
                data['quality'] = data.apply(
                    lambda row: self.classify_genome_quality(row['completeness'], row['contamination']),
                    axis=1
                )
                
                quality_counts = data['quality'].value_counts().to_dict()
                
                stats['quality'] = {
                    'high_quality': quality_counts.get('high', 0),
                    'medium_quality': quality_counts.get('medium', 0),
                    'low_quality': quality_counts.get('low', 0),
                    'very_low_quality': quality_counts.get('very_low', 0),
                    'completeness_mean': float(data['completeness'].mean()),
                    'completeness_median': float(data['completeness'].median()),
                    'completeness_std': float(data['completeness'].std()),
                    'contamination_mean': float(data['contamination'].mean()),
                    'contamination_median': float(data['contamination'].median()),
                    'contamination_std': float(data['contamination'].std())
                }
            
            # Estadísticas de secuencias si están disponibles
            if 'length' in data.columns:
                lengths = data['length'].tolist()
                stats['sequences'] = {
                    'total_sequences': len(data),
                    'total_length': int(data['length'].sum()),
                    'mean_length': float(data['length'].mean()),
                    'median_length': float(data['length'].median()),
                    'min_length': int(data['length'].min()),
                    'max_length': int(data['length'].max()),
                    'n50': int(self._calculate_n50(lengths))
                }
                
                if 'gc_content' in data.columns:
                    stats['sequences'].update({
                        'mean_gc': float(data['gc_content'].mean()),
                        'median_gc': float(data['gc_content'].median()),
                        'std_gc': float(data['gc_content'].std())
                    })
            
            # Estadísticas numéricas generales
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_columns:
                stats['numeric_summary'] = {}
                for col in numeric_columns:
                    clean_data = data[col].dropna()
                    if len(clean_data) > 0:
                        stats['numeric_summary'][col] = {
                            'count': int(len(clean_data)),
                            'mean': float(clean_data.mean()),
                            'median': float(clean_data.median()),
                            'std': float(clean_data.std()),
                            'min': float(clean_data.min()),
                            'max': float(clean_data.max())
                        }
            
            logger.info("✅ Estadísticas CheckM generadas correctamente")
            
        except Exception as e:
            logger.error(f"Error generando estadísticas: {e}")
            stats['error'] = str(e)
        
        return stats