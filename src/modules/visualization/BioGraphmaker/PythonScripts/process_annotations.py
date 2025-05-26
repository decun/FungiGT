#!/usr/bin/env python3
# process_annotations.py

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os
import sys

def main():
    # Verificar que se proporcionen los argumentos necesarios
    if len(sys.argv) != 3:
        print("Uso: python3 process_annotations.py <archivo_de_entrada.emapper.annotations> <directorio_de_salida>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Verificar que el archivo de entrada existe
    if not os.path.isfile(input_file):
        print(f"El archivo de entrada {input_file} no existe.")
        sys.exit(1)
    
    # Crear el directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Configurar el estilo de los gráficos
    sns.set(style='whitegrid', font_scale=1.2)
    
    # Leer el archivo de anotaciones, manejando el encabezado correctamente
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
    df = pd.read_csv(input_file, sep='\t', header=None, names=header_line, skiprows=skip_rows, low_memory=False)
    
    # Gráfico de Categorías COG
    if 'COG_category' in df.columns:
        df_cog = df.dropna(subset=['COG_category'])
        cog_categories = ''.join(df_cog['COG_category'].tolist())
        cog_list = list(cog_categories)
        cog_counts = Counter(cog_list)
        cog_df = pd.DataFrame.from_dict(cog_counts, orient='index').reset_index()
        cog_df.columns = ['COG_category', 'Count']
        cog_dict = {
            'A': 'RNA processing & modification',
            'B': 'Chromatin structure & dynamics',
            'C': 'Energy production & conversion',
            'D': 'Cell cycle control, mitosis & meiosis',
            'E': 'Amino acid transport & metabolism',
            'F': 'Nucleotide transport & metabolism',
            'G': 'Carbohydrate transport & metabolism',
            'H': 'Coenzyme transport & metabolism',
            'I': 'Lipid transport & metabolism',
            'J': 'Translation, ribosomal structure & biogenesis',
            'K': 'Transcription',
            'L': 'Replication, recombination & repair',
            'M': 'Cell wall/membrane/envelope biogenesis',
            'N': 'Cell motility',
            'O': 'Posttranslational modification, protein turnover, chaperones',
            'P': 'Inorganic ion transport & metabolism',
            'Q': 'Secondary metabolites biosynthesis, transport & catabolism',
            'R': 'General function prediction only',
            'S': 'Function unknown',
            'T': 'Signal transduction mechanisms',
            'U': 'Intracellular trafficking, secretion, and vesicular transport',
            'V': 'Defense mechanisms',
            'W': 'Extracellular structures',
            'Y': 'Nuclear structure',
            'Z': 'Cytoskeleton',
        }
        cog_df['Description'] = cog_df['COG_category'].map(cog_dict)
        cog_df = cog_df.sort_values('Count', ascending=False)
        plt.figure(figsize=(12,6))
        sns.barplot(data=cog_df, x='COG_category', y='Count', palette='viridis')
        plt.title('Distribución de Categorías COG')
        plt.xlabel('Categoría COG')
        plt.ylabel('Número de Proteínas')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'cog_categories.png'), dpi=300)
        plt.close()
    else:
        print("La columna 'COG_category' no se encontró en el archivo de anotaciones.")
    
    # Gráfico de Términos GO Más Comunes
    if 'GOs' in df.columns:
        df_go = df.dropna(subset=['GOs'])
        go_terms = df_go['GOs'].str.split(',', expand=True).stack().reset_index(level=1, drop=True)
        go_terms.name = 'GO_term'
        go_counts = go_terms.value_counts().reset_index()
        go_counts.columns = ['GO_term', 'Count']
        top_go = go_counts.head(20)
        plt.figure(figsize=(10,8))
        sns.barplot(data=top_go, y='GO_term', x='Count', palette='magma')
        plt.title('Top 20 Términos GO Más Comunes')
        plt.xlabel('Número de Proteínas')
        plt.ylabel('Término GO')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_go_terms.png'), dpi=300)
        plt.close()
    else:
        print("La columna 'GOs' no se encontró en el archivo de anotaciones.")
    
    # Gráfico de Vías KEGG Más Comunes
    if 'KEGG_Pathway' in df.columns:
        df_kegg = df.dropna(subset=['KEGG_Pathway'])
        kegg_pathways = df_kegg['KEGG_Pathway'].str.split(',', expand=True).stack().reset_index(level=1, drop=True)
        kegg_pathways.name = 'KEGG_Pathway'
        kegg_counts = kegg_pathways.value_counts().reset_index()
        kegg_counts.columns = ['KEGG_Pathway', 'Count']
        top_kegg = kegg_counts.head(10)
        plt.figure(figsize=(10,6))
        sns.barplot(data=top_kegg, y='KEGG_Pathway', x='Count', palette='cividis')
        plt.title('Top 10 Vías KEGG Más Comunes')
        plt.xlabel('Número de Proteínas')
        plt.ylabel('Vía KEGG')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_kegg_pathways.png'), dpi=300)
        plt.close()
    else:
        print("La columna 'KEGG_Pathway' no se encontró en el archivo de anotaciones.")
    
    # Gráfico de Familias PFAM Más Comunes
    if 'PFAMs' in df.columns:
        df_pfam = df.dropna(subset=['PFAMs'])
        pfam_families = df_pfam['PFAMs'].str.split(',', expand=True).stack().reset_index(level=1, drop=True)
        pfam_families.name = 'PFAM'
        pfam_counts = pfam_families.value_counts().reset_index()
        pfam_counts.columns = ['PFAM', 'Count']
        top_pfam = pfam_counts.head(15)
        plt.figure(figsize=(10,8))
        sns.barplot(data=top_pfam, y='PFAM', x='Count', palette='plasma')
        plt.title('Top 15 Familias PFAM Más Comunes')
        plt.xlabel('Número de Proteínas')
        plt.ylabel('Familia PFAM')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_pfam_families.png'), dpi=300)
        plt.close()
    else:
        print("La columna 'PFAMs' no se encontró en el archivo de anotaciones.")
    
    # Gráfico de Números EC Más Comunes
    if 'EC' in df.columns:
        df_ec = df.dropna(subset=['EC'])
        ec_numbers = df_ec['EC'].str.split(',', expand=True).stack().reset_index(level=1, drop=True)
        ec_numbers.name = 'EC_number'
        ec_counts = ec_numbers.value_counts().reset_index()
        ec_counts.columns = ['EC_number', 'Count']
        top_ec = ec_counts.head(10)
        plt.figure(figsize=(10,6))
        sns.barplot(data=top_ec, y='EC_number', x='Count', palette='inferno')
        plt.title('Top 10 Números EC Más Comunes')
        plt.xlabel('Número de Proteínas')
        plt.ylabel('Número EC')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_ec_numbers.png'), dpi=300)
        plt.close()
    else:
        print("La columna 'EC' no se encontró en el archivo de anotaciones.")
    
    print(f"Gráficos generados y guardados en {output_dir}")

if __name__ == "__main__":
    main()
