#!/usr/bin/env python3
"""
Visualizador Especializado para Seed Orthologs EggNOG
=====================================================

Visualizador especializado para archivos .emapper.seed_orthologs generados por eggNOG-mapper.
Estos archivos contienen información sobre los orthólogos semilla encontrados.
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

class SeedOrthologsVisualizer(BaseVisualizer):
    """Visualizador especializado para archivos seed_orthologs de EggNOG."""
    
    def __init__(self, output_dir: Path, config: Dict = None):
        super().__init__(output_dir, config)
        self.name = "EggNOG Seed Orthologs Analysis"
        
        # Columnas típicas de seed_orthologs
        self.seed_columns = [
            'query', 'seed_ortholog', 'evalue', 'score', 'query_start', 'query_end',
            'target_start', 'target_end', 'coverage', 'identity'
        ]
        
    def get_supported_extensions(self) -> List[str]:
        """Extensiones soportadas para archivos de seed orthologs."""
        return ['.emapper.seed_orthologs', '.seed_orthologs', '.tsv', '.txt']
    
    def validate_file(self, file_path: Path) -> bool:
        """Validar archivo de seed orthologs."""
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
            
            if len(columns) < 4:
                print(f"❌ Formato no válido - Se esperaban al menos 4 columnas, encontradas {len(columns)}")
                return False
            
            print(f"✅ Archivo de seed orthologs válido - Detectadas {len(columns)} columnas")
            return True
            
        except Exception as e:
            print(f"❌ Error validando archivo: {e}")
            return False
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo de seed orthologs."""
        try:
            print(f"🔍 Parseando archivo de seed orthologs: {file_path.name}")
            
            # Leer archivo saltando comentarios
            df = pd.read_csv(file_path, sep='\t', comment='#', header=None, low_memory=False)
            
            # Crear nombres de columnas dinámicamente según el número real de columnas
            actual_columns = len(df.columns)
            print(f"📊 Detectadas {actual_columns} columnas en el archivo")
            
            # Asignar nombres de columnas de forma flexible
            if actual_columns >= len(self.seed_columns):
                # Usar todos los nombres predefinidos + genéricos para las extra
                column_names = self.seed_columns + [f'extra_col_{i}' for i in range(len(self.seed_columns), actual_columns)]
                df.columns = column_names[:actual_columns]
            else:
                # Usar solo los nombres que caben
                basic_cols = ['query', 'seed_ortholog', 'evalue', 'score', 'query_start', 'query_end',
                             'target_start', 'target_end', 'coverage', 'identity']
                
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
                             'target_end', 'coverage', 'identity']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✅ Parseados {len(df)} seed orthologs de {len(df['query'].unique())} secuencias únicas")
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo de seed orthologs: {str(e)}")
    
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """Generar todas las visualizaciones de seed orthologs."""
        graphs = []
        
        try:
            # Resumen general
            overview_graphs = self._plot_seed_overview(data)
            graphs.extend(overview_graphs)
        except Exception as e:
            print(f"Error creando overview: {e}")
        
        try:
            # Análisis de calidad de alineamientos
            quality_graphs = self._plot_alignment_quality(data)
            graphs.extend(quality_graphs)
        except Exception as e:
            print(f"Error creando análisis de calidad: {e}")
        
        try:
            # Análisis de ortólogos
            ortholog_graphs = self._plot_ortholog_analysis(data)
            graphs.extend(ortholog_graphs)
        except Exception as e:
            print(f"Error creando análisis de ortólogos: {e}")
        
        try:
            # Panel de navegación y controles
            navigation_graph = self._create_navigation_panel(data)
            if navigation_graph:
                graphs.append(navigation_graph)
        except Exception as e:
            print(f"Error creando panel de navegación: {e}")
        
        return [g for g in graphs if g]
    
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas de seed orthologs."""
        stats = {
            'total_seed_orthologs': len(data),
            'unique_queries': len(data['query'].unique()) if 'query' in data.columns else 0,
            'unique_seeds': len(data['seed_ortholog'].unique()) if 'seed_ortholog' in data.columns else 0,
        }
        
        if 'score' in data.columns:
            scores = data['score'].dropna()
            if len(scores) > 0:
                stats['avg_score'] = float(scores.mean())
                stats['max_score'] = float(scores.max())
        
        if 'coverage' in data.columns:
            coverage = data['coverage'].dropna()
            if len(coverage) > 0:
                stats['avg_coverage'] = float(coverage.mean())
        
        if 'identity' in data.columns:
            identity = data['identity'].dropna()
            if len(identity) > 0:
                stats['avg_identity'] = float(identity.mean())
        
        return stats
    
    def _plot_seed_overview(self, data: pd.DataFrame) -> List[str]:
        """Crear gráficos de resumen de seed orthologs."""
        graphs = []
        
        # 1. Top seed orthologs
        try:
            plt.figure(figsize=(14, 8))
            top_seeds = data['seed_ortholog'].value_counts().head(15)
            
            plt.barh(range(len(top_seeds)), top_seeds.values, color='skyblue')
            plt.yticks(range(len(top_seeds)), 
                      [seed[:60] + '...' if len(seed) > 60 else seed for seed in top_seeds.index])
            plt.title('Top 15 Seed Orthologs más Frecuentes', fontsize=14, fontweight='bold')
            plt.xlabel('Frecuencia')
            plt.tight_layout()
            graphs.append(self.save_figure('top_seed_orthologs'))
            plt.close()
        except Exception as e:
            print(f"Error creando top seeds: {e}")
        
        # 2. Distribución de scores
        try:
            if 'score' in data.columns:
                plt.figure(figsize=(10, 6))
                scores = data['score'].dropna()
                if len(scores) > 0:
                    plt.hist(scores, bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
                    plt.title('Distribución de Scores de Alineamiento', fontsize=14, fontweight='bold')
                    plt.xlabel('Score')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    graphs.append(self.save_figure('score_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución de scores: {e}")
        
        # 3. Estadísticas generales
        try:
            plt.figure(figsize=(10, 8))
            stats_text = f"""ESTADÍSTICAS DE SEED ORTHOLOGS

