from flask import Flask, jsonify, request, send_file, render_template, flash
import os
import json
from routes.admin import admin_bp
from routes.api import api_bp

app = Flask(__name__)
# Set DATA_FOLDER to the absolute path of the data directory inside src
app.config['DATA_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data')
app.config['SECRET_KEY'] = 'dev-key-for-demo-only'

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)

# Load product data from products.json
def load_products():
    try:
        products_file = os.path.join(app.config['DATA_FOLDER'], 'products.json')
        with open(products_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login():
    # Just return 200 for this example, assuming no auth needed
    return '', 200

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
    if not barcode or barcode not in products:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(products[barcode]), 200

@app.route('/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    image_path = os.path.join(app.config['DATA_FOLDER'], 'images', filename)
    if os.path.exists(image_path):
        return send_file(image_path)
    return jsonify({"error": "Image not found"}), 404

@app.route('/barcodes/<path:filename>', methods=['GET'])
def serve_barcode(filename):
    barcode_path = os.path.join(app.config['DATA_FOLDER'], 'barcodes', filename)
    if os.path.exists(barcode_path):
        return send_file(barcode_path)
    return jsonify({"error": "Barcode not found"}), 404

if __name__ == '__main__':
    # Ensure the required directories exist
    os.makedirs(os.path.join(app.config['DATA_FOLDER'], 'images'), exist_ok=True)
    os.makedirs(os.path.join(app.config['DATA_FOLDER'], 'barcodes'), exist_ok=True)
    
    # If products.json doesn't exist, create it with initial data
    products_file = os.path.join(app.config['DATA_FOLDER'], 'products.json')
    if not os.path.exists(products_file):
        initial_data = {
            "123456": [
                {"fieldName": "_id", "label": "Item ID", "value": "123456", "editable": "false", "fieldType": "TEXT"},
                {"fieldName": "_price", "label": "Sale Price", "value": "$49.99", "editable": "true", "fieldType": "TEXT"},
                {"fieldName": "_image", "label": "Image", "value": "/images/123456.png", "editable": "false", "fieldType": "IMAGE_URI"}
            ],
            "789012": [
                {"fieldName": "_id", "label": "Item ID", "value": "789012", "editable": "false", "fieldType": "TEXT"},
                {"fieldName": "_price", "label": "Sale Price", "value": "$59.99", "editable": "true", "fieldType": "TEXT"},
                {"fieldName": "_image", "label": "Image", "value": "/images/789012.png", "editable": "false", "fieldType": "IMAGE_URI"}
            ]
        }
        with open(products_file, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    app.run(port=5555, host="0.0.0.0", debug=True)
