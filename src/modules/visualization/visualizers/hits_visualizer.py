#!/usr/bin/env python3
"""
Visualizador Especializado para Hits EggNOG
===========================================

Visualizador especializado para archivos .emapper.hits generados por eggNOG-mapper.
Estos archivos contienen todos los hits encontrados durante el proceso de búsqueda.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any
import re

from .base_visualizer import BaseVisualizer

class HitsVisualizer(BaseVisualizer):
    """Visualizador especializado para archivos hits de EggNOG."""
    
    def __init__(self, output_dir: Path, config: Dict = None):
        super().__init__(output_dir, config)
        self.name = "EggNOG Hits Analysis"
        
        # Columnas típicas de hits
        self.hits_columns = [
            'query', 'target', 'evalue', 'score', 'query_start', 'query_end',
            'target_start', 'target_end', 'query_length', 'target_length',
            'alignment_length', 'identity', 'similarity'
        ]
        
    def get_supported_extensions(self) -> List[str]:
        """Extensiones soportadas para archivos de hits."""
        return ['.emapper.hits', '.hits', '.blast', '.tsv', '.txt']
    
    def validate_file(self, file_path: Path) -> bool:
        """Validar archivo de hits."""
        try:
            # Verificar extensión
            if not any(str(file_path).lower().endswith(ext) for ext in self.get_supported_extensions()):
                print(f"❌ Extensión no soportada. Extensiones válidas: {self.get_supported_extensions()}")
                return False
            
            # Leer primeras líneas
            with open(file_path, 'r') as f:
                lines = []
                for i, line in enumerate(f):
                    if i > 50:
                        break
                    if not line.startswith('#'):
                        lines.append(line.strip())
                
            if not lines:
                print("❌ Archivo vacío o solo contiene comentarios")
                return False
            
            # Verificar formato básico
            first_data_line = lines[0]
            columns = first_data_line.split('\t')
            
            if len(columns) < 6:
                print(f"❌ Formato no válido - Se esperaban al menos 6 columnas, encontradas {len(columns)}")
                return False
            
            print(f"✅ Archivo de hits válido - Detectadas {len(columns)} columnas")
            return True
            
        except Exception as e:
            print(f"❌ Error validando archivo: {e}")
            return False
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo de hits."""
        try:
            print(f"🔍 Parseando archivo de hits: {file_path.name}")
            
            # Leer archivo saltando comentarios
            df = pd.read_csv(file_path, sep='\t', comment='#', header=None, low_memory=False)
            
            # Crear nombres de columnas dinámicamente según el número real de columnas
            actual_columns = len(df.columns)
            print(f"📊 Detectadas {actual_columns} columnas en el archivo")
            
            # Asignar nombres de columnas de forma flexible
            if actual_columns >= len(self.hits_columns):
                # Usar todos los nombres predefinidos + genéricos para las extra
                column_names = self.hits_columns + [f'extra_col_{i}' for i in range(len(self.hits_columns), actual_columns)]
                df.columns = column_names[:actual_columns]
            else:
                # Usar solo los nombres que caben
                basic_cols = ['query', 'target', 'evalue', 'score', 'identity', 'coverage', 
                             'query_start', 'query_end', 'target_start', 'target_end', 
                             'alignment_length', 'query_length', 'target_length']
                
                column_names = []
                for i in range(actual_columns):
                    if i < len(basic_cols):
                        column_names.append(basic_cols[i])
                    else:
                        column_names.append(f'col_{i}')
                
                df.columns = column_names
            
            print(f"✅ Columnas asignadas: {list(df.columns)}")
            
            # Limpiar datos
            df = df.dropna(subset=['query'])
            df = df[df['query'] != '']
            
            # Convertir tipos de datos para columnas que existen
            numeric_columns = ['evalue', 'score', 'query_start', 'query_end', 'target_start', 
                             'target_end', 'query_length', 'target_length', 'alignment_length', 
                             'identity', 'similarity', 'coverage']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✅ Parseados {len(df)} hits de {len(df['query'].unique())} secuencias únicas")
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo de hits: {str(e)}")
    
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """Generar todas las visualizaciones de hits."""
        graphs = []
        
        try:
            # Resumen general de hits
            overview_graphs = self._plot_hits_overview(data)
            graphs.extend(overview_graphs)
        except Exception as e:
            print(f"Error creando overview: {e}")
        
        try:
            # Análisis de calidad de hits
            quality_graphs = self._plot_hit_quality(data)
            graphs.extend(quality_graphs)
        except Exception as e:
            print(f"Error creando análisis de calidad: {e}")
        
        try:
            # Análisis de distribución de targets
            target_graphs = self._plot_target_analysis(data)
            graphs.extend(target_graphs)
        except Exception as e:
            print(f"Error creando análisis de targets: {e}")
        
        try:
            # Panel de navegación y controles
            navigation_graph = self._create_navigation_panel(data)
            if navigation_graph:
                graphs.append(navigation_graph)
        except Exception as e:
            print(f"Error creando panel de navegación: {e}")
        
        return [g for g in graphs if g]
    
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas de hits."""
        stats = {
            'total_hits': len(data),
            'unique_queries': len(data['query'].unique()) if 'query' in data.columns else 0,
            'unique_targets': len(data['target'].unique()) if 'target' in data.columns else 0,
        }
        
        if 'score' in data.columns:
            scores = data['score'].dropna()
            if len(scores) > 0:
                stats['avg_score'] = float(scores.mean())
                stats['max_score'] = float(scores.max())
                stats['min_score'] = float(scores.min())
        
        if 'identity' in data.columns:
            identity = data['identity'].dropna()
            if len(identity) > 0:
                stats['avg_identity'] = float(identity.mean())
                stats['max_identity'] = float(identity.max())
        
        if 'evalue' in data.columns:
            evalues = data['evalue'].dropna()
            evalues = evalues[evalues > 0]
            if len(evalues) > 0:
                stats['avg_evalue'] = float(evalues.mean())
                stats['min_evalue'] = float(evalues.min())
        
        return stats
    
    def _plot_hits_overview(self, data: pd.DataFrame) -> List[str]:
        """Crear gráficos de resumen de hits."""
        graphs = []
        
        # 1. Número de hits por query
        try:
            plt.figure(figsize=(12, 8))
            hits_per_query = data['query'].value_counts()
            
            # Crear histograma de distribución
            plt.hist(hits_per_query.values, bins=min(50, len(hits_per_query.unique())), 
                    alpha=0.7, color='skyblue', edgecolor='black')
            plt.title('📊 Distribución de Número de Hits por Query', fontsize=14, fontweight='bold')
            plt.xlabel('Número de Hits')
            plt.ylabel('Número de Queries')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            graphs.append(self.save_figure('hits_per_query_distribution'))
            plt.close()
        except Exception as e:
            print(f"Error creando distribución de hits: {e}")
        
        # 2. Top queries con más hits
        try:
            plt.figure(figsize=(14, 8))
            top_queries = data['query'].value_counts().head(15)
            
            plt.barh(range(len(top_queries)), top_queries.values, color='lightgreen')
            plt.yticks(range(len(top_queries)), 
                      [q[:50] + '...' if len(q) > 50 else q for q in top_queries.index])
            plt.title('🎯 Top 15 Queries con Más Hits', fontsize=14, fontweight='bold')
            plt.xlabel('Número de Hits')
            plt.tight_layout()
            graphs.append(self.save_figure('top_queries_hits'))
            plt.close()
        except Exception as e:
            print(f"Error creando top queries: {e}")
        
        # 3. Top targets más frecuentes
        try:
            plt.figure(figsize=(14, 8))
            top_targets = data['target'].value_counts().head(15)
            
            plt.barh(range(len(top_targets)), top_targets.values, color='lightcoral')
            plt.yticks(range(len(top_targets)), 
                      [t[:50] + '...' if len(t) > 50 else t for t in top_targets.index])
            plt.title('🎯 Top 15 Targets más Frecuentes', fontsize=14, fontweight='bold')
            plt.xlabel('Frecuencia')
            plt.tight_layout()
            graphs.append(self.save_figure('top_targets'))
            plt.close()
        except Exception as e:
            print(f"Error creando top targets: {e}")
        
        # 4. Estadísticas generales
        try:
            plt.figure(figsize=(10, 8))
            stats_text = f"""ESTADÍSTICAS DE HITS

