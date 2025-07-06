# 🍄 Dr. Fungito AI Agent - Versión 2.0

Dr. Fungito es un agente de inteligencia artificial especializado en análisis genómico de hongos con capacidades avanzadas de análisis de imágenes, memoria contextual y generación de reportes PDF.

## 🚀 Nuevas Características v2.0

### 🧠 Memoria Contextual con LangChain
- **Chat inteligente**: Mantiene memoria de conversaciones anteriores
- **Contexto de imágenes**: Relaciona automáticamente las imágenes analizadas con las conversaciones
- **Respuestas personalizadas**: Utiliza el historial del usuario para proporcionar respuestas más precisas

### 📄 Generación de Reportes PDF
- **Reportes profesionales**: Genera documentos PDF con formato profesional
- **Imágenes incluidas**: Cada reporte incluye las imágenes analizadas con sus interpretaciones
- **Múltiples tipos**: Reportes detallados, resúmenes ejecutivos y análisis comparativos
- **Descarga directa**: Los reportes se pueden descargar directamente desde el chat

### 🔗 Integración Mejorada con Visualizadores
- **Análisis directo**: Los visualizadores pueden enviar imágenes directamente al Dr. Fungito
- **Botones especializados**: Botones "Enviar a Dr. Fungito" en cada visualizador
- **Análisis específico**: Análisis especializados para BinDash, eggNOG, CheckM, etc.

## 🛠️ Instalación y Configuración

### Requisitos
- Node.js >= 18.0.0
- MongoDB
- Clave API de Anthropic
- Puppeteer para generación de PDF

### Instalación de Dependencias
```bash
npm install
```

### Variables de Entorno
```bash
# Clave API de Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# MongoDB
MONGODB_URI=mongodb://admin:admin123@localhost:27017/fungigt?authSource=admin

# Puerto del servidor
PORT=4009

# URL del frontend
FRONTEND_URL=http://localhost:4005
```

## 🔧 Uso del API

### Análisis de Imágenes
```bash
# Subir y analizar imagen
POST /analyze-image
Content-Type: multipart/form-data
X-User-Id: user_id

{
  "image": <file>,
  "analysisType": "bindash|eggnog|checkm|general",
  "userContext": "Contexto opcional",
  "saveToMemory": true
}
```

### Análisis desde Visualizadores
```bash
# Enviar imagen desde visualizador
POST /analyze-from-visualizer
Content-Type: application/json
X-User-Id: user_id

{
  "imageUrl": "http://localhost:4003/visualization/image.png",
  "analysisType": "bindash",
  "filename": "matriz_distancias.png",
  "userContext": "Análisis de similaridad genómica"
}
```

### Generación de Reportes PDF
```bash
# Generar reporte con PDF
POST /generate-report
Content-Type: application/json
X-User-Id: user_id

{
  "reportType": "detailed|summary|comparative",
  "title": "Reporte de Análisis Genómico",
  "includeAllImages": false,
  "generatePDF": true,
  "imageIds": ["id1", "id2"]
}
```

### Chat con Memoria Contextual
```bash
# Chat con Dr. Fungito
POST /chat
Content-Type: application/json
X-User-Id: user_id

{
  "message": "¿Qué puedes decirme sobre los últimos análisis?",
  "includeMemoryContext": true
}
```

## 🌐 Integración con Frontend

### Función Global para Visualizadores
```javascript
// Enviar imagen al Dr. Fungito desde cualquier visualizador
window.sendImageToDrFungito(imageUrl, analysisType, filename);

// Ejemplo de uso
window.sendImageToDrFungito(
  'http://localhost:4003/visualization/bindash.png',
  'bindash',
  'matriz_distancias_bindash.png'
);
```

### Botones en Visualizadores
```html
<!-- Botón para enviar al Dr. Fungito -->
<button onclick="sendImageToDrFungito(chartImageUrl, 'bindash', 'bindash_analysis.png')" 
        class="btn btn-success">
    🍄 Enviar a Dr. Fungito
</button>
```

