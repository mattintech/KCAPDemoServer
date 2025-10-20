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
from functools import wraps

app = Flask(__name__)
# Set DATA_FOLDER to the absolute path of the data directory inside src
app.config['DATA_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data')
app.config['SECRET_KEY'] = 'dev-key-for-demo-only'

# Custom converter for tenant IDs
class TenantConverter(BaseConverter):
    regex = '[a-zA-Z0-9_-]+'
    
    def to_python(self, value):
        # Convert to lowercase when parsing from URL
        return value.lower()
    
    def to_url(self, value):
        # Convert to lowercase when generating URLs
        return value.lower()

app.url_map.converters['tenant'] = TenantConverter

# Load product data from database
def load_products(tenant_id=None):
    return database.get_all_products(tenant_id)

@app.route('/')
def index():
    # Show a tenant selection page or redirect to default
    tenants = database.get_all_tenants()
    server_url = database.get_server_url()
    return render_template('tenant_selection.html', tenants=tenants, server_url=server_url)

@app.route('/tenant/<tenant:tenant_id>/delete', methods=['POST'])
def delete_tenant(tenant_id):
    """Delete a tenant and all its data"""
    database.delete_tenant(tenant_id)
    flash(f'Tenant "{tenant_id}" has been deleted successfully.', 'success')
    return redirect('/')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        server_url = request.form.get('server_url', '').strip()
        if server_url:
            # Remove trailing slash for consistency
            server_url = server_url.rstrip('/')
            database.set_setting('server_url', server_url)
            flash('Server settings updated successfully.', 'success')
        else:
            flash('Please provide a valid server URL.', 'error')
        return redirect('/settings')
    
    server_url = database.get_server_url()
    return render_template('settings.html', server_url=server_url)

@app.route('/<tenant:tenant_id>/')
def tenant_index(tenant_id):
    # Auto-create tenant if it doesn't exist
    tenant = database.get_or_create_tenant(tenant_id)
    if tenant is None:
        # Reserved tenant ID or invalid
        return jsonify({"error": f"'{tenant_id}' is a reserved name and cannot be used as a tenant ID"}), 404

    # Load products for this tenant
    products = load_products(tenant_id)
    custom_fields = database.get_custom_ar_fields(tenant_id)

    return render_template('index.html', tenant=tenant, products=products, custom_fields=custom_fields)

@app.route('/<tenant:tenant_id>/settings')
def tenant_settings(tenant_id):
    # Get tenant
    tenant = database.get_or_create_tenant(tenant_id)
    if tenant is None:
        return jsonify({"error": f"'{tenant_id}' is a reserved name and cannot be used as a tenant ID"}), 404
    
    # Get custom AR fields for this tenant
    custom_fields = database.get_custom_ar_fields(tenant_id)
    
    # Get server URL for API endpoint display
    server_url = database.get_server_url()
    
    return render_template('tenant_settings.html', tenant=tenant, custom_fields=custom_fields, server_url=server_url)

@app.route('/<tenant:tenant_id>/settings/credentials', methods=['POST'])
def update_tenant_credentials(tenant_id):
    # Get tenant
    tenant = database.get_tenant(tenant_id)
    if tenant is None:
        return jsonify({"error": "Tenant not found"}), 404

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username:
        flash('Username is required.', 'error')
        return redirect(f'/{tenant_id}/settings')

    # Update credentials
    database.update_tenant_credentials(tenant_id, username, password if password else None)

    flash('Credentials updated successfully.', 'success')
    return redirect(f'/{tenant_id}/settings')

@app.route('/<tenant:tenant_id>/settings/barcode', methods=['POST'])
def update_tenant_barcode_type(tenant_id):
    # Get tenant
    tenant = database.get_tenant(tenant_id)
    if tenant is None:
        return jsonify({"error": "Tenant not found"}), 404

    barcode_type = request.form.get('barcode_type', '').strip()

    if not barcode_type:
        flash('Barcode type is required.', 'error')
        return redirect(f'/{tenant_id}/settings')

    # Update barcode type
    database.update_tenant_barcode_type(tenant_id, barcode_type)

    flash('Barcode type updated successfully.', 'success')
    return redirect(f'/{tenant_id}/settings')

def check_basic_auth(auth_header, tenant_id):
    """Validate Basic authentication credentials for a tenant"""
    if not auth_header or not auth_header.startswith('Basic '):
        return False
    
    try:
        # Decode the base64 credentials
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        
        # Get tenant credentials from database (without creating)
        tenant = database.get_tenant(tenant_id)
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
    # Get custom fields defined for this tenant
    fields = database.get_custom_ar_fields(tenant_id)
    return jsonify(fields), 200

