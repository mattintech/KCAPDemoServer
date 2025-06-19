from flask import Flask, jsonify, request, send_file, render_template, flash, Response
import os
import base64
from routes.admin import admin_bp
from routes.api import api_bp
import database
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import shutil

app = Flask(__name__)
# Set DATA_FOLDER to the absolute path of the data directory inside src
app.config['DATA_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data')
app.config['SECRET_KEY'] = 'dev-key-for-demo-only'

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)

# Load product data from database
def load_products():
    return database.get_all_products()

@app.route('/')
def index():
    return render_template('index.html')

def check_basic_auth(auth_header):
    """Validate Basic authentication credentials"""
    if not auth_header or not auth_header.startswith('Basic '):
        return False
    
    try:
        # Decode the base64 credentials
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        
        # Simple hardcoded credentials - in production, use secure storage
        # You can change these credentials as needed
        if username == 'admin' and password == 'knox123':
            return True
    except Exception:
        pass
    
    return False

@app.route('/login', methods=['GET'])
def login():
    auth_header = request.headers.get('Authorization')
    
    if check_basic_auth(auth_header):
        return jsonify({"status": "success", "message": "Authentication successful"}), 200
    
    return jsonify({"error": "Unauthorized"}), 401

@app.route('/arcontentfields', methods=['GET'])
def get_ar_content_fields():
    # Return a fixed set of attributes
    fields = [
        {"fieldName": "_id", "label": "Item ID", "editable": "false", "fieldType": "TEXT"},
        {"fieldName": "_price", "label": "Sale Price", "editable": "true", "fieldType": "TEXT"},
        {"fieldName": "_image", "label": "Image", "editable": "false", "fieldType": "IMAGE_URI"}
    ]
    return jsonify(fields), 200

@app.route('/arinfo', methods=['GET'])
def get_ar_info():
    barcode = request.args.get('barcode')
    products = load_products()
    
    # Helper function to convert relative image paths to absolute URLs
    def make_absolute_urls(product_fields):
        # Create absolute URL for image fields
        for field in product_fields:
            if field['fieldName'] == '_image' and field['value']:
                # If it's already an absolute URL, leave it as is
                if not field['value'].startswith('http'):
                    # Build absolute URL using request host
                    field['value'] = f"{request.url_root.rstrip('/')}{field['value']}"
        return product_fields
    
    # If barcode is provided, return specific product
    if barcode:
        if barcode in products:
            product_data = make_absolute_urls(products[barcode])
            response = jsonify(product_data)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 200
        return jsonify({"error": "Product not found"}), 404
    
    # Return all products if no barcode specified
    # Convert all products to have absolute URLs
    all_products = {}
    for product_id, fields in products.items():
        all_products[product_id] = make_absolute_urls(fields)
    response = jsonify(all_products)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response, 200

@app.route('/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    # Log the request for debugging
    app.logger.info(f"Image requested: {filename}")
    
    # Extract product ID from filename (e.g., "123456.jpg" -> "123456")
    product_id = os.path.splitext(filename)[0]
    
    # Get image from database
    image_data = database.get_product_image(product_id)
    if image_data:
        image_bytes, mime_type = image_data
        response = Response(image_bytes, mimetype=mime_type)
        # Add CORS headers to allow cross-origin requests
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        app.logger.info(f"Serving image from database: {product_id} ({len(image_bytes)} bytes)")
        return response
    
    # Fallback to file system for backward compatibility
    image_path = os.path.join(app.config['DATA_FOLDER'], 'images', filename)
    if os.path.exists(image_path):
        app.logger.info(f"Serving image from filesystem: {image_path}")
        response = send_file(image_path)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    app.logger.warning(f"Image not found: {filename}")
    return jsonify({"error": "Image not found"}), 404

@app.route('/barcodes/<path:filename>', methods=['GET'])
def serve_barcode(filename):
    # Parse filename to extract product_id and barcode type
    # Expected format: {product_id}_{type}.png
    name_parts = os.path.splitext(filename)[0].split('_')
    if len(name_parts) < 2:
        return jsonify({"error": "Invalid barcode filename format"}), 400
    
    product_id = '_'.join(name_parts[:-1])  # Handle product IDs with underscores
    code_type = name_parts[-1].lower()
    
    # Generate barcode dynamically
    try:
        buffer = BytesIO()
        
        if code_type == 'qr':
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f'http://{request.host}/arinfo?barcode={product_id}')
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(buffer, format='PNG')
        
        elif code_type == 'ean13':
            # Generate EAN-13 barcode
            # Convert product_id to numeric format if needed
            numeric_id = ''.join(filter(str.isdigit, product_id))
            if not numeric_id:
                numeric_id = str(abs(hash(product_id)) % 1000000000000)[:12]
            else:
                numeric_id = numeric_id[:12].zfill(12)
            
            EAN = barcode.get_barcode_class('ean13')
            ean = EAN(numeric_id, writer=ImageWriter())
            ean.write(buffer)
        
        elif code_type == 'code128':
            # Generate Code 128 barcode
            CODE128 = barcode.get_barcode_class('code128')
            code = CODE128(product_id, writer=ImageWriter())
            code.write(buffer)
        
        else:
            return jsonify({"error": "Unsupported barcode type"}), 400
        
        buffer.seek(0)
        return Response(buffer.getvalue(), mimetype='image/png')
    
    except Exception as e:
        app.logger.error(f"Barcode generation error: {str(e)}")
        return jsonify({"error": "Failed to generate barcode"}), 500

if __name__ == '__main__':
    # Initialize database
    database.init_database()
    
    # Migrate existing data from JSON if needed
    products_file = os.path.join(app.config['DATA_FOLDER'], 'products.json')
    if os.path.exists(products_file):
        print("Migrating data from products.json to SQLite...")
        database.migrate_from_json()
        # Optionally rename the JSON file to indicate it's been migrated
        shutil.move(products_file, products_file + '.migrated')
        print("Migration complete.")
    
    app.run(port=5555, host="0.0.0.0", debug=True)
