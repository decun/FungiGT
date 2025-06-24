#!/usr/bin/env python3
"""
Visualizador Especializado para Anotaciones EggNOG
==================================================

Visualizador especializado para archivos .emapper.annotations generados por eggNOG-mapper.
Estos archivos contienen anotaciones funcionales completas incluyendo GO, KEGG, COG, etc.
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

class AnnotationsVisualizer(BaseVisualizer):
    """Visualizador especializado para archivos annotations de EggNOG."""
    
    def __init__(self, output_dir: Path, config: Dict = None):
        super().__init__(output_dir, config)
        self.name = "EggNOG Annotations Analysis"
        
        # Columnas estándar de .emapper.annotations
        self.annotation_columns = [
            'query', 'seed_ortholog', 'evalue', 'score', 'eggNOG_OGs', 'max_annot_lvl',
            'COG_category', 'Description', 'Preferred_name', 'GOs', 'EC', 'KEGG_ko',
            'KEGG_Pathway', 'KEGG_Module', 'KEGG_Reaction', 'KEGG_rclass', 'BRITE',
            'KEGG_TC', 'CAZy', 'BiGG_Reaction', 'PFAMs'
        ]
        
    def get_supported_extensions(self) -> List[str]:
        """Extensiones soportadas para archivos de anotaciones."""
        return ['.emapper.annotations', '.annotations', '.tsv', '.txt']
    
    def validate_file(self, file_path: Path) -> bool:
        """Validar archivo de anotaciones."""
        try:
            # Verificar extensión
            if not any(str(file_path).lower().endswith(ext) for ext in self.get_supported_extensions()):
                print(f"❌ Extensión no soportada. Extensiones válidas: {self.get_supported_extensions()}")
                return False
            
            # Leer primeras líneas para verificar formato
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
            
            # Verificar que tenga columnas mínimas de anotaciones
            first_data_line = lines[0]
            columns = first_data_line.split('\t')
            
            if len(columns) < 10:
                print(f"❌ Formato no válido - Se esperaban al menos 10 columnas, encontradas {len(columns)}")
                return False
            
            print(f"✅ Archivo de anotaciones válido - Detectadas {len(columns)} columnas")
            return True
            
        except Exception as e:
            print(f"❌ Error validando archivo: {e}")
            return False
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo de anotaciones."""
        try:
            print(f"🔍 Parseando archivo de anotaciones: {file_path.name}")
            
            # Leer archivo saltando comentarios
            df = pd.read_csv(file_path, sep='\t', comment='#', header=None, low_memory=False)
            
            # Asignar nombres de columnas
            if len(df.columns) >= len(self.annotation_columns):
                df.columns = self.annotation_columns[:len(df.columns)]
            else:
                # Si tiene menos columnas, usar genéricos pero mantener los conocidos
                df.columns = [f'col_{i}' for i in range(len(df.columns))]
                known_cols = ['query', 'seed_ortholog', 'evalue', 'score', 'Description', 'GOs', 'KEGG_ko', 'COG_category']
                for i, col in enumerate(known_cols[:len(df.columns)]):
                    df.columns.values[i] = col
            
            # Limpiar datos
            df = df.dropna(subset=['query'])
            df = df[df['query'] != '']
            
            # Convertir tipos de datos
            if 'evalue' in df.columns:
                df['evalue'] = pd.to_numeric(df['evalue'], errors='coerce')
            if 'score' in df.columns:
                df['score'] = pd.to_numeric(df['score'], errors='coerce')
            
            print(f"✅ Parseadas {len(df)} anotaciones de {len(df['query'].unique())} secuencias únicas")
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo de anotaciones: {str(e)}")
    
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """Generar todas las visualizaciones de anotaciones."""
        graphs = []
        
        try:
            # Resumen general
            overview_graphs = self._plot_annotation_overview(data)
            graphs.extend(overview_graphs)
        except Exception as e:
            print(f"Error creando overview: {e}")
        
        try:
            # Análisis GO
            if 'GOs' in data.columns:
                go_graphs = self._plot_go_analysis(data)
                graphs.extend(go_graphs)
        except Exception as e:
            print(f"Error creando análisis GO: {e}")
        
        try:
            # Análisis KEGG
            if 'KEGG_ko' in data.columns:
                kegg_graphs = self._plot_kegg_analysis(data)
                graphs.extend(kegg_graphs)
        except Exception as e:
            print(f"Error creando análisis KEGG: {e}")
        
        try:
            # Análisis COG
            if 'COG_category' in data.columns:
                cog_graphs = self._plot_cog_analysis(data)
                graphs.extend(cog_graphs)
        except Exception as e:
            print(f"Error creando análisis COG: {e}")
        
        try:
            # Gráfico de navegación y controles
            navigation_graph = self._create_navigation_panel(data)
            graphs.append(navigation_graph)
        except Exception as e:
            print(f"Error creando panel de navegación: {e}")
        
        return [g for g in graphs if g]
    
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas de anotaciones."""
        stats = {
            'total_annotations': len(data),
            'unique_proteins': len(data['query'].unique()) if 'query' in data.columns else 0,
        }
        
        if 'GOs' in data.columns:
            go_data = data[data['GOs'].notna() & (data['GOs'] != '-')]
            stats['proteins_with_go'] = len(go_data)
        
        if 'KEGG_ko' in data.columns:
            kegg_data = data[data['KEGG_ko'].notna() & (data['KEGG_ko'] != '-')]
            stats['proteins_with_kegg'] = len(kegg_data)
        
        if 'score' in data.columns:
            scores = data['score'].dropna()
            if len(scores) > 0:
                stats['avg_score'] = float(scores.mean())
                stats['max_score'] = float(scores.max())
        
        return stats
    
    def _plot_annotation_overview(self, data: pd.DataFrame) -> List[str]:
        """Crear gráficos de resumen de anotaciones."""
        graphs = []
        
        # 1. Cobertura por base de datos
        try:
            plt.figure(figsize=(12, 8))
            
            coverage_data = {}
            if 'GOs' in data.columns:
                coverage_data['GO Terms'] = len(data[data['GOs'].notna() & (data['GOs'] != '-')])
            if 'KEGG_ko' in data.columns:
                coverage_data['KEGG'] = len(data[data['KEGG_ko'].notna() & (data['KEGG_ko'] != '-')])
            if 'COG_category' in data.columns:
                coverage_data['COG'] = len(data[data['COG_category'].notna() & (data['COG_category'] != '-')])
            if 'PFAMs' in data.columns:
                coverage_data['Pfam'] = len(data[data['PFAMs'].notna() & (data['PFAMs'] != '-')])
            
            if coverage_data:
                plt.bar(coverage_data.keys(), coverage_data.values(), color=['lightblue', 'lightgreen', 'orange', 'pink'])
                plt.title('📊 Cobertura por Base de Datos', fontsize=14, fontweight='bold')
                plt.ylabel('Número de Proteínas Anotadas')
                plt.xticks(rotation=45)
                plt.tight_layout()
                graphs.append(self.save_figure('annotation_coverage'))
                plt.close()
        except Exception as e:
            print(f"Error creando cobertura: {e}")
        
        # 2. Top descripciones
        try:
            if 'Description' in data.columns:
                plt.figure(figsize=(14, 8))
                desc_data = data[data['Description'].notna() & (data['Description'] != '-')]
                if len(desc_data) > 0:
                    top_descriptions = desc_data['Description'].value_counts().head(15)
                    
                    plt.barh(range(len(top_descriptions)), top_descriptions.values, color='skyblue')
                    plt.yticks(range(len(top_descriptions)), 
                              [desc[:60] + '...' if len(desc) > 60 else desc for desc in top_descriptions.index])
                    plt.title('📊 Top 15 Descripciones Funcionales', fontsize=14, fontweight='bold')
                    plt.xlabel('Frecuencia')
                    plt.tight_layout()
                    graphs.append(self.save_figure('top_descriptions'))
                    plt.close()
        except Exception as e:
            print(f"Error creando descripciones: {e}")
        
        # 3. Distribución de e-values
        try:
            if 'evalue' in data.columns:
                plt.figure(figsize=(10, 6))
                evalues = data['evalue'].dropna()
                evalues = evalues[evalues > 0]
                if len(evalues) > 0:
                    plt.hist(np.log10(evalues), bins=30, alpha=0.7, color='orange', edgecolor='black')
                    plt.title('📊 Distribución de E-values (log10)', fontsize=14, fontweight='bold')
                    plt.xlabel('Log10(E-value)')
                    plt.ylabel('Frecuencia')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    graphs.append(self.save_figure('evalue_distribution'))
                    plt.close()
        except Exception as e:
            print(f"Error creando e-values: {e}")
        
        # 4. Estadísticas generales
        try:
            plt.figure(figsize=(10, 8))
            stats_text = f"""ESTADÍSTICAS DE ANOTACIONES FUNCIONALES

