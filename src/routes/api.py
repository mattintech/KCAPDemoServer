# API routes scaffold
from flask import jsonify

def api_index(tenant_id):
    return jsonify({'message': 'API Home', 'tenant': tenant_id})
