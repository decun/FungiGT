#!/usr/bin/env python3
"""
DNA Features Viewer - Visualizador de Características de DNA
=============================================================

Visualizador especializado usando DNA Features Viewer para:
- Archivos GenBank (.gb, .gbk)
- Archivos GFF (.gff, .gff3)  
- Archivos FASTA (.fna, .faa, .fasta)
- BioPython SeqRecords

Implementa todos los ejemplos de DNA Features Viewer:
- Gráficos básicos lineales y circulares
- Visualización de secuencias y traducciones
- Plots interactivos con Bokeh
- Multi-línea y multi-página
- Traductores personalizados
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Optional
import warnings
import tempfile
import os

# Suppress warnings
warnings.filterwarnings('ignore')

# Configurar matplotlib
plt.rcParams['figure.max_open_warning'] = 50
plt.rcParams['font.size'] = 10

# Importaciones para DNA Features Viewer
try:
    from dna_features_viewer import GraphicFeature, GraphicRecord, CircularGraphicRecord, BiopythonTranslator
    DNA_FEATURES_AVAILABLE = True
    print("✅ DNA Features Viewer disponible correctamente")
except ImportError as e:
    DNA_FEATURES_AVAILABLE = False
    print(f"❌ DNA Features Viewer no está disponible: {e}")

# Importaciones para BioPython
try:
    from Bio import SeqIO
    from Bio.SeqRecord import SeqRecord
    from Bio.Seq import Seq
    # Intentar importar GC desde diferentes ubicaciones según la versión
    try:
        from Bio.SeqUtils import gc_fraction as GC
    except ImportError:
        try:
            from Bio.SeqUtils import GC
        except ImportError:
            # Crear función GC simple si no está disponible
            def GC(seq):
                seq_str = str(seq).upper()
                return (seq_str.count('G') + seq_str.count('C')) / len(seq_str) * 100
    
    BIOPYTHON_AVAILABLE = True
    print("✅ BioPython disponible correctamente")
except ImportError as e:
    BIOPYTHON_AVAILABLE = False
    # Crear clases dummy para evitar errores de tipo
    class SeqRecord:
        pass
    class Seq:
        pass
    def GC(seq):
        return 0
    print(f"❌ BioPython no está disponible: {e}")

# Importaciones para Bokeh (opcional)
try:
    import bokeh
    BOKEH_AVAILABLE = True
except ImportError:
    BOKEH_AVAILABLE = False

# Importaciones para GFF (opcional)
try:
    from BCBio import GFF
    GFF_AVAILABLE = True
except ImportError:
    GFF_AVAILABLE = False

from .base_visualizer import BaseVisualizer

class DNAFeaturesVisualizer(BaseVisualizer):
    """Visualizador especializado para características de DNA usando DNA Features Viewer."""
    
    def __init__(self, output_dir: Path, config: Dict = None):
        super().__init__(output_dir, config)
        self.name = "DNA Features Viewer"
        self.default_figsize = (12, 8)
        
        # Verificar dependencias
        if not DNA_FEATURES_AVAILABLE:
            print("⚠️ DNA Features Viewer no disponible. Algunas funcionalidades estarán limitadas.")
        
    def get_supported_extensions(self) -> List[str]:
        """Extensiones soportadas para archivos de DNA."""
        return ['.gb', '.gbk', '.genbank', '.gff', '.gff3', '.fna', '.faa', '.fasta', '.fa', '.fas']
    
    def validate_file(self, file_path: Path) -> bool:
        """Validar archivo de DNA."""
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False
            
        # Verificar por extensión y contenido
        ext = file_path.suffix.lower()
        
        if ext in ['.gb', '.gbk', '.genbank']:
            return self._validate_genbank_file(file_path)
        elif ext in ['.gff', '.gff3']:
            return self._validate_gff_file(file_path)
        elif ext in ['.fna', '.faa', '.fasta', '.fa', '.fas']:
            return self._validate_fasta_file(file_path)
        
        return False
    
    def _validate_genbank_file(self, file_path: Path) -> bool:
        """Validar archivo GenBank."""
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                return first_line.startswith('LOCUS')
        except:
            return False
    
    def _validate_gff_file(self, file_path: Path) -> bool:
        """Validar archivo GFF."""
        try:
            with open(file_path, 'r') as f:
                content = f.read(100)
                return '##gff' in content.lower() or content.count('\t') >= 8
        except:
            return False
    
    def _validate_fasta_file(self, file_path: Path) -> bool:
        """Validar archivo FASTA."""
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                return first_line.startswith('>')
        except:
            return False
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo DNA y preparar datos."""
        ext = file_path.suffix.lower()
        
        if ext in ['.gb', '.gbk', '.genbank']:
            return self._parse_genbank_file(file_path)
        elif ext in ['.gff', '.gff3']:
            return self._parse_gff_file(file_path)
        elif ext in ['.fna', '.faa', '.fasta', '.fa', '.fas']:
            return self._parse_fasta_file(file_path)
        else:
            raise ValueError(f"Formato de archivo no soportado: {ext}")
    
    def _parse_genbank_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo GenBank."""
        if not BIOPYTHON_AVAILABLE:
            raise ValueError("BioPython requerido para archivos GenBank")
        
        try:
            records = list(SeqIO.parse(file_path, "genbank"))
            if not records:
                raise ValueError("No se encontraron registros en el archivo GenBank")
            
            # Usar el primer registro
            record = records[0]
            
            # Extraer información del registro
            data = {
                'file_type': 'genbank',
                'record': record,
                'sequence_length': len(record.seq),
                'features_count': len(record.features),
                'description': record.description,
                'organism': record.annotations.get('organism', 'Unknown'),
                'file_path': str(file_path)
            }
            
            return pd.DataFrame([data])
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo GenBank: {str(e)}")
    
    def _parse_gff_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo GFF."""
        if not GFF_AVAILABLE:
            raise ValueError("bcbio-gff requerido para archivos GFF")
        
        try:
            # Leer archivo GFF
            with open(file_path) as f:
                records = list(GFF.parse(f))
            
            if not records:
                raise ValueError("No se encontraron registros en el archivo GFF")
            
            record = records[0]
            
            data = {
                'file_type': 'gff',
                'record': record,
                'sequence_length': len(record.seq) if record.seq else 1000,
                'features_count': len(record.features),
                'description': record.description,
                'file_path': str(file_path)
            }
            
            return pd.DataFrame([data])
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo GFF: {str(e)}")
    
    def _parse_fasta_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo FASTA y crear características artificiales."""
        try:
            # Forzar importación aquí para asegurar que funcione
            from Bio import SeqIO
            from Bio.SeqRecord import SeqRecord
            
            records = list(SeqIO.parse(file_path, "fasta"))
            if not records:
                raise ValueError("No se encontraron secuencias en el archivo FASTA")
            
            record = records[0]
            
            # Para archivos FASTA, crear características artificiales basadas en la secuencia
            features = self._create_artificial_features(record)
            
            data = {
                'file_type': 'fasta',
                'record': record,
                'sequence_length': len(record.seq),
                'features_count': len(features),
                'description': record.description,
                'artificial_features': features,
                'file_path': str(file_path)
            }
            
            return pd.DataFrame([data])
            
        except ImportError:
            raise ValueError("BioPython requerido para archivos FASTA")
        except Exception as e:
            raise ValueError(f"Error parseando archivo FASTA: {str(e)}")
    
    def _create_artificial_features(self, record: SeqRecord) -> List[Dict]:
        """Crear características artificiales para secuencias FASTA."""
        features = []
        sequence = str(record.seq).upper()
        seq_len = len(sequence)
        
        # Detectar ORFs simples (ATG...TAA/TAG/TGA)
        start_codons = ['ATG']
        stop_codons = ['TAA', 'TAG', 'TGA']
        
        # Buscar ORFs en ambas direcciones
        for strand in [1, -1]:
            seq_to_search = sequence if strand == 1 else str(record.seq.reverse_complement()).upper()
            
            i = 0
            while i < len(seq_to_search) - 2:
                codon = seq_to_search[i:i+3]
                if codon in start_codons:
                    # Buscar codón de parada
                    for j in range(i + 3, len(seq_to_search) - 2, 3):
                        stop_codon = seq_to_search[j:j+3]
                        if stop_codon in stop_codons:
                            orf_length = j + 3 - i
                            if orf_length >= 150:  # ORFs mínimos de 50 aminoácidos
                                start_pos = i if strand == 1 else seq_len - (j + 3)
                                end_pos = j + 3 if strand == 1 else seq_len - i
                                
                                features.append({
                                    'start': min(start_pos, end_pos),
                                    'end': max(start_pos, end_pos),
                                    'strand': strand,
                                    'type': 'ORF',
                                    'label': f'ORF {len(features)+1} ({orf_length}bp)',
                                    'color': '#ffcccc' if strand == 1 else '#ccccff'
                                })
                            break
                i += 1
        
        # Analizar contenido GC en ventanas
        window_size = max(50, seq_len // 20)
        for i in range(0, seq_len - window_size, window_size):
            window_seq = sequence[i:i+window_size]
            gc_content = (window_seq.count('G') + window_seq.count('C')) / len(window_seq) * 100
            
            if gc_content > 60:
                color = '#90EE90'  # Verde claro para alto GC
                label = f'High GC ({gc_content:.1f}%)'
            elif gc_content < 40:
                color = '#FFB6C1'  # Rosa claro para bajo GC
                label = f'Low GC ({gc_content:.1f}%)'
            else:
                continue
            
            features.append({
                'start': i,
                'end': i + window_size,
                'strand': 0,
                'type': 'GC_region',
                'label': label,
                'color': color
            })
        
        return features
    
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """Generar todas las visualizaciones DNA Features Viewer."""
        if not DNA_FEATURES_AVAILABLE:
            return [self._create_error_plot("DNA Features Viewer no está instalado")]
        
        graphs = []
        
        for _, row in data.iterrows():
            file_type = row['file_type']
            
            if file_type == 'genbank':
                graphs.extend(self._create_genbank_visualizations(row))
            elif file_type == 'gff':
                graphs.extend(self._create_gff_visualizations(row))
            elif file_type == 'fasta':
                graphs.extend(self._create_fasta_visualizations(row))
        
        return graphs
    
    def _create_genbank_visualizations(self, row: pd.Series) -> List[str]:
        """Crear visualizaciones para archivos GenBank."""
        graphs = []
        record = row['record']
        
        # 1. Plot básico lineal
        try:
            graphs.append(self._plot_basic_linear(record, "GenBank Linear View"))
        except Exception as e:
            print(f"Error en plot lineal: {e}")
        
        # 2. Plot circular
        try:
            graphs.append(self._plot_basic_circular(record, "GenBank Circular View"))
        except Exception as e:
            print(f"Error en plot circular: {e}")
        
        # 3. Plot con secuencia y traducción
        try:
            graphs.append(self._plot_with_sequence(record, "GenBank with Sequence"))
        except Exception as e:
            print(f"Error en plot con secuencia: {e}")
        
        # 4. Plot con estadísticas (GC content)
        try:
            graphs.append(self._plot_with_gc_content(record, "GenBank with GC Content"))
        except Exception as e:
            print(f"Error en plot con GC: {e}")
        
        return graphs
    
    def _create_gff_visualizations(self, row: pd.Series) -> List[str]:
        """Crear visualizaciones para archivos GFF."""
        graphs = []
        record = row['record']
        
        try:
            graphs.append(self._plot_basic_linear(record, "GFF Linear View"))
            graphs.append(self._plot_basic_circular(record, "GFF Circular View"))
        except Exception as e:
            print(f"Error en visualizaciones GFF: {e}")
        
        return graphs
    
    def _create_fasta_visualizations(self, row: pd.Series) -> List[str]:
        """Crear visualizaciones para archivos FASTA."""
        graphs = []
        record = row['record']
        artificial_features = row.get('artificial_features', [])
        
        try:
            # Importar aquí para asegurar disponibilidad
            from dna_features_viewer import GraphicFeature, GraphicRecord, CircularGraphicRecord
            
            # Crear GraphicRecord con características artificiales
            features = []
            for feat in artificial_features:
                features.append(GraphicFeature(
                    start=feat['start'],
                    end=feat['end'],
                    strand=feat['strand'],
                    color=feat['color'],
                    label=feat['label']
                ))
            
            # Si no hay características, crear algunas básicas
            if not features:
                seq_len = len(record.seq)
                features = [
                    GraphicFeature(start=0, end=seq_len//3, strand=1, color='#ffcccc', label='Region 1'),
                    GraphicFeature(start=seq_len//3, end=2*seq_len//3, strand=1, color='#ccffcc', label='Region 2'),
                    GraphicFeature(start=2*seq_len//3, end=seq_len, strand=1, color='#ccccff', label='Region 3')
                ]
            
            graphic_record = GraphicRecord(
                sequence_length=len(record.seq),
                features=features,
                sequence=str(record.seq) if len(record.seq) <= 1000 else None  # Solo secuencias cortas
            )
            
            # Plot lineal simple
            graphs.append(self._plot_fasta_simple(graphic_record, record, "FASTA Linear View"))
            
            # Plot circular
            graphs.append(self._plot_fasta_circular_simple(graphic_record, record, "FASTA Circular View"))
            
        except Exception as e:
            print(f"Error en visualizaciones FASTA: {e}")
            # Crear visualización de error específica
            graphs.append(self._create_error_plot(f"Error en FASTA: {str(e)}"))
        
        return graphs
    
    def _plot_basic_linear(self, record, title: str) -> str:
        """Plot básico lineal usando BiopythonTranslator."""
        try:
            fig, ax = plt.subplots(figsize=self.default_figsize)
            
            # Usar BiopythonTranslator para convertir el registro
            translator = BiopythonTranslator()
            graphic_record = translator.translate_record(record)
            
            # Plot con características avanzadas
            graphic_record.plot(ax=ax, figure_width=10, strand_in_label_threshold=7)
            
            ax.set_title(f"{title}\n{record.description}", fontsize=14, pad=20)
            
            # Información adicional
            info_text = f"Length: {len(record.seq):,} bp | Features: {len(record.features)}"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=10, 
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_linear_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot lineal: {e}")
            return self._create_error_plot(f"Error en visualización lineal: {str(e)}")
    
    def _plot_basic_circular(self, record, title: str) -> str:
        """Plot básico circular."""
        try:
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # Usar BiopythonTranslator para convertir
            translator = BiopythonTranslator()
            graphic_record = translator.translate_record(record)
            
            # Convertir a circular
            circular_record = CircularGraphicRecord(
                sequence_length=graphic_record.sequence_length,
                features=graphic_record.features
            )
            
            circular_record.plot(ax=ax)
            
            ax.set_title(f"{title}\n{record.description}", fontsize=14, pad=20)
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_circular_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot circular: {e}")
            return self._create_error_plot(f"Error en visualización circular: {str(e)}")
    
    def _plot_with_sequence(self, record, title: str) -> str:
        """Plot con secuencia y traducción."""
        try:
            # Tomar una subsección para mostrar secuencia
            seq_length = len(record.seq)
            start_crop = min(100, seq_length // 4)
            end_crop = min(start_crop + 300, seq_length - 50)
            
            translator = BiopythonTranslator()
            graphic_record = translator.translate_record(record)
            
            # Crear figura con subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
            
            # Plot superior: overview completo
            graphic_record.plot(ax=ax1, figure_width=10)
            ax1.set_title(f"{title} - Overview", fontsize=12)
            
            # Plot inferior: detalle con secuencia
            cropped_record = graphic_record.crop((start_crop, end_crop))
            cropped_record.plot(ax=ax2)
            
            # Agregar secuencia si no es muy larga
            if end_crop - start_crop <= 200:
                cropped_record.plot_sequence(ax=ax2)
                
                # Buscar un ORF para mostrar traducción
                for feature in record.features:
                    if (hasattr(feature, 'type') and feature.type == 'CDS' and 
                        feature.location.start >= start_crop and 
                        feature.location.end <= end_crop):
                        try:
                            cropped_record.plot_translation(
                                ax=ax2, 
                                location=(feature.location.start - start_crop, 
                                         feature.location.end - start_crop),
                                fontdict={'weight': 'bold', 'size': 8}
                            )
                            break
                        except:
                            pass
            
            ax2.set_title(f"Detail View ({start_crop}-{end_crop} bp)", fontsize=10)
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_sequence_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot con secuencia: {e}")
            return self._create_error_plot(f"Error en visualización con secuencia: {str(e)}")
    
    def _plot_with_gc_content(self, record, title: str) -> str:
        """Plot con contenido GC."""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6),
                                          gridspec_kw={'height_ratios': [4, 1]}, 
                                          sharex=True)
            
            # Plot superior: características
            translator = BiopythonTranslator()
            graphic_record = translator.translate_record(record)
            graphic_record.plot(ax=ax1, with_ruler=False, strand_in_label_threshold=4)
            ax1.set_title(f"{title} with GC Content Analysis", fontsize=12)
            
            # Plot inferior: contenido GC
            sequence = str(record.seq)
            window_size = max(50, len(sequence) // 100)
            
            if len(sequence) > window_size:
                gc_content = []
                positions = []
                
                for i in range(0, len(sequence) - window_size, window_size // 2):
                    window = sequence[i:i + window_size]
                    gc_percent = (window.count('G') + window.count('C')) / len(window) * 100
                    gc_content.append(gc_percent)
                    positions.append(i + window_size // 2)
                
                ax2.fill_between(positions, gc_content, alpha=0.6, color='skyblue')
                ax2.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% GC')
                ax2.set_ylim(0, 100)
                ax2.set_ylabel('GC Content (%)')
                ax2.set_xlabel('Position (bp)')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
                
                # Estadísticas
                avg_gc = np.mean(gc_content)
                ax2.text(0.02, 0.95, f'Average GC: {avg_gc:.1f}%', 
                        transform=ax2.transAxes, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_gc_content_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot con GC: {e}")
            return self._create_error_plot(f"Error en análisis GC: {str(e)}")
    
    def _plot_fasta_analysis(self, graphic_record, record, title: str) -> str:
        """Plot especializado para análisis FASTA."""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Plot principal: características detectadas
            graphic_record.plot(ax=axes[0, 0], figure_width=8)
            axes[0, 0].set_title(f"{title}\nDetected ORFs and GC Regions", fontsize=10)
            
            # Estadísticas de secuencia
            sequence = str(record.seq)
            seq_stats = self._calculate_sequence_stats(sequence)
            
            # Plot de composición de nucleótidos
            nucleotides = ['A', 'T', 'G', 'C']
            counts = [sequence.count(n) for n in nucleotides]
            colors = ['red', 'blue', 'green', 'orange']
            
            axes[0, 1].pie(counts, labels=nucleotides, colors=colors, autopct='%1.1f%%')
            axes[0, 1].set_title('Nucleotide Composition')
            
            # Plot de contenido GC a lo largo de la secuencia
            window_size = max(50, len(sequence) // 50)
            if len(sequence) > window_size:
                gc_profile = []
                positions = []
                
                for i in range(0, len(sequence) - window_size, window_size):
                    window = sequence[i:i + window_size]
                    gc_percent = (window.count('G') + window.count('C')) / len(window) * 100
                    gc_profile.append(gc_percent)
                    positions.append(i + window_size // 2)
                
                axes[1, 0].plot(positions, gc_profile, 'b-', alpha=0.7)
                axes[1, 0].axhline(y=50, color='red', linestyle='--', alpha=0.5)
                axes[1, 0].fill_between(positions, gc_profile, alpha=0.3)
                axes[1, 0].set_xlabel('Position (bp)')
                axes[1, 0].set_ylabel('GC Content (%)')
                axes[1, 0].set_title(f'GC Content Profile (window: {window_size} bp)')
                axes[1, 0].grid(True, alpha=0.3)
            
            # Tabla de estadísticas
            axes[1, 1].axis('off')
            stats_text = f"""
