from flask import jsonify
from . import api_bp

@api_bp.route('/')
def api_index(tenant_id):
    """API home endpoint"""
    return jsonify({'message': 'API Home', 'tenant': tenant_id})
