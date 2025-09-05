import os
import csv
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# --- Configuración Inicial ---

# Directorio para los datos persistentes. Usará la variable de entorno DATA_DIR
# si está definida, de lo contrario usará una carpeta 'data' local.
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data'))

# Asegurarse de que el directorio de datos exista
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
# Configura la ruta de la base de datos para que apunte al directorio de datos
db_path = os.path.join(DATA_DIR, 'ccsp_data.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa la extensión de la base de datos
db = SQLAlchemy(app)

# --- Modelos de la Base de Datos ---

# Modelo para los Clientes
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Cliente {self.name}>'

# Modelo para los Productos de Red Hat
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(300), nullable=False)
    term = db.Column(db.String(50))
    unit_of_measure = db.Column(db.String(50))
    list_price = db.Column(db.Float)

    def __repr__(self):
        return f'<Producto {self.sku}>'

# Modelo para el registro de consumo mensual
class Consumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False)  # Formato: YYYY-MM
    quantity = db.Column(db.Integer, nullable=False)
    
    # Relaciones con otras tablas
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    # Propiedades para acceder fácilmente a los objetos relacionados
    client = db.relationship('Client', backref=db.backref('consumptions', lazy=True))
    product = db.relationship('Product', backref=db.backref('consumptions', lazy=True))

    def __repr__(self):
        return f'{self.client.name} - {self.product.sku} - {self.month}: {self.quantity}'

# --- Rutas de la Aplicación (Páginas Web) ---

@app.route('/')
def index():
    # Página principal que muestra los últimos 5 registros de consumo
    latest_consumptions = Consumption.query.order_by(Consumption.id.desc()).limit(5).all()
    return render_template('index.html', consumptions=latest_consumptions)

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
        # Lógica para agregar un nuevo cliente
        client_name = request.form['client_name']
        if client_name:
            new_client = Client(name=client_name)
            db.session.add(new_client)
            db.session.commit()
        return redirect(url_for('clients'))

    all_clients = Client.query.all()
    return render_template('clients.html', clients=all_clients)

@app.route('/products')
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)
    
@app.route('/consumption', methods=['GET', 'POST'])
def consumption():
    if request.method == 'POST':
        # Lógica para agregar un nuevo registro de consumo
        client_id = request.form['client_id']
        product_id = request.form['product_id']
        month = request.form['month']
        quantity = request.form['quantity']
        
        new_consumption = Consumption(
            client_id=client_id,
            product_id=product_id,
            month=month,
            quantity=quantity
        )
        db.session.add(new_consumption)
        db.session.commit()
        return redirect(url_for('index'))
        
    # Enviamos la lista de clientes y productos al formulario
    all_clients = Client.query.all()
    all_products = Product.query.all()
    return render_template('consumption.html', clients=all_clients, products=all_products)


# --- Comandos especiales para la línea de comandos ---
@app.cli.command('init-db')
def init_db_command():
    """Crea las tablas de la base de datos."""
    db.create_all()
    print('Base de datos inicializada.')

@app.cli.command('load-products')
def load_products_command():
    """Carga los productos desde el archivo CSV a la base de datos."""
    file_path = 'CCSP - Direct LATAM USD Q4 2025 - SPBP.csv'
    try:
        with open(file_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                # Verificamos si el producto ya existe por su SKU
                exists = Product.query.filter_by(sku=row['SKU']).first()
                if not exists:
                    product = Product(
                        sku=row['SKU'],
                        description=row['SKU Description'],
                        term=row['Term'],
                        unit_of_measure=row['Unit of Measure'],
                        list_price=float(row['List Price'])
                    )
                    db.session.add(product)
            db.session.commit()
            print(f'Productos cargados exitosamente desde {file_path}')
    except FileNotFoundError:
        print(f'Error: No se encontró el archivo {file_path}. Asegúrate de que está en la misma carpeta.')
    except Exception as e:
        print(f'Ocurrió un error: {e}')