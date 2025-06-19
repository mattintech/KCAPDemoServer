from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import json
import uuid
import io
from werkzeug.utils import secure_filename
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import database

# Import barcode generator class, but handle the case if it fails
try:
    from utils.barcode_generator import BarcodeGenerator
    BARCODE_GENERATOR_AVAILABLE = True
except ImportError:
    BARCODE_GENERATOR_AVAILABLE = False
    class BarcodeGenerator:
        @staticmethod
        def check_dependencies():
            return {'qrcode': False, 'barcode': False, 'pillow': False}

DATA_FOLDER = os.path.join(os.path.dirname(__file__), '../data')
PRODUCTS_FILE = os.path.join(DATA_FOLDER, 'products.json')
UPLOAD_FOLDER = os.path.join(DATA_FOLDER, 'images')
BARCODE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'barcodes'))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_products(tenant_id):
    return database.get_all_products(tenant_id)

def save_products(products):
    # This is now handled by database operations
    pass

def index(tenant_id):
    products = load_products(tenant_id)
    tenant = database.get_or_create_tenant(tenant_id)
    return render_template('admin/index.html', products=products, tenant=tenant)

def add_product(tenant_id):
    if request.method == 'POST':
        # Get form data
        product_id = request.form.get('product_id')
        name = request.form.get('name')
        price = request.form.get('price')
        
        # Basic validation
        if not product_id or not name or not price:
            flash('Product ID, Name, and Price are required fields.')
            return render_template('admin/add_product.html', tenant_id=tenant_id)
        
        # Check if product ID already exists
        products = load_products(tenant_id)
        if product_id in products:
            flash('Product ID already exists.')
            return render_template('admin/add_product.html', tenant_id=tenant_id)
        
        # Handle image upload
        image_data = None
        image_mime_type = None
        image_path = f"/images/{product_id}.png"  # Default path for display
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                extension = file.filename.rsplit('.', 1)[1].lower()
                image_path = f"/images/{product_id}.{extension}"
                
                # Read image data
                image_data = file.read()
                
                # Determine mime type
                mime_types = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif'
                }
                image_mime_type = mime_types.get(extension, 'image/jpeg')
        
        # Create product data structure
        product_data = [
            {"fieldName": "_id", "label": "Item ID", "value": product_id, "editable": "false", "fieldType": "TEXT"},
            {"fieldName": "_name", "label": "Product Name", "value": name, "editable": "true", "fieldType": "TEXT"},
            {"fieldName": "_price", "label": "Sale Price", "value": f"${price}", "editable": "true", "fieldType": "TEXT"},
            {"fieldName": "_image", "label": "Image", "value": image_path, "editable": "false", "fieldType": "IMAGE_URI"}
        ]
        
        # Save to database
        database.save_product(product_id, tenant_id, product_data, image_data, image_mime_type)
        
        flash('Product added successfully!')
        return redirect(url_for('admin.index', tenant_id=tenant_id))
    
    return render_template('admin/add_product.html', tenant_id=tenant_id)

def edit_product(tenant_id, product_id):
    products = load_products(tenant_id)
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index', tenant_id=tenant_id))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        price = request.form.get('price')
        
        # Basic validation
        if not name or not price:
            flash('Name and Price are required fields.')
            return render_template('admin/edit_product.html', product_id=product_id, product=products[product_id], tenant_id=tenant_id)
        
        # Update name and price
        for field in products[product_id]:
            if field["fieldName"] == "_name":
                field["value"] = name
            elif field["fieldName"] == "_price":
                field["value"] = f"${price}"
        
        # Handle image upload
        image_data = None
        image_mime_type = None
        
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if allowed_file(file.filename):
                # Read new image data
                image_data = file.read()
                
                # Determine mime type
                extension = file.filename.rsplit('.', 1)[1].lower()
                mime_types = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif'
                }
                image_mime_type = mime_types.get(extension, 'image/jpeg')
                
                # Update image path in product data
                image_path = f"/images/{product_id}.{extension}"
                for field in products[product_id]:
                    if field["fieldName"] == "_image":
                        field["value"] = image_path
        
        # Save to database
        database.save_product(product_id, tenant_id, products[product_id], image_data, image_mime_type)
        
        flash('Product updated successfully!')
        return redirect(url_for('admin.index', tenant_id=tenant_id))
    
    return render_template('admin/edit_product.html', product_id=product_id, product=products[product_id], tenant_id=tenant_id)

def delete_product(tenant_id, product_id):
    products = load_products(tenant_id)
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index', tenant_id=tenant_id))
    
    # Delete product from database (image is stored in DB)
    database.delete_product(product_id, tenant_id)
    
    flash('Product deleted successfully!')
    return redirect(url_for('admin.index', tenant_id=tenant_id))

def view_product(tenant_id, product_id):
    products = load_products(tenant_id)
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index', tenant_id=tenant_id))
    
    return render_template('admin/view_product.html', product_id=product_id, product=products[product_id], tenant_id=tenant_id)

def generate_barcode(tenant_id, product_id, code_type):
    """Redirect to the main barcode generation endpoint"""
    products = load_products(tenant_id)
    if product_id not in products:
        return jsonify({"error": "Product not found"}), 404
    
    # Map code_type to the expected format for the main endpoint
    type_mapping = {
        'qrcode': 'qr',
        'ean13': 'ean13',
        'code128': 'code128'
    }
    
    barcode_type = type_mapping.get(code_type, code_type)
    
    # Redirect to the main barcode endpoint which generates dynamically
    return redirect(f'/{tenant_id}/barcodes/{product_id}_{barcode_type}.png')

def generate_barcode_page(tenant_id, product_id):
    """Show a page with different barcode options for a product"""
    products = load_products(tenant_id)
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index', tenant_id=tenant_id))
    
    # Extract product data
    product_data = {}
    for field in products[product_id]:
        field_name = field["fieldName"][1:] if field["fieldName"].startswith('_') else field["fieldName"]
        product_data[field_name] = field["value"]
    
    # Add product ID
    product_data['id'] = product_id
    
    # Check if barcode generation is available
    dependency_status = {}
    if BARCODE_GENERATOR_AVAILABLE:
        dependency_status = BarcodeGenerator.check_dependencies()
    else:
        dependency_status = {
            'qrcode': False,
            'barcode': False,
            'pillow': False
        }
    
    return render_template('admin/generate_barcode.html', 
                          product_id=product_id, 
                          product=product_data,
                          dependencies=dependency_status,
                          tenant_id=tenant_id)

def manage_credentials(tenant_id):
    """Manage tenant login credentials"""
    tenant = database.get_or_create_tenant(tenant_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            database.update_tenant_credentials(tenant_id, username, password)
            flash('Credentials updated successfully!')
            return redirect(url_for('admin.index', tenant_id=tenant_id))
        else:
            flash('Username and password are required.')
    
    return render_template('admin/credentials.html', tenant=tenant, tenant_id=tenant_id)
