from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/<tenant:tenant_id>/api')

from . import routes
