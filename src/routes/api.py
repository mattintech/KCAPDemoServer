# API routes blueprint scaffold
from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/')
def api_index():
    return jsonify({'message': 'API Home'})
