#!/usr/bin/env python3
"""
Visualizador Especializado para Resultados de CheckM
===================================================

Visualizador especializado para análisis de calidad genómica usando CheckM:
- Gráficos de Completitud vs Contaminación
- Distribuciones de GC Content
- Métricas de calidad genómica (N50, tamaño del genoma, etc.)
- Evaluación de bins genómicos
- Estadísticas de secuencias FASTA
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Configurar matplotlib para español
plt.rcParams['figure.max_open_warning'] = 50
plt.rcParams['font.size'] = 10

# Importaciones para análisis BioPython (opcional)
try:
    from Bio import SeqIO
    from Bio.SeqUtils import GC
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    print("BioPython no está disponible. Funcionalidades de FASTA limitadas.")

from .base_visualizer import BaseVisualizer

class CheckMVisualizer(BaseVisualizer):
    """Visualizador especializado para datos de CheckM y análisis de calidad genómica."""
    
    def __init__(self, output_dir: Path, config: Dict = None):
        super().__init__(output_dir, config)
        self.name = "CheckM Genomic Quality Assessment"
        self.default_figsize = (12, 8)
        
    def get_supported_extensions(self) -> List[str]:
        """Extensiones soportadas para archivos CheckM."""
        return ['.txt', '.tsv', '.csv', '.qc', '.quality', '.stats', '.fna', '.fasta', '.fa']
    
    def validate_file(self, file_path: Path) -> bool:
        """Validar archivo CheckM o FASTA."""
        if not file_path.exists():
            return False
            
        # Verificar tamaño del archivo
        if file_path.stat().st_size == 0:
            return False
            
        # Verificar si es archivo FASTA
        if file_path.suffix.lower() in ['.fna', '.fasta', '.fa']:
            return self._validate_fasta_file(file_path)
        
        try:
            # Intentar leer las primeras líneas
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(10)]
                
            # Verificar si hay contenido
            non_empty_lines = [line for line in lines if line]
            if len(non_empty_lines) < 2:
                return False
                
            # Verificar si parece ser un archivo de datos CheckM
            header = non_empty_lines[0].lower()
            checkm_keywords = ['bin', 'completeness', 'contamination', 'gc', 'genome', 'lineage', 'marker']
            
            return any(keyword in header for keyword in checkm_keywords)
            
        except Exception:
            return False
    
    def _validate_fasta_file(self, file_path: Path) -> bool:
        """Validar archivo FASTA."""
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                return first_line.startswith('>')
        except Exception:
            return False
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo CheckM o FASTA."""
        file_type = self._detect_file_type(file_path)
        
        if file_type == 'fasta':
            return self._parse_fasta_file(file_path)
        elif file_type == 'checkm_lineage':
            return self._parse_checkm_lineage(file_path)
        elif file_type == 'checkm_qa':
            return self._parse_checkm_qa(file_path)
        else:
            return self._parse_general_checkm(file_path)
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detectar tipo de archivo basado en extensión y contenido."""
        # Verificar extensión
        if file_path.suffix.lower() in ['.fna', '.fasta', '.fa']:
            return 'fasta'
        
        try:
            # Leer primeras líneas para detectar formato
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(5)]
            
            content = ' '.join(lines).lower()
            
            # Detectar formato CheckM específico
            if 'lineage' in content and 'marker' in content:
                return 'checkm_lineage'
            elif 'completeness' in content and 'contamination' in content:
                return 'checkm_qa'
            else:
                return 'checkm_general'
                
        except Exception:
            return 'checkm_general'
    
    def _parse_fasta_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo FASTA y calcular estadísticas."""
        sequences_data = []
        
        if BIOPYTHON_AVAILABLE:
            # Usar BioPython si está disponible
            try:
                for record in SeqIO.parse(file_path, "fasta"):
                    seq_len = len(record.seq)
                    gc_content = GC(record.seq)
                    sequences_data.append({
                        'sequence_id': record.id,
                        'description': record.description,
                        'length': seq_len,
                        'gc_content': gc_content
                    })
            except Exception as e:
                print(f"Error con BioPython: {e}")
                sequences_data = self._parse_fasta_manual(file_path)
        else:
            sequences_data = self._parse_fasta_manual(file_path)
        
        if not sequences_data:
            raise ValueError("No se pudieron parsear secuencias FASTA")
        
        df = pd.DataFrame(sequences_data)
        
        # Calcular estadísticas adicionales
        lengths = df['length']
        sorted_lengths = sorted(lengths, reverse=True)
        
        # Calcular N50
        total_length = sum(sorted_lengths)
        cumulative_length = 0
        n50 = 0
        for length in sorted_lengths:
            cumulative_length += length
            if cumulative_length >= total_length * 0.5:
                n50 = length
                break
        
        # Guardar estadísticas en atributos del DataFrame
        df.attrs['fasta_stats'] = {
            'total_sequences': len(df),
            'total_length': int(total_length),
            'average_length': float(lengths.mean()),
            'min_length': int(lengths.min()),
            'max_length': int(lengths.max()),
            'n50': int(n50),
            'average_gc': float(df['gc_content'].mean()),
            'min_gc': float(df['gc_content'].min()),
            'max_gc': float(df['gc_content'].max())
        }
        
        return df
    
    def _parse_fasta_manual(self, file_path: Path) -> List[Dict]:
        """Parsear FASTA manualmente sin BioPython."""
        sequences_data = []
        
        try:
            with open(file_path, 'r') as f:
                current_id = None
                current_seq = ""
                
                for line in f:
                    line = line.strip()
                    if line.startswith('>'):
                        if current_id:
                            # Procesar secuencia anterior
                            gc_count = current_seq.count('G') + current_seq.count('C')
                            gc_content = (gc_count / len(current_seq)) * 100 if current_seq else 0
                            
                            sequences_data.append({
                                'sequence_id': current_id,
                                'description': current_id,
                                'length': len(current_seq),
                                'gc_content': gc_content
                            })
                        
                        current_id = line[1:]  # Remover '>'
                        current_seq = ""
                    else:
                        current_seq += line.upper()
                
                # Procesar última secuencia
                if current_id:
                    gc_count = current_seq.count('G') + current_seq.count('C')
                    gc_content = (gc_count / len(current_seq)) * 100 if current_seq else 0
                    
                    sequences_data.append({
                        'sequence_id': current_id,
                        'description': current_id,
                        'length': len(current_seq),
                        'gc_content': gc_content
                    })
                    
        except Exception as e:
            print(f"Error parseando FASTA manualmente: {e}")
            
        return sequences_data

    def _parse_checkm_lineage(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo de lineage CheckM."""
        try:
            # Intentar diferentes separadores
            separators = ['\t', ',', ' ', ';']
            df = None
            
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, sep=sep, comment='#')
                    if len(df.columns) > 1:
                        break
                except:
                    continue
            
            if df is None or len(df.columns) <= 1:
                # Fallback: leer como texto y parsear manualmente
                df = pd.read_csv(file_path, sep='\t')
            
            return df
            
        except Exception as e:
            print(f"Error parseando CheckM lineage: {e}")
            return pd.DataFrame()

    def _parse_checkm_qa(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo CheckM QA (quality assessment)."""
        try:
            # Leer archivo, saltando comentarios
            df = pd.read_csv(file_path, sep='\t', comment='#')
            
            # Si no hay datos, intentar con diferentes separadores
            if df.empty or len(df.columns) <= 1:
                separators = [',', ' ', ';']
                for sep in separators:
                    try:
                        df = pd.read_csv(file_path, sep=sep, comment='#')
                        if not df.empty and len(df.columns) > 1:
                            break
                    except:
                        continue
            
            return df
            
        except Exception as e:
            print(f"Error parseando CheckM QA: {e}")
            return pd.DataFrame()

    def _parse_general_checkm(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo CheckM general."""
        try:
            # Intent different encodings and separators
            encodings = ['utf-8', 'latin-1', 'cp1252']
            separators = ['\t', ',', ' ', ';']
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        df = pd.read_csv(file_path, sep=sep, encoding=encoding, comment='#')
                        if not df.empty and len(df.columns) > 1:
                            return df
                    except:
                        continue
            
            # Si todo falla, leer como texto plano
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Crear DataFrame básico
            data = []
            for i, line in enumerate(lines[:100]):  # Limitar a 100 líneas
                if line.strip():
                    data.append({'line_number': i + 1, 'content': line.strip()})
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"Error parseando archivo general: {e}")
            return pd.DataFrame()

    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """Generar visualización simple y práctica según el tipo de datos."""
        if data.empty:
            return []
        
        # Detectar tipo de datos automáticamente
        file_type = self._detect_file_type_from_data(data)
        
        if file_type == 'fasta':
            return [self._create_fasta_summary(data)]
        else:
            return [self._create_checkm_summary(data)]
    
    def _detect_file_type_from_data(self, data: pd.DataFrame) -> str:
        """Detectar tipo de archivo basado en las columnas del DataFrame."""
        columns = [col.lower() for col in data.columns]
        
        if 'sequence_id' in columns and 'length' in columns and 'gc_content' in columns:
            return 'fasta'
        else:
            return 'checkm'
    
    def _find_column(self, data: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """Encontrar columna que contenga alguna de las palabras clave."""
        for col in data.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in keywords):
                return col
        return None
    
    def _create_fasta_summary(self, data: pd.DataFrame) -> str:
        """Crear resumen simple para archivos FASTA."""
        plt.figure(figsize=(14, 10))
        
        # Configurar grid
        gs = plt.GridSpec(2, 2, height_ratios=[1, 1], width_ratios=[1, 1])
        
        # Panel 1: Estadísticas principales
        ax1 = plt.subplot(gs[0, 0])
        ax1.axis('off')
        
        stats = data.attrs.get('fasta_stats', {})
        total_seq = len(data)
        total_length = data['length'].sum() if 'length' in data.columns else 0
        avg_length = data['length'].mean() if 'length' in data.columns else 0
        avg_gc = data['gc_content'].mean() if 'gc_content' in data.columns else 0
        n50 = stats.get('n50', 0)
        
        stats_text = f"""📊 RESUMEN FASTA
        
🧬 Secuencias totales: {total_seq:,}
📏 Longitud total: {total_length:,} bp
📐 Longitud promedio: {avg_length:.0f} bp
🎯 N50: {n50:,} bp
🔬 GC promedio: {avg_gc:.1f}%

💡 Calidad del ensamblaje:
{'🟢 Excelente' if n50 > 50000 else '🟡 Buena' if n50 > 10000 else '🔴 Mejorable'}
        """
        
        ax1.text(0.05, 0.95, stats_text, transform=ax1.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        
        # Panel 2: Distribución de longitudes
        ax2 = plt.subplot(gs[0, 1])
        if 'length' in data.columns:
            lengths = data['length']
            ax2.hist(lengths, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.axvline(lengths.mean(), color='red', linestyle='--', linewidth=2,
                       label=f'Media: {lengths.mean():.0f} bp')
            ax2.set_title('📏 Distribución de Longitudes', fontweight='bold')
            ax2.set_xlabel('Longitud (bp)')
            ax2.set_ylabel('Frecuencia')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # Panel 3: Distribución de GC
        ax3 = plt.subplot(gs[1, 0])
        if 'gc_content' in data.columns:
            gc = data['gc_content']
            ax3.hist(gc, bins=25, alpha=0.7, color='lightgreen', edgecolor='black')
            ax3.axvline(gc.mean(), color='darkgreen', linestyle='--', linewidth=2,
                       label=f'Media: {gc.mean():.1f}%')
            ax3.set_title('🔬 Distribución de GC%', fontweight='bold')
            ax3.set_xlabel('Contenido GC (%)')
            ax3.set_ylabel('Frecuencia')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # Panel 4: Top secuencias
        ax4 = plt.subplot(gs[1, 1])
        if 'length' in data.columns:
            top_seqs = data.nlargest(10, 'length')
            y_pos = range(len(top_seqs))
            ax4.barh(y_pos, top_seqs['length'], color='lightcoral')
            ax4.set_yticks(y_pos)
            ax4.set_yticklabels([seq[:20] + '...' if len(seq) > 20 else seq 
                               for seq in top_seqs['sequence_id']], fontsize=8)
            ax4.set_title('🏆 Top 10 Secuencias', fontweight='bold')
            ax4.set_xlabel('Longitud (bp)')
        
        plt.suptitle('📋 Análisis de Archivo FASTA', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        return self.save_figure('fasta_analysis')
    
    def _create_checkm_summary(self, data: pd.DataFrame) -> str:
        """Crear resumen simple y práctico para datos CheckM."""
        plt.figure(figsize=(16, 12))
        
        # Detectar columnas importantes
        completeness_col = self._find_column(data, ['completeness', 'complete'])
        contamination_col = self._find_column(data, ['contamination', 'contam'])
        
        # Si no hay datos de calidad, mostrar tabla simple
        if not completeness_col or not contamination_col:
            return self._create_data_table_view(data)
        
        # Preparar datos de calidad
        comp_data = pd.to_numeric(data[completeness_col], errors='coerce')
        cont_data = pd.to_numeric(data[contamination_col], errors='coerce')
        valid_mask = ~(comp_data.isna() | cont_data.isna())
        
        if valid_mask.sum() == 0:
            return self._create_data_table_view(data)
        
        # Clasificar por calidad
        alta_calidad = ((comp_data >= 90) & (cont_data <= 5)).sum()
        media_calidad = ((comp_data >= 70) & (cont_data <= 10)).sum()
        baja_calidad = ((comp_data >= 50) & (cont_data <= 15)).sum()
        muy_baja = len(data) - alta_calidad - media_calidad - baja_calidad
        
        # Configurar layout
        gs = plt.GridSpec(3, 2, height_ratios=[1, 1, 1], width_ratios=[1, 1])
        
        # Panel 1: Resumen de calidad
        ax1 = plt.subplot(gs[0, :])
        ax1.axis('off')
        
        total_genomas = valid_mask.sum()
        avg_comp = comp_data[valid_mask].mean()
        avg_cont = cont_data[valid_mask].mean()
        
        summary_text = f"""🏆 RESUMEN DE CALIDAD CHECKM
        
📊 Total de genomas analizados: {total_genomas}
📈 Completitud promedio: {avg_comp:.1f}%
⚠️ Contaminación promedio: {avg_cont:.1f}%

🟢 ALTA CALIDAD (≥90% comp, ≤5% cont): {alta_calidad} genomas ({alta_calidad/total_genomas*100:.1f}%)
🟡 CALIDAD MEDIA (≥70% comp, ≤10% cont): {media_calidad} genomas ({media_calidad/total_genomas*100:.1f}%)
🟠 CALIDAD BAJA (≥50% comp, ≤15% cont): {baja_calidad} genomas ({baja_calidad/total_genomas*100:.1f}%)
🔴 MUY BAJA CALIDAD: {muy_baja} genomas ({muy_baja/total_genomas*100:.1f}%)
        """
        
        ax1.text(0.05, 0.95, summary_text, transform=ax1.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
        
        # Panel 2: Gráfico de calidad
        ax2 = plt.subplot(gs[1, 0])
        categories = ['Alta\nCalidad', 'Calidad\nMedia', 'Calidad\nBaja', 'Muy Baja\nCalidad']
        values = [alta_calidad, media_calidad, baja_calidad, muy_baja]
        colors = ['green', 'orange', 'red', 'darkred']
        
        bars = ax2.bar(categories, values, color=colors, alpha=0.7)
        ax2.set_title('📊 Distribución de Calidad', fontweight='bold', fontsize=14)
        ax2.set_ylabel('Número de Genomas')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Añadir valores en las barras
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom', fontweight='bold')
        
        # Panel 3: Scatter plot Completitud vs Contaminación
        ax3 = plt.subplot(gs[1, 1])
        
        # Crear colores según calidad
        colors_scatter = []
        for comp, cont in zip(comp_data[valid_mask], cont_data[valid_mask]):
            if comp >= 90 and cont <= 5:
                colors_scatter.append('green')
            elif comp >= 70 and cont <= 10:
                colors_scatter.append('orange')
            elif comp >= 50 and cont <= 15:
                colors_scatter.append('red')
            else:
                colors_scatter.append('darkred')
        
        ax3.scatter(cont_data[valid_mask], comp_data[valid_mask], 
                   c=colors_scatter, alpha=0.7, s=60)
        
        # Líneas de referencia
        ax3.axhline(90, color='green', linestyle='--', alpha=0.5)
        ax3.axhline(70, color='orange', linestyle='--', alpha=0.5)
        ax3.axhline(50, color='red', linestyle='--', alpha=0.5)
        ax3.axvline(5, color='green', linestyle='--', alpha=0.5)
        ax3.axvline(10, color='orange', linestyle='--', alpha=0.5)
        ax3.axvline(15, color='red', linestyle='--', alpha=0.5)
        
        ax3.set_title('⭐ Completitud vs Contaminación', fontweight='bold', fontsize=14)
        ax3.set_xlabel('Contaminación (%)')
        ax3.set_ylabel('Completitud (%)')
        ax3.grid(True, alpha=0.3)
        
        # Panel 4: Tabla de mejores genomas
        ax4 = plt.subplot(gs[2, :])
        ax4.axis('off')
        
        # Seleccionar top 10 genomas de mejor calidad
        data_with_quality = data[valid_mask].copy()
        data_with_quality['quality_score'] = comp_data[valid_mask] - cont_data[valid_mask]
        top_genomes = data_with_quality.nlargest(10, 'quality_score')
        
        # Crear tabla
        table_data = []
        for idx, row in top_genomes.iterrows():
            genome_id = str(row.iloc[0])[:20]  # Primera columna como ID
            comp = row[completeness_col]
            cont = row[contamination_col]
            
            if comp >= 90 and cont <= 5:
                quality = "🟢 Alta"
            elif comp >= 70 and cont <= 10:
                quality = "🟡 Media"
            elif comp >= 50 and cont <= 15:
                quality = "🟠 Baja"
            else:
                quality = "🔴 Muy Baja"
            
            table_data.append([genome_id, f"{comp:.1f}%", f"{cont:.1f}%", quality])
        
        table = ax4.table(cellText=table_data,
                         colLabels=['Genoma ID', 'Completitud', 'Contaminación', 'Calidad'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0.1, 0.1, 0.8, 0.8])
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        
        # Colorear header
        for i in range(4):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        ax4.set_title('🏆 Top 10 Genomas de Mejor Calidad', fontweight='bold', fontsize=14, pad=20)
        
        plt.suptitle('📋 Análisis CheckM - Resultados de Calidad Genómica', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        return self.save_figure('checkm_analysis')
    
    def _create_data_table_view(self, data: pd.DataFrame) -> str:
        """Crear vista de tabla simple cuando no hay datos de calidad."""
        plt.figure(figsize=(14, 10))
        plt.axis('off')
        
        # Mostrar información básica del archivo
        info_text = f"""📊 INFORMACIÓN DEL ARCHIVO CHECKM
        
📁 Tipo de datos: Datos tabulares CheckM
📋 Número de filas: {len(data)}
📊 Número de columnas: {len(data.columns)}

📂 Columnas detectadas:
{chr(10).join([f"  • {col}" for col in data.columns[:15]])}
{'  • ... y más' if len(data.columns) > 15 else ''}

💡 Muestra de datos (primeras 5 filas):
        """
        
        plt.text(0.05, 0.95, info_text, transform=plt.gca().transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
        
        # Mostrar tabla con muestra de datos
        if len(data) > 0:
            sample_data = data.head(5)
            # Limitar ancho de columnas para que se vea bien
            display_cols = data.columns[:6] if len(data.columns) > 6 else data.columns
            sample_display = sample_data[display_cols]
            
            # Crear tabla
            table_data = []
            for _, row in sample_display.iterrows():
                table_data.append([str(val)[:15] + '...' if len(str(val)) > 15 else str(val) 
                                 for val in row])
            
            table = plt.table(cellText=table_data,
                            colLabels=[col[:15] + '...' if len(col) > 15 else col 
                                     for col in display_cols],
                            cellLoc='center',
                            loc='center',
                            bbox=[0.05, 0.1, 0.9, 0.4])
            
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.5)
            
            # Colorear header
            for i in range(len(display_cols)):
                table[(0, i)].set_facecolor('#2196F3')
                table[(0, i)].set_text_props(weight='bold', color='white')
        
        plt.title('📋 Vista Previa de Datos CheckM', fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        
        return self.save_figure('checkm_data_view')

    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas CheckM."""
        file_type = self._detect_file_type_from_data(data)
        
        if file_type == 'fasta':
            return self._generate_fasta_statistics(data)
        else:
            return self._generate_checkm_statistics(data)
    
    def _generate_fasta_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas para archivos FASTA."""
        stats = data.attrs.get('fasta_stats', {})
        
        return {
            'file_type': 'FASTA',
            'total_sequences': stats.get('total_sequences', len(data)),
            'total_length': stats.get('total_length', data['length'].sum()),
            'average_length': stats.get('average_length', data['length'].mean()),
            'min_length': stats.get('min_length', data['length'].min()),
            'max_length': stats.get('max_length', data['length'].max()),
            'n50': stats.get('n50', 0),
            'average_gc': stats.get('average_gc', data['gc_content'].mean()),
            'min_gc': stats.get('min_gc', data['gc_content'].min()),
            'max_gc': stats.get('max_gc', data['gc_content'].max()),
            'gc_std': data['gc_content'].std()
        }
    
    def _generate_checkm_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas para datos de CheckM."""
        stats = {
            'file_type': 'CheckM',
            'total_bins': len(data),
            'total_genomes': len(data)
        }
        
        # Buscar columnas relevantes
        completeness_col = None
        contamination_col = None
        gc_col = None
        genome_size_col = None
        
        for col in data.columns:
            col_lower = col.lower()
            if 'completeness' in col_lower:
                completeness_col = col
            elif 'contamination' in col_lower:
                contamination_col = col
            elif 'gc' in col_lower and 'content' in col_lower:
                gc_col = col
            elif 'genome_size' in col_lower or 'size' in col_lower:
                genome_size_col = col
        
        # Estadísticas de completitud
        if completeness_col:
            completeness = data[completeness_col]
            stats.update({
                'avg_completeness': completeness.mean(),
                'min_completeness': completeness.min(),
                'max_completeness': completeness.max(),
                'std_completeness': completeness.std()
            })
        
        # Estadísticas de contaminación
        if contamination_col:
            contamination = data[contamination_col]
            stats.update({
                'avg_contamination': contamination.mean(),
                'min_contamination': contamination.min(),
                'max_contamination': contamination.max(),
                'std_contamination': contamination.std()
            })
        
        # Clasificación de calidad
        if completeness_col and contamination_col:
            high_quality = ((data[completeness_col] >= 90) & (data[contamination_col] <= 5)).sum()
            medium_quality = ((data[completeness_col] >= 70) & (data[contamination_col] <= 10)).sum()
            low_quality = (data[completeness_col] >= 50).sum() - high_quality - medium_quality
            
            stats.update({
                'high_quality': high_quality,
                'medium_quality': medium_quality,
                'low_quality': low_quality,
                'very_low_quality': len(data) - high_quality - medium_quality - low_quality
            })
        
        # Estadísticas de GC
        if gc_col:
            gc_content = data[gc_col]
            stats.update({
                'avg_gc_content': gc_content.mean(),
                'min_gc_content': gc_content.min(),
                'max_gc_content': gc_content.max(),
                'std_gc_content': gc_content.std()
            })
        
        # Estadísticas de tamaño de genoma
        if genome_size_col:
            genome_sizes = data[genome_size_col]
            stats.update({
                'avg_genome_size': genome_sizes.mean(),
                'min_genome_size': genome_sizes.min(),
                'max_genome_size': genome_sizes.max(),
                'total_genome_size': genome_sizes.sum()
            })
        
        return stats 