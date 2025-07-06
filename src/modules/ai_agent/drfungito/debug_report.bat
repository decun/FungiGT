@echo off
echo 🔧 Debug del Sistema de Reportes - FungiGT
echo.

set DR_FUNGITO_URL=http://localhost:4009
set USER_ID=anonymous

echo 1. Verificando conexión con Dr. Fungito...
curl -s --connect-timeout 5 %DR_FUNGITO_URL%/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Dr. Fungito no está disponible en %DR_FUNGITO_URL%
    echo    Asegúrate de que el servicio esté ejecutándose
    pause
    exit /b 1
)
echo ✅ Dr. Fungito está disponible

echo.
echo 2. Obteniendo lista de reportes...
curl -s -H "X-User-Id: %USER_ID%" %DR_FUNGITO_URL%/debug/reports > temp_reports.json
if %errorlevel% neq 0 (
    echo ❌ Error al obtener reportes
    pause
    exit /b 1
)

echo ✅ Reportes obtenidos, guardados en temp_reports.json

echo.
echo 3. Contenido del archivo de debug:
type temp_reports.json
echo.

echo 4. Para debugear un reporte específico, usa:
echo    curl -H "X-User-Id: %USER_ID%" %DR_FUNGITO_URL%/debug/report/ID_DEL_REPORTE
echo.

echo 5. Para probar descarga HEAD:
echo    curl -I -H "X-User-Id: %USER_ID%" %DR_FUNGITO_URL%/download-report/ID_DEL_REPORTE
echo.

echo 6. Para probar descarga GET:
echo    curl -H "X-User-Id: %USER_ID%" %DR_FUNGITO_URL%/download-report/ID_DEL_REPORTE -o reporte.pdf
echo.

echo 💡 Instrucciones:
echo    1. Copia el ID del reporte problemático desde temp_reports.json
echo    2. Ejecuta los comandos curl de arriba reemplazando ID_DEL_REPORTE
echo    3. Revisa los logs del servidor para más detalles
echo.

pause
del temp_reports.json >nul 2>&1 