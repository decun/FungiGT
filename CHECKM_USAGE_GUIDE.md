# 🔬 Guía de Uso - Visualizador CheckM para FungiGT

## 🚀 Inicio Rápido

### 1. **Activación del Sistema**

```bash
# Iniciar servicios Docker de FungiGT
cd /workspace
docker-compose up -d visualization-server quality-control

# Verificar que los servicios estén activos
docker ps | grep fungigt
```

### 2. **Acceso a la Interfaz Web**

```
🌐 Servidor Principal:    http://localhost:4003
🔬 FungiVisualizer:      http://localhost:4008
📊 Quality Control:      http://localhost:4004
```

## 📁 Tipos de Archivos Soportados

### ✅ Archivos CheckM QA Results
```
Formato: .tsv, .txt, .csv
Ejemplo: checkm_qa_results.tsv
Columnas requeridas: Completeness, Contamination
```

### ✅ Archivos FASTA/FNA
```
Formato: .fna, .fasta, .fa
Ejemplo: genome_assembly.fna
Contenido: Secuencias de genoma/MAGs
```

### ✅ Otros Archivos CheckM
```
- Lineage analysis (.tsv)
- Bin statistics (.tsv)  
- Marker statistics (.marker_stats)
```

## 🔄 Métodos de Procesamiento

### **Método 1: Upload de Archivo**

```javascript
// JavaScript/Frontend
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:4003/process-checkm', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Gráficos:', data.graphs);
    console.log('Estadísticas:', data.stats);
});
```

### **Método 2: Archivo del Servidor**

```javascript
// Procesar archivo ya en el servidor
fetch('http://localhost:4003/process-checkm', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: 'filePath=/app/data/checkm_results.tsv'
})
.then(response => response.json())
.then(data => console.log(data));
```

### **Método 3: cURL desde Terminal**

```bash
# Upload de archivo
curl -X POST \
  http://localhost:4003/process-checkm \
  -F "file=@/path/to/checkm_qa.tsv"

# Archivo del servidor  
curl -X POST \
  http://localhost:4003/process-checkm \
  -d "filePath=/data/checkm_results.tsv"
```

## 📊 Estructura de Respuesta

```json
{
  "message": "Archivo CheckM procesado exitosamente",
  "file_type": "checkm",
  "visualizer": "CheckMVisualizer",
  "graphs": [
    "/graphs/checkm_20240101_123456/quality_assessment.png",
    "/graphs/checkm_20240101_123456/quality_distribution.png",
    "/graphs/checkm_20240101_123456/quality_scatter_advanced.png"
  ],
  "stats": {
    "basic": {
      "total_genomes": 20,
      "total_columns": 13,
      "columns": ["bin_id", "completeness", "contamination", ...]
    },
    "quality": {
      "high_quality": 3,
      "medium_quality": 4,
      "low_quality": 6,
      "very_low_quality": 7,
      "completeness_mean": 86.83,
      "contamination_mean": 12.98
    }
  },
  "data_summary": {
    "analysis_type": "qa_results",
    "records_processed": 20
  }
}
```

## 🎨 Visualizaciones Generadas

### 1. **quality_assessment.png**
- **Scatter plot principal**: Completitud vs Contaminación
- **Distribución de calidad**: Pie chart con categorías
- **Histogramas**: Distribución de completitud y contaminación
- **Líneas de referencia**: Umbrales de calidad

### 2. **quality_distribution.png**  
- **Box plots**: Por categoría de calidad
- **Índice de calidad neta**: Completitud - Contaminación
- **Comparaciones estadísticas**: Entre categorías

### 3. **quality_scatter_advanced.png**
- **Mapa de color**: Densidad de completitud
- **Hexbin plot**: Patrones de agrupación
- **Contornos de densidad**: Distribución bidimensional
- **Análisis por tamaño**: Si disponible

### 4. **correlation_matrix.png** (Si hay múltiples variables)
- **Heatmap de correlación**: Entre todas las variables numéricas
- **Pairplot**: Análisis pairwise de variables

### 5. **pca_analysis.png** (Para análisis multivariable)
- **Varianza explicada**: Por componente principal
- **Biplot PC1 vs PC2**: Con loadings de variables
- **Varianza acumulada**: Hasta 95%

## 🔍 Interpretación de Resultados

### **Clasificación de Calidad**

