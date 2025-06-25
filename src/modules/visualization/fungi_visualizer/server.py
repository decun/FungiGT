#!/usr/bin/env python3
"""
Servidor de Visualización BinDash para FungiGT
==============================================

Servidor Flask especializado en la visualización de resultados de BinDash:
- Matrices de distancias genómicas
- Dendrogramas filogenéticos
- Heatmaps de ANI (Average Nucleotide Identity)
- Gráficos de distribución de distancias
- Análisis de clustering genómico
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend no interactivo
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from sklearn.manifold import MDS
from sklearn.decomposition import PCA

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Importaciones para análisis BioPython (opcional)
try:
    from Bio import SeqIO
    from Bio.SeqUtils import gc_fraction
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    print("⚠️  BioPython no disponible. Algunas funciones de análisis FNA estarán limitadas.")

app = Flask(__name__)

# Configuración CORS
CORS(app, origins=[
    'http://localhost:4005',
    'http://localhost:3000',
    'http://localhost:4000'
], supports_credentials=True)

# Configuración de directorios
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'output'
TEMP_DIR = BASE_DIR / 'temp'

# Crear directorios si no existen
for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuración de archivos permitidos
ALLOWED_EXTENSIONS = {'.txt', '.tsv', '.csv', '.out', '.distances', '.fna', '.fasta', '.fa', '.tree', '.nwk', '.analyze'}

def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def clean_old_files():
    """Limpiar archivos temporales antiguos (más de 1 hora)"""
    import time
    current_time = time.time()
    
    for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
        if directory.exists():
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 3600:  # 1 hora
                        try:
                            file_path.unlink()
                        except Exception as e:
                            print(f"Error eliminando {file_path}: {e}")

class BinDashVisualizer:
    """Clase principal para visualización de resultados BinDash"""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar estilo de matplotlib
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def parse_bindash_output(self, file_path):
        """
        Parsear archivo de salida de BinDash
        Formatos soportados:
        1. Query\tTarget\tMutation_distance\tP_value\tJaccard_index
        2. Query\tTarget\tDistance (formato simplificado)
        3. Matriz de distancias directa
        """
        try:
            # Leer archivo y detectar formato
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                f.seek(0)
                content = f.read()
            
            # Detectar si es una matriz de distancias directa
            lines = content.strip().split('\n')
            if len(lines) > 1:
                first_data_line = lines[1] if lines[0].startswith('#') or '\t' in lines[0] else lines[0]
                cols = first_data_line.split('\t')
                
                # Si la primera columna parece ser un nombre y el resto números, es matriz directa
                if len(cols) > 2:
                    try:
                        # Intentar convertir todas las columnas excepto la primera a float
                        [float(x) for x in cols[1:]]
                        return self._parse_distance_matrix(file_path)
                    except ValueError:
                        pass
            
            # Formato estándar de pares de comparaciones
            try:
                df = pd.read_csv(file_path, sep='\t', comment='#')
                
                # Detectar columnas automáticamente
                if len(df.columns) >= 3:
                    # Renombrar columnas según el contenido
                    if len(df.columns) == 3:
                        df.columns = ['Query', 'Target', 'Distance']
                        df['Mutation_distance'] = df['Distance']
                        df['P_value'] = 0.0  # Valor por defecto
                        df['Jaccard_index'] = 1 - df['Distance']  # Aproximación
                    elif len(df.columns) >= 5:
                        df.columns = ['Query', 'Target', 'Mutation_distance', 'P_value', 'Jaccard_index']
                    else:
                        # Formato personalizado, usar las primeras 3 columnas
                        df = df.iloc[:, :3]
                        df.columns = ['Query', 'Target', 'Distance']
                        df['Mutation_distance'] = df['Distance']
                        df['P_value'] = 0.0
                        df['Jaccard_index'] = 1 - df['Distance']
                
                # Limpiar nombres de genomas (quitar rutas y extensiones)
                df['Query'] = df['Query'].apply(lambda x: Path(str(x)).stem if pd.notna(x) else x)
                df['Target'] = df['Target'].apply(lambda x: Path(str(x)).stem if pd.notna(x) else x)
                
                # Calcular ANI (Average Nucleotide Identity)
                df['ANI'] = 1 - df['Mutation_distance']
                
                # Filtrar valores válidos
                df = df.dropna()
                df = df[df['Mutation_distance'] >= 0]
                df = df[df['Mutation_distance'] <= 1]
                
                return df
                
            except Exception as e:
                raise ValueError(f"Error parseando formato de pares: {str(e)}")
                
        except Exception as e:
            raise ValueError(f"Error parseando archivo BinDash: {str(e)}")
    
    def _parse_distance_matrix(self, file_path):
        """Parsear matriz de distancias directa"""
        try:
            # Leer matriz de distancias
            matrix_df = pd.read_csv(file_path, sep='\t', index_col=0, comment='#')
            
            # Convertir matriz a formato de pares
            pairs = []
            genomes = matrix_df.index.tolist()
            
            for i, query in enumerate(genomes):
                for j, target in enumerate(genomes):
                    if i < j:  # Solo tomar triángulo superior para evitar duplicados
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
    
    def create_distance_matrix(self, df):
        """Crear matriz de distancias simétrica y completa"""
        # Obtener todos los genomas únicos
        genomes = sorted(set(df['Query'].tolist() + df['Target'].tolist()))
        n_genomes = len(genomes)
        
        print(f"📊 Creando matriz de distancias para {n_genomes} genomas")
        
        # Crear matriz de distancias inicializada con NaN
        matrix = pd.DataFrame(index=genomes, columns=genomes, dtype=float)
        
        # Llenar matriz con distancias conocidas
        for _, row in df.iterrows():
            query, target = row['Query'], row['Target']
            distance = row['Mutation_distance']
            
            if query in genomes and target in genomes:
                matrix.loc[query, target] = distance
                matrix.loc[target, query] = distance  # Simétrica
        
        # Diagonal = 0 (distancia de un genoma a sí mismo)
        for genome in genomes:
            matrix.loc[genome, genome] = 0.0
        
        # Manejar valores faltantes
        # Opción 1: Llenar con la distancia máxima observada + 0.1
        max_distance = df['Mutation_distance'].max()
        fill_value = min(1.0, max_distance + 0.1)  # No exceder 1.0
        
        # Opción 2: Usar distancia promedio para valores faltantes
        # fill_value = df['Mutation_distance'].mean()
        
        matrix = matrix.fillna(fill_value)
        
        print(f"✅ Matriz creada: {matrix.shape}, rango: {matrix.min().min():.3f} - {matrix.max().max():.3f}")
        
        return matrix
    
    def plot_distance_heatmap(self, df):
        """Crear heatmap de distancias genómicas"""
        distance_matrix = self.create_distance_matrix(df)
        
        plt.figure(figsize=(12, 10))
        
        # Crear heatmap
        mask = np.triu(np.ones_like(distance_matrix, dtype=bool))
        sns.heatmap(distance_matrix, 
                   mask=mask,
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlBu_r',
                   square=True,
                   linewidths=0.5,
                   cbar_kws={"shrink": .8})
        
        plt.title('Matriz de Distancias Genómicas (BinDash)', fontsize=16, fontweight='bold')
        plt.xlabel('Genomas', fontsize=12)
        plt.ylabel('Genomas', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        output_path = self.output_dir / 'distance_heatmap.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def plot_ani_heatmap(self, df):
        """Crear heatmap de ANI (Average Nucleotide Identity)"""
        distance_matrix = self.create_distance_matrix(df)
        ani_matrix = 1 - distance_matrix  # Convertir distancia a ANI
        
        plt.figure(figsize=(12, 10))
        
        # Crear heatmap de ANI
        mask = np.triu(np.ones_like(ani_matrix, dtype=bool))
        sns.heatmap(ani_matrix, 
                   mask=mask,
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlGn',
                   square=True,
                   linewidths=0.5,
                   vmin=0.7,  # Rango típico de ANI
                   vmax=1.0,
                   cbar_kws={"shrink": .8})
        
        plt.title('Matriz de ANI (Average Nucleotide Identity)', fontsize=16, fontweight='bold')
        plt.xlabel('Genomas', fontsize=12)
        plt.ylabel('Genomas', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        output_path = self.output_dir / 'ani_heatmap.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def plot_dendrogram(self, df):
        """Crear dendrograma filogenético mejorado"""
        distance_matrix = self.create_distance_matrix(df)
        
        # Verificar que la matriz sea válida
        if distance_matrix.empty or distance_matrix.shape[0] < 2:
            raise ValueError("Matriz de distancias insuficiente para crear dendrograma")
        
        # Convertir a matriz condensada para scipy
        try:
            # Asegurar que la matriz sea simétrica y válida
            matrix_values = distance_matrix.values
            
            # Verificar simetría
            if not np.allclose(matrix_values, matrix_values.T, rtol=1e-10):
                print("⚠️  Matriz no simétrica, corrigiendo...")
                matrix_values = (matrix_values + matrix_values.T) / 2
            
            # Asegurar diagonal cero
            np.fill_diagonal(matrix_values, 0)
            
            # Convertir a formato condensado
            condensed_distances = squareform(matrix_values)
            
            # Verificar que no hay distancias negativas o NaN
            if np.any(np.isnan(condensed_distances)) or np.any(condensed_distances < 0):
                print("⚠️  Distancias inválidas detectadas, limpiando...")
                condensed_distances = np.nan_to_num(condensed_distances, nan=1.0, neginf=0.0, posinf=1.0)
                condensed_distances = np.abs(condensed_distances)
            
            # Crear linkage con diferentes métodos
            methods = ['average', 'complete', 'single', 'ward']
            linkage_matrices = {}
            
            for method in methods:
                try:
                    if method == 'ward':
                        # Ward requiere distancias euclidianas
                        linkage_matrices[method] = linkage(condensed_distances, method=method, metric='euclidean')
                    else:
                        linkage_matrices[method] = linkage(condensed_distances, method=method)
                except Exception as e:
                    print(f"⚠️  Error con método {method}: {e}")
                    continue
            
            if not linkage_matrices:
                raise ValueError("No se pudo crear linkage con ningún método")
            
            # Usar el mejor método disponible (preferir average)
            best_method = 'average' if 'average' in linkage_matrices else list(linkage_matrices.keys())[0]
            linkage_matrix = linkage_matrices[best_method]
            
            # Crear figura con subplots para múltiples dendrogramas
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.suptitle('Dendrogramas Filogenéticos (BinDash)', fontsize=16, fontweight='bold')
            
            # Dendrograma principal (average linkage)
            ax1 = axes[0, 0]
            dendrogram(linkage_matrix, 
                      labels=distance_matrix.index,
                      orientation='top',
                      distance_sort='descending',
                      show_leaf_counts=True,
                      leaf_rotation=45,
                      ax=ax1)
            ax1.set_title(f'Dendrograma - Método: {best_method.title()}')
            ax1.set_xlabel('Genomas')
            ax1.set_ylabel('Distancia Genómica')
            
            # Dendrograma horizontal
            ax2 = axes[0, 1]
            dendrogram(linkage_matrix,
                      labels=distance_matrix.index,
                      orientation='left',
                      distance_sort='descending',
                      show_leaf_counts=True,
                      ax=ax2)
            ax2.set_title('Dendrograma Horizontal')
            ax2.set_xlabel('Distancia Genómica')
            ax2.set_ylabel('Genomas')
            
            # Dendrograma circular (si hay pocos genomas)
            ax3 = axes[1, 0]
            if len(distance_matrix.index) <= 20:
                # Para dendrograma circular, usar plot personalizado
                self._plot_circular_dendrogram(linkage_matrix, distance_matrix.index, ax3)
            else:
                # Dendrograma truncado para muchos genomas
                dendrogram(linkage_matrix,
                          labels=distance_matrix.index,
                          orientation='top',
                          distance_sort='descending',
                          show_leaf_counts=True,
                          leaf_rotation=90,
                          truncate_mode='lastp',
                          p=15,
                          ax=ax3)
                ax3.set_title('Dendrograma Truncado (Top 15)')
            
            # Heatmap de la matriz de distancias
            ax4 = axes[1, 1]
            im = ax4.imshow(distance_matrix.values, cmap='viridis', aspect='auto')
            ax4.set_xticks(range(len(distance_matrix.columns)))
            ax4.set_yticks(range(len(distance_matrix.index)))
            ax4.set_xticklabels(distance_matrix.columns, rotation=45, ha='right')
            ax4.set_yticklabels(distance_matrix.index)
            ax4.set_title('Matriz de Distancias')
            plt.colorbar(im, ax=ax4, shrink=0.8)
            
            plt.tight_layout()
            
            output_path = self.output_dir / 'dendrogram_complete.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            # Crear dendrograma simple adicional
            plt.figure(figsize=(15, 8))
            dendrogram(linkage_matrix, 
                      labels=distance_matrix.index,
                      orientation='top',
                      distance_sort='descending',
                      show_leaf_counts=True,
                      leaf_rotation=45)
            
            plt.title('Dendrograma Filogenético (BinDash)', fontsize=16, fontweight='bold')
            plt.xlabel('Genomas', fontsize=12)
            plt.ylabel('Distancia Genómica', fontsize=12)
            plt.tight_layout()
            
            simple_output_path = self.output_dir / 'dendrogram_simple.png'
            plt.savefig(simple_output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return [str(output_path), str(simple_output_path)]
            
        except Exception as e:
            print(f"❌ Error creando dendrograma: {e}")
            # Crear un gráfico de error informativo
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, f'Error creando dendrograma:\n{str(e)}\n\nVerifica el formato de datos',
                    ha='center', va='center', fontsize=12, 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral"))
            plt.xlim(0, 1)
            plt.ylim(0, 1)
            plt.axis('off')
            plt.title('Error en Dendrograma', fontsize=14, fontweight='bold')
            
            error_path = self.output_dir / 'dendrogram_error.png'
            plt.savefig(error_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return [str(error_path)]
    
    def _plot_circular_dendrogram(self, linkage_matrix, labels, ax):
        """Crear dendrograma circular para pocos genomas"""
        try:
            # Implementación simplificada de dendrograma circular
            ax.text(0.5, 0.5, 'Dendrograma Circular\n(En desarrollo)', 
                   ha='center', va='center', fontsize=12,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.set_title('Vista Circular')
        except Exception as e:
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
    
    def plot_distance_distribution(self, df):
        """Crear histograma de distribución de distancias"""
        plt.figure(figsize=(12, 8))
        
        # Subplot para múltiples métricas
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Distribución de distancias de mutación
        axes[0, 0].hist(df['Mutation_distance'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('Distribución de Distancias de Mutación')
        axes[0, 0].set_xlabel('Distancia de Mutación')
        axes[0, 0].set_ylabel('Frecuencia')
        
        # Distribución de ANI
        axes[0, 1].hist(df['ANI'], bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
        axes[0, 1].set_title('Distribución de ANI')
        axes[0, 1].set_xlabel('ANI (Average Nucleotide Identity)')
        axes[0, 1].set_ylabel('Frecuencia')
        
        # Distribución de P-values
        axes[1, 0].hist(df['P_value'], bins=30, alpha=0.7, color='salmon', edgecolor='black')
        axes[1, 0].set_title('Distribución de P-values')
        axes[1, 0].set_xlabel('P-value')
        axes[1, 0].set_ylabel('Frecuencia')
        axes[1, 0].set_yscale('log')
        
        # Distribución de Índice de Jaccard
        axes[1, 1].hist(df['Jaccard_index'], bins=30, alpha=0.7, color='gold', edgecolor='black')
        axes[1, 1].set_title('Distribución de Índice de Jaccard')
        axes[1, 1].set_xlabel('Índice de Jaccard')
        axes[1, 1].set_ylabel('Frecuencia')
        
        plt.suptitle('Distribuciones de Métricas BinDash', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        output_path = self.output_dir / 'distance_distributions.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def plot_scatter_analysis(self, df):
        """Crear gráficos de dispersión para análisis de correlaciones"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # ANI vs P-value
        axes[0, 0].scatter(df['ANI'], df['P_value'], alpha=0.6, color='blue')
        axes[0, 0].set_xlabel('ANI')
        axes[0, 0].set_ylabel('P-value')
        axes[0, 0].set_title('ANI vs P-value')
        axes[0, 0].set_yscale('log')
        
        # ANI vs Jaccard Index
        axes[0, 1].scatter(df['ANI'], df['Jaccard_index'], alpha=0.6, color='green')
        axes[0, 1].set_xlabel('ANI')
        axes[0, 1].set_ylabel('Índice de Jaccard')
        axes[0, 1].set_title('ANI vs Índice de Jaccard')
        
        # Mutation Distance vs P-value
        axes[1, 0].scatter(df['Mutation_distance'], df['P_value'], alpha=0.6, color='red')
        axes[1, 0].set_xlabel('Distancia de Mutación')
        axes[1, 0].set_ylabel('P-value')
        axes[1, 0].set_title('Distancia de Mutación vs P-value')
        axes[1, 0].set_yscale('log')
        
        # Mutation Distance vs Jaccard Index
        axes[1, 1].scatter(df['Mutation_distance'], df['Jaccard_index'], alpha=0.6, color='purple')
        axes[1, 1].set_xlabel('Distancia de Mutación')
        axes[1, 1].set_ylabel('Índice de Jaccard')
        axes[1, 1].set_title('Distancia de Mutación vs Índice de Jaccard')
        
        plt.suptitle('Análisis de Correlaciones BinDash', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        output_path = self.output_dir / 'scatter_analysis.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def plot_mds_analysis(self, df):
        """Crear análisis MDS (Multidimensional Scaling)"""
        distance_matrix = self.create_distance_matrix(df)
        
        # Aplicar MDS
        mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42)
        mds_coords = mds.fit_transform(distance_matrix.values)
        
        plt.figure(figsize=(12, 8))
        
        # Crear scatter plot MDS
        plt.scatter(mds_coords[:, 0], mds_coords[:, 1], s=100, alpha=0.7)
        
        # Añadir etiquetas
        for i, genome in enumerate(distance_matrix.index):
            plt.annotate(genome, (mds_coords[i, 0], mds_coords[i, 1]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=9)
        
        plt.title('Análisis MDS de Distancias Genómicas', fontsize=16, fontweight='bold')
        plt.xlabel('Dimensión 1')
        plt.ylabel('Dimensión 2')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_path = self.output_dir / 'mds_analysis.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def generate_summary_stats(self, df):
        """Generar estadísticas resumen"""
        stats = {
            'total_comparisons': len(df),
            'unique_genomes': len(set(df['Query'].tolist() + df['Target'].tolist())),
            'mean_ani': float(df['ANI'].mean()),
            'std_ani': float(df['ANI'].std()),
            'min_ani': float(df['ANI'].min()),
            'max_ani': float(df['ANI'].max()),
            'mean_mutation_distance': float(df['Mutation_distance'].mean()),
            'std_mutation_distance': float(df['Mutation_distance'].std()),
            'mean_jaccard': float(df['Jaccard_index'].mean()),
            'std_jaccard': float(df['Jaccard_index'].std())
        }
        
        # Guardar estadísticas
        stats_path = self.output_dir / 'summary_stats.json'
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return stats
    
    def process_bindash_file(self, file_path):
        """Procesar archivo BinDash y generar todas las visualizaciones"""
        try:
            print(f"🔍 Procesando archivo: {file_path}")
            
            # Parsear datos
            df = self.parse_bindash_output(file_path)
            print(f"📊 Datos parseados: {len(df)} comparaciones")
            
            if df.empty:
                raise ValueError("No se encontraron datos válidos en el archivo")
            
            # Generar visualizaciones
            graphs = []
            
            # Heatmap de distancias
            try:
                graphs.append(self.plot_distance_heatmap(df))
                print("✅ Heatmap de distancias creado")
            except Exception as e:
                print(f"⚠️  Error creando heatmap de distancias: {e}")
            
            # Heatmap de ANI
            try:
                graphs.append(self.plot_ani_heatmap(df))
                print("✅ Heatmap de ANI creado")
            except Exception as e:
                print(f"⚠️  Error creando heatmap de ANI: {e}")
            
            # Dendrograma (puede devolver múltiples archivos)
            try:
                dendro_files = self.plot_dendrogram(df)
                if isinstance(dendro_files, list):
                    graphs.extend(dendro_files)
                else:
                    graphs.append(dendro_files)
                print("✅ Dendrograma(s) creado(s)")
            except Exception as e:
                print(f"⚠️  Error creando dendrograma: {e}")
            
            # Distribuciones
            try:
                graphs.append(self.plot_distance_distribution(df))
                print("✅ Distribuciones creadas")
            except Exception as e:
                print(f"⚠️  Error creando distribuciones: {e}")
            
            # Análisis de dispersión
            try:
                graphs.append(self.plot_scatter_analysis(df))
                print("✅ Análisis de dispersión creado")
            except Exception as e:
                print(f"⚠️  Error creando análisis de dispersión: {e}")
            
            # Análisis MDS
            try:
                graphs.append(self.plot_mds_analysis(df))
                print("✅ Análisis MDS creado")
            except Exception as e:
                print(f"⚠️  Error creando análisis MDS: {e}")
            
            # Estadísticas resumen
            stats = self.generate_summary_stats(df)
            print("✅ Estadísticas generadas")
            
            return {
                'graphs': [g for g in graphs if g],  # Filtrar None
                'stats': stats,
                'data_summary': {
                    'total_comparisons': len(df),
                    'unique_genomes': len(set(df['Query'].tolist() + df['Target'].tolist()))
                }
            }
            
        except Exception as e:
            print(f"❌ Error procesando archivo BinDash: {e}")
            raise Exception(f"Error procesando archivo BinDash: {str(e)}")


class CheckMVisualizer:
    """Clase para visualización de resultados CheckM y análisis FNA"""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar estilo de matplotlib
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def detect_file_type(self, file_path):
        """Detectar automáticamente el tipo de archivo CheckM basado en nombre y contenido"""
        file_path = Path(file_path)
        filename = file_path.name.lower()
        
        # Detección por extensión y nombre de archivo
        if filename.endswith(('.fna', '.fasta', '.fa')):
            return 'fna_analysis'
        elif filename.endswith(('.tree', '.nwk')) or 'tree' in filename:
            return 'tree_qa'
        elif 'hmmer.analyze' in filename or filename.endswith('.analyze'):
            return 'hmmer_analyze'
        elif 'hmmer.tree' in filename:
            return 'hmmer_tree'
        elif 'lineage' in filename and ('ms' in filename or '.tsv' in filename):
            return 'lineage_ms'
        elif 'bins' in filename and ('stats' in filename or '.tsv' in filename):
            return 'bins_stats'
        elif 'qa_results' in filename or 'qa.tsv' in filename:
            return 'qa_results'
        elif 'checkm' in filename:
            return 'general_checkm'
        else:
            # Detección por contenido del archivo
            try:
                with open(file_path, 'r') as f:
                    first_lines = [f.readline().strip() for _ in range(3)]
                    
                # Verificar si es FASTA
                if any(line.startswith('>') for line in first_lines):
                    return 'fna_analysis'
                
                # Verificar si es archivo de árbol (formato Newick)
                if any('(' in line and ')' in line and ';' in line for line in first_lines):
                    return 'tree_qa'
                
                # Verificar columnas típicas de CheckM
                header = first_lines[0].lower() if first_lines else ''
                if 'completeness' in header and 'contamination' in header:
                    return 'qa_results'
                elif 'lineage' in header or 'marker' in header:
                    return 'lineage_ms'
                elif 'bin' in header and ('gc' in header or 'size' in header):
                    return 'bins_stats'
                
            except Exception:
                pass
            
            # Tipo por defecto
            return 'general_checkm'
    
    def parse_checkm_file(self, file_path, analysis_type=None):
        """Parsear diferentes tipos de archivos CheckM"""
        try:
            file_path = Path(file_path)
            
            # Si no se especifica el tipo, detectarlo automáticamente
            if not analysis_type:
                analysis_type = self.detect_file_type(file_path)
            
            if analysis_type == 'fna_analysis':
                return self._parse_fna_file(file_path)
            elif analysis_type == 'lineage_ms':
                return self._parse_lineage_ms(file_path)
            elif analysis_type == 'bins_stats':
                return self._parse_bins_stats(file_path)
            elif analysis_type == 'qa_results':
                return self._parse_qa_results(file_path)
            elif analysis_type == 'tree_qa':
                return self._parse_tree_qa(file_path)
            elif analysis_type == 'hmmer_analyze':
                return self._parse_hmmer_analyze(file_path)
            elif analysis_type == 'hmmer_tree':
                return self._parse_hmmer_tree(file_path)
            else:
                return self._parse_general_checkm(file_path)
                
        except Exception as e:
            raise ValueError(f"Error parseando archivo CheckM: {str(e)}")
    
    def _parse_fna_file(self, file_path):
        """Parsear archivo FNA/FASTA para análisis con BioPython"""
        if not BIOPYTHON_AVAILABLE:
            raise ValueError("BioPython no está disponible para análisis FNA")
        
        try:
            sequences = []
            for record in SeqIO.parse(file_path, "fasta"):
                sequences.append({
                    'id': record.id,
                    'description': record.description,
                    'length': len(record.seq),
                    'gc_content': gc_fraction(record.seq) * 100,  # Convertir a porcentaje
                    'sequence': str(record.seq)
                })
            
            return pd.DataFrame(sequences)
            
        except Exception as e:
            raise ValueError(f"Error parseando archivo FNA: {str(e)}")
    
    def _parse_lineage_ms(self, file_path):
        """Parsear archivo lineage_ms.tsv"""
        try:
            df = pd.read_csv(file_path, sep='\t', comment='#')
            # Normalizar nombres de columnas
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            raise ValueError(f"Error parseando lineage_ms: {str(e)}")
    
    def _parse_bins_stats(self, file_path):
        """Parsear archivo bins_stats.tsv"""
        try:
            df = pd.read_csv(file_path, sep='\t', comment='#')
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            raise ValueError(f"Error parseando bins_stats: {str(e)}")
    
    def _parse_qa_results(self, file_path):
        """Parsear archivo qa_results.tsv"""
        try:
            df = pd.read_csv(file_path, sep='\t', comment='#')
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            raise ValueError(f"Error parseando qa_results: {str(e)}")
    
    def _parse_tree_qa(self, file_path):
        """Parsear archivo de árbol filogenético"""
        try:
            with open(file_path, 'r') as f:
                tree_content = f.read().strip()
            return {'tree_content': tree_content}
        except Exception as e:
            raise ValueError(f"Error parseando árbol: {str(e)}")
    
    def _parse_hmmer_analyze(self, file_path):
        """Parsear archivo hmmer.analyze"""
        try:
            df = pd.read_csv(file_path, sep='\t', comment='#')
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            raise ValueError(f"Error parseando archivo HMMER analyze: {str(e)}")
    
    def _parse_hmmer_tree(self, file_path):
        """Parsear archivo hmmer.tree"""
        try:
            with open(file_path, 'r') as f:
                tree_content = f.read().strip()
            return {'tree_content': tree_content, 'type': 'hmmer_tree'}
        except Exception as e:
            raise ValueError(f"Error parseando archivo HMMER tree: {str(e)}")
    
    def _parse_general_checkm(self, file_path):
        """Parsear archivo CheckM general"""
        try:
            df = pd.read_csv(file_path, sep='\t', comment='#')
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            raise ValueError(f"Error parseando archivo CheckM: {str(e)}")
    
    def analyze_fna_sequences(self, df, options):
        """Analizar secuencias FNA con BioPython"""
        results = {}
        
        if options.get('basic_stats', True):
            results['basic_stats'] = {
                'total_sequences': len(df),
                'total_length': df['length'].sum(),
                'mean_length': df['length'].mean(),
                'median_length': df['length'].median(),
                'min_length': df['length'].min(),
                'max_length': df['length'].max()
            }
        
        if options.get('gc_content', True):
            results['gc_stats'] = {
                'mean_gc': df['gc_content'].mean(),
                'median_gc': df['gc_content'].median(),
                'std_gc': df['gc_content'].std(),
                'min_gc': df['gc_content'].min(),
                'max_gc': df['gc_content'].max()
            }
        
        if options.get('n50_stats', True):
            results['n50_stats'] = self._calculate_n50_n90(df['length'].tolist())
        
        return results
    
    def _calculate_n50_n90(self, lengths):
        """Calcular N50 y N90"""
        lengths_sorted = sorted(lengths, reverse=True)
        total_length = sum(lengths_sorted)
        
        cumsum = 0
        n50 = n90 = 0
        
        for length in lengths_sorted:
            cumsum += length
            if cumsum >= total_length * 0.5 and n50 == 0:
                n50 = length
            if cumsum >= total_length * 0.9 and n90 == 0:
                n90 = length
                break
        
        return {'n50': n50, 'n90': n90}
    
    def plot_checkm_quality(self, df):
        """Crear gráfico de calidad CheckM (completitud vs contaminación)"""
        try:
            # Detectar columnas de completitud y contaminación
            completeness_col = None
            contamination_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if 'complet' in col_lower:
                    completeness_col = col
                elif 'contamin' in col_lower:
                    contamination_col = col
            
            if not completeness_col or not contamination_col:
                raise ValueError("No se encontraron columnas de completitud y contaminación")
            
            plt.figure(figsize=(12, 8))
            
            # Scatter plot
            scatter = plt.scatter(df[contamination_col], df[completeness_col], 
                                alpha=0.7, s=60, c=df[completeness_col], 
                                cmap='RdYlGn', edgecolors='black', linewidth=0.5)
            
            # Líneas de referencia para calidad
            plt.axhline(y=90, color='green', linestyle='--', alpha=0.7, label='Alta calidad (>90%)')
            plt.axhline(y=70, color='orange', linestyle='--', alpha=0.7, label='Calidad media (>70%)')
            plt.axvline(x=5, color='red', linestyle='--', alpha=0.7, label='Contaminación alta (>5%)')
            plt.axvline(x=10, color='darkred', linestyle='--', alpha=0.7, label='Contaminación muy alta (>10%)')
            
            plt.colorbar(scatter, label='Completitud (%)')
            plt.xlabel('Contaminación (%)', fontsize=12)
            plt.ylabel('Completitud (%)', fontsize=12)
            plt.title('Evaluación de Calidad CheckM\nCompletitud vs Contaminación', fontsize=14, fontweight='bold')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            output_path = self.output_dir / 'completeness_contamination.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error creando gráfico de calidad: {e}")
            return None
    
    def plot_fna_statistics(self, df, options):
        """Crear gráficos de estadísticas FNA"""
        graphs = []
        
        try:
            # Distribución de longitudes
            if options.get('length_distribution', True):
                plt.figure(figsize=(12, 6))
                
                plt.subplot(1, 2, 1)
                plt.hist(df['length'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                plt.xlabel('Longitud de secuencia (bp)')
                plt.ylabel('Frecuencia')
                plt.title('Distribución de Longitudes')
                plt.grid(True, alpha=0.3)
                
                plt.subplot(1, 2, 2)
                plt.boxplot(df['length'])
                plt.ylabel('Longitud de secuencia (bp)')
                plt.title('Box plot de Longitudes')
                plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                output_path = self.output_dir / 'sequence_length_distribution.png'
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                graphs.append(str(output_path))
            
            # Distribución de contenido GC
            if options.get('gc_content', True):
                plt.figure(figsize=(12, 6))
                
                plt.subplot(1, 2, 1)
                plt.hist(df['gc_content'], bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
                plt.xlabel('Contenido GC (%)')
                plt.ylabel('Frecuencia')
                plt.title('Distribución de Contenido GC')
                plt.grid(True, alpha=0.3)
                
                plt.subplot(1, 2, 2)
                plt.scatter(df['length'], df['gc_content'], alpha=0.6, color='green')
                plt.xlabel('Longitud de secuencia (bp)')
                plt.ylabel('Contenido GC (%)')
                plt.title('Longitud vs Contenido GC')
                plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                output_path = self.output_dir / 'gc_content_distribution.png'
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                graphs.append(str(output_path))
            
        except Exception as e:
            print(f"Error creando gráficos FNA: {e}")
        
        return graphs
    
    def plot_hmmer_analysis(self, df):
        """Crear gráficos para análisis HMMER"""
        graphs = []
        
        try:
            # Gráfico de distribución de scores
            if 'score' in df.columns or 'e-value' in df.columns:
                plt.figure(figsize=(12, 6))
                
                if 'score' in df.columns:
                    plt.subplot(1, 2, 1)
                    plt.hist(df['score'], bins=30, alpha=0.7, color='orange', edgecolor='black')
                    plt.xlabel('HMMER Score')
                    plt.ylabel('Frecuencia')
                    plt.title('Distribución de Scores HMMER')
                    plt.grid(True, alpha=0.3)
                
                if 'e-value' in df.columns:
                    plt.subplot(1, 2, 2)
                    # Usar log scale para e-values
                    log_evalues = -np.log10(df['e-value'] + 1e-300)  # Evitar log(0)
                    plt.hist(log_evalues, bins=30, alpha=0.7, color='red', edgecolor='black')
                    plt.xlabel('-log10(E-value)')
                    plt.ylabel('Frecuencia')
                    plt.title('Distribución de E-values HMMER')
                    plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                output_path = self.output_dir / 'hmmer_analysis.png'
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                graphs.append(str(output_path))
            
            # Gráfico de top hits
            if len(df) > 0:
                plt.figure(figsize=(12, 8))
                
                # Top 20 hits por score
                top_hits = df.head(20)
                
                if 'target name' in df.columns:
                    target_col = 'target name'
                elif 'target' in df.columns:
                    target_col = 'target'
                else:
                    target_col = df.columns[0]
                
                if 'score' in df.columns:
                    score_col = 'score'
                elif 'bit score' in df.columns:
                    score_col = 'bit score'
                else:
                    score_col = None
                
                if score_col:
                    plt.barh(range(len(top_hits)), top_hits[score_col], color='skyblue', alpha=0.7)
                    plt.yticks(range(len(top_hits)), top_hits[target_col], fontsize=8)
                    plt.xlabel('Score')
                    plt.title('Top 20 Hits HMMER por Score')
                    plt.grid(True, alpha=0.3)
                    plt.gca().invert_yaxis()
                    
                    plt.tight_layout()
                    output_path = self.output_dir / 'hmmer_top_hits.png'
                    plt.savefig(output_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    graphs.append(str(output_path))
            
        except Exception as e:
            print(f"Error creando gráficos HMMER: {e}")
        
        return graphs
    
    def generate_checkm_stats(self, df, analysis_type, fna_analysis=None):
        """Generar estadísticas para CheckM"""
        stats = {'analysis_type': analysis_type}
        
        if analysis_type == 'fna_analysis' and fna_analysis:
            stats.update({
                'total_bins': 1,  # Un archivo FNA
                'high_quality': 0,
                'medium_quality': 0,
                'low_quality': 1,
                'fna_stats': fna_analysis.get('basic_stats', {}),
                'gc_stats': fna_analysis.get('gc_stats', {}),
                'n50_stats': fna_analysis.get('n50_stats', {})
            })
        else:
            # Análisis general para otros tipos de CheckM
            total_bins = len(df) if hasattr(df, '__len__') else 0
            
            # Intentar detectar calidad basada en columnas comunes
            high_quality = medium_quality = low_quality = 0
            
            if hasattr(df, 'columns'):
                completeness_col = None
                contamination_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if 'complet' in col_lower:
                        completeness_col = col
                    elif 'contamin' in col_lower:
                        contamination_col = col
                
                if completeness_col and contamination_col:
                    for _, row in df.iterrows():
                        comp = row[completeness_col]
                        cont = row[contamination_col]
                        
                        if comp >= 90 and cont <= 5:
                            high_quality += 1
                        elif comp >= 70 and cont <= 10:
                            medium_quality += 1
                        else:
                            low_quality += 1
            
            stats.update({
                'total_bins': total_bins,
                'high_quality': high_quality,
                'medium_quality': medium_quality,
                'low_quality': low_quality
            })
        
        return stats
    
    def process_checkm_file(self, file_path, analysis_type, fna_options=None):
        """Procesar archivo CheckM y generar visualizaciones"""
        try:
            print(f"🔍 Procesando archivo CheckM: {file_path} (tipo: {analysis_type})")
            
            # Parsear datos
            data = self.parse_checkm_file(file_path, analysis_type)
            print(f"📊 Datos parseados exitosamente")
            
            graphs = []
            fna_analysis = None
            
            if analysis_type == 'fna_analysis':
                # Análisis específico para archivos FNA
                if fna_options:
                    fna_analysis = self.analyze_fna_sequences(data, fna_options)
                    graphs.extend(self.plot_fna_statistics(data, fna_options))
                    print("✅ Análisis FNA completado")
            elif analysis_type in ['hmmer_analyze', 'hmmer_tree']:
                # Análisis específico para archivos HMMER
                if analysis_type == 'hmmer_analyze' and hasattr(data, 'columns'):
                    graphs.extend(self.plot_hmmer_analysis(data))
                    print("✅ Análisis HMMER completado")
                elif analysis_type == 'hmmer_tree':
                    # Para árboles HMMER, crear visualización simple
                    print("✅ Árbol HMMER procesado")
            else:
                # Análisis para otros tipos de CheckM
                if hasattr(data, 'columns'):
                    quality_plot = self.plot_checkm_quality(data)
                    if quality_plot:
                        graphs.append(quality_plot)
                        print("✅ Gráfico de calidad CheckM creado")
            
            # Generar estadísticas
            stats = self.generate_checkm_stats(data, analysis_type, fna_analysis)
            print("✅ Estadísticas generadas")
            
            return {
                'graphs': graphs,
                'stats': stats,
                'data_summary': {
                    'analysis_type': analysis_type,
                    'records_processed': len(data) if hasattr(data, '__len__') else 1
                }
            }
            
        except Exception as e:
            print(f"❌ Error procesando archivo CheckM: {e}")
            raise Exception(f"Error procesando archivo CheckM: {str(e)}")


# ========== RUTAS DE LA API ==========

@app.route('/')
def index():
    """Ruta principal"""
    return jsonify({
        'service': 'FungiGT Multi-Genomic Visualizer',
        'version': '2.1.0',
        'status': 'running',
        'biopython_available': BIOPYTHON_AVAILABLE,
        'endpoints': [
            'POST /process-bindash - Procesar archivo BinDash',
            'POST /process-checkm - Procesar archivo CheckM (mejorado)',
            'GET /graphs/<path> - Servir gráficos generados',
            'POST /cleanup - Limpiar archivos temporales'
        ]
    })

@app.route('/process-bindash', methods=['POST'])
def process_bindash():
    """Procesar archivo de resultados BinDash"""
    try:
        # Verificar archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de archivo no permitido'}), 400
        
        # Guardar archivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_path = UPLOAD_DIR / f"{timestamp}_{filename}"
        file.save(upload_path)
        
        # Crear directorio de salida
        output_dir = OUTPUT_DIR / f"bindash_{timestamp}"
        
        # Procesar archivo
        visualizer = BinDashVisualizer(output_dir)
        result = visualizer.process_bindash_file(upload_path)
        
        # Convertir rutas a URLs relativas
        graphs_urls = []
        for graph_path in result['graphs']:
            relative_path = Path(graph_path).relative_to(OUTPUT_DIR)
            graphs_urls.append(f"/graphs/{relative_path}")
        
        # Limpiar archivo temporal
        upload_path.unlink()
        
        return jsonify({
            'message': 'Archivo procesado exitosamente',
            'graphs': graphs_urls,
            'stats': result['stats'],
            'data_summary': result['data_summary']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process-checkm', methods=['POST'])
def process_checkm():
    """Procesar archivo de resultados CheckM"""
    try:
        # Verificar si es archivo del servidor o archivo subido
        file_path = request.form.get('filePath')
        analysis_type = request.form.get('analysis_type')  # Opcional, se detectará automáticamente
        fna_options_str = request.form.get('fna_options')
        
        fna_options = {}
        if fna_options_str:
            try:
                fna_options = json.loads(fna_options_str)
            except json.JSONDecodeError:
                fna_options = {}
        
        upload_path = None
        
        if file_path:
            # Archivo del servidor (desde file manager)
            # Construir ruta completa al archivo
            server_file_path = Path('/app/data') / file_path.lstrip('/')
            if not server_file_path.exists():
                return jsonify({'error': f'Archivo no encontrado en el servidor: {file_path}'}), 404
            upload_path = server_file_path
        else:
            # Archivo subido por el usuario
            if 'file' not in request.files:
                return jsonify({'error': 'No se proporcionó archivo'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No se seleccionó archivo'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'Tipo de archivo no permitido'}), 400
            
            # Guardar archivo temporal
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            upload_path = UPLOAD_DIR / f"{timestamp}_{filename}"
            file.save(upload_path)
        
        # Crear directorio de salida
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = OUTPUT_DIR / f"checkm_{timestamp}"
        
        # Procesar archivo
        visualizer = CheckMVisualizer(output_dir)
        result = visualizer.process_checkm_file(upload_path, analysis_type, fna_options)
        
        # Convertir rutas a URLs relativas
        graphs_urls = []
        for graph_path in result['graphs']:
            relative_path = Path(graph_path).relative_to(OUTPUT_DIR)
            graphs_urls.append(f"/graphs/{relative_path}")
        
        # Limpiar archivo temporal si fue subido por el usuario
        if not file_path and upload_path and upload_path.exists():
            upload_path.unlink()
        
        return jsonify({
            'message': 'Archivo CheckM procesado exitosamente',
            'graphs': graphs_urls,
            'stats': result['stats'],
            'data_summary': result['data_summary']
        })
        
    except Exception as e:
        print(f"Error en endpoint CheckM: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/graphs/<path:filename>')
def serve_graph(filename):
    """Servir archivos de gráficos"""
    try:
        return send_from_directory(OUTPUT_DIR, filename)
    except Exception as e:
        return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Limpiar archivos temporales"""
    try:
        clean_old_files()
        return jsonify({'message': 'Limpieza completada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🧬 Iniciando FungiGT Multi-Genomic Visualizer...")
    print(f"📁 Directorio de uploads: {UPLOAD_DIR}")
    print(f"📊 Directorio de output: {OUTPUT_DIR}")
    print(f"🔬 BioPython disponible: {BIOPYTHON_AVAILABLE}")
    print("🚀 Servidor disponible en http://localhost:4008")
    print("📋 Endpoints disponibles:")
    print("   - POST /process-bindash - Procesar archivos BinDash")
    print("   - POST /process-checkm - Procesar archivos CheckM (mejorado)")
    print("   - GET /graphs/<path> - Servir gráficos generados")
    
    app.run(host='0.0.0.0', port=4008, debug=True) 