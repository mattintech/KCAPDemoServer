from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import json
import uuid
import io
from werkzeug.utils import secure_filename

# Import barcode generator class, but handle the case if it fails
try:
    from barcode_generator import BarcodeGenerator
    BARCODE_GENERATOR_AVAILABLE = True
except ImportError:
    BARCODE_GENERATOR_AVAILABLE = False
    # Create a stub class for graceful degradation
    class BarcodeGenerator:
        @staticmethod
        def check_dependencies():
            return {'qrcode': False, 'barcode': False, 'pillow': False}

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

PRODUCTS_FILE = 'static/products.json'
UPLOAD_FOLDER = 'static/images'
BARCODE_FOLDER = 'static/barcodes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_products():
    try:
        with open(PRODUCTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_products(products):
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f, indent=2)

@admin_bp.route('/')
def index():
    products = load_products()
    return render_template('admin/index.html', products=products)

@admin_bp.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        # Get form data
        product_id = request.form.get('product_id')
        name = request.form.get('name')
        price = request.form.get('price')
        
        # Basic validation
        if not product_id or not name or not price:
            flash('Product ID, Name, and Price are required fields.')
            return render_template('admin/add_product.html')
        
        # Check if product ID already exists
        products = load_products()
        if product_id in products:
            flash('Product ID already exists.')
            return render_template('admin/add_product.html')
        
        # Handle image upload
        image_filename = f"{product_id}.png"  # Default name
        image_path = f"/images/{image_filename}"
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                extension = file.filename.rsplit('.', 1)[1].lower()
                image_filename = f"{product_id}.{extension}"
                image_path = f"/images/{image_filename}"
                file.save(os.path.join(UPLOAD_FOLDER, image_filename))
        
        # Create product data structure
        product_data = [
            {"fieldName": "_id", "label": "Item ID", "value": product_id, "editable": "false", "fieldType": "TEXT"},
            {"fieldName": "_name", "label": "Product Name", "value": name, "editable": "true", "fieldType": "TEXT"},
            {"fieldName": "_price", "label": "Sale Price", "value": f"${price}", "editable": "true", "fieldType": "TEXT"},
            {"fieldName": "_image", "label": "Image", "value": image_path, "editable": "false", "fieldType": "IMAGE_URI"}
        ]
        
        # Save to products.json
        products[product_id] = product_data
        save_products(products)
        
        flash('Product added successfully!')
        return redirect(url_for('admin.index'))
    
    return render_template('admin/add_product.html')

@admin_bp.route('/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    products = load_products()
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        price = request.form.get('price')
        
        # Basic validation
        if not name or not price:
            flash('Name and Price are required fields.')
            return render_template('admin/edit_product.html', product_id=product_id, product=products[product_id])
        
        # Update name and price
        for field in products[product_id]:
            if field["fieldName"] == "_name":
                field["value"] = name
            elif field["fieldName"] == "_price":
                field["value"] = f"${price}"
        
        # Handle image upload
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if allowed_file(file.filename):
                # Find current image path
                current_image = None
                for field in products[product_id]:
                    if field["fieldName"] == "_image":
                        current_image = field["value"]
                
                if current_image:
                    # Get current filename
                    current_filename = os.path.basename(current_image)
                    # Delete old file if it exists and is different
                    old_path = os.path.join(UPLOAD_FOLDER, current_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Save new image
                extension = file.filename.rsplit('.', 1)[1].lower()
                image_filename = f"{product_id}.{extension}"
                image_path = f"/images/{image_filename}"
                file.save(os.path.join(UPLOAD_FOLDER, image_filename))
                
                # Update image path
                for field in products[product_id]:
                    if field["fieldName"] == "_image":
                        field["value"] = image_path
        
        # Save to products.json
        save_products(products)
        
        flash('Product updated successfully!')
        return redirect(url_for('admin.index'))
    
    return render_template('admin/edit_product.html', product_id=product_id, product=products[product_id])

@admin_bp.route('/delete/<product_id>', methods=['POST'])
def delete_product(product_id):
    products = load_products()
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index'))
    
    # Find image path
    image_path = None
    for field in products[product_id]:
        if field["fieldName"] == "_image":
            image_path = field["value"]
    
    # Delete image file
    if image_path:
        image_filename = os.path.basename(image_path)
        image_file_path = os.path.join(UPLOAD_FOLDER, image_filename)
        if os.path.exists(image_file_path):
            os.remove(image_file_path)
    
    # Delete product from dict
    del products[product_id]
    
    # Save updated products
    save_products(products)
    
    flash('Product deleted successfully!')
    return redirect(url_for('admin.index'))

@admin_bp.route('/view/<product_id>')
def view_product(product_id):
    products = load_products()
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index'))
    
    return render_template('admin/view_product.html', product_id=product_id, product=products[product_id])

@admin_bp.route('/generate_barcode/<product_id>/<code_type>')
def generate_barcode(product_id, code_type):
    """Generate and serve a barcode or QR code for a product"""
    # Make sure the barcodes directory exists
    os.makedirs(BARCODE_FOLDER, exist_ok=True)
    
    products = load_products()
    if product_id not in products:
        return jsonify({"error": "Product not found"}), 404
    
    # Check if barcode generator is available
    if not BARCODE_GENERATOR_AVAILABLE:
        # Create a simple error image
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (300, 150), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 299, 149], outline=(0, 0, 0), width=2)
        d.text((25, 65), "Barcode generation unavailable", fill=(0, 0, 0))
        
        # Save and serve the error image
        image_path = os.path.join(BARCODE_FOLDER, f"{product_id}_{code_type}_error.png")
        img.save(image_path)
        return send_file(image_path, mimetype='image/png')
    
    generator = BarcodeGenerator()
    
    # Content for the code - use the product ID
    data = product_id
    
    # Base filename for the saved code
    base_filename = f"{product_id}_{code_type}"
    image_path = os.path.join(BARCODE_FOLDER, f"{base_filename}.png")
    
    # Generate the requested code type
    if code_type == 'qrcode':
        # Generate QR code with product URL
        product_url = request.host_url.rstrip('/') + f"/arinfo?barcode={product_id}"
        img = generator.generate_qr_code(product_url)
        generator.save_image(img, image_path)
        
    elif code_type == 'ean13':
        # For EAN-13, make sure the product ID is numeric
        numeric_id = ''.join(filter(str.isdigit, product_id))
        img = generator.generate_ean13_barcode(numeric_id)
        generator.save_image(img, image_path)
        
    elif code_type == 'code128':
        img = generator.generate_code128_barcode(data)
        generator.save_image(img, image_path)
        
    else:
        return jsonify({"error": "Invalid code type"}), 400
    
    # Return the image directly
    return send_file(image_path, mimetype='image/png')

@admin_bp.route('/generate_barcode_page/<product_id>')
def generate_barcode_page(product_id):
    """Show a page with different barcode options for a product"""
    products = load_products()
    
    if product_id not in products:
        flash('Product not found.')
        return redirect(url_for('admin.index'))
    
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
                          dependencies=dependency_status)
