from flask import render_template, request, redirect, url_for, flash, jsonify
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import database

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
    custom_fields = database.get_custom_ar_fields(tenant_id)
    return render_template('admin/index.html', products=products, tenant=tenant, custom_fields=custom_fields)

def add_product(tenant_id):
    # Get custom AR fields for this tenant
    custom_fields = database.get_custom_ar_fields(tenant_id)
    
    if request.method == 'POST':
        # Get form data
        product_id = request.form.get('product_id')
        
        # Basic validation
        if not product_id:
            flash('Product ID is required.')
            return render_template('admin/add_product.html', tenant_id=tenant_id, custom_fields=custom_fields)
        
        # Check if product ID already exists
        products = load_products(tenant_id)
        if product_id in products:
            flash('Product ID already exists.')
            return render_template('admin/add_product.html', tenant_id=tenant_id, custom_fields=custom_fields)
        
        # Handle backward compatibility image upload
        image_data = None
        image_mime_type = None
        
        # Create product data structure based on custom fields
        product_data = []
        
        # Always include _id field
        product_data.append({
            "fieldName": "_id", 
            "label": "Item ID", 
            "value": product_id, 
            "editable": "false", 
            "fieldType": "TEXT"
        })
        
        # Process images after product is saved
        images_to_save = []
        
        # Add other fields based on custom configuration
        for field in custom_fields:
            field_name = field['fieldName']
            if field_name == '_id':
                continue  # Already added
            elif field['fieldType'] == 'IMAGE_URI':
                # Check if image was uploaded for this field
                image_field_name = f'image_{field_name}'
                if image_field_name in request.files:
                    file = request.files[image_field_name]
                    if file and file.filename and allowed_file(file.filename):
                        # Read image data
                        file.seek(0)
                        img_data = file.read()
                        
                        # Determine mime type
                        extension = file.filename.rsplit('.', 1)[1].lower()
                        mime_types = {
                            'jpg': 'image/jpeg',
                            'jpeg': 'image/jpeg',
                            'png': 'image/png',
                            'gif': 'image/gif'
                        }
                        mime_type = mime_types.get(extension, 'image/jpeg')
                        
                        # Store for later saving
                        images_to_save.append({
                            'field_name': field_name,
                            'data': img_data,
                            'mime_type': mime_type
                        })
                        
                        # Set the image URL path (strip leading underscore from field_name to avoid double underscores)
                        field_suffix = field_name[1:] if field_name.startswith('_') else field_name
                        image_path = f"/images/{product_id}_{field_suffix}.{extension}"
                        
                        # For backward compatibility with _image field
                        if field_name == '_image':
                            image_data = img_data
                            image_mime_type = mime_type
                    else:
                        image_path = ""
                else:
                    image_path = ""
                
                product_data.append({
                    "fieldName": field_name,
                    "label": field['label'],
                    "value": image_path,
                    "editable": field['editable'],
                    "fieldType": field['fieldType']
                })
            else:
                # Get value from form
                value = request.form.get(f'field_{field_name}', '')
                product_data.append({
                    "fieldName": field_name,
                    "label": field['label'],
                    "value": value,
                    "editable": field['editable'],
                    "fieldType": field['fieldType']
                })
        
        # Also save fields that aren't in custom fields (for backward compatibility)
        if '_name' not in [f['fieldName'] for f in custom_fields]:
            name = request.form.get('name', '')
            if name:
                product_data.append({
                    "fieldName": "_name",
                    "label": "Product Name",
                    "value": name,
                    "editable": "true",
                    "fieldType": "TEXT"
                })
        
        if '_price' not in [f['fieldName'] for f in custom_fields]:
            price = request.form.get('price', '')
            if price:
                product_data.append({
                    "fieldName": "_price",
                    "label": "Sale Price",
                    "value": f"${price}",
                    "editable": "true",
                    "fieldType": "TEXT"
                })
        
        # Save to database
        database.save_product(product_id, tenant_id, product_data, image_data, image_mime_type)
        
        # Save additional images
        for img in images_to_save:
            database.save_product_image(product_id, tenant_id, img['field_name'], img['data'], img['mime_type'])
        
        flash('Product added successfully!')
        return redirect(f'/{tenant_id}/')
    
    return render_template('admin/add_product.html', tenant_id=tenant_id, custom_fields=custom_fields)

