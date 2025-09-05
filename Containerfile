# Paso 1: Usar una imagen base oficial de Python
FROM python:3.11-slim

# Paso 2: Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Paso 3: Copiar el archivo de requisitos e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Paso 4: Copiar todos los archivos de la aplicación al contenedor
COPY . .

# Paso 5: Exponer el puerto en el que correrá la aplicación
EXPOSE 5000

# Paso 6: Ejecutar el script de inicio cuando el contenedor arranque
ENTRYPOINT ["/app/entrypoint.sh"]