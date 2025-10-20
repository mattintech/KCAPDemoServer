import os
from flask import Flask, redirect
from flask_session import Session
from werkzeug.routing import BaseConverter

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])

    # Ensure data folder exists
    os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

    # Initialize Flask-Session for server-side sessions
    Session(app)

    # Custom converter for tenant IDs
    class TenantConverter(BaseConverter):
        regex = '[a-zA-Z0-9_-]+'

        def to_python(self, value):
            # Convert to lowercase when parsing from URL
            return value.lower()

        def to_url(self, value):
            # Convert to lowercase when generating URLs
            return value.lower()

    app.url_map.converters['tenant'] = TenantConverter

    # Initialize database
    with app.app_context():
        from app.models.base import init_database
        from app.models.user import UserModel

        init_database()
        # Create user tables
        UserModel.create_table()

    # Register blueprints
    from app.blueprints import main_bp, tenant_bp, admin_bp, api_bp
    from app.blueprints.auth import auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tenant_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Catch-all route for admin without tenant - redirect to home
    @app.route('/admin/')
    @app.route('/admin/<path:path>')
    def redirect_admin_to_home(path=None):
        return redirect('/')

    return app
