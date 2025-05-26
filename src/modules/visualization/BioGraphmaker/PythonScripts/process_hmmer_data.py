#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import sys
from matplotlib.ticker import ScalarFormatter

def setup_plot_style():
    """Configurar el estilo general de los gráficos"""
    sns.set_theme(style='whitegrid')
    sns.set_palette("husl")
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['figure.figsize'] = (12, 8)

def create_frequency_plot(df, output_dir, top_n=20):
    """Crear gráfico de frecuencia de dominios horizontal con los top N más frecuentes"""
    domain_counts = df['Query Name'].value_counts()
    
    # Separar los top N dominios y agrupar el resto como "Otros"
    top_domains = domain_counts.head(top_n)
    others_sum = domain_counts[top_n:].sum()
    
    if len(domain_counts) > top_n:
        top_domains = pd.concat([top_domains, pd.Series({'Otros': others_sum})])
    
    # Crear el gráfico horizontal
    plt.figure(figsize=(12, max(8, top_n * 0.3)))
    bars = plt.barh(y=range(len(top_domains)), width=top_domains.values, 
                   color=sns.color_palette("husl", len(top_domains)))
    
    # Añadir etiquetas y valores
    plt.yticks(range(len(top_domains)), top_domains.index)
    plt.xlabel('Frecuencia')
    plt.title('Frecuencia de Dominios (Top {})'.format(top_n))
    
    # Añadir valores en las barras
    for i, v in enumerate(top_domains.values):
        plt.text(v, i, f' {v:,}', va='center')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'domain_frequency.png'), dpi=300, bbox_inches='tight')
    plt.close()

def create_evalue_distribution(df, output_dir, top_n=20):
    """Crear gráfico de caja para la distribución de E-values"""
    # Filtrar por los dominios más frecuentes
    top_domains = df['Query Name'].value_counts().head(top_n).index
    filtered_df = df[df['Query Name'].isin(top_domains)]
    
    plt.figure(figsize=(12, 8))
    # Crear boxplot horizontal
    sns.boxplot(data=filtered_df, y='Query Name', x='E-value', whis=1.5, 
                order=filtered_df.groupby('Query Name')['E-value'].median().sort_values().index)
    
    plt.xscale('log')
    plt.xlabel('E-value (escala logarítmica)')
    plt.ylabel('Dominio')
    plt.title('Distribución de E-values por Dominio')
    
    # Formatear el eje x para valores científicos
    ax = plt.gca()
    ax.xaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0e'))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'evalue_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()

def create_score_heatmap(df, output_dir, top_n=20):
    """Crear mapa de calor de puntuaciones promedio por dominio"""
    # Calcular estadísticas por dominio
    domain_stats = df.groupby('Query Name').agg({
        'Score': ['mean', 'count'],
        'E-value': 'mean'
    }).round(2)
    
    # Seleccionar top N dominios por frecuencia
    top_domains = domain_stats.sort_values(('Score', 'count'), ascending=False).head(top_n)
    
    # Crear matriz para el heatmap
    heatmap_data = pd.DataFrame({
        'Dominio': top_domains.index,
        'Puntuación Media': top_domains[('Score', 'mean')],
        'E-value Medio': -np.log10(top_domains[('E-value', 'mean')]),
        'Frecuencia': top_domains[('Score', 'count')]
    }).set_index('Dominio')
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='YlOrRd', 
                center=0, cbar_kws={'label': 'Valor'})
    
    plt.title('Resumen de Dominios (Top {})'.format(top_n))
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'domain_summary_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Verificar argumentos
    if len(sys.argv) != 3:
        print("Uso: python3 process_hmmer_data.py <archivo_hmmer.analyze.txt> <directorio_de_salida>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Verificar archivo de entrada
    if not os.path.isfile(input_file):
        print(f"El archivo de entrada {input_file} no existe.")
        sys.exit(1)
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # Configurar estilo global
    setup_plot_style()
    
    try:
        # Leer datos
        df = pd.read_csv(input_file, delim_whitespace=True, comment='#', header=None,
                        names=["Target Name", "Accession", "tlen", "Query Name", "Query Accession",
                               "qlen", "E-value", "Score", "Bias", "Domain No", "of", "c-Evalue",
                               "i-Evalue", "Domain Score", "Domain Bias", "Hmm From", "Hmm To",
                               "Ali From", "Ali To", "Env From", "Env To", "Acc", "Description"])
        
        # Crear visualizaciones
        create_frequency_plot(df, output_dir)
        create_evalue_distribution(df, output_dir)
        create_score_heatmap(df, output_dir)
        
        print(f"Gráficos generados y guardados en {output_dir}")
        
    except Exception as e:
        print(f"Error al procesar el archivo: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
