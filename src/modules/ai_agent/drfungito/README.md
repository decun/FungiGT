# 🍄 Dr. Fungito AI Agent

**Agente de IA especializado en análisis genómico de hongos con capacidades de análisis de imágenes**

## 🎯 **Descripción**

Dr. Fungito es un agente de inteligencia artificial especializado que utiliza **Claude 3 Sonnet** de Anthropic para analizar automáticamente gráficos genómicos, interpretar resultados bioinformáticos y generar reportes detallados. Está diseñado específicamente para el análisis de genomas fúngicos.

## ✨ **Características Principales**

### 🔬 **Análisis Inteligente de Imágenes**
- Interpretación automática de gráficos genómicos (heatmaps, dendrogramas, gráficos de barras)
- Análisis especializado por tipo:
  - **BinDash**: Matrices de distancias, ANI, relaciones filogenéticas
  - **Anotaciones**: Categorías COG, GO terms, vías KEGG
  - **Control de Calidad**: CheckM, completitud genómica, contaminación
  - **HMMER**: Dominios, familias de proteínas

### 📊 **Generación de Reportes**
- Reportes detallados con interpretación biológica
- Análisis comparativo entre múltiples gráficos
- Recomendaciones para análisis adicionales
- Exportación en múltiples formatos

### 🧠 **Memoria por Usuario**
- Seguimiento de imágenes analizadas por usuario
- Historial de reportes generados
- Contexto mantenido entre sesiones
- Análisis evolutivo de resultados

### 🎨 **Integración Frontend**
- Botones en cada módulo de visualización
- Efectos hover sutiles y animaciones
- Modal de reportes interactivo
- Chat contextual integrado

## 🏗️ **Arquitectura**

```
📁 src/modules/ai_agent/drfungito/
├── 📄 server.js              # Servidor principal
├── 📄 package.json           # Dependencias Node.js
├── 📄 config.example.js      # Configuración
├── 📄 README.md              # Esta documentación
└── 📁 logs/                  # Archivos de log
    ├── 📄 error.log
    └── 📄 combined.log
```

## 🚀 **Instalación**

### 1. **Configurar API Key de Anthropic**

```bash
# Obtener API key en: https://console.anthropic.com/
export ANTHROPIC_API_KEY="tu_api_key_aqui"
```

### 2. **Instalar Dependencias**

```bash
cd src/modules/ai_agent/drfungito
npm install
```

### 3. **Configurar Variables de Entorno**

```bash
# Copiar configuración de ejemplo
cp config.example.js config.js

# Editar configuración
nano config.js
```

### 4. **Ejecutar con Docker**

```bash
# Desde el directorio raíz del proyecto
docker-compose up drfungito-agent
```

## 🔧 **Configuración**

### **Variables de Entorno Principales**

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API Key de Anthropic | `sk-ant-api03-...` |
| `PORT` | Puerto del servidor | `4009` |
| `MONGODB_URI` | URI de MongoDB | `mongodb://admin:admin123@localhost:27017/fungigt` |
| `FRONTEND_URL` | URL del frontend | `http://localhost:4005` |

### **Configuración de Imágenes**

```javascript
images: {
    maxSize: 10 * 1024 * 1024,     // 10MB máximo
    allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    maxWidth: 1024,                 // Redimensionado automático
    maxHeight: 1024,
    quality: 85                     // Calidad JPEG
}
```

## 📡 **API Endpoints**

### **🔍 Análisis de Imágenes**

```http
POST /analyze-image
Content-Type: multipart/form-data
X-User-Id: usuario123

{
  "image": [archivo],
  "analysisType": "bindash",
  "userContext": "Análisis de 5 genomas fúngicos",
  "saveToMemory": "true"
}
```

**Respuesta:**
```json
{
  "imageId": "uuid-v4",
  "filename": "graph_1.png",
  "analysisType": "bindash",
  "analysis": "Este heatmap muestra distancias genómicas...",
  "uploadDate": "2025-01-09T10:30:00Z",
  "metadata": {
    "originalSize": 2048576,
    "optimizedSize": 1024768,
    "mimetype": "image/png"
  }
}
```

### **📄 Generación de Reportes**

```http
POST /generate-report
Content-Type: application/json
X-User-Id: usuario123

{
  "reportType": "detailed",
  "title": "Reporte de Análisis Genómico",
  "imageIds": ["uuid1", "uuid2"],
  "includeAllImages": false
}
```

### **🧠 Memoria del Usuario**

```http
GET /memory?limit=10&type=bindash
X-User-Id: usuario123
```

### **💬 Chat Contextual**

```http
POST /chat
Content-Type: application/json
X-User-Id: usuario123

{
  "message": "¿Qué puedes decirme sobre los resultados de BinDash?",
  "includeMemoryContext": true
}
```

## 🎨 **Integración Frontend**

### **Botones Automáticos en Visualizadores**

