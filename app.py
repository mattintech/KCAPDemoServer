from flask import Flask, jsonify, request, send_file
import os

app = Flask(__name__)
app.config['STATIC_FOLDER'] = './static'

# Sample in-memory data for item attributes
ITEM_ATTRIBUTES = {
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
    if not barcode or barcode not in ITEM_ATTRIBUTES:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(ITEM_ATTRIBUTES[barcode]), 200

@app.route('/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    image_path = os.path.join(app.config['STATIC_FOLDER'], filename)
    if os.path.exists(image_path):
        return send_file(image_path)
    return jsonify({"error": "Image not found"}), 404

if __name__ == '__main__':
    app.run(port=5555, host="0.0.0.0", debug=True)
