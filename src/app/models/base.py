import sqlite3
from contextlib import contextmanager
from flask import current_app

@contextmanager
def get_db():
    """Context manager for database connections"""
    db_path = current_app.config['DATABASE_PATH']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize the database with required tables"""
    import os
    db_path = current_app.config['DATABASE_PATH']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with get_db() as conn:
        cursor = conn.cursor()

        # Create tenants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT,
                password TEXT,
                barcode_type TEXT DEFAULT 'qr',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create products table with tenant_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                price TEXT,
                inventory INTEGER,
                image_data BLOB,
                image_mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, tenant_id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            )
        ''')

        # Create product_fields table with tenant_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_fields (
                product_id TEXT,
                tenant_id TEXT,
                field_name TEXT,
                label TEXT,
                value TEXT,
                editable TEXT,
                field_type TEXT,
                FOREIGN KEY (product_id, tenant_id) REFERENCES products(id, tenant_id) ON DELETE CASCADE,
                PRIMARY KEY (product_id, tenant_id, field_name)
            )
        ''')

        # Create custom_ar_fields table for tenant-specific AR field definitions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_ar_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                label TEXT NOT NULL,
                field_type TEXT NOT NULL,
                editable TEXT DEFAULT 'true',
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                UNIQUE(tenant_id, field_name)
            )
        ''')

        # Create product_images table for storing multiple images per product
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                image_data BLOB NOT NULL,
                image_mime_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id, tenant_id) REFERENCES products(id, tenant_id) ON DELETE CASCADE,
                UNIQUE(product_id, tenant_id, field_name)
            )
        ''')

        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