Total de seed orthologs: {len(data):,}
Queries únicas: {len(data['query'].unique()):,}
Seeds únicos: {len(data['seed_ortholog'].unique()):,}
"""
            
            if 'score' in data.columns:
                scores = data['score'].dropna()
                if len(scores) > 0:
                    stats_text += f"\nScore promedio: {scores.mean():.2f}\n"
                    stats_text += f"Score máximo: {scores.max():.2f}\n"
            
            if 'coverage' in data.columns:
                coverage = data['coverage'].dropna()
                if len(coverage) > 0:
                    stats_text += f"Cobertura promedio: {coverage.mean():.1f}%\n"
            
            if 'identity' in data.columns:
                identity = data['identity'].dropna()
                if len(identity) > 0:
                    stats_text += f"Identidad promedio: {identity.mean():.1f}%\n"
            
            plt.text(0.1, 0.5, stats_text, fontsize=14, verticalalignment='center',
                    bbox=dict(boxstyle="round,pad=1", facecolor='lightblue', alpha=0.8))
            plt.xlim(0, 1)
            plt.ylim(0, 1)
            plt.axis('off')
            plt.title('Estadísticas Generales de Seed Orthologs', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            graphs.append(self.save_figure('seed_stats'))
            plt.close()
        except Exception as e:
            print(f"Error creando estadísticas: {e}")
        
        return graphs
    
    def _plot_alignment_quality(self, data: pd.DataFrame) -> List[str]:
        """Análisis de calidad de alineamientos."""
        graphs = []
        
        # 1. Distribución de e-values
        try:
            if 'evalue' in data.columns:
                plt.figure(figsize=(10, 6))
                evalues = data['evalue'].dropna()
                evalues = evalues[evalues > 0]
                if len(evalues) > 0:
                    plt.hist(np.log10(evalues), bins=30, alpha=0.7, color='orange', edgecolor='black')
                    plt.title('Distribución de E-values (log10)', fontsize=14, fontweight='bold')
                    plt.xlabel('Log10(E-value)')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    graphs.append(self.save_figure('evalue_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando e-values: {e}")
        
        # 2. Cobertura vs Identidad (si están disponibles)
        try:
            if 'coverage' in data.columns and 'identity' in data.columns:
                plt.figure(figsize=(10, 8))
                coverage = data['coverage'].dropna()
                identity = data['identity'].dropna()
                
                if len(coverage) > 0 and len(identity) > 0:
                    # Filtrar datos válidos para ambas columnas
                    valid_data = data[data['coverage'].notna() & data['identity'].notna()]
                    if len(valid_data) > 0:
                        plt.scatter(valid_data['coverage'], valid_data['identity'], 
                                  alpha=0.6, c='purple', s=50)
                        plt.xlabel('Cobertura (%)')
                        plt.ylabel('Identidad (%)')
                        plt.title('Cobertura vs Identidad de Alineamientos', fontsize=14, fontweight='bold')
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        graphs.append(self.save_figure('coverage_vs_identity'))
                        plt.close()
        except Exception as e:
            print(f"Error creando cobertura vs identidad: {e}")
        
        return graphs
    
    def _plot_ortholog_analysis(self, data: pd.DataFrame) -> List[str]:
        """Análisis de patrones de ortólogos."""
        graphs = []
        
        # 1. Distribución por organismo/taxonomía si está disponible
        try:
            if 'seed_ortholog' in data.columns:
                plt.figure(figsize=(12, 8))
                
                # Extraer información taxonómica básica del nombre del seed ortholog
                taxa = []
                for seed in data['seed_ortholog']:
                    if pd.notna(seed):
                        # Intentar extraer información del organismo
                        parts = seed.split('.')
                        if len(parts) > 1:
                            taxa.append(parts[0])  # Primer parte como identificador del organismo
                        else:
                            taxa.append('Otros')
                    else:
                        taxa.append('Desconocido')
                
                if taxa:
                    taxa_counts = Counter(taxa)
                    top_taxa = dict(taxa_counts.most_common(10))
                    
                    plt.bar(range(len(top_taxa)), list(top_taxa.values()), color='lightcoral')
                    plt.xticks(range(len(top_taxa)), 
                              [taxon[:15] + '...' if len(taxon) > 15 else taxon for taxon in top_taxa.keys()], 
                              rotation=45, ha='right')
                    plt.title('Top 10 Grupos Taxonómicos de Seed Orthologs', fontsize=14, fontweight='bold')
                    plt.ylabel('Frecuencia')
                    plt.tight_layout()
                    graphs.append(self.save_figure('taxonomic_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando distribución taxonómica: {e}")
        
        # 2. Análisis de score vs e-value
        try:
            if 'score' in data.columns and 'evalue' in data.columns:
                plt.figure(figsize=(10, 8))
                scores = data['score'].dropna()
                evalues = data['evalue'].dropna()
                
                if len(scores) > 0 and len(evalues) > 0:
                    # Filtrar datos válidos para ambas columnas
                    valid_data = data[data['score'].notna() & data['evalue'].notna()]
                    valid_data = valid_data[valid_data['evalue'] > 0]
                    
                    if len(valid_data) > 0:
                        plt.scatter(valid_data['score'], np.log10(valid_data['evalue']), 
                                  alpha=0.6, c='green', s=50)
                        plt.xlabel('Score')
                        plt.ylabel('Log10(E-value)')
                        plt.title('⚖️ Score vs E-value de Alineamientos', fontsize=14, fontweight='bold')
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        graphs.append(self.save_figure('score_vs_evalue'))
                        plt.close()
        except Exception as e:
            print(f"Error creando score vs evalue: {e}")
        
        return graphs
    
    def _create_navigation_panel(self, data: pd.DataFrame) -> str:
        """Crear panel de navegación y controles interactivos para seed orthologs."""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('🎛️ Panel de Control - Visualizador EggNOG Seed Orthologs', fontsize=16, fontweight='bold')
            
            # Control 1: Resumen de seed orthologs
            ax1.text(0.5, 0.8, 'RESUMEN DE SEED ORTHOLOGS', ha='center', va='center', 
                    fontsize=14, fontweight='bold')
            
            summary_text = f"""