def edit_product(tenant_id, product_id):
    products = load_products(tenant_id)
    custom_fields = database.get_custom_ar_fields(tenant_id)

    if product_id not in products:
        flash('Product not found.')
        return redirect(f'/{tenant_id}/')
    
    if request.method == 'POST':
        # Handle backward compatibility image upload
        image_data = None
        image_mime_type = None

        # Process images after product is saved
        images_to_save = []

        # Update fields based on form data
        updated_product = []
        
        # Always include _id field
        for field in products[product_id]:
            if field["fieldName"] == "_id":
                updated_product.append(field)
                break
        
        # Process each custom field
        for custom_field in custom_fields:
            field_name = custom_field['fieldName']
            if field_name == '_id':
                continue
                
            # Find existing field data
            existing_field = None
            for field in products[product_id]:
                if field["fieldName"] == field_name:
                    existing_field = field.copy()
                    break
            
            if not existing_field:
                existing_field = {
                    "fieldName": field_name,
                    "label": custom_field['label'],
                    "value": "",
                    "editable": custom_field['editable'],
                    "fieldType": custom_field['fieldType']
                }
            
            if custom_field['fieldType'] == 'IMAGE_URI':
                # Check if new image was uploaded
                image_field_name = f'image_{field_name}'
                if image_field_name in request.files and request.files[image_field_name].filename:
                    file = request.files[image_field_name]
                    if allowed_file(file.filename):
                        # Read image data
                        file.seek(0)
                        img_data = file.read()

                        # Determine mime type
                        extension = file.filename.rsplit('.', 1)[1].lower()
                        mime_types = {
                            'jpg': 'image/jpeg',
                            'jpeg': 'image/jpeg',
                            'png': 'image/png',
                            'gif': 'image/gif'
                        }
                        mime_type = mime_types.get(extension, 'image/jpeg')

                        # Store for later saving
                        images_to_save.append({
                            'field_name': field_name,
                            'data': img_data,
                            'mime_type': mime_type
                        })

                        # Update image path (strip leading underscore from field_name to avoid double underscores)
                        field_suffix = field_name[1:] if field_name.startswith('_') else field_name
                        existing_field["value"] = f"/images/{product_id}_{field_suffix}.{extension}"

                        # For backward compatibility with _image field
                        if field_name == '_image':
                            image_data = img_data
                            image_mime_type = mime_type
                # If no new image uploaded, keep the existing value (already in existing_field)
            else:
                # Get value from form
                value = request.form.get(f'field_{field_name}', '')
                if field_name == '_price' and value and not value.startswith('$'):
                    value = f"${value}"
                existing_field["value"] = value
            
            updated_product.append(existing_field)
        
        # Handle backward compatibility fields
        if '_name' not in [f['fieldName'] for f in custom_fields]:
            name = request.form.get('name', '')
            if name:
                for field in products[product_id]:
                    if field["fieldName"] == "_name":
                        field["value"] = name
                        updated_product.append(field)
                        break
        
        if '_price' not in [f['fieldName'] for f in custom_fields]:
            price = request.form.get('price', '')
            if price:
                for field in products[product_id]:
                    if field["fieldName"] == "_price":
                        field["value"] = f"${price}"
                        updated_product.append(field)
                        break
        
        # Save to database
        database.save_product(product_id, tenant_id, updated_product, image_data, image_mime_type)
        
        # Save additional images
        for img in images_to_save:
            database.save_product_image(product_id, tenant_id, img['field_name'], img['data'], img['mime_type'])
        
        flash('Product updated successfully!')
        return redirect(f'/{tenant_id}/')
    
    return render_template('admin/edit_product.html', 
                         product_id=product_id, 
                         product=products[product_id], 
                         tenant_id=tenant_id,
                         custom_fields=custom_fields)

def delete_product(tenant_id, product_id):
    products = load_products(tenant_id)

    if product_id not in products:
        flash('Product not found.')
        return redirect(f'/{tenant_id}/')

    # Delete product from database (image is stored in DB)
    database.delete_product(product_id, tenant_id)

    flash('Product deleted successfully!')
    return redirect(f'/{tenant_id}/')

def view_product(tenant_id, product_id):
    products = load_products(tenant_id)

    if product_id not in products:
        flash('Product not found.')
        return redirect(f'/{tenant_id}/')

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

def manage_credentials(tenant_id):
    """Manage tenant login credentials"""
    tenant = database.get_or_create_tenant(tenant_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            database.update_tenant_credentials(tenant_id, username, password)
            flash('Credentials updated successfully!')
            return redirect(f'/{tenant_id}/')
        else:
            flash('Username and password are required.')
    
    return render_template('admin/credentials.html', tenant=tenant, tenant_id=tenant_id)

def manage_ar_fields(tenant_id):
    """Manage custom AR content fields"""
    tenant = database.get_or_create_tenant(tenant_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            field_data = {
                'fieldName': request.form.get('fieldName'),
                'label': request.form.get('label'),
                'fieldType': request.form.get('fieldType'),
                'editable': request.form.get('editable', 'true'),
                'displayOrder': int(request.form.get('displayOrder', 0))
            }
            
            if field_data['fieldName'] and field_data['label']:
                database.save_custom_ar_field(tenant_id, field_data)
                flash('Custom field added successfully!')
            else:
                flash('Field name and label are required.')
        
        elif action == 'delete':
            field_id = request.form.get('field_id')
            if field_id:
                database.delete_custom_ar_field(tenant_id, int(field_id))
                flash('Custom field deleted successfully!')
        
        elif action == 'update':
            field_data = {
                'id': int(request.form.get('field_id')),
                'fieldName': request.form.get('fieldName'),
                'label': request.form.get('label'),
                'fieldType': request.form.get('fieldType'),
                'editable': request.form.get('editable', 'true'),
                'displayOrder': int(request.form.get('displayOrder', 0))
            }
            
            if field_data['fieldName'] and field_data['label']:
                database.save_custom_ar_field(tenant_id, field_data)
                flash('Custom field updated successfully!')
            else:
                flash('Field name and label are required.')
        
        return redirect(url_for('admin.manage_ar_fields', tenant_id=tenant_id))
    
    # Get existing custom fields
    custom_fields = database.get_custom_ar_fields(tenant_id)
    
    # Available field types
    field_types = [
        'TEXT',
        'IMAGE_URI'
    ]
    
    return render_template('admin/ar_fields.html', 
                         tenant=tenant, 
                         tenant_id=tenant_id,
                         custom_fields=custom_fields,
                         field_types=field_types)