Total de hits: {len(data):,}
Queries únicas: {len(data['query'].unique()):,}
Targets únicos: {len(data['target'].unique()):,}
Promedio hits/query: {len(data) / len(data['query'].unique()):.1f}
"""
            
            if 'score' in data.columns:
                scores = data['score'].dropna()
                if len(scores) > 0:
                    stats_text += f"\nScore promedio: {scores.mean():.2f}\n"
                    stats_text += f"Score máximo: {scores.max():.2f}\n"
                    stats_text += f"Score mínimo: {scores.min():.2f}\n"
            
            if 'identity' in data.columns:
                identity = data['identity'].dropna()
                if len(identity) > 0:
                    stats_text += f"\nIdentidad promedio: {identity.mean():.1f}%\n"
                    stats_text += f"Identidad máxima: {identity.max():.1f}%\n"
            
            plt.text(0.1, 0.5, stats_text, fontsize=14, verticalalignment='center',
                    bbox=dict(boxstyle="round,pad=1", facecolor='lightyellow', alpha=0.8))
            plt.xlim(0, 1)
            plt.ylim(0, 1)
            plt.axis('off')
            plt.title('📊 Estadísticas Generales de Hits', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            graphs.append(self.save_figure('hits_stats'))
            plt.close()
        except Exception as e:
            print(f"Error creando estadísticas: {e}")
        
        return graphs
    
    def _plot_hit_quality(self, data: pd.DataFrame) -> List[str]:
        """Análisis de calidad de hits."""
        graphs = []
        
        # 1. Distribución de scores
        try:
            if 'score' in data.columns:
                plt.figure(figsize=(10, 6))
                scores = data['score'].dropna()
                if len(scores) > 0:
                    plt.hist(scores, bins=50, alpha=0.7, color='orange', edgecolor='black')
                    plt.title('📊 Distribución de Scores de Hits', fontsize=14, fontweight='bold')
                    plt.xlabel('Score')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    graphs.append(self.save_figure('score_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución de scores: {e}")
        
        # 2. Distribución de e-values
        try:
            if 'evalue' in data.columns:
                plt.figure(figsize=(10, 6))
                evalues = data['evalue'].dropna()
                evalues = evalues[evalues > 0]
                if len(evalues) > 0:
                    plt.hist(np.log10(evalues), bins=50, alpha=0.7, color='red', edgecolor='black')
                    plt.title('📊 Distribución de E-values (log10)', fontsize=14, fontweight='bold')
                    plt.xlabel('Log10(E-value)')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    graphs.append(self.save_figure('evalue_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución de e-values: {e}")
        
        # 3. Distribución de identidad
        try:
            if 'identity' in data.columns:
                plt.figure(figsize=(10, 6))
                identity = data['identity'].dropna()
                if len(identity) > 0:
                    plt.hist(identity, bins=50, alpha=0.7, color='green', edgecolor='black')
                    plt.title('📊 Distribución de Identidad de Secuencias', fontsize=14, fontweight='bold')
                    plt.xlabel('Identidad (%)')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    graphs.append(self.save_figure('identity_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución de identidad: {e}")
        
        # 4. Score vs Identity scatter plot
        try:
            if 'score' in data.columns and 'identity' in data.columns:
                plt.figure(figsize=(10, 8))
                valid_data = data[data['score'].notna() & data['identity'].notna()]
                
                if len(valid_data) > 0:
                    # Tomar muestra si hay demasiados puntos
                    if len(valid_data) > 10000:
                        valid_data = valid_data.sample(10000)
                    
                    plt.scatter(valid_data['identity'], valid_data['score'], 
                              alpha=0.5, c='purple', s=20)
                    plt.xlabel('Identidad (%)')
                    plt.ylabel('Score')
                    plt.title('⚖️ Score vs Identidad de Hits', fontsize=14, fontweight='bold')
                    plt.grid(True, alpha=0.3)
                    graphs.append(self.save_figure('score_vs_identity'))
                    plt.close()
        except Exception as e:
            print(f"Error creando score vs identity: {e}")
        
        return graphs
    
    def _plot_target_analysis(self, data: pd.DataFrame) -> List[str]:
        """Análisis de patrones de targets."""
        graphs = []
        
        # 1. Distribución por longitud de alineamiento
        try:
            if 'alignment_length' in data.columns:
                plt.figure(figsize=(10, 6))
                lengths = data['alignment_length'].dropna()
                if len(lengths) > 0:
                    plt.hist(lengths, bins=50, alpha=0.7, color='teal', edgecolor='black')
                    plt.title('📏 Distribución de Longitudes de Alineamiento', fontsize=14, fontweight='bold')
                    plt.xlabel('Longitud de Alineamiento')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    graphs.append(self.save_figure('alignment_length_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución de longitudes: {e}")
        
        # 2. Análisis de cobertura (si disponible)
        try:
            if 'query_length' in data.columns and 'alignment_length' in data.columns:
                plt.figure(figsize=(10, 6))
                valid_data = data[data['query_length'].notna() & data['alignment_length'].notna()]
                valid_data = valid_data[valid_data['query_length'] > 0]
                
                if len(valid_data) > 0:
                    coverage = (valid_data['alignment_length'] / valid_data['query_length']) * 100
                    plt.hist(coverage, bins=50, alpha=0.7, color='gold', edgecolor='black')
                    plt.title('📊 Distribución de Cobertura de Query', fontsize=14, fontweight='bold')
                    plt.xlabel('Cobertura (%)')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    graphs.append(self.save_figure('query_coverage_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución de cobertura: {e}")
        
        # 3. Heatmap de calidad si hay suficientes datos
        try:
            if 'score' in data.columns and 'identity' in data.columns and len(data) > 100:
                plt.figure(figsize=(10, 8))
                
                # Crear bins para el heatmap
                score_bins = pd.cut(data['score'].dropna(), bins=20)
                identity_bins = pd.cut(data['identity'].dropna(), bins=20)
                
                # Crear tabla de contingencia
                valid_data = data[data['score'].notna() & data['identity'].notna()]
                if len(valid_data) > 0:
                    score_binned = pd.cut(valid_data['score'], bins=15)
                    identity_binned = pd.cut(valid_data['identity'], bins=15)
                    
                    crosstab = pd.crosstab(score_binned, identity_binned)
                    
                    if crosstab.size > 0:
                        plt.imshow(crosstab.values, cmap='Blues', aspect='auto')
                        plt.colorbar(label='Frecuencia')
                        plt.title('🔥 Heatmap Score vs Identidad', fontsize=14, fontweight='bold')
                        plt.xlabel('Identidad')
                        plt.ylabel('Score')
                        plt.tight_layout()
                        graphs.append(self.save_figure('score_identity_heatmap'))
                        plt.close()
        except Exception as e:
            print(f"Error creando heatmap: {e}")
        
        return graphs
    
    def _create_navigation_panel(self, data: pd.DataFrame) -> str:
        """Crear panel de navegación y controles interactivos para hits."""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('🎛️ Panel de Control - Visualizador EggNOG Hits', fontsize=16, fontweight='bold')
            
            # Control 1: Resumen de hits
            ax1.text(0.5, 0.8, 'RESUMEN DE HITS', ha='center', va='center', fontsize=14, fontweight='bold')
            
            summary_text = f"""