Total de anotaciones: {len(data):,}
Proteínas únicas: {len(data['query'].unique()):,}
"""
            
            if 'GOs' in data.columns:
                go_count = len(data[data['GOs'].notna() & (data['GOs'] != '-')])
                stats_text += f"Proteínas con GO: {go_count:,}\n"
            
            if 'KEGG_ko' in data.columns:
                kegg_count = len(data[data['KEGG_ko'].notna() & (data['KEGG_ko'] != '-')])
                stats_text += f"Proteínas con KEGG: {kegg_count:,}\n"
            
            if 'score' in data.columns:
                scores = data['score'].dropna()
                if len(scores) > 0:
                    stats_text += f"\nScore promedio: {scores.mean():.2f}\n"
                    stats_text += f"Score máximo: {scores.max():.2f}\n"
            
            plt.text(0.1, 0.5, stats_text, fontsize=14, verticalalignment='center',
                    bbox=dict(boxstyle="round,pad=1", facecolor='lightgreen', alpha=0.8))
            plt.xlim(0, 1)
            plt.ylim(0, 1)
            plt.axis('off')
            plt.title('📊 Estadísticas Generales de Anotaciones', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            graphs.append(self.save_figure('annotation_stats'))
            plt.close()
        except Exception as e:
            print(f"Error creando estadísticas: {e}")
        
        return graphs
    
    def _plot_go_analysis(self, data: pd.DataFrame) -> List[str]:
        """Análisis de términos GO."""
        graphs = []
        go_data = data[data['GOs'].notna() & (data['GOs'] != '-')]
        
        if len(go_data) == 0:
            return graphs
        
        # Extraer términos GO individuales
        all_go_terms = []
        for go_string in go_data['GOs']:
            if pd.notna(go_string) and go_string != '-':
                terms = go_string.split(',')
                all_go_terms.extend([term.strip() for term in terms])
        
        if not all_go_terms:
            return graphs
        
        # Top términos GO
        try:
            plt.figure(figsize=(12, 8))
            go_counts = Counter(all_go_terms)
            top_go = dict(go_counts.most_common(15))
            
            plt.bar(range(len(top_go)), list(top_go.values()), color='lightcoral')
            plt.xticks(range(len(top_go)), 
                      [term[:15] + '...' if len(term) > 15 else term for term in top_go.keys()], 
                      rotation=45, ha='right')
            plt.title('🧬 Top 15 Términos GO', fontsize=14, fontweight='bold')
            plt.ylabel('Frecuencia')
            plt.tight_layout()
            graphs.append(self.save_figure('go_top_terms'))
            plt.close()
        except Exception as e:
            print(f"Error creando top términos GO: {e}")
        
        return graphs
    
    def _plot_kegg_analysis(self, data: pd.DataFrame) -> List[str]:
        """Análisis de rutas KEGG."""
        graphs = []
        kegg_data = data[data['KEGG_ko'].notna() & (data['KEGG_ko'] != '-')]
        
        if len(kegg_data) == 0:
            return graphs
        
        # Top KO terms
        try:
            plt.figure(figsize=(12, 8))
            ko_counts = kegg_data['KEGG_ko'].value_counts().head(15)
            
            plt.bar(range(len(ko_counts)), ko_counts.values, color='lightgreen')
            plt.xticks(range(len(ko_counts)), 
                      [ko[:15] + '...' if len(ko) > 15 else ko for ko in ko_counts.index], 
                      rotation=45, ha='right')
            plt.title('🔬 Top 15 Términos KEGG KO', fontsize=14, fontweight='bold')
            plt.ylabel('Frecuencia')
            plt.tight_layout()
            graphs.append(self.save_figure('kegg_top_terms'))
            plt.close()
        except Exception as e:
            print(f"Error creando top KEGG: {e}")
        
        return graphs
    
    def _plot_cog_analysis(self, data: pd.DataFrame) -> List[str]:
        """Análisis de categorías COG."""
        graphs = []
        cog_data = data[data['COG_category'].notna() & (data['COG_category'] != '-')]
        
        if len(cog_data) == 0:
            return graphs
        
        # Distribución de categorías COG
        try:
            plt.figure(figsize=(12, 8))
            cog_counts = cog_data['COG_category'].value_counts().head(15)
            
            plt.bar(range(len(cog_counts)), cog_counts.values, color='gold')
            plt.xticks(range(len(cog_counts)), cog_counts.index, rotation=45)
            plt.title('🔧 Top 15 Categorías COG', fontsize=14, fontweight='bold')
            plt.ylabel('Frecuencia')
            plt.tight_layout()
            graphs.append(self.save_figure('cog_categories'))
            plt.close()
        except Exception as e:
            print(f"Error creando categorías COG: {e}")
        
        return graphs
    
    def _create_navigation_panel(self, data: pd.DataFrame) -> str:
        """Crear panel de navegación y controles interactivos."""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('🎛️ Panel de Control - Visualizador EggNOG Annotations', fontsize=16, fontweight='bold')
            
            # Control 1: Resumen de datos
            ax1.text(0.5, 0.7, 'RESUMEN DE DATOS', ha='center', va='center', fontsize=14, fontweight='bold')
            
            summary_text = f"""