@app.route('/<tenant:tenant_id>/arinfo', methods=['GET', 'POST'])
def get_ar_info(tenant_id):
    barcode = request.args.get('barcode')
    products = load_products(tenant_id)

    # Get custom AR fields for this tenant
    custom_fields = database.get_custom_ar_fields(tenant_id)
    custom_field_names = [f['fieldName'] for f in custom_fields]

    # Handle POST request - update product fields
    if request.method == 'POST':
        if not barcode:
            return jsonify({"error": "Barcode parameter required"}), 400

        if barcode not in products:
            return jsonify({"error": "Product not found"}), 404

        try:
            # Get the updated fields from the request body
            updated_fields = request.get_json()

            if not isinstance(updated_fields, list):
                return jsonify({"error": "Request body must be an array of fields"}), 400

            # Get current product data
            current_product = products[barcode]

            # Update only the editable fields
            for updated_field in updated_fields:
                field_name = updated_field.get('fieldName')
                new_value = updated_field.get('value')

                # Find the field in the current product and update it
                for field in current_product:
                    if field['fieldName'] == field_name:
                        # Check if the field is editable
                        if field.get('editable') == 'true':
                            field['value'] = new_value
                        break

            # Save the updated product to database
            database.save_product(barcode, tenant_id, current_product)

            app.logger.info(f"Updated product {barcode} for tenant {tenant_id}")
            return jsonify({"success": True}), 200

        except Exception as e:
            app.logger.error(f"Error updating product: {str(e)}")
            return jsonify({"error": "Failed to update product"}), 500

    # Helper function to convert relative image paths to absolute URLs and filter fields
    def filter_and_process_fields(product_fields):
        # Filter to only include fields defined in custom AR fields
        filtered_fields = []

        # Get field types for all custom fields
        field_types = {f['fieldName']: f['fieldType'] for f in custom_fields}

        for field in product_fields:
            if field['fieldName'] in custom_field_names:
                # Create absolute URL for IMAGE_URI fields
                if field_types.get(field['fieldName']) == 'IMAGE_URI' and field['value']:
                    # If it's already an absolute URL, leave it as is
                    if not field['value'].startswith('http'):
                        # Build absolute URL using request host with tenant
                        field['value'] = f"{request.url_root.rstrip('/')}/{tenant_id}{field['value']}"
                filtered_fields.append(field)
        return filtered_fields

    # Handle GET request - return product data
    # If barcode is provided, return specific product
    if barcode:
        if barcode in products:
            product_data = filter_and_process_fields(products[barcode])
            response = jsonify(product_data)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 200
        return jsonify({"error": "Product not found"}), 404

    # Return all products if no barcode specified
    # Convert all products to have absolute URLs and filter fields
    all_products = {}
    for product_id, fields in products.items():
        all_products[product_id] = filter_and_process_fields(fields)
    response = jsonify(all_products)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response, 200

@app.route('/<tenant:tenant_id>/images/<path:filename>', methods=['GET'])
def serve_image(tenant_id, filename):
    # Log the request for debugging
    app.logger.info(f"Image requested for tenant {tenant_id}: {filename}")
    
    # Check if filename contains field name (e.g., "123456_thumbnail.jpg")
    base_name = os.path.splitext(filename)[0]
    
    if '_' in base_name:
        # Split to get product_id and field_name
        parts = base_name.split('_', 1)
        product_id = parts[0]
        field_name = '_' + parts[1] if len(parts) > 1 else '_image'
        
        # Try to get field-specific image
        image_data = database.get_product_image_by_field(product_id, tenant_id, field_name)
        if image_data:
            image_bytes, mime_type = image_data
            response = Response(image_bytes, mimetype=mime_type)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            app.logger.info(f"Serving field-specific image: {product_id}/{field_name} ({len(image_bytes)} bytes)")
            return response
    
    # Try standard image lookup (backward compatibility)
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

@app.route('/<tenant:tenant_id>/qrcode/template', methods=['GET'])
def generate_template_qr_code(tenant_id):
    """Generate QR code for the AR Template URL"""
    try:
        # Get server URL from settings
        server_url = database.get_server_url()
        template_url = f"{server_url}/{tenant_id}/"

        # Generate QR code
        buffer = BytesIO()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(template_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        app.logger.error(f"QR code generation error: {str(e)}")
        return jsonify({"error": "Failed to generate QR code"}), 500

@app.route('/<tenant:tenant_id>/qrcode/arinfo', methods=['GET'])
def generate_ar_qr_code(tenant_id):
    """Generate QR code for the AR API endpoint"""
    try:
        # Get server URL from settings
        server_url = database.get_server_url()
        ar_url = f"{server_url}/{tenant_id}/arinfo"

        # Generate QR code
        buffer = BytesIO()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(ar_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        app.logger.error(f"QR code generation error: {str(e)}")
        return jsonify({"error": "Failed to generate QR code"}), 500

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

# Import product management routes
from routes.admin import (add_product, edit_product, delete_product,
                         generate_barcode, manage_ar_fields, view_all_barcodes)

# Register product management routes (remove /admin/ from paths)
app.add_url_rule('/<tenant:tenant_id>/add', 'admin.add_product', add_product, methods=['GET', 'POST'])
app.add_url_rule('/<tenant:tenant_id>/edit/<product_id>', 'admin.edit_product', edit_product, methods=['GET', 'POST'])
app.add_url_rule('/<tenant:tenant_id>/delete/<product_id>', 'admin.delete_product', delete_product, methods=['POST'])
app.add_url_rule('/<tenant:tenant_id>/generate_barcode/<product_id>/<code_type>', 'admin.generate_barcode', generate_barcode)
app.add_url_rule('/<tenant:tenant_id>/ar_fields', 'admin.manage_ar_fields', manage_ar_fields, methods=['GET', 'POST'])
app.add_url_rule('/<tenant:tenant_id>/barcodes', 'admin.view_all_barcodes', view_all_barcodes, methods=['GET'])

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
