from flask import render_template, request, redirect, flash, jsonify, Response, current_app, session
from . import tenant_bp
from app.models import TenantModel, ProductModel, ARFieldModel, SettingsModel, UserModel
from app.services import AuthService, ProductService, BarcodeService
from app.decorators.auth import tenant_access_required
import os

@tenant_bp.route('/')
@tenant_access_required
def index(tenant_id):
    """Tenant home page - product listing"""
    # Get the tenant name from query parameter if provided (for new tenant creation)
    tenant_name = request.args.get('tenant_name')

    # Check if tenant exists first
    existing_tenant = TenantModel.get_by_id(tenant_id)

    if existing_tenant:
        tenant = existing_tenant
    elif tenant_name:
        # Create new tenant with display name
        tenant = TenantModel.create(tenant_id, tenant_name)
    else:
        # Create with default name (tenant_id)
        tenant = TenantModel.create(tenant_id)

    if tenant is None:
        return jsonify({"error": f"'{tenant_id}' is a reserved name and cannot be used as a tenant ID"}), 404

    # Check if we should create default fields for a new tenant
    create_defaults = request.args.get('create_defaults', '0') == '1'
    custom_fields = ARFieldModel.get_all(tenant_id)

    # If no custom fields exist and user requested defaults, create them
    if create_defaults and not custom_fields:
        ARFieldModel.create_default_fields(tenant_id)
        custom_fields = ARFieldModel.get_all(tenant_id)
        flash('Tenant created with default product fields!', 'success')
        # Redirect to remove the query parameter
        return redirect(f'/{tenant_id}/')

    products = ProductModel.get_all(tenant_id)

    return render_template('index.html', tenant=tenant, products=products, custom_fields=custom_fields)

@tenant_bp.route('/delete', methods=['POST'])
@tenant_access_required
def delete_tenant(tenant_id):
    """Delete a tenant and all its data"""
    # Also remove the user's association with this tenant
    user_id = session['user']['id']
    UserModel.remove_tenant(user_id, tenant_id)

    TenantModel.delete(tenant_id)
    flash(f'Tenant "{tenant_id}" has been deleted successfully.', 'success')
    return redirect('/')

@tenant_bp.route('/settings')
@tenant_access_required
def settings(tenant_id):
    """Tenant settings page"""
    tenant = TenantModel.get_or_create(tenant_id)
    if tenant is None:
        return jsonify({"error": f"'{tenant_id}' is a reserved name and cannot be used as a tenant ID"}), 404

    custom_fields = ARFieldModel.get_all(tenant_id)
    server_url = SettingsModel.get_server_url()

    return render_template('tenant_settings.html', tenant=tenant, custom_fields=custom_fields, server_url=server_url)

@tenant_bp.route('/settings/credentials', methods=['POST'])
@tenant_access_required
def update_credentials(tenant_id):
    """Update tenant credentials"""
    tenant = TenantModel.get_by_id(tenant_id)
    if tenant is None:
        return jsonify({"error": "Tenant not found"}), 404

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username:
        flash('Username is required.', 'error')
        return redirect(f'/{tenant_id}/settings')

    TenantModel.update_credentials(tenant_id, username, password if password else None)
    flash('Credentials updated successfully.', 'success')
    return redirect(f'/{tenant_id}/settings')

@tenant_bp.route('/settings/barcode', methods=['POST'])
@tenant_access_required
def update_barcode_type(tenant_id):
    """Update tenant barcode type"""
    tenant = TenantModel.get_by_id(tenant_id)
    if tenant is None:
        return jsonify({"error": "Tenant not found"}), 404

    barcode_type = request.form.get('barcode_type', '').strip()

    if not barcode_type:
        flash('Barcode type is required.', 'error')
        return redirect(f'/{tenant_id}/settings')

    TenantModel.update_barcode_type(tenant_id, barcode_type)
    flash('Barcode type updated successfully.', 'success')
    return redirect(f'/{tenant_id}/settings')

@tenant_bp.route('/login', methods=['GET'])
def login(tenant_id):
    """Login endpoint for API authentication"""
    auth_header = request.headers.get('Authorization')

    if AuthService.check_basic_auth(auth_header, tenant_id):
        return jsonify({"status": "success", "message": "Authentication successful"}), 200

    return jsonify({"error": "Unauthorized"}), 401

@tenant_bp.route('/arcontentfields', methods=['GET'])
def get_ar_content_fields(tenant_id):
    """Get custom AR fields for tenant"""
    fields = ARFieldModel.get_all(tenant_id)
    return jsonify(fields), 200

