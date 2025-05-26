#!/usr/bin/env python3
# process_seed_orthologs.py

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

def main():
    # Verificar que se proporcionen los argumentos necesarios
    if len(sys.argv) not in [2, 3]:
        print("Uso: python3 process_seed_orthologs.py <archivo_de_entrada.seed_orthologs+> [<directorio_de_salida>]")
        print("Si no se proporciona <directorio_de_salida>, se usará el directorio actual.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) == 3 else '.'
    
    # Verificar que el archivo de entrada existe
    if not os.path.isfile(input_file):
        print(f"El archivo de entrada {input_file} no existe.")
        sys.exit(1)
    
    # Crear el directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Configurar el estilo de los gráficos
    sns.set(style='whitegrid', font_scale=1.2)
    
    # Leer el archivo de ortólogos semilla, manejando el encabezado correctamente
    header_line = None
    skip_rows = 0
    with open(input_file, 'r') as f:
        for line in f:
            if line.startswith('##'):
                skip_rows += 1
                continue
            elif line.startswith('#'):
                header_line = line[1:].strip().split('\t')
                skip_rows += 1
                break
            else:
                skip_rows += 1
    
    if header_line is None:
        print("No se encontró la línea de encabezado en el archivo.")
        sys.exit(1)
    
    # Leer el archivo en un DataFrame de pandas
    try:
        df = pd.read_csv(input_file, sep='\t', header=None, names=header_line, skiprows=skip_rows, low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        sys.exit(1)
    
    # Convertir columnas numéricas y eliminar filas con valores nulos
    numerical_cols = ['evalue', 'bitscore', 'qstart', 'qend', 'sstart', 'send', 'pident', 'qcov', 'scov']
    missing_cols = [col for col in numerical_cols if col not in df.columns]
    if missing_cols:
        print(f"Las siguientes columnas faltan en el archivo de anotaciones: {', '.join(missing_cols)}")
        sys.exit(1)
    
    df[numerical_cols] = df[numerical_cols].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=numerical_cols)
    
    # Gráfico de Distribución de e-values
    if 'evalue' in df.columns:
        plt.figure(figsize=(10,6))
        sns.histplot(df['evalue'], bins=50, log_scale=(True, False), kde=False, color='skyblue')
        plt.title('Distribución de e-values')
        plt.xlabel('e-value')
        plt.ylabel('Frecuencia')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'evalue_distribution.png'), dpi=300)
        plt.close()
    else:
        print("La columna 'evalue' no se encontró en el archivo de anotaciones.")
    
    # Gráfico de Bitscore vs. Porcentaje de Identidad
    if 'bitscore' in df.columns and 'pident' in df.columns:
        plt.figure(figsize=(10,6))
        sns.scatterplot(data=df, x='bitscore', y='pident', alpha=0.6, edgecolor=None, color='coral')
        plt.title('Bitscore vs. Porcentaje de Identidad')
        plt.xlabel('Bitscore')
        plt.ylabel('Porcentaje de Identidad (%)')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bitscore_vs_pident.png'), dpi=300)
        plt.close()
    else:
        print("Las columnas 'bitscore' y/o 'pident' no se encontraron en el archivo de anotaciones.")
    
    # Gráfico de Bitscore por Secuencia de Consulta
    if 'qseqid' in df.columns and 'bitscore' in df.columns:
        plt.figure(figsize=(12,8))
        df_sorted = df.sort_values(by='bitscore', ascending=False)
        # Para evitar demasiadas barras, limitar el número de secuencias
        top_n = 50
        df_top = df_sorted.head(top_n)
        sns.barplot(data=df_top, x='qseqid', y='bitscore', palette='muted')
        plt.title(f'Bitscore por Secuencia de Consulta (Top {top_n})')
        plt.xlabel('ID de Secuencia de Consulta')
        plt.ylabel('Bitscore')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bitscore_per_sequence.png'), dpi=300)
        plt.close()
    else:
        print("Las columnas 'qseqid' y/o 'bitscore' no se encontraron en el archivo de anotaciones.")
    
    # Mapa de Calor de Coberturas
    if 'qseqid' in df.columns and 'qcov' in df.columns and 'scov' in df.columns:
        coverage_data = df[['qseqid', 'qcov', 'scov']].dropna()
        
        # Convertir de formato ancho a largo (melt)
        coverage_data = coverage_data.melt(id_vars='qseqid', var_name='Tipo', value_name='Cobertura')
        
        # Crear la tabla pivot
        pivot_table = coverage_data.pivot(index='qseqid', columns='Tipo', values='Cobertura')
        
        # Crear el mapa de calor
        plt.figure(figsize=(10,12))
        sns.heatmap(pivot_table, annot=False, cmap='viridis', cbar_kws={'label': 'Cobertura (%)'})
        plt.title('Mapa de Calor de Coberturas')
        plt.xlabel('Tipo de Cobertura')
        plt.ylabel('ID de Secuencia de Consulta')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'coverage_heatmap.png'), dpi=300)
        plt.close()
    else:
        print("Las columnas 'qseqid', 'qcov' y/o 'scov' no se encontraron en el archivo de anotaciones.")
    
    # Matriz de Correlación
    correlation_cols = ['evalue', 'bitscore', 'pident', 'qcov', 'scov']
    if all(col in df.columns for col in correlation_cols):
        plt.figure(figsize=(8,6))
        corr_matrix = df[correlation_cols].corr()
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5)
        plt.title('Matriz de Correlación')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'correlation_matrix.png'), dpi=300)
        plt.close()
    else:
        print(f"Una o más de las columnas {correlation_cols} no se encontraron en el archivo de anotaciones.")
    
    print(f"Gráficos generados y guardados en {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main()
