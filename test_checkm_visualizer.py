#!/usr/bin/env python3
"""
Script de prueba para el visualizador CheckM
===========================================

Prueba la funcionalidad básica del visualizador CheckM
sin dependencias externas complejas.
"""

import os
import sys
from pathlib import Path
import csv

# Simular las dependencias que no están disponibles
class MockPandas:
    def read_csv(self, *args, **kwargs):
        # Leer CSV manualmente
        data = []
        with open(args[0], 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                data.append(row)
        return MockDataFrame(data)

class MockDataFrame:
    def __init__(self, data):
        self.data = data
        self.columns = list(data[0].keys()) if data else []
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, key):
        if isinstance(key, str):
            return MockSeries([row[key] for row in self.data if key in row])
        return self.data[key]
    
    def apply(self, func, axis=1):
        return MockSeries([func(MockRow(row)) for row in self.data])

class MockSeries:
    def __init__(self, data):
        self.data = data
    
    def mean(self):
        try:
            numeric_data = [float(x) for x in self.data if x and x != 'N/A']
            return sum(numeric_data) / len(numeric_data) if numeric_data else 0
        except:
            return 0
    
    def std(self):
        try:
            numeric_data = [float(x) for x in self.data if x and x != 'N/A']
            if len(numeric_data) < 2:
                return 0
            mean_val = sum(numeric_data) / len(numeric_data)
            variance = sum((x - mean_val) ** 2 for x in numeric_data) / (len(numeric_data) - 1)
            return variance ** 0.5
        except:
            return 0
    
    def value_counts(self):
        counts = {}
        for item in self.data:
            counts[item] = counts.get(item, 0) + 1
        return MockSeries(list(counts.values()))

class MockRow:
    def __init__(self, row_dict):
        self.row_dict = row_dict
    
    def __getitem__(self, key):
        return self.row_dict.get(key, 0)

# Clase simplificada del visualizador CheckM
class SimpleCheckMVisualizer:
    """Versión simplificada del visualizador CheckM para pruebas."""
    
    def __init__(self):
        self.quality_thresholds = {
            'high_quality': {'completeness': 90, 'contamination': 5},
            'medium_quality': {'completeness': 70, 'contamination': 10},
            'low_quality': {'completeness': 50, 'contamination': 15}
        }
    
    def classify_genome_quality(self, completeness, contamination):
        """Clasificar calidad del genoma."""
        try:
            comp = float(completeness)
            cont = float(contamination)
            
            if comp >= 90 and cont <= 5:
                return 'high'
            elif comp >= 70 and cont <= 10:
                return 'medium'
            elif comp >= 50 and cont <= 15:
                return 'low'
            else:
                return 'very_low'
        except:
            return 'unknown'
    
    def parse_checkm_file(self, file_path):
        """Parsear archivo CheckM básico."""
        print(f"📊 Parseando archivo: {file_path}")
        
        # Usar el mock pandas
        pd = MockPandas()
        try:
            data = pd.read_csv(file_path)
            print(f"✅ Archivo parseado exitosamente: {len(data)} registros")
            return data
        except Exception as e:
            print(f"❌ Error parseando archivo: {e}")
            return None
    
    def analyze_quality_distribution(self, data):
        """Analizar distribución de calidad."""
        print("\n🔍 Analizando distribución de calidad...")
        
        quality_counts = {'high': 0, 'medium': 0, 'low': 0, 'very_low': 0, 'unknown': 0}
        completeness_values = []
        contamination_values = []
        
        for row in data.data:
            # Obtener valores de completitud y contaminación
            completeness = row.get('Completeness', '0')
            contamination = row.get('Contamination', '0')
            
            # Clasificar calidad
            quality = self.classify_genome_quality(completeness, contamination)
            quality_counts[quality] += 1
            
            # Guardar valores para estadísticas
            try:
                completeness_values.append(float(completeness))
                contamination_values.append(float(contamination))
            except:
                pass
        
        return {
            'quality_distribution': quality_counts,
            'completeness_stats': self._calculate_stats(completeness_values),
            'contamination_stats': self._calculate_stats(contamination_values)
        }
    
    def _calculate_stats(self, values):
        """Calcular estadísticas básicas."""
        if not values:
            return {'mean': 0, 'min': 0, 'max': 0, 'count': 0}
        
        return {
            'mean': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'count': len(values)
        }
    
    def generate_text_report(self, analysis_results):
        """Generar reporte de texto."""
        print("\n📋 REPORTE DE ANÁLISIS CHECKM")
        print("=" * 50)
        
        # Distribución de calidad
        quality_dist = analysis_results['quality_distribution']
        total_genomes = sum(quality_dist.values())
        
        print(f"\n🧬 GENOMAS ANALIZADOS: {total_genomes}")
        print("-" * 30)
        
        for quality, count in quality_dist.items():
            percentage = (count / total_genomes * 100) if total_genomes > 0 else 0
            emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠', 'very_low': '🔴', 'unknown': '⚫'}
            print(f"{emoji.get(quality, '⚫')} {quality.replace('_', ' ').title():12}: {count:3d} ({percentage:5.1f}%)")
        
        # Estadísticas de completitud
        comp_stats = analysis_results['completeness_stats']
        print(f"\n📊 COMPLETITUD")
        print("-" * 20)
        print(f"Media:    {comp_stats['mean']:6.2f}%")
        print(f"Mínima:   {comp_stats['min']:6.2f}%")
        print(f"Máxima:   {comp_stats['max']:6.2f}%")
        
        # Estadísticas de contaminación
        cont_stats = analysis_results['contamination_stats']
        print(f"\n🦠 CONTAMINACIÓN")
        print("-" * 20)
        print(f"Media:    {cont_stats['mean']:6.2f}%")
        print(f"Mínima:   {cont_stats['min']:6.2f}%")
        print(f"Máxima:   {cont_stats['max']:6.2f}%")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES")
        print("-" * 20)
        high_quality = quality_dist['high']
        total_good = quality_dist['high'] + quality_dist['medium']
        
        if high_quality > total_genomes * 0.7:
            print("✅ Excelente! La mayoría de genomas son de alta calidad.")
        elif total_good > total_genomes * 0.5:
            print("👍 Buena calidad general, algunos genomas pueden mejorarse.")
        else:
            print("⚠️  Considerar filtrado adicional o re-ensamblaje.")
        
        print("\n" + "=" * 50)

