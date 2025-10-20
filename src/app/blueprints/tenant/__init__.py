from flask import Blueprint

tenant_bp = Blueprint('tenant', __name__, url_prefix='/<tenant:tenant_id>')

from . import routes
