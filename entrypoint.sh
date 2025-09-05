#!/bin/sh

# Establece las variables de entorno necesarias para Flask
export FLASK_APP=app

# La ruta a la base de datos dentro del contenedor
DB_PATH_IN_CONTAINER="$DATA_DIR/ccsp_data.db"

# Espera un momento para asegurar que el volumen se haya montado correctamente
sleep 2

# Revisa si el archivo de la base de datos NO existe
if [ ! -f "$DB_PATH_IN_CONTAINER" ]; then
    echo ">> La base de datos no existe. Inicializando por primera vez..."
    flask init-db
    echo ">> Base de datos creada. Cargando productos desde el CSV..."
    flask load-products
    echo ">> Productos cargados."
else
    echo ">> La base de datos ya existe. Omitiendo inicialización."
fi

# Inicia la aplicación Flask para que sea accesible desde fuera del contenedor
echo ">> Iniciando servidor de la aplicación..."
exec flask run --host=0.0.0.0 --port=5000