📊 Total de anotaciones: {len(data):,}
🧬 Proteínas únicas: {len(data['query'].unique()):,}
📈 Promedio anotaciones/proteína: {len(data) / len(data['query'].unique()):.1f}
"""
            
            if 'GOs' in data.columns:
                go_count = len(data[data['GOs'].notna() & (data['GOs'] != '-')])
                summary_text += f"🔬 Proteínas con GO: {go_count:,} ({go_count/len(data)*100:.1f}%)\n"
            
            if 'KEGG_ko' in data.columns:
                kegg_count = len(data[data['KEGG_ko'].notna() & (data['KEGG_ko'] != '-')])
                summary_text += f"🧪 Proteínas con KEGG: {kegg_count:,} ({kegg_count/len(data)*100:.1f}%)\n"
            
            ax1.text(0.1, 0.3, summary_text, ha='left', va='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.7))
            ax1.set_xlim(0, 1)
            ax1.set_ylim(0, 1)
            ax1.axis('off')
            
            # Control 2: Calidad de anotaciones
            if 'score' in data.columns:
                scores = data['score'].dropna()
                if len(scores) > 0:
                    ax2.hist(scores, bins=20, alpha=0.7, color='green', edgecolor='black')
                    ax2.set_title('📊 Distribución de Scores', fontweight='bold')
                    ax2.set_xlabel('Score')
                    ax2.set_ylabel('Frecuencia')
                    ax2.grid(True, alpha=0.3)
            else:
                ax2.text(0.5, 0.5, 'CONTROL DE CALIDAD\n\n⚠️ No hay datos de score\ndisponibles', 
                        ha='center', va='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.7))
                ax2.set_xlim(0, 1)
                ax2.set_ylim(0, 1)
                ax2.axis('off')
            
            # Control 3: Base de datos más representada
            db_stats = {}
            if 'GOs' in data.columns:
                db_stats['GO'] = len(data[data['GOs'].notna() & (data['GOs'] != '-')])
            if 'KEGG_ko' in data.columns:
                db_stats['KEGG'] = len(data[data['KEGG_ko'].notna() & (data['KEGG_ko'] != '-')])
            if 'COG_category' in data.columns:
                db_stats['COG'] = len(data[data['COG_category'].notna() & (data['COG_category'] != '-')])
            if 'PFAMs' in data.columns:
                db_stats['Pfam'] = len(data[data['PFAMs'].notna() & (data['PFAMs'] != '-')])
            
            if db_stats:
                databases = list(db_stats.keys())
                counts = list(db_stats.values())
                colors = ['lightcoral', 'lightgreen', 'gold', 'lightblue'][:len(databases)]
                
                ax3.pie(counts, labels=databases, colors=colors, autopct='%1.1f%%', startangle=90)
                ax3.set_title('🗂️ Cobertura por Base de Datos', fontweight='bold')
            else:
                ax3.text(0.5, 0.5, 'BASES DE DATOS\n\n⚠️ No hay datos de\nbases de datos disponibles', 
                        ha='center', va='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcoral', alpha=0.7))
                ax3.set_xlim(0, 1)
                ax3.set_ylim(0, 1)
                ax3.axis('off')
            
            # Control 4: Instrucciones y navegación
            ax4.text(0.5, 0.8, 'NAVEGACIÓN Y CONTROLES', ha='center', va='center', 
                    fontsize=14, fontweight='bold')
            
            instructions = """
🖱️ CONTROLES DISPONIBLES:

📊 Gráficos generados automáticamente
🔍 Estadísticas detalladas calculadas
📈 Análisis comparativo incluido
🗂️ Exportación de resultados disponible

💡 CONSEJOS:
• Revisa las estadísticas de calidad
• Compara cobertura entre bases de datos
• Identifica patrones funcionales
• Usa filtros para análisis específicos
"""
            
            ax4.text(0.1, 0.5, instructions, ha='left', va='center', fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgreen', alpha=0.7))
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
            
            plt.tight_layout()
            return self.save_figure('navigation_panel')
            
        except Exception as e:
            print(f"Error creando panel de navegación: {e}")
            return None 