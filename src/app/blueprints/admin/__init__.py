from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/<tenant:tenant_id>')

from . import routes
