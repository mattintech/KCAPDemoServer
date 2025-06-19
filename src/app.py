from flask import Flask, jsonify, request, send_file, render_template, flash, Response, redirect
import os
import base64
import database
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import shutil
from werkzeug.routing import BaseConverter

app = Flask(__name__)
# Set DATA_FOLDER to the absolute path of the data directory inside src
app.config['DATA_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data')
app.config['SECRET_KEY'] = 'dev-key-for-demo-only'

# Custom converter for tenant IDs
class TenantConverter(BaseConverter):
    regex = '[a-zA-Z0-9_-]+'

app.url_map.converters['tenant'] = TenantConverter

# Load product data from database
def load_products(tenant_id=None):
    return database.get_all_products(tenant_id)

@app.route('/')
def index():
    # Show a tenant selection page or redirect to default
    tenants = database.get_all_tenants()
    return render_template('tenant_selection.html', tenants=tenants)

@app.route('/tenant/<tenant:tenant_id>/delete', methods=['POST'])
def delete_tenant(tenant_id):
    """Delete a tenant and all its data"""
    database.delete_tenant(tenant_id)
    flash(f'Tenant "{tenant_id}" has been deleted successfully.', 'success')
    return redirect('/')

@app.route('/<tenant:tenant_id>/')
def tenant_index(tenant_id):
    # Auto-create tenant if it doesn't exist
    tenant = database.get_or_create_tenant(tenant_id)
    if tenant is None:
        # Reserved tenant ID or invalid
        return jsonify({"error": f"'{tenant_id}' is a reserved name and cannot be used as a tenant ID"}), 404
    return render_template('index.html', tenant=tenant)

def check_basic_auth(auth_header, tenant_id):
    """Validate Basic authentication credentials for a tenant"""
    if not auth_header or not auth_header.startswith('Basic '):
        return False
    
    try:
        # Decode the base64 credentials
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        
        # Get tenant credentials from database
        tenant = database.get_or_create_tenant(tenant_id)
        if tenant and username == tenant['username'] and password == tenant['password']:
            return True
    except Exception:
        pass
    
    return False

@app.route('/<tenant:tenant_id>/login', methods=['GET'])
def login(tenant_id):
    auth_header = request.headers.get('Authorization')
    
    if check_basic_auth(auth_header, tenant_id):
        return jsonify({"status": "success", "message": "Authentication successful"}), 200
    
    return jsonify({"error": "Unauthorized"}), 401

@app.route('/<tenant:tenant_id>/arcontentfields', methods=['GET'])
def get_ar_content_fields(tenant_id):
    # Return a fixed set of attributes (tenant_id could be used for custom fields in the future)
    fields = [
        {"fieldName": "_id", "label": "Item ID", "editable": "false", "fieldType": "TEXT"},
        {"fieldName": "_price", "label": "Sale Price", "editable": "true", "fieldType": "TEXT"},
        {"fieldName": "_image", "label": "Image", "editable": "false", "fieldType": "IMAGE_URI"}
    ]
    return jsonify(fields), 200

@app.route('/<tenant:tenant_id>/arinfo', methods=['GET'])
def get_ar_info(tenant_id):
    barcode = request.args.get('barcode')
    products = load_products(tenant_id)
    
    # Helper function to convert relative image paths to absolute URLs
    def make_absolute_urls(product_fields):
        # Create absolute URL for image fields
        for field in product_fields:
            if field['fieldName'] == '_image' and field['value']:
                # If it's already an absolute URL, leave it as is
                if not field['value'].startswith('http'):
                    # Build absolute URL using request host with tenant
                    field['value'] = f"{request.url_root.rstrip('/')}/{tenant_id}{field['value']}"
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

@app.route('/<tenant:tenant_id>/images/<path:filename>', methods=['GET'])
def serve_image(tenant_id, filename):
    # Log the request for debugging
    app.logger.info(f"Image requested for tenant {tenant_id}: {filename}")
    
    # Extract product ID from filename (e.g., "123456.jpg" -> "123456")
    product_id = os.path.splitext(filename)[0]
    
    # Get image from database for this tenant
    image_data = database.get_product_image(product_id, tenant_id)
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

@app.route('/<tenant:tenant_id>/barcodes/<path:filename>', methods=['GET'])
def serve_barcode(tenant_id, filename):
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
            # Generate QR code with tenant in URL
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f'http://{request.host}/{tenant_id}/arinfo?barcode={product_id}')
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

# Import the admin routes directly and register them with tenant support
from routes.admin import (index as admin_index, add_product, edit_product, 
                         delete_product, view_product, generate_barcode, 
                         generate_barcode_page, manage_credentials)

# Register admin routes with tenant prefix
app.add_url_rule('/<tenant:tenant_id>/admin/', 'admin.index', admin_index)
app.add_url_rule('/<tenant:tenant_id>/admin/add', 'admin.add_product', add_product, methods=['GET', 'POST'])
app.add_url_rule('/<tenant:tenant_id>/admin/edit/<product_id>', 'admin.edit_product', edit_product, methods=['GET', 'POST'])
app.add_url_rule('/<tenant:tenant_id>/admin/delete/<product_id>', 'admin.delete_product', delete_product, methods=['POST'])
app.add_url_rule('/<tenant:tenant_id>/admin/view/<product_id>', 'admin.view_product', view_product)
app.add_url_rule('/<tenant:tenant_id>/admin/generate_barcode/<product_id>/<code_type>', 'admin.generate_barcode', generate_barcode)
app.add_url_rule('/<tenant:tenant_id>/admin/generate_barcode_page/<product_id>', 'admin.generate_barcode_page', generate_barcode_page)
app.add_url_rule('/<tenant:tenant_id>/admin/credentials', 'admin.manage_credentials', manage_credentials, methods=['GET', 'POST'])

# Register API routes with tenant prefix
from routes.api import api_index
app.add_url_rule('/<tenant:tenant_id>/api/', 'api.api_index', api_index)

# Catch-all route for admin without tenant - redirect to home
@app.route('/admin/')
@app.route('/admin/<path:path>')
def redirect_admin_to_home(path=None):
    return redirect('/')

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
    
    # Clean up any accidentally created reserved tenants
    deleted_count = database.cleanup_reserved_tenants()
    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} reserved tenant(s)")
    
    app.run(port=5555, host="0.0.0.0", debug=True)