## 📊 Tipos de Análisis Especializados

### BinDash
- Análisis de matrices de distancia genómica
- Interpretación de valores ANI
- Identificación de clusters y outliers
- Recomendaciones taxonómicas

### eggNOG
- Análisis de anotaciones funcionales
- Categorías COG, GO, KEGG
- Patrones metabólicos específicos de hongos
- Genes de interés (metabolismo secundario)

### CheckM
- Evaluación de completitud genómica
- Detección de contaminación
- Calidad del ensamblaje
- Estándares específicos para hongos

### DNA Features
- Visualización de características de ADN/ARN
- Análisis de regiones codificantes
- Identificación de elementos regulatorios

## 📁 Estructura de Archivos

```
drfungito/
├── server.js           # Servidor principal
├── package.json        # Dependencias
├── config.example.js   # Configuración de ejemplo
├── data/
│   ├── reports/        # Reportes PDF generados
│   └── temp/           # Archivos temporales
├── logs/
│   ├── error.log       # Logs de errores
│   └── combined.log    # Logs combinados
└── README.md          # Este archivo
```

## 🧪 Endpoints del API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado del servicio |
| `/info` | GET | Información del agente |
| `/analyze-image` | POST | Análisis de imagen subida |
| `/analyze-from-visualizer` | POST | Análisis desde visualizador |
| `/memory` | GET | Obtener memoria del usuario |
| `/generate-report` | POST | Generar reporte PDF |
| `/download-report/:id` | GET | Descargar reporte PDF |
| `/chat` | POST | Chat con memoria contextual |
| `/chat-history` | GET | Historial de conversaciones |

## 🔍 Monitoreo y Logs

### Logs Disponibles
- `logs/error.log` - Errores del sistema
- `logs/combined.log` - Todos los eventos
- Consola - Logs en tiempo real

### Health Check
```bash
curl http://localhost:4009/health
```

## 🎯 Casos de Uso

### 1. Análisis Automático de Resultados
```bash
# El usuario ejecuta análisis BinDash
# El visualizador genera un gráfico
# El usuario hace clic en "Enviar a Dr. Fungito"
# Dr. Fungito analiza automáticamente la imagen
# El análisis se guarda en memoria contextual
```

### 2. Generación de Reportes Inteligentes
```bash
# Dr. Fungito tiene varias imágenes analizadas
# El usuario solicita un reporte
# Se genera un PDF con todas las imágenes y análisis
# El reporte se puede descargar directamente
```

### 3. Chat Contextual
```bash
# Usuario: "¿Qué opinas de los últimos análisis?"
# Dr. Fungito usa memoria contextual para responder
# Incluye información de imágenes analizadas recientemente
# Mantiene el contexto de la conversación
```

## 🛡️ Seguridad

- Autenticación por usuario con header `X-User-Id`
- Validación de tipos de archivo
- Límites de tamaño de imagen (10MB)
- Sanitización de entrada
- Logs de seguridad

## 📈 Rendimiento

- Imágenes optimizadas automáticamente
- Generación de PDF en segundo plano
- Memoria contextual limitada (20 conversaciones)
- Limpieza automática de archivos temporales

## 🔄 Actualizaciones

### Versión 2.0 - Nuevas Características
- ✅ Memoria contextual con LangChain
- ✅ Generación de reportes PDF
- ✅ Integración mejorada con visualizadores
- ✅ Chat inteligente con historial
- ✅ Análisis especializado por tipo de dato

### Próximas Características
- 🔄 Análisis de múltiples imágenes simultáneamente
- 🔄 Exportación de reportes en múltiples formatos
- 🔄 Integración con bases de datos externas
- 🔄 API REST completa para terceros

## 📞 Soporte

Para reportar bugs o solicitar funcionalidades:
- Crear un issue en el repositorio
- Enviar logs relevantes
- Incluir pasos para reproducir el problema

---

🍄 **Dr. Fungito AI Agent v2.0** - Análisis genómico inteligente con memoria contextual y generación de reportes PDF. 