SEQUENCE STATISTICS

Length: {seq_stats['length']:,} bp
GC Content: {seq_stats['gc_content']:.1f}%
AT Content: {seq_stats['at_content']:.1f}%

Nucleotide Counts:
  A: {seq_stats['A_count']:,} ({seq_stats['A_percent']:.1f}%)
  T: {seq_stats['T_count']:,} ({seq_stats['T_percent']:.1f}%)
  G: {seq_stats['G_count']:,} ({seq_stats['G_percent']:.1f}%)
  C: {seq_stats['C_count']:,} ({seq_stats['C_percent']:.1f}%)
  N: {seq_stats['N_count']:,} ({seq_stats['N_percent']:.1f}%)

ORFs Detected: {len([f for f in graphic_record.features if hasattr(f, 'label') and 'ORF' in str(f.label)])}
GC Regions: {len([f for f in graphic_record.features if hasattr(f, 'label') and 'GC' in str(f.label)])}
            """
            
            axes[1, 1].text(0.05, 0.95, stats_text, transform=axes[1, 1].transAxes,
                           verticalalignment='top', fontfamily='monospace', fontsize=9,
                           bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_fasta_analysis_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en análisis FASTA: {e}")
            return self._create_error_plot(f"Error en análisis FASTA: {str(e)}")
    
    def _plot_fasta_simple(self, graphic_record, record, title: str) -> str:
        """Plot lineal simple para FASTA."""
        try:
            fig, ax = plt.subplots(figsize=self.default_figsize)
            
            # Plot básico
            graphic_record.plot(ax=ax, figure_width=10)
            ax.set_title(f"{title}\n{record.description[:100]}", fontsize=14, pad=20)
            
            # Información adicional
            sequence = str(record.seq)
            gc_content = (sequence.count('G') + sequence.count('C')) / len(sequence) * 100
            info_text = f"Length: {len(sequence):,} bp | GC: {gc_content:.1f}% | Features: {len(graphic_record.features)}"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=10, 
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_fasta_linear_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot FASTA simple: {e}")
            return self._create_error_plot(f"Error en visualización FASTA simple: {str(e)}")

    def _plot_fasta_circular_simple(self, graphic_record, record, title: str) -> str:
        """Plot circular simple para FASTA."""
        try:
            from dna_features_viewer import CircularGraphicRecord
            
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # Convertir a circular
            circular_record = CircularGraphicRecord(
                sequence_length=graphic_record.sequence_length,
                features=graphic_record.features
            )
            
            circular_record.plot(ax=ax)
            
            # Información adicional
            sequence = str(record.seq)
            gc_content = (sequence.count('G') + sequence.count('C')) / len(sequence) * 100
            
            info_text = f"""
{title}
Length: {len(sequence):,} bp
GC Content: {gc_content:.1f}%
Features: {len(graphic_record.features)}
            """
            
            ax.text(0.02, 0.98, info_text.strip(), transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.9))
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_fasta_circular_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot circular FASTA simple: {e}")
            return self._create_error_plot(f"Error en visualización circular FASTA simple: {str(e)}")

    def _plot_fasta_circular(self, graphic_record, record, title: str) -> str:
        """Plot circular para FASTA."""
        try:
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # Convertir a circular
            circular_record = CircularGraphicRecord(
                sequence_length=graphic_record.sequence_length,
                features=graphic_record.features
            )
            
            circular_record.plot(ax=ax)
            
            # Información adicional
            sequence = str(record.seq)
            gc_content = (sequence.count('G') + sequence.count('C')) / len(sequence) * 100
            
            info_text = f"""
{title}
Length: {len(sequence):,} bp
GC Content: {gc_content:.1f}%
Features: {len(graphic_record.features)}
            """
            
            ax.text(0.02, 0.98, info_text.strip(), transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))
            
            plt.tight_layout()
            output_path = self.output_dir / f"dna_fasta_circular_{title.lower().replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error en plot circular FASTA: {e}")
            return self._create_error_plot(f"Error en visualización circular FASTA: {str(e)}")
    
    def _calculate_sequence_stats(self, sequence: str) -> Dict:
        """Calcular estadísticas de la secuencia."""
        length = len(sequence)
        if length == 0:
            return {}
        
        # Contar nucleótidos
        A_count = sequence.count('A')
        T_count = sequence.count('T')
        G_count = sequence.count('G')
        C_count = sequence.count('C')
        N_count = sequence.count('N')
        
        return {
            'length': length,
            'A_count': A_count,
            'T_count': T_count,
            'G_count': G_count,
            'C_count': C_count,
            'N_count': N_count,
            'A_percent': (A_count / length) * 100,
            'T_percent': (T_count / length) * 100,
            'G_percent': (G_count / length) * 100,
            'C_percent': (C_count / length) * 100,
            'N_percent': (N_count / length) * 100,
            'gc_content': ((G_count + C_count) / length) * 100,
            'at_content': ((A_count + T_count) / length) * 100
        }
    
    def _create_error_plot(self, error_message: str) -> str:
        """Crear plot de error."""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"❌ Error en DNA Features Viewer\n\n{error_message}", 
                ha='center', va='center', fontsize=12, 
                bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        output_path = self.output_dir / "dna_error.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas descriptivas de los datos DNA Features."""
        if data.empty:
            return {}
        
        stats = {}
        
        for _, row in data.iterrows():
            file_type = row['file_type']
            record = row['record']
            
            # Estadísticas básicas de secuencia
            sequence_length = len(record.seq) if hasattr(record, 'seq') else row.get('sequence_length', 0)
            features_count = row.get('features_count', 0)
            
            # Análisis de secuencia si está disponible
            if hasattr(record, 'seq') and record.seq:
                seq_stats = self._calculate_sequence_stats(str(record.seq))
                gc_content = seq_stats['gc_content']
                at_content = seq_stats['at_content']
                n_content = seq_stats.get('n_content', 0)  # Usar get() para evitar KeyError
            else:
                gc_content = 0
                at_content = 0
                n_content = 0
            
            # Contar ORFs detectados para archivos FASTA
            orfs_detected = 0
            if file_type == 'fasta' and 'artificial_features' in row:
                artificial_features = row['artificial_features']
                orfs_detected = len([f for f in artificial_features if f['type'] == 'ORF'])
            
            stats.update({
                'file_type': file_type,
                'sequence_length': sequence_length,
                'features_count': features_count,
                'gc_content': round(gc_content, 2),
                'at_content': round(at_content, 2),
                'n_content': round(n_content, 2),
                'orfs_detected': orfs_detected,
                'description': record.description if hasattr(record, 'description') else 'No description'
            })
            
            # Estadísticas específicas por tipo de archivo
            if file_type == 'genbank' and hasattr(record, 'annotations'):
                stats['organism'] = record.annotations.get('organism', 'Unknown')
                stats['topology'] = record.annotations.get('topology', 'Unknown')
                stats['molecule_type'] = record.annotations.get('molecule_type', 'Unknown')
            
            break  # Solo procesar el primer registro
        
        return stats

    def get_analysis_summary(self, data: pd.DataFrame) -> str:
        """Generar resumen del análisis."""
        if data.empty:
            return "No hay datos para analizar."
        
        summary_parts = []
        
        for _, row in data.iterrows():
            file_type = row['file_type']
            file_path = row['file_path']
            
            if file_type == 'genbank':
                summary_parts.append(f"""
📄 **Archivo GenBank**: {Path(file_path).name}
- **Organismo**: {row.get('organism', 'Unknown')}
- **Descripción**: {row['description'][:100]}...
- **Longitud**: {row['sequence_length']:,} bp
- **Características**: {row['features_count']}
- **Visualizaciones**: Linear, Circular, Sequence Detail, GC Analysis
                """)
            
            elif file_type == 'gff':
                summary_parts.append(f"""
📄 **Archivo GFF**: {Path(file_path).name}
- **Descripción**: {row['description'][:100]}...
- **Longitud**: {row['sequence_length']:,} bp
- **Características**: {row['features_count']}
- **Visualizaciones**: Linear, Circular
                """)
            
            elif file_type == 'fasta':
                summary_parts.append(f"""
📄 **Archivo FASTA**: {Path(file_path).name}
- **Descripción**: {row['description'][:100]}...
- **Longitud**: {row['sequence_length']:,} bp
- **ORFs Detectados**: {len([f for f in row['artificial_features'] if f['type'] == 'ORF'])}
- **Regiones GC**: {len([f for f in row['artificial_features'] if f['type'] == 'GC_region'])}
- **Visualizaciones**: ORF Analysis, Circular View, Statistics
                """)
        
        return "\n".join(summary_parts)


