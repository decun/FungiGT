# Bindash Analysis Module - FungiGT

Módulo de análisis genómico usando **Bindash** para comparación rápida de genomas y cálculo de distancias evolutivas.

## 🧬 ¿Qué es Bindash?

Bindash es una herramienta para comparación rápida de secuencias genómicas basada en:
- **MinHash**: Técnica probabilística para estimar similaridad
- **K-mers**: Fragmentos de ADN de longitud k
- **Sketching**: Representación compacta de genomas

## 🚀 Características

### ✅ Funcionalidades Disponibles
- **Sketch Creation**: Crear representaciones compactas de genomas
- **Genome Comparison**: Comparar múltiples genomas simultáneamente
- **Distance Matrix**: Calcular matrices de distancia filogenética
- **Batch Processing**: Procesar múltiples archivos
- **REST API**: Interfaz web para análisis remotos

### 📊 Tipos de Análisis
1. **Comparación par a par**: Similaridad entre dos genomas
2. **Análisis masivo**: Comparación de múltiples genomas
3. **Clustering**: Agrupación por similaridad
4. **Distancias evolutivas**: Matrices para análisis filogenético

## 🔧 API Endpoints

### Básicos
```
GET  /health        - Health check del servicio
GET  /info          - Información del servicio
GET  /demo          - Ejemplos de uso
```

### Análisis
```
POST /upload        - Subir archivos FASTA/FASTQ
POST /sketch        - Crear sketch de genoma
POST /compare       - Comparar genomas
POST /distance      - Calcular matriz de distancias
GET  /results/:id   - Obtener resultados
```

## 📁 Formatos Soportados

### Entrada
- `.fasta`, `.fa`, `.fna`, `.fas` - Archivos FASTA
- `.fastq`, `.fq` - Archivos FASTQ
- Tamaño máximo: **100MB** por archivo

### Salida
- **JSON**: Resultados estructurados
- **TSV**: Tabular separated values
- **Phylip**: Formato para análisis filogenético

## 🛠️ Ejemplos de Uso

### 1. Crear Sketch
```bash
curl -X POST http://localhost:4007/sketch \
  -H "Content-Type: application/json" \
  -d '{
    "inputFile": "/data/uploads/genome.fasta",
    "kmerSize": 21,
    "sketchSize": 1000
  }'
```

### 2. Comparar Genomas
```bash
curl -X POST http://localhost:4007/compare \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      "/data/uploads/genome1.fasta",
      "/data/uploads/genome2.fasta"
    ],
    "kmerSize": 21,
    "threshold": 0.1
  }'
```

### 3. Matriz de Distancias
```bash
curl -X POST http://localhost:4007/distance \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      "/data/uploads/genome1.fasta",
      "/data/uploads/genome2.fasta",
      "/data/uploads/genome3.fasta"
    ],
    "kmerSize": 21,
    "outputFormat": "phylip"
  }'
```

## ⚙️ Parámetros

### K-mer Size (`kmerSize`)
- **Valores**: 15-31 (impar recomendado)
- **Por defecto**: 21
- **Uso**: Fragmentos de ADN para comparación

### Sketch Size (`sketchSize`)
- **Valores**: 100-10000
- **Por defecto**: 1000
- **Uso**: Número de hashes en el sketch

### Threshold (`threshold`)
- **Valores**: 0.0-1.0
- **Por defecto**: 0.1
- **Uso**: Umbral de similaridad para reportar

## 📈 Interpretación de Resultados

### Distancia Genómica
- **0.0**: Genomas idénticos
- **0.1**: Muy similares (misma especie)
- **0.5**: Moderadamente similares
- **1.0**: Muy diferentes

### P-value
- **< 0.05**: Significativo estadísticamente
- **< 0.01**: Altamente significativo

### Similaridad
- **> 0.9**: Muy similar
- **0.7-0.9**: Moderadamente similar
- **< 0.7**: Distante

## 🗂️ Estructura de Directorios

```
/data/
├── bindash_uploads/     # Archivos subidos
├── bindash_results/     # Resultados de análisis
│   └── {jobId}/        # Por cada trabajo
│       ├── sketch.txt
│       ├── comparison.txt
│       └── distances.phylip
```

## 🚦 Códigos de Estado

- **200**: Éxito
- **400**: Error de parámetros
- **404**: Archivo/resultado no encontrado
- **500**: Error interno del servidor

## 🔍 Troubleshooting

### Errores Comunes

1. **"Comando falló"**: Archivo FASTA corrupto o vacío
2. **"Archivo no encontrado"**: Verificar rutas de archivos
3. **"Timeout"**: Archivos muy grandes, aumentar límites

### Logs
```bash
# Ver logs del contenedor
docker logs fungigt-bindash-analysis

# Seguir logs en tiempo real  
docker logs -f fungigt-bindash-analysis
```

## 🧪 Testing

### Health Check
```bash
curl http://localhost:4007/health
```

### Demo Endpoints
```bash
curl http://localhost:4007/demo
curl http://localhost:4007/info
```

## 📚 Referencias

- [Bindash GitHub](https://github.com/onecodex/bindash)
- [MinHash Algorithm](https://en.wikipedia.org/wiki/MinHash)
- [K-mer Analysis](https://en.wikipedia.org/wiki/K-mer)

---

**Desarrollado para FungiGT** - Plataforma de Análisis Genómico para Hongos 