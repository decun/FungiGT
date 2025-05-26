FROM python:3.9-slim

WORKDIR /app

# Copiar los requerimientos
COPY src/modules/visualization/requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY src/modules/visualization ./

# Comando para iniciar el servicio
CMD ["python", "app.py"] 