# Traductor personalizado avanzado para demostración
class AdvancedCustomTranslator(BiopythonTranslator):
    """Traductor avanzado con múltiples temas y configuraciones."""
    
    def __init__(self, theme='default'):
        super().__init__()
        self.theme = theme
        self.setup_theme()
    
    def setup_theme(self):
        """Configurar diferentes temas."""
        themes = {
            'default': {
                'CDS': '#3498db',
                'tRNA': '#2ecc71', 
                'rRNA': '#e74c3c',
                'gene': '#f39c12',
                'promoter': '#9b59b6'
            },
            'colorblind_friendly': {
                'CDS': '#0173b2',
                'tRNA': '#029e73',
                'rRNA': '#d55e00', 
                'gene': '#cc78bc',
                'promoter': '#ca9161'
            },
            'monochrome': {
                'CDS': '#2c3e50',
                'tRNA': '#34495e',
                'rRNA': '#7f8c8d',
                'gene': '#95a5a6',
                'promoter': '#bdc3c7'
            }
        }
        
        self.colors = themes.get(self.theme, themes['default'])
    
    def compute_feature_color(self, feature):
        return self.colors.get(feature.type, '#95a5a6')
    
    def compute_feature_label(self, feature):
        if feature.type == 'CDS':
            gene_name = feature.qualifiers.get('gene', [''])[0]
            product = feature.qualifiers.get('product', [''])[0]
            label = gene_name if gene_name else product
            return label[:20] + '...' if len(label) > 20 else label
        
        return BiopythonTranslator.compute_feature_label(self, feature) 