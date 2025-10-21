import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-demo-only'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FOLDER = os.path.join(BASE_DIR, 'data')
    DATABASE_PATH = os.path.join(DATA_FOLDER, 'products.db')

    # Reserved tenant IDs that cannot be used
    RESERVED_TENANT_IDS = {
        'admin', 'api', 'login', 'logout', 'arcontentfields', 'arinfo',
        'images', 'barcodes', 'static', 'assets', 'js', 'css', 'tenant',
        'auth', 'oauth', 'callback', 'webhook', 'health', 'status'
    }

    # File upload settings
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = os.path.join(DATA_FOLDER, 'flask_session')

    # Authentication Mode
    # Options: 'entra' (Entra ID/Azure AD) or 'none' (no authentication)
    AUTH_MODE = os.environ.get('AUTH_MODE', 'entra').lower()

    # Entra ID (Azure AD) Configuration
    AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
    AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
    AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID')
    REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5555/auth/callback')
    AUTHORITY = os.environ.get('AUTHORITY', 'https://login.microsoftonline.com/')
    SCOPE = os.environ.get('SCOPE', 'User.Read').split()

    # Admin configuration
    DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', '')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_PATH = ':memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
