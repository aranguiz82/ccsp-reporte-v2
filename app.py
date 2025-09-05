import os
import csv
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# --- Configuración Inicial ---
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data'))
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
db_path = os.path.join(DATA_DIR, 'ccsp_data.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Modelos de la Base de Datos ---

# NUEVO: Tabla de asociación para la relación muchos a muchos entre Servicio y Cliente
service_clients = db.Table('service_clients',
    db.Column('service_id', db.Integer, db.ForeignKey('service.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('client.id'), primary_key=True)
)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Cliente {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(300), nullable=False)
    term = db.Column(db.String(50))
    unit_of_measure = db.Column(db.String(50))
    list_price = db.Column(db.Float)

    def __repr__(self):
        return f'<Producto {self.sku}>'

# NUEVO: Modelo para los Servicios
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    service_type = db.Column(db.String(100))
    # Relación muchos a muchos con Clientes
    clients = db.relationship('Client', secondary=service_clients, lazy='subquery',
        backref=db.backref('services', lazy=True))

    def __repr__(self):
        return f'<Servicio {self.name}>'

class Consumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    # NUEVO: Campo opcional para el servicio
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    
    client = db.relationship('Client', backref=db.backref('consumptions', lazy=True))
    product = db.relationship('Product', backref=db.backref('consumptions', lazy=True))
    # NUEVO: Relación con el servicio
    service = db.relationship('Service', backref=db.backref('consumptions', lazy=True))

    def __repr__(self):
        service_name = self.service.name if self.service else "N/A"
        return f'{self.client.name} - {self.product.sku} (Servicio: {service_name}) - {self.month}: {self.quantity}'

# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    latest_consumptions = Consumption.query.order_by(Consumption.id.desc()).limit(10).all()
    return render_template('index.html', consumptions=latest_consumptions)

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
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

# NUEVO: Ruta para crear y listar servicios
@app.route('/services', methods=['GET', 'POST'])
def services():
    if request.method == 'POST':
        service_name = request.form['service_name']
        service_type = request.form['service_type']
        if service_name:
            new_service = Service(name=service_name, service_type=service_type)
            db.session.add(new_service)
            db.session.commit()
        return redirect(url_for('services'))
    all_services = Service.query.all()
    return render_template('services.html', services=all_services)

# NUEVO: Ruta para asignar servicios a clientes
@app.route('/assign-service/<int:service_id>', methods=['GET', 'POST'])
def assign_service(service_id):
    service = Service.query.get_or_404(service_id)
    if request.method == 'POST':
        # Obtenemos la lista de IDs de los clientes seleccionados
        client_ids = request.form.getlist('client_ids')
        # Limpiamos las asignaciones anteriores
        service.clients.clear()
        # Asignamos los nuevos clientes
        for client_id in client_ids:
            client = Client.query.get(client_id)
            if client:
                service.clients.append(client)
        db.session.commit()
        return redirect(url_for('services'))
    
    all_clients = Client.query.all()
    return render_template('assign_service.html', service=service, clients=all_clients)

@app.route('/consumption', methods=['GET', 'POST'])
def consumption():
    if request.method == 'POST':
        try:
            # Obtenemos los datos del formulario
            client_id = request.form['client_id']
            product_id = request.form['product_id']
            month = request.form['month']
            quantity = request.form['quantity']
            service_id_str = request.form.get('service_id')

            # --- INICIO DE LA CORRECCIÓN ---
            # Convertimos las IDs y la cantidad a números enteros.
            # Para service_id, si el texto no está vacío, lo convertimos a número.
            # Si está vacío (el usuario eligió "Ninguno"), lo dejamos como None.
            final_service_id = int(service_id_str) if service_id_str else None

            new_consumption = Consumption(
                client_id=int(client_id),
                product_id=int(product_id),
                month=month,
                quantity=int(quantity),
                service_id=final_service_id
            )
            # --- FIN DE LA CORRECCIÓN ---
            
            db.session.add(new_consumption)
            db.session.commit()
            return redirect(url_for('index'))
        
        except Exception as e:
            # En caso de cualquier otro error, lo mostramos en la consola del contenedor
            # y devolvemos un mensaje más claro.
            db.session.rollback()
            print(f"Error al guardar el consumo: {e}")
            return "Ocurrió un error al procesar el formulario. Revisa los logs del contenedor.", 500

    # La lógica para la petición GET no cambia
    all_clients = Client.query.all()
    all_products = Product.query.all()
    all_services = Service.query.all()
    return render_template('consumption.html', clients=all_clients, products=all_products, services=all_services)

# --- Comandos CLI ---
@app.cli.command('init-db')
def init_db_command():
    """Crea o actualiza las tablas de la base de datos."""
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
        print(f'Error: No se encontró el archivo {file_path}.')
    except Exception as e:
        print(f'Ocurrió un error: {e}')