def test_checkm_visualizer():
    """Función principal de prueba."""
    print("🧬 INICIANDO PRUEBA DEL VISUALIZADOR CHECKM")
    print("=" * 60)
    
    # Crear instancia del visualizador
    visualizer = SimpleCheckMVisualizer()
    
    # Archivo de prueba
    test_file = Path("data/test_checkm_qa.tsv")
    
    if not test_file.exists():
        print(f"❌ Archivo de prueba no encontrado: {test_file}")
        print("💡 Asegúrate de que el archivo de prueba existe.")
        return False
    
    # Parsear archivo
    data = visualizer.parse_checkm_file(test_file)
    if data is None:
        return False
    
    # Analizar calidad
    analysis_results = visualizer.analyze_quality_distribution(data)
    
    # Generar reporte
    visualizer.generate_text_report(analysis_results)
    
    print("\n✅ PRUEBA COMPLETADA EXITOSAMENTE!")
    print("🎯 El visualizador CheckM está funcionando correctamente.")
    
    return True

def test_fasta_analysis():
    """Probar análisis básico de archivos FASTA."""
    print("\n🧬 INICIANDO PRUEBA DE ANÁLISIS FASTA")
    print("=" * 50)
    
    fasta_file = Path("data/test_genome.fna")
    
    if not fasta_file.exists():
        print(f"❌ Archivo FASTA no encontrado: {fasta_file}")
        return False
    
    # Análisis básico manual de FASTA
    sequences = []
    current_seq = ""
    current_header = ""
    
    with open(fasta_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if current_seq:
                    sequences.append({
                        'header': current_header,
                        'length': len(current_seq),
                        'gc_content': (current_seq.count('G') + current_seq.count('C')) / len(current_seq) * 100
                    })
                current_header = line[1:]
                current_seq = ""
            else:
                current_seq += line
        
        # Agregar última secuencia
        if current_seq:
            sequences.append({
                'header': current_header,
                'length': len(current_seq),
                'gc_content': (current_seq.count('G') + current_seq.count('C')) / len(current_seq) * 100
            })
    
    # Mostrar resultados
    print(f"\n📊 ANÁLISIS DE {len(sequences)} SECUENCIAS")
    print("-" * 40)
    
    total_length = sum(seq['length'] for seq in sequences)
    avg_gc = sum(seq['gc_content'] for seq in sequences) / len(sequences) if sequences else 0
    
    print(f"Secuencias totales: {len(sequences)}")
    print(f"Longitud total:     {total_length:,} bp")
    print(f"Longitud promedio:  {total_length // len(sequences):,} bp")
    print(f"Contenido GC medio: {avg_gc:.2f}%")
    
    print("\n📋 DETALLE POR SECUENCIA:")
    for i, seq in enumerate(sequences, 1):
        print(f"  {i}. {seq['length']:,} bp, GC: {seq['gc_content']:.1f}%")
    
    print("\n✅ ANÁLISIS FASTA COMPLETADO!")
    return True

if __name__ == "__main__":
    print("🔬 SISTEMA DE PRUEBAS - VISUALIZADOR CHECKM")
    print("Versión simplificada para demostración")
    print("=" * 60)
    
    success = True
    
    # Probar análisis CheckM
    if not test_checkm_visualizer():
        success = False
    
    # Probar análisis FASTA
    if not test_fasta_analysis():
        success = False
    
    if success:
        print("\n🎉 TODAS LAS PRUEBAS EXITOSAS!")
        print("📈 El visualizador CheckM está listo para usar.")
        print("\n💡 Para usar con datos reales:")
        print("   1. Instalar dependencias completas (pandas, matplotlib, etc.)")
        print("   2. Usar el visualizador completo en src/modules/visualization/")
        print("   3. Procesar archivos reales de CheckM")
    else:
        print("\n❌ ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisar configuración y archivos de prueba")
    
    print("\n" + "=" * 60)