🎯 Total de hits: {len(data):,}
🧬 Queries únicas: {len(data['query'].unique()):,}
🔍 Targets únicos: {len(data['target'].unique()):,}
📈 Promedio hits/query: {len(data) / len(data['query'].unique()):.1f}
"""
            
            if 'score' in data.columns:
                scores = data['score'].dropna()
                if len(scores) > 0:
                    summary_text += f"⭐ Score promedio: {scores.mean():.2f}\n"
                    summary_text += f"🏆 Score máximo: {scores.max():.2f}\n"
            
            if 'identity' in data.columns:
                identity = data['identity'].dropna()
                if len(identity) > 0:
                    summary_text += f"🔬 Identidad promedio: {identity.mean():.1f}%\n"
            
            ax1.text(0.1, 0.4, summary_text, ha='left', va='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.7))
            ax1.set_xlim(0, 1)
            ax1.set_ylim(0, 1)
            ax1.axis('off')
            
            # Control 2: Calidad de hits
            if 'evalue' in data.columns:
                evalues = data['evalue'].dropna()
                evalues = evalues[evalues > 0]
                if len(evalues) > 0:
                    ax2.hist(np.log10(evalues), bins=20, alpha=0.7, color='orange', edgecolor='black')
                    ax2.set_title('📊 E-values (log10)', fontweight='bold')
                    ax2.set_xlabel('Log10(E-value)')
                    ax2.set_ylabel('Frecuencia')
                    ax2.grid(True, alpha=0.3)
            else:
                ax2.text(0.5, 0.5, 'CONTROL DE CALIDAD\n\n⚠️ No hay datos de E-value\ndisponibles', 
                        ha='center', va='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcoral', alpha=0.7))
                ax2.set_xlim(0, 1)
                ax2.set_ylim(0, 1)
                ax2.axis('off')
            
            # Control 3: Top queries con más hits
            if len(data) > 0:
                top_queries = data['query'].value_counts().head(8)
                if len(top_queries) > 0:
                    ax3.barh(range(len(top_queries)), top_queries.values, color='lightgreen')
                    ax3.set_yticks(range(len(top_queries)))
                    ax3.set_yticklabels([q[:20] + '...' if len(q) > 20 else q for q in top_queries.index])
                    ax3.set_title('🏆 Top Queries (más hits)', fontweight='bold')
                    ax3.set_xlabel('Número de hits')
            else:
                ax3.text(0.5, 0.5, 'TOP QUERIES\n\n⚠️ No hay datos disponibles', 
                        ha='center', va='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.7))
                ax3.set_xlim(0, 1)
                ax3.set_ylim(0, 1)
                ax3.axis('off')
            
            # Control 4: Instrucciones de navegación
            ax4.text(0.5, 0.8, 'NAVEGACIÓN Y CONTROLES', ha='center', va='center', 
                    fontsize=14, fontweight='bold')
            
            instructions = """
🖱️ CONTROLES DE HITS:

🎯 Análisis de homología completo
🔍 Filtros por score e identidad
📊 Estadísticas de calidad
📈 Distribuciones detalladas

💡 FUNCIONES DISPONIBLES:
• Histogramas de scores e identidad
• Top queries y targets
• Análisis de cobertura
• Correlaciones entre métricas
• Heatmaps de calidad
"""
            
            ax4.text(0.1, 0.4, instructions, ha='left', va='center', fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.7))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            
            plt.tight_layout()
            return self.save_figure('hits_navigation_panel')
            
        except Exception as e:
            print(f"Error creando panel de navegación de hits: {e}")
            return None 