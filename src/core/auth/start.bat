@echo off
echo ======================================
echo = Iniciando Servicio de Autenticacion =
echo ======================================

:: Configurar entorno
set AUTH_PORT=4001
set JWT_SECRET=fungi-gt-secret-key-2024-super-secure
set JWT_EXPIRATION=24h

:: Inicializar la base de datos
echo Inicializando la base de datos...
node scripts/init.js

:: Iniciar el servicio
echo Iniciando el servicio de autenticacion...
node index.js

pause 