```
🟢 Alta Calidad (High):
   ✅ Completitud ≥ 90%
   ✅ Contaminación ≤ 5%
   → Genomas listos para análisis downstream

🟡 Calidad Media (Medium):  
   ⚠️ Completitud ≥ 70%
   ⚠️ Contaminación ≤ 10%
   → Útiles para muchos análisis

🟠 Calidad Baja (Low):
   ⚠️ Completitud ≥ 50%  
   ⚠️ Contaminación ≤ 15%
   → Requieren filtrado adicional

🔴 Muy Baja Calidad (Very Low):
   ❌ No cumple criterios mínimos
   → Considerar re-ensamblaje
```

### **Métricas Clave**

- **Completitud**: % de genes marcadores encontrados
- **Contaminación**: % de genes marcadores duplicados
- **Strain Heterogeneity**: Diversidad intraespecífica
- **N50**: Estadística de continuidad del ensamblaje

## 🛠️ Casos de Uso Prácticos

### **Evaluación de MAGs**
```bash
# Procesar resultados de binning
curl -X POST http://localhost:4003/process-checkm \
  -F "file=@binning_results/checkm_qa.tsv"
```

### **Comparación de Métodos de Ensamblaje**
```bash
# Analizar múltiples ensamblajes
for assembly in *.fna; do
  curl -X POST http://localhost:4003/process-checkm \
    -F "file=@$assembly"
done
```

### **Control de Calidad en Pipeline**
```python
import requests

def check_quality(file_path):
    """Evaluar calidad de genoma en pipeline automatizado."""
    response = requests.post(
        'http://localhost:4003/process-checkm',
        data={'filePath': file_path}
    )
    
    if response.status_code == 200:
        data = response.json()
        high_quality = data['stats']['quality']['high_quality']
        total = data['stats']['basic']['total_genomes']
        
        quality_ratio = high_quality / total if total > 0 else 0
        
        if quality_ratio > 0.8:
            print(f"✅ Excelente calidad: {quality_ratio:.1%}")
        elif quality_ratio > 0.5:
            print(f"⚠️ Calidad aceptable: {quality_ratio:.1%}")
        else:
            print(f"❌ Calidad insuficiente: {quality_ratio:.1%}")
            
        return data
    else:
        print(f"❌ Error procesando: {response.text}")
        return None
```

## 🔧 Troubleshooting

### **Problemas Comunes**

```
❌ Error: "Archivo no válido para CheckMVisualizer"
💡 Verificar que el archivo tenga las columnas requeridas:
   - Completeness, Contamination (para QA results)
   - Formato FASTA válido (para archivos .fna)

❌ Error: "No se encontraron datos válidos"  
💡 Verificar formato del archivo:
   - Separador de columnas (TAB para .tsv)
   - Encoding del archivo (UTF-8)
   - Headers correctos

❌ Error: "BioPython requerido para análisis FASTA"
💡 Instalar BioPython en el contenedor:
   pip install biopython
```

### **Logs de Debugging**

```bash
# Ver logs del contenedor de visualización
docker logs fungigt-visualization-server

# Ver logs específicos de CheckM
grep "CheckM" /var/log/fungigt/visualization.log
```

## 📈 Optimización de Rendimiento

### **Archivos Grandes**
```python
# Para archivos >1000 genomas, usar procesamiento en chunks
# El sistema automáticamente optimiza para archivos grandes
```

### **Memoria**
```bash
# Aumentar memoria del contenedor si es necesario
docker-compose.yml:
  visualization-server:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 🆘 Soporte

### **Recursos Adicionales**
- 📄 **Documentación completa**: `CHECKM_VISUALIZER_REPORT.md`
- 🧪 **Script de pruebas**: `test_checkm_visualizer.py`
- 🔬 **Código fuente**: `src/modules/visualization/visualizers/checkm_visualizer.py`

### **Contacto**
Para soporte técnico, revisar los logs y la documentación completa del sistema FungiGT.

---

## ✅ Checklist de Uso

- [ ] Servicios Docker iniciados
- [ ] Archivo CheckM preparado (formato correcto)
- [ ] Endpoint seleccionado (`/process-checkm`)
- [ ] Respuesta procesada (gráficos + estadísticas)
- [ ] Visualizaciones interpretadas
- [ ] Decisiones tomadas basadas en calidad

¡El visualizador CheckM está listo para acelerar tu investigación genómica! 🚀