# 🔧 Guía de Debug para Reportes - Dr. Fungito AI

## Problema Resuelto

**Síntoma**: Aparece el mensaje "⚠️ Advertencia de descarga: El reporte fue generado pero puede haber problemas con la descarga" en el chat.

**Solución**: Hemos implementado un sistema completo de debug para identificar y resolver estos problemas.

## Herramientas de Debug Disponibles

### 1. 💬 Comandos en el Chat

En el chat de Dr. Fungito, puedes usar:

- `debug reportes` - Ver todos los reportes disponibles
- `debug cd57000a-5dd8-4a6a-9dff-0584bba7c75b` - Debug específico de un reporte por ID
- `debug` - Ver ayuda de comandos disponibles

### 2. 🖥️ Scripts de PowerShell

**Uso básico:**
```powershell
.\debug_report.ps1
```

**Debug de reporte específico:**
```powershell
.\debug_report.ps1 -ReportId "cd57000a-5dd8-4a6a-9dff-0584bba7c75b"
```

**Con usuario específico:**
```powershell
.\debug_report.ps1 -UserID "mi_usuario" -ReportId "cd57000a-5dd8-4a6a-9dff-0584bba7c75b"
```

### 3. 🌐 Endpoints de API

**Debug general:**
```bash
curl -H "X-User-Id: anonymous" http://localhost:4009/debug/reports
```

**Debug específico:**
```bash
curl -H "X-User-Id: anonymous" http://localhost:4009/debug/report/REPORT_ID
```

**Verificar descarga HEAD:**
```bash
curl -I -H "X-User-Id: anonymous" http://localhost:4009/download-report/REPORT_ID
```

**Probar descarga:**
```bash
curl -H "X-User-Id: anonymous" http://localhost:4009/download-report/REPORT_ID -o reporte.pdf
```

## Información de Debug

El sistema proporciona la siguiente información:

### 📊 Datos del Reporte
- **ID del reporte**
- **Título y tipo**
- **Número de imágenes**
- **Tipos de análisis incluidos**
- **Fecha de creación**
- **Número de descargas**

### 🔍 Estado del PDF
- **Ruta del archivo en el servidor**
- **Si el archivo existe físicamente**
- **Tamaño del archivo**
- **Fecha de última modificación**

### 🌐 Pruebas de Conectividad
- **Status de petición HEAD**
- **Status de petición GET**
- **Verificación de headers HTTP**

## Problemas Comunes y Soluciones

### ❌ "PDF no existe"
**Causa**: El archivo PDF fue eliminado del servidor
**Solución**: Generar un nuevo reporte

### ❌ "Reporte no encontrado"
**Causa**: El reporte no existe en la memoria del usuario
**Solución**: 
1. Verificar el ID del reporte
2. Usar `debug reportes` para ver IDs disponibles
3. Si no hay reportes, generar uno nuevo

### ❌ "Error 404 en descarga"
**Causa**: Problema con el endpoint o el archivo
**Solución**: 
1. Usar debug específico para verificar el estado
2. Revisar logs del servidor
3. Regenerar el reporte si es necesario

### ❌ "Error de conectividad"
**Causa**: Dr. Fungito no está ejecutándose
**Solución**: 
1. Verificar que el servicio esté en puerto 4009
2. Revisar logs del contenedor Docker
3. Reiniciar el servicio si es necesario

## Logs del Servidor

Los logs de Dr. Fungito incluyen información detallada:

```
🍄 [DOWNLOAD] Solicitud de descarga para reporte: REPORT_ID
🍄 [DOWNLOAD] Archivo PDF encontrado: /path/to/pdf
🍄 [DOWNLOAD] Descarga completada exitosamente: REPORT_ID
```

Para ver logs en tiempo real:
```bash
docker logs -f fungigt-ai-agent
```

## Mantenimiento

### Limpiar Reportes Obsoletos
```bash
curl -X POST -H "Content-Type: application/json" http://localhost:4009/admin/cleanup-reports -d '{"daysOld": 7}'
```

### Reparar Base de Datos
```bash
curl -X POST http://localhost:4009/admin/fix-database
```

### Limpiar Completamente
```bash
curl -X POST http://localhost:4009/admin/clean-database
```

## Contacto

Si los problemas persisten después de usar estas herramientas de debug, revisa:

1. **Logs del servidor** para errores específicos
2. **Estado del contenedor Docker** 
3. **Espacio en disco** para archivos PDF
4. **Configuración de MongoDB** para la memoria de usuario

La implementación de este sistema de debug debería eliminar completamente las advertencias de descarga problemáticas y proporcionar información clara sobre cualquier problema real que pueda existir. 