Total de seed orthologs: {len(data):,}
Queries únicas: {len(data['query'].unique()):,}
Seeds únicos: {len(data['seed_ortholog'].unique()):,}
Ratio seed/query: {len(data['seed_ortholog'].unique()) / len(data['query'].unique()):.2f}
"""
            
            if 'score' in data.columns:
                scores = data['score'].dropna()
                if len(scores) > 0:
                    summary_text += f"⭐ Score promedio: {scores.mean():.2f}\n"
                    summary_text += f"Score máximo: {scores.max():.2f}\n"
            
            if 'coverage' in data.columns:
                coverage = data['coverage'].dropna()
                if len(coverage) > 0:
                    summary_text += f"Cobertura promedio: {coverage.mean():.1f}%\n"
            
            if 'identity' in data.columns:
                identity = data['identity'].dropna()
                if len(identity) > 0:
                    summary_text += f"Identidad promedio: {identity.mean():.1f}%\n"
            
            ax1.text(0.1, 0.3, summary_text, ha='left', va='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgreen', alpha=0.7))
            ax1.set_xlim(0, 1)
            ax1.set_ylim(0, 1)
            ax1.axis('off')
            
            # Control 2: Calidad de alineamientos
            if 'coverage' in data.columns and 'identity' in data.columns:
                valid_data = data[data['coverage'].notna() & data['identity'].notna()]
                if len(valid_data) > 10:
                    # Tomar muestra si hay demasiados puntos
                    if len(valid_data) > 1000:
                        valid_data = valid_data.sample(1000)
                    
                    ax2.scatter(valid_data['coverage'], valid_data['identity'], 
                              alpha=0.6, c='purple', s=30)
                    ax2.set_xlabel('Cobertura (%)')
                    ax2.set_ylabel('Identidad (%)')
                    ax2.set_title('Calidad de Alineamientos', fontweight='bold')
                    ax2.grid(True, alpha=0.3)
                else:
                    ax2.text(0.5, 0.5, 'CALIDAD DE ALINEAMIENTOS\n\n⚠️ Datos insuficientes\npara el scatter plot', 
                            ha='center', va='center', fontsize=12,
                            bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.7))
                    ax2.set_xlim(0, 1)
                    ax2.set_ylim(0, 1)
                    ax2.axis('off')
            else:
                ax2.text(0.5, 0.5, 'CALIDAD DE ALINEAMIENTOS\n\n⚠️ No hay datos de\ncobertura e identidad', 
                        ha='center', va='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcoral', alpha=0.7))
                ax2.set_xlim(0, 1)
                ax2.set_ylim(0, 1)
                ax2.axis('off')
            
            # Control 3: Top seed orthologs más frecuentes
            if len(data) > 0:
                top_seeds = data['seed_ortholog'].value_counts().head(8)
                if len(top_seeds) > 0:
                    ax3.barh(range(len(top_seeds)), top_seeds.values, color='skyblue')
                    ax3.set_yticks(range(len(top_seeds)))
                    ax3.set_yticklabels([s[:25] + '...' if len(s) > 25 else s for s in top_seeds.index])
                    ax3.set_title('Top Seed Orthologs', fontweight='bold')
                    ax3.set_xlabel('Frecuencia')
            else:
                ax3.text(0.5, 0.5, 'TOP SEED ORTHOLOGS\n\n⚠️ No hay datos disponibles', 
                        ha='center', va='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.7))
                ax3.set_xlim(0, 1)
                ax3.set_ylim(0, 1)
                ax3.axis('off')
            
            # Control 4: Instrucciones de navegación
            ax4.text(0.5, 0.8, 'NAVEGACIÓN Y CONTROLES', ha='center', va='center', 
                    fontsize=14, fontweight='bold')
            
            instructions = """
CONTROLES DE SEED ORTHOLOGS:

Análisis de ortología completo
Métricas de alineamiento
Distribuciones de calidad
Análisis filogenético

FUNCIONES DISPONIBLES:
• Gráficos de cobertura vs identidad
• Distribución de scores
• Top seed orthologs frecuentes
• Análisis de e-values
• Patrones taxonómicos
"""
            
            ax4.text(0.1, 0.4, instructions, ha='left', va='center', fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcyan', alpha=0.7))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            
            plt.tight_layout()
            return self.save_figure('seed_orthologs_navigation_panel')
            
        except Exception as e:
            print(f"Error creando panel de navegación de seed orthologs: {e}")
            return None 