```javascript
// Se agregan automáticamente al mostrar un visualizador
showVisualizer('bindashVisualizer');  // Agrega botón específico para BinDash
```

### **Análisis Manual de Imágenes**

```javascript
// Analizar imágenes actuales en el contenedor
analyzeCurrentImages('annotation', panelElement);
```

### **Efectos Hover Sutiles**

```css
.drfungito-avatar:hover {
    transform: scale(1.1) rotate(5deg);
    box-shadow: 0 4px 15px rgba(34, 197, 94, 0.4);
}
```

## 🔬 **Tipos de Análisis Soportados**

### **1. General** (`general`)
- Detección automática del tipo de gráfico
- Interpretación biológica general
- Recomendaciones básicas

### **2. BinDash** (`bindash`)
- Análisis de matrices de distancias genómicas
- Interpretación de dendrogramas filogenéticos
- Evaluación de ANI (Average Nucleotide Identity)
- Identificación de clusters taxonómicos

### **3. Anotaciones** (`annotation`)
- Análisis de categorías COG
- Interpretación de términos GO
- Evaluación de vías KEGG
- Análisis de familias PFAM

### **4. Control de Calidad** (`quality`)
- Evaluación de completitud genómica
- Detección de contaminación
- Análisis de métricas N50
- Recomendaciones de mejora

### **5. HMMER** (`hmmer`)
- Análisis de dominios proteicos
- Interpretación de E-values
- Cobertura de secuencias
- Familias funcionales

## 📊 **Tipos de Reportes**

### **Detallado** (`detailed`)
```markdown
# Reporte de Análisis Genómico

## 1. Resumen Ejecutivo
- Principales hallazgos

## 2. Análisis Individual
- Interpretación por gráfico

## 3. Análisis Comparativo
- Relaciones entre resultados

## 4. Interpretación Biológica
- Significado para genómica fúngica

## 5. Recomendaciones
- Próximos pasos

## 6. Conclusiones
- Síntesis final
```

### **Resumen** (`summary`)
- Extracto ejecutivo conciso
- Principales métricas
- Conclusiones clave

### **Comparativo** (`comparative`)
- Análisis lado a lado
- Diferencias significativas
- Correlaciones encontradas

## 🔒 **Seguridad**

### **Rate Limiting**
- 100 requests por 15 minutos por IP
- Protección contra abuso de API

### **Validación de Imágenes**
- Tipos de archivo permitidos
- Tamaño máximo configurable
- Sanitización automática

### **Headers de Seguridad**
```javascript
helmet({
    contentSecurityPolicy: true,
    crossOriginEmbedderPolicy: false
})
```

## 📝 **Logging**

### **Niveles de Log**
- `error`: Errores críticos
- `warn`: Advertencias
- `info`: Información general
- `debug`: Depuración detallada

### **Archivos de Log**
```
logs/
├── error.log     # Solo errores
└── combined.log  # Todos los eventos
```

## 🐛 **Troubleshooting**

### **Error: API Key no configurada**
```bash
⚠️  ADVERTENCIA: ANTHROPIC_API_KEY no configurada
```
**Solución:** Configurar variable de entorno `ANTHROPIC_API_KEY`

### **Error: MongoDB no accesible**
```bash
MongooseError: Connection failed
```
**Solución:** Verificar `MONGODB_URI` y estado de MongoDB

### **Error: Imagen demasiado grande**
```json
{"error": "Archivo excede el tamaño máximo permitido"}
```
**Solución:** Reducir tamaño de imagen o ajustar `MAX_IMAGE_SIZE`

### **Error: Formato no soportado**
```json
{"error": "Tipo de archivo no permitido"}
```
**Solución:** Usar formatos: JPEG, PNG, GIF, WebP

## 🔄 **Health Checks**

```bash
# Verificar estado del servicio
curl http://localhost:4009/health

# Respuesta esperada
{
  "status": "healthy",
  "service": "Dr. Fungito AI Agent",
  "timestamp": "2025-01-09T10:30:00Z",
  "version": "1.0.0"
}
```

## 🚀 **Deployment**

### **Variables de Entorno Producción**
```bash
NODE_ENV=production
ANTHROPIC_API_KEY=sk-ant-api03-...
MONGODB_URI=mongodb://user:pass@cluster.mongodb.net/fungigt
FRONTEND_URL=https://fungigt.com
LOG_LEVEL=info
```

### **Monitoreo**
```bash
# Logs en tiempo real
docker logs -f fungigt-drfungito-agent

# Métricas de memoria
docker stats fungigt-drfungito-agent
```

## 🤝 **Contribuir**

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 **Licencia**

MIT License - Ver archivo `LICENSE` para detalles.

## 📞 **Soporte**

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/fungigt/issues)
- **Documentación**: [Wiki del Proyecto](https://github.com/tu-usuario/fungigt/wiki)
- **Email**: soporte@fungigt.com

---

**🍄 Dr. Fungito** - *Tu especialista en genómica fúngica impulsado por IA* 