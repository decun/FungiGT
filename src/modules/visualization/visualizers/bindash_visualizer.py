#!/usr/bin/env python3
"""
Visualizador Especializado para Resultados de BinDash
=====================================================

Visualizador especializado para análisis genómico comparativo usando BinDash:
- Matrices de distancias genómicas
- Dendrogramas filogenéticos  
- Heatmaps de ANI (Average Nucleotide Identity)
- Análisis de clustering genómico
- Correlaciones entre métricas
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from sklearn.manifold import MDS
from pathlib import Path
from typing import Dict, List, Any

from .base_visualizer import BaseVisualizer

class BinDashVisualizer(BaseVisualizer):
    """Visualizador especializado para resultados de BinDash."""
    
    def __init__(self, output_dir: Path, config: Dict = None):
        super().__init__(output_dir, config)
        self.name = "BinDash Genomic Comparative Analysis"
        
    def get_supported_extensions(self) -> List[str]:
        """Extensiones soportadas para archivos BinDash."""
        return ['.txt', '.tsv', '.csv', '.out', '.distances']
    
    def validate_file(self, file_path: Path) -> bool:
        """Validar archivo BinDash con validación más robusta."""
        try:
            # Verificar extensión
            if file_path.suffix.lower() not in self.get_supported_extensions():
                print(f"❌ Extensión {file_path.suffix} no soportada. Extensiones válidas: {self.get_supported_extensions()}")
                return False
            
            # Verificar contenido básico
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            # Debe tener al menos 1 línea de datos
            data_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            if len(data_lines) < 1:
                print(f"❌ Archivo vacío o sin datos válidos")
                return False
                
            # Verificar formato básico de la primera línea de datos
            first_line = data_lines[0]
            print(f"🔍 Validando primera línea: {first_line[:100]}...")
            
            # Detectar separador y verificar estructura
            separators = ['\t', ',', ' ']
            for sep in separators:
                if sep in first_line:
                    cols = first_line.split(sep)
                    cols = [c.strip() for c in cols if c.strip()]
                    if len(cols) >= 3:
                        sep_name = 'TAB' if sep == '\t' else sep
                        print(f"✅ Archivo válido - Detectadas {len(cols)} columnas con separador '{sep_name}'")
                        return True
            
            # Si no hay separadores claros, verificar que al menos tenga algún contenido
            words = first_line.split()
            if len(words) >= 3:
                print(f"✅ Archivo válido - Detectadas {len(words)} columnas separadas por espacios")
                return True
            
            print(f"❌ Formato no válido - Se esperaban al menos 3 columnas")
            return False
            
        except Exception as e:
            print(f"❌ Error validando archivo: {e}")
            return False
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """Parsear archivo BinDash."""
        try:
            # Leer archivo y detectar formato
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            
            # Detectar si es una matriz de distancias directa
            if len(lines) > 1:
                first_data_line = lines[1] if lines[0].startswith('#') else lines[0]
                cols = first_data_line.split('\t')
                
                # Si la primera columna parece ser un nombre y el resto números, es matriz directa
                if len(cols) > 2:
                    try:
                        [float(x) for x in cols[1:]]
                        return self._parse_distance_matrix(file_path)
                    except ValueError:
                        pass
            
            # Formato estándar de pares de comparaciones
            return self._parse_comparison_pairs(file_path)
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo BinDash: {str(e)}")
    
    def _parse_distance_matrix(self, file_path: Path) -> pd.DataFrame:
        """Parsear matriz de distancias directa."""
        try:
            matrix_df = pd.read_csv(file_path, sep='\t', index_col=0, comment='#')
            
            # Convertir matriz a formato de pares
            pairs = []
            genomes = matrix_df.index.tolist()
            
            for i, query in enumerate(genomes):
                for j, target in enumerate(genomes):
                    if i < j:  # Solo triángulo superior
                        distance = matrix_df.loc[query, target]
                        if pd.notna(distance) and distance >= 0:
                            pairs.append({
                                'Query': Path(str(query)).stem,
                                'Target': Path(str(target)).stem,
                                'Mutation_distance': float(distance),
                                'P_value': 0.0,
                                'Jaccard_index': max(0, 1 - float(distance)),
                                'ANI': max(0, 1 - float(distance))
                            })
            
            return pd.DataFrame(pairs)
            
        except Exception as e:
            raise ValueError(f"Error parseando matriz de distancias: {str(e)}")
    
    def _parse_comparison_pairs(self, file_path: Path) -> pd.DataFrame:
        """Parsear formato estándar de pares de comparaciones."""
        try:
            # Leer archivo línea por línea para manejar mejor formatos complejos
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Filtrar comentarios y líneas vacías
            data_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            
            if not data_lines:
                raise ValueError("No se encontraron datos válidos en el archivo")
            
            # Detectar separador (tab es más común en BinDash)
            separator = '\t'
            first_line = data_lines[0]
            if '\t' in first_line:
                separator = '\t'
            elif ',' in first_line:
                separator = ','
            elif ' ' in first_line and len(first_line.split(' ')) >= 3:
                separator = ' '
            
            sep_name = 'TAB' if separator == '\t' else separator
            print(f"🔍 Detectado separador: {sep_name}")
            print(f"📄 Procesando {len(data_lines)} líneas de datos...")
            
            # Parsear manualmente para manejar formatos complejos
            parsed_data = []
            errors_count = 0
            
            for i, line in enumerate(data_lines):
                try:
                    # Usar el separador detectado
                    if separator == '\t':
                        parts = line.split('\t')
                    else:
                        parts = line.split(separator)
                    
                    # Filtrar partes vacías
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    if len(parts) < 3:
                        continue
                    
                    # Extraer nombres de genomas (primeras dos columnas)
                    query_raw = str(parts[0])
                    target_raw = str(parts[1])
                    
                    # Extraer nombre de archivo del genoma (parte final de la ruta)
                    query = Path(query_raw).stem
                    target = Path(target_raw).stem
                    
                    # Remover extensiones comunes de genomas
                    query = query.replace('_genomic', '').replace('.fna', '').replace('.fa', '').replace('.fasta', '')
                    target = target.replace('_genomic', '').replace('.fna', '').replace('.fa', '').replace('.fasta', '')
                    
                    # Parsear distancia (puede estar en notación científica)
                    distance_raw = str(parts[2])
                    try:
                        distance = float(distance_raw)
                        # Las distancias en BinDash suelen estar ya normalizadas
                        distance = max(0.0, min(1.0, distance))
                    except ValueError:
                        print(f"⚠️ No se pudo parsear distancia '{distance_raw}' en línea {i+1}, usando 0.5")
                        distance = 0.5
                    
                    # Parsear P-value (puede estar en notación científica)
                    p_value = 0.0
                    if len(parts) >= 4:
                        try:
                            p_value_raw = str(parts[3])
                            p_value = max(0.0, min(1.0, float(p_value_raw)))
                        except (ValueError, IndexError):
                            p_value = 0.0
                    
                    # Parsear Jaccard index (puede ser fracción como "8533/16384")
                    jaccard_index = max(0.0, 1.0 - distance)  # Valor por defecto
                    if len(parts) >= 5:
                        try:
                            jaccard_raw = str(parts[4])
                            if '/' in jaccard_raw:
                                # Es una fracción
                                numerator, denominator = jaccard_raw.split('/', 1)
                                jaccard_index = float(numerator) / float(denominator)
                            else:
                                # Es un número decimal
                                jaccard_index = float(jaccard_raw)
                            jaccard_index = max(0.0, min(1.0, jaccard_index))
                        except (ValueError, ZeroDivisionError, IndexError):
                            jaccard_index = max(0.0, 1.0 - distance)
                    
                    # Calcular ANI (Average Nucleotide Identity)
                    # ANI = 1 - distancia genómica
                    ani = max(0.0, min(1.0, 1.0 - distance))
                    
                    # Agregar datos parseados
                    parsed_data.append({
                        'Query': query,
                        'Target': target,
                        'Mutation_distance': distance,
                        'P_value': p_value,
                        'Jaccard_index': jaccard_index,
                        'ANI': ani
                    })
                    
                except Exception as e:
                    errors_count += 1
                    if errors_count <= 5:  # Solo mostrar los primeros 5 errores
                        print(f"⚠️ Error parseando línea {i+1}: {line[:100]}... Error: {e}")
                    continue
            
            if not parsed_data:
                raise ValueError("No se pudieron parsear datos válidos del archivo")
            
            df = pd.DataFrame(parsed_data)
            
            # Filtrar duplicados y datos inválidos
            initial_count = len(df)
            df = df.drop_duplicates(subset=['Query', 'Target'])
            df = df[df['Query'] != df['Target']]  # Remover auto-comparaciones
            
            print(f"✅ Parseados {len(df)} pares de comparaciones válidos (de {initial_count} iniciales)")
            if errors_count > 0:
                print(f"⚠️ Se encontraron {errors_count} líneas con errores que fueron omitidas")
            
            # Mostrar estadísticas básicas
            print(f"📊 Estadísticas básicas:")
            print(f"   - Genomas únicos: {len(set(df['Query'].tolist() + df['Target'].tolist()))}")
            print(f"   - Distancia promedio: {df['Mutation_distance'].mean():.4f}")
            print(f"   - ANI promedio: {df['ANI'].mean():.4f}")
            print(f"   - Jaccard promedio: {df['Jaccard_index'].mean():.4f}")
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error parseando formato de pares: {str(e)}")
    
    def generate_visualizations(self, data: pd.DataFrame) -> List[str]:
        """Generar todas las visualizaciones BinDash."""
        graphs = []
        
        try:
            # Heatmap de distancias
            graphs.append(self._plot_distance_heatmap(data))
        except Exception as e:
            print(f"Error creando heatmap de distancias: {e}")
        
        try:
            # Heatmap de ANI
            graphs.append(self._plot_ani_heatmap(data))
        except Exception as e:
            print(f"Error creando heatmap de ANI: {e}")
        
        try:
            # Dendrograma
            dendro_files = self._plot_dendrogram(data)
            if isinstance(dendro_files, list):
                graphs.extend(dendro_files)
            else:
                graphs.append(dendro_files)
        except Exception as e:
            print(f"Error creando dendrograma: {e}")
        
        try:
            # Distribuciones
            graphs.append(self._plot_distance_distribution(data))
        except Exception as e:
            print(f"Error creando distribuciones: {e}")
        
        try:
            # Análisis de dispersión
            graphs.append(self._plot_scatter_analysis(data))
        except Exception as e:
            print(f"Error creando análisis de dispersión: {e}")
        
        try:
            # Análisis MDS
            graphs.append(self._plot_mds_analysis(data))
        except Exception as e:
            print(f"Error creando análisis MDS: {e}")
        
        return [g for g in graphs if g]
    
    def generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generar estadísticas de análisis BinDash."""
        return {
            'total_comparisons': len(data),
            'unique_genomes': len(set(data['Query'].tolist() + data['Target'].tolist())),
            'mean_ani': float(data['ANI'].mean()),
            'std_ani': float(data['ANI'].std()),
            'min_ani': float(data['ANI'].min()),
            'max_ani': float(data['ANI'].max()),
            'mean_mutation_distance': float(data['Mutation_distance'].mean()),
            'std_mutation_distance': float(data['Mutation_distance'].std()),
            'mean_jaccard': float(data['Jaccard_index'].mean()),
            'std_jaccard': float(data['Jaccard_index'].std()),
            'median_ani': float(data['ANI'].median()),
            'q25_ani': float(data['ANI'].quantile(0.25)),
            'q75_ani': float(data['ANI'].quantile(0.75))
        }
    
    def _create_distance_matrix(self, data: pd.DataFrame) -> pd.DataFrame:
        """Crear matriz de distancias simétrica."""
        genomes = sorted(set(data['Query'].tolist() + data['Target'].tolist()))
        matrix = pd.DataFrame(index=genomes, columns=genomes, dtype=float)
        
        # Llenar matriz
        for _, row in data.iterrows():
            query, target = row['Query'], row['Target']
            distance = row['Mutation_distance']
            
            if query in genomes and target in genomes:
                matrix.loc[query, target] = distance
                matrix.loc[target, query] = distance
        
        # Diagonal = 0
        for genome in genomes:
            matrix.loc[genome, genome] = 0.0
        
        # Llenar valores faltantes
        max_distance = data['Mutation_distance'].max()
        fill_value = min(1.0, max_distance + 0.1)
        matrix = matrix.fillna(fill_value)
        
        return matrix
    
    def _plot_distance_heatmap(self, data: pd.DataFrame) -> str:
        """Crear heatmap de distancias genómicas."""
        distance_matrix = self._create_distance_matrix(data)
        
        plt.figure(figsize=self.default_figsize)
        mask = np.triu(np.ones_like(distance_matrix, dtype=bool))
        
        sns.heatmap(distance_matrix, 
                   mask=mask,
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlBu_r',
                   square=True,
                   linewidths=0.5,
                   cbar_kws={"shrink": .8})
        
        plt.title('🔥 Matriz de Distancias Genómicas (BinDash)', fontsize=16, fontweight='bold')
        plt.xlabel('Genomas')
        plt.ylabel('Genomas')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        return self.save_figure('distance_heatmap')
    
    def _plot_ani_heatmap(self, data: pd.DataFrame) -> str:
        """Crear heatmap de ANI."""
        distance_matrix = self._create_distance_matrix(data)
        ani_matrix = 1 - distance_matrix
        
        plt.figure(figsize=self.default_figsize)
        mask = np.triu(np.ones_like(ani_matrix, dtype=bool))
        
        sns.heatmap(ani_matrix, 
                   mask=mask,
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlGn',
                   square=True,
                   linewidths=0.5,
                   vmin=0.7,
                   vmax=1.0,
                   cbar_kws={"shrink": .8})
        
        plt.title('🧬 Matriz de ANI (Average Nucleotide Identity)', fontsize=16, fontweight='bold')
        plt.xlabel('Genomas')
        plt.ylabel('Genomas')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        return self.save_figure('ani_heatmap')
    
    def _plot_dendrogram(self, data: pd.DataFrame) -> List[str]:
        """Crear dendrograma filogenético."""
        distance_matrix = self._create_distance_matrix(data)
        
        if distance_matrix.empty or distance_matrix.shape[0] < 2:
            return [self.create_basic_plot("Dendrograma", "Datos insuficientes para dendrograma", "lightcoral")]
        
        try:
            matrix_values = distance_matrix.values
            matrix_values = (matrix_values + matrix_values.T) / 2
            np.fill_diagonal(matrix_values, 0)
            
            condensed_distances = squareform(matrix_values)
            condensed_distances = np.nan_to_num(condensed_distances, nan=1.0, neginf=0.0, posinf=1.0)
            
            linkage_matrix = linkage(condensed_distances, method='average')
            
            # Dendrograma principal
            plt.figure(figsize=(15, 8))
            dendrogram(linkage_matrix, 
                      labels=distance_matrix.index,
                      orientation='top',
                      distance_sort='descending',
                      show_leaf_counts=True,
                      leaf_rotation=45)
            
            plt.title('🌳 Dendrograma Filogenético (BinDash)', fontsize=16, fontweight='bold')
            plt.xlabel('Genomas')
            plt.ylabel('Distancia Genómica')
            plt.tight_layout()
            
            simple_path = self.save_figure('dendrogram_simple')
            
            return [simple_path]
            
        except Exception as e:
            return [self.create_basic_plot("Error Dendrograma", f"Error: {str(e)}", "lightcoral")]
    
    def _plot_distance_distribution(self, data: pd.DataFrame) -> str:
        """Crear histogramas de distribuciones."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Distribución de distancias
        axes[0, 0].hist(data['Mutation_distance'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('Distribución de Distancias de Mutación')
        axes[0, 0].set_xlabel('Distancia de Mutación')
        axes[0, 0].set_ylabel('Frecuencia')
        
        # Distribución de ANI
        axes[0, 1].hist(data['ANI'], bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
        axes[0, 1].set_title('Distribución de ANI')
        axes[0, 1].set_xlabel('ANI (Average Nucleotide Identity)')
        axes[0, 1].set_ylabel('Frecuencia')
        
        # Distribución de P-values
        axes[1, 0].hist(data['P_value'], bins=30, alpha=0.7, color='salmon', edgecolor='black')
        axes[1, 0].set_title('Distribución de P-values')
        axes[1, 0].set_xlabel('P-value')
        axes[1, 0].set_ylabel('Frecuencia')
        
        # Distribución de Jaccard
        axes[1, 1].hist(data['Jaccard_index'], bins=30, alpha=0.7, color='gold', edgecolor='black')
        axes[1, 1].set_title('Distribución de Índice de Jaccard')
        axes[1, 1].set_xlabel('Índice de Jaccard')
        axes[1, 1].set_ylabel('Frecuencia')
        
        plt.suptitle('📊 Distribuciones de Métricas BinDash', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        return self.save_figure('distance_distributions')
    
    def _plot_scatter_analysis(self, data: pd.DataFrame) -> str:
        """Crear análisis de correlaciones."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # ANI vs P-value
        axes[0, 0].scatter(data['ANI'], data['P_value'], alpha=0.6, color='blue')
        axes[0, 0].set_xlabel('ANI')
        axes[0, 0].set_ylabel('P-value')
        axes[0, 0].set_title('ANI vs P-value')
        
        # ANI vs Jaccard
        axes[0, 1].scatter(data['ANI'], data['Jaccard_index'], alpha=0.6, color='green')
        axes[0, 1].set_xlabel('ANI')
        axes[0, 1].set_ylabel('Índice de Jaccard')
        axes[0, 1].set_title('ANI vs Índice de Jaccard')
        
        # Distancia vs P-value
        axes[1, 0].scatter(data['Mutation_distance'], data['P_value'], alpha=0.6, color='red')
        axes[1, 0].set_xlabel('Distancia de Mutación')
        axes[1, 0].set_ylabel('P-value')
        axes[1, 0].set_title('Distancia vs P-value')
        
        # Distancia vs Jaccard
        axes[1, 1].scatter(data['Mutation_distance'], data['Jaccard_index'], alpha=0.6, color='purple')
        axes[1, 1].set_xlabel('Distancia de Mutación')
        axes[1, 1].set_ylabel('Índice de Jaccard')
        axes[1, 1].set_title('Distancia vs Jaccard')
        
        plt.suptitle('📈 Análisis de Correlaciones BinDash', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        return self.save_figure('scatter_analysis')
    
    def _plot_mds_analysis(self, data: pd.DataFrame) -> str:
        """Crear análisis MDS."""
        distance_matrix = self._create_distance_matrix(data)
        
        try:
            mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42)
            mds_coords = mds.fit_transform(distance_matrix.values)
            
            plt.figure(figsize=self.default_figsize)
            plt.scatter(mds_coords[:, 0], mds_coords[:, 1], s=100, alpha=0.7)
            
            # Añadir etiquetas
            for i, genome in enumerate(distance_matrix.index):
                plt.annotate(genome, (mds_coords[i, 0], mds_coords[i, 1]), 
                           xytext=(5, 5), textcoords='offset points', fontsize=9)
            
            plt.title('🎯 Análisis MDS de Distancias Genómicas', fontsize=16, fontweight='bold')
            plt.xlabel('Dimensión 1')
            plt.ylabel('Dimensión 2')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            return self.save_figure('mds_analysis')
            
        except Exception as e:
            return self.create_basic_plot("Error MDS", f"Error en MDS: {str(e)}", "lightcoral") 