@echo off
echo =========================================
echo    ARREGLANDO ERROR RST_STREAM DOCKER
echo =========================================

echo.
echo [1/6] Parando todos los contenedores de FungiGT...
docker-compose down --remove-orphans

echo.
echo [2/6] Limpiando imagenes corruptas...
docker image prune -f
docker builder prune -f

echo.
echo [3/6] Eliminando volúmenes temporales...
docker volume prune -f

echo.
echo [4/6] Limpiando cache de construcción...
docker system prune -f

echo.
echo [5/6] Eliminando imagen específica del file-manager...
docker rmi fungigt-file-manager:latest 2>nul
docker rmi fungigt-file-manager 2>nul

echo.
echo [6/6] Reconstruyendo file-manager desde cero...
docker-compose build --no-cache file-manager

echo.
echo =========================================
echo   LIMPIEZA COMPLETADA - INICIANDO...
echo =========================================

echo.
echo Iniciando file-manager...
docker-compose up -d file-manager

echo.
echo Verificando estado...
timeout /t 10 /nobreak >nul
docker-compose ps file-manager

echo.
echo Mostrando logs...
docker-compose logs file-manager

echo.
echo =========================================
echo          SCRIPT COMPLETADO
echo =========================================
echo.
echo Verifica el servicio en:
echo http://localhost:4002
echo http://localhost:4002/health
echo. 