@tenant_bp.route('/arinfo', methods=['GET', 'POST'])
def get_ar_info(tenant_id):
    """Get or update AR product information"""
    barcode = request.args.get('barcode')

    # Handle POST request - update product fields
    if request.method == 'POST':
        if not barcode:
            return jsonify({"error": "Barcode parameter required"}), 400

        product = ProductModel.get_by_id(barcode, tenant_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        try:
            updated_fields = request.get_json()
            if not isinstance(updated_fields, list):
                return jsonify({"error": "Request body must be an array of fields"}), 400

            # Update only the editable fields
            for updated_field in updated_fields:
                field_name = updated_field.get('fieldName')
                new_value = updated_field.get('value')

                for field in product:
                    if field['fieldName'] == field_name:
                        if field.get('editable') == 'true':
                            field['value'] = new_value
                        break

            # Save the updated product
            ProductModel.save(barcode, tenant_id, product)
            current_app.logger.info(f"Updated product {barcode} for tenant {tenant_id}")
            return jsonify({"success": True}), 200

        except Exception as e:
            current_app.logger.error(f"Error updating product: {str(e)}")
            return jsonify({"error": "Failed to update product"}), 500

    # Handle GET request - return product data
    if barcode:
        product_data = ProductService.get_product_filtered(barcode, tenant_id)
        if product_data:
            response = jsonify(product_data)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 200
        return jsonify({"error": "Product not found"}), 404

    # Return all products if no barcode specified
    all_products = ProductService.get_all_products_filtered(tenant_id)
    response = jsonify(all_products)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response, 200

@tenant_bp.route('/images/<path:filename>', methods=['GET'])
def serve_image(tenant_id, filename):
    """Serve product images"""
    current_app.logger.info(f"Image requested for tenant {tenant_id}: {filename}")

    # Check if filename contains field name (e.g., "123456_thumbnail.jpg")
    base_name = os.path.splitext(filename)[0]

    if '_' in base_name:
        parts = base_name.split('_', 1)
        product_id = parts[0]
        field_name = '_' + parts[1] if len(parts) > 1 else '_image'

        # Try to get field-specific image
        image_data = ProductModel.get_image_by_field(product_id, tenant_id, field_name)
        if image_data:
            image_bytes, mime_type = image_data
            response = Response(image_bytes, mimetype=mime_type)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            current_app.logger.info(f"Serving field-specific image: {product_id}/{field_name} ({len(image_bytes)} bytes)")
            return response

    # Try standard image lookup (backward compatibility)
    product_id = os.path.splitext(filename)[0]
    image_data = ProductModel.get_image(product_id, tenant_id)
    if image_data:
        image_bytes, mime_type = image_data
        response = Response(image_bytes, mimetype=mime_type)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        current_app.logger.info(f"Serving image from database: {product_id} ({len(image_bytes)} bytes)")
        return response

    current_app.logger.warning(f"Image not found: {filename}")
    return jsonify({"error": "Image not found"}), 404

@tenant_bp.route('/qrcode/template', methods=['GET'])
def generate_template_qr_code(tenant_id):
    """Generate QR code for the AR Template URL"""
    try:
        server_url = SettingsModel.get_server_url()
        template_url = f"{server_url}/{tenant_id}/"
        buffer = BarcodeService.generate_qr_code(template_url)
        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        current_app.logger.error(f"QR code generation error: {str(e)}")
        return jsonify({"error": "Failed to generate QR code"}), 500

@tenant_bp.route('/qrcode/arinfo', methods=['GET'])
def generate_ar_qr_code(tenant_id):
    """Generate QR code for the AR API endpoint"""
    try:
        server_url = SettingsModel.get_server_url()
        ar_url = f"{server_url}/{tenant_id}/arinfo"
        buffer = BarcodeService.generate_qr_code(ar_url)
        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        current_app.logger.error(f"QR code generation error: {str(e)}")
        return jsonify({"error": "Failed to generate QR code"}), 500

@tenant_bp.route('/barcodes/<path:filename>', methods=['GET'])
def serve_barcode(tenant_id, filename):
    """Serve dynamically generated barcodes"""
    name_parts = os.path.splitext(filename)[0].split('_')
    if len(name_parts) < 2:
        return jsonify({"error": "Invalid barcode filename format"}), 400

    product_id = '_'.join(name_parts[:-1])
    code_type = name_parts[-1].lower()

    try:
        url = None
        if code_type == 'qr':
            url = f'http://{request.host}/{tenant_id}/arinfo?barcode={product_id}'

        buffer = BarcodeService.generate_barcode(product_id, code_type, url)
        return Response(buffer.getvalue(), mimetype='image/png')

    except Exception as e:
        current_app.logger.error(f"Barcode generation error: {str(e)}")
        return jsonify({"error": "Failed to generate barcode"}), 500
