import os

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
