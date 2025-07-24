#!/usr/bin/env python3
"""
Script para reformatear headers de archivos FASTA para compatibilidad con Funannotate
Los headers se limitarán a 16 caracteres máximo
"""

import sys
import os
import re

def fix_fasta_headers(input_file, output_file=None):
    """
    Reformatea headers de FASTA para cumplir con límite de 16 caracteres
    """
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_fixed{ext}"
    
    header_count = 0
    sequences_processed = 0
    
    print(f"📁 Procesando: {input_file}")
    print(f"💾 Guardando en: {output_file}")
    
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in infile:
                line = line.strip()
                
                if line.startswith('>'):  # Es un header
                    header_count += 1
                    original_header = line
                    
                    # Extraer solo el ID de accesión (primera parte hasta el espacio)
                    header_parts = line[1:].split()  # Remover '>' y dividir por espacios
                    if header_parts:
                        accession_id = header_parts[0]
                        
                        # Limitar a 16 caracteres
                        if len(accession_id) > 16:
                            new_header = accession_id[:16]
                        else:
                            new_header = accession_id
                        
                        # Escribir nuevo header
                        outfile.write(f">{new_header}\n")
                        
                        if header_count <= 5:  # Mostrar primeros 5 ejemplos
                            print(f"  {header_count}. {original_header[:50]}... → >{new_header}")
                    
                else:  # Es secuencia
                    outfile.write(f"{line}\n")
                    if line:  # Solo contar líneas no vacías
                        sequences_processed += 1
    
    except FileNotFoundError:
        print(f"❌ Error: No se pudo encontrar el archivo {input_file}")
        return False
    except Exception as e:
        print(f"❌ Error procesando archivo: {e}")
        return False
    
    print(f"✅ Procesamiento completado:")
    print(f"   📊 Headers reformateados: {header_count}")
    print(f"   🧬 Líneas de secuencia: {sequences_processed}")
    print(f"   📁 Archivo generado: {output_file}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Uso: python fix_fasta_headers.py <archivo_entrada.fna> [archivo_salida.fna]")
        print("")
        print("Ejemplos:")
        print("  python fix_fasta_headers.py genome.fna")
        print("  python fix_fasta_headers.py genome.fna genome_clean.fna")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"❌ Error: El archivo {input_file} no existe")
        sys.exit(1)
    
    print("🔧 Reformateador de Headers FASTA para Funannotate")
    print("=" * 50)
    
    success = fix_fasta_headers(input_file, output_file)
    
    if success:
        print("=" * 50)
        print("🎉 ¡Headers reformateados exitosamente!")
        print("   Ahora puedes usar el archivo con Funannotate")
    else:
        print("❌ Falló el procesamiento")
        sys.exit(1)

if __name__ == "__main__":
    main()