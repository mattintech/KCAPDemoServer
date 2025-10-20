import sqlite3
import json
import os
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
import base64

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'products.db')

# Reserved tenant IDs that cannot be used
RESERVED_TENANT_IDS = {
    'admin', 'api', 'login', 'logout', 'arcontentfields', 'arinfo', 
    'images', 'barcodes', 'static', 'assets', 'js', 'css', 'tenant',
    'auth', 'oauth', 'callback', 'webhook', 'health', 'status'
}

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize the database with required tables"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create tenants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT,
                password TEXT,
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
                image_data BLOB,
                image_mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id, tenant_id) REFERENCES products(id, tenant_id) ON DELETE CASCADE,
                UNIQUE(product_id, tenant_id, field_name)
            )
        ''')
        
        # Create settings table for server configuration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

def migrate_from_json():
    """Migrate existing JSON data to SQLite with default tenant"""
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
    
    if not os.path.exists(json_path):
        return
    
    with open(json_path, 'r') as f:
        products_data = json.load(f)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create default tenant if not exists
        default_tenant_id = 'default'
        cursor.execute('''
            INSERT OR IGNORE INTO tenants (id, name, username, password)
            VALUES (?, ?, ?, ?)
        ''', (default_tenant_id, 'Default', 'admin', 'admin'))
        
        for product_id, fields in products_data.items():
            # Extract core fields
            name = ''
            price = ''
            inventory = None
            image_path = ''
            
            for field in fields:
                if field['fieldName'] == '_name':
                    name = field['value']
                elif field['fieldName'] == '_price':
                    price = field['value']
                elif field['fieldName'] == '_inventory':
                    inventory = int(field['value']) if field['value'] else None
                elif field['fieldName'] == '_image':
                    image_path = field['value']
            
            # Read image data if exists
            image_data = None
            image_mime_type = None
            if image_path:
                # Extract filename from path like '/images/filename.jpg'
                filename = image_path.split('/')[-1]
                full_image_path = os.path.join(os.path.dirname(__file__), 'data', 'images', filename)
                
                if os.path.exists(full_image_path):
                    with open(full_image_path, 'rb') as img_file:
                        image_data = img_file.read()
                        # Determine mime type from extension
                        ext = os.path.splitext(filename)[1].lower()
                        mime_types = {
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.png': 'image/png',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp'
                        }
                        image_mime_type = mime_types.get(ext, 'image/jpeg')
            
            # Insert into products table with tenant_id
            cursor.execute('''
                INSERT OR REPLACE INTO products (id, tenant_id, name, price, inventory, image_data, image_mime_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, default_tenant_id, name, price, inventory, image_data, image_mime_type))
            
            # Insert all fields into product_fields table with tenant_id
            for field in fields:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_fields 
                    (product_id, tenant_id, field_name, label, value, editable, field_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_id,
                    default_tenant_id,
                    field['fieldName'],
                    field['label'],
                    field['value'],
                    field.get('editable', 'true'),
                    field.get('fieldType', 'TEXT')
                ))
        
        conn.commit()

def get_all_products(tenant_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get all products for a tenant in the legacy format"""
    # Normalize tenant_id to lowercase if provided
    if tenant_id:
        tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all product IDs for the tenant
        if tenant_id:
            cursor.execute('SELECT id FROM products WHERE tenant_id = ?', (tenant_id,))
        else:
            cursor.execute('SELECT id FROM products')
        product_ids = [row['id'] for row in cursor.fetchall()]
        
        result = {}
        for product_id in product_ids:
            # Get all fields for this product
            if tenant_id:
                cursor.execute('''
                    SELECT field_name, label, value, editable, field_type
                    FROM product_fields
                    WHERE product_id = ? AND tenant_id = ?
                    ORDER BY field_name
                ''', (product_id, tenant_id))
            else:
                cursor.execute('''
                    SELECT field_name, label, value, editable, field_type
                    FROM product_fields
                    WHERE product_id = ?
                    ORDER BY field_name
                ''', (product_id,))
            
            fields = []
            for row in cursor.fetchall():
                fields.append({
                    'fieldName': row['field_name'],
                    'label': row['label'],
                    'value': row['value'],
                    'editable': row['editable'],
                    'fieldType': row['field_type']
                })
            
            result[product_id] = fields
        
        return result

def get_product(product_id: str, tenant_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get a single product by ID and tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT field_name, label, value, editable, field_type
            FROM product_fields
            WHERE product_id = ? AND tenant_id = ?
            ORDER BY field_name
        ''', (product_id, tenant_id))
        
        fields = []
        for row in cursor.fetchall():
            fields.append({
                'fieldName': row['field_name'],
                'label': row['label'],
                'value': row['value'],
                'editable': row['editable'],
                'fieldType': row['field_type']
            })
        
        return fields if fields else None

def save_product(product_id: str, tenant_id: str, fields: List[Dict[str, Any]], image_data: Optional[bytes] = None, image_mime_type: Optional[str] = None):
    """Save or update a product for a tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Extract core fields
        name = ''
        price = ''
        inventory = None
        
        for field in fields:
            if field['fieldName'] == '_name':
                name = field['value']
            elif field['fieldName'] == '_price':
                price = field['value']
            elif field['fieldName'] == '_inventory':
                inventory = int(field['value']) if field['value'] else None
        
        # Check if product exists
        cursor.execute('SELECT id FROM products WHERE id = ? AND tenant_id = ?', (product_id, tenant_id))
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update existing product
            if image_data is not None:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, price = ?, inventory = ?, image_data = ?, image_mime_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND tenant_id = ?
                ''', (name, price, inventory, image_data, image_mime_type, product_id, tenant_id))
            else:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, price = ?, inventory = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND tenant_id = ?
                ''', (name, price, inventory, product_id, tenant_id))
        else:
            # Insert new product
            cursor.execute('''
                INSERT INTO products (id, tenant_id, name, price, inventory, image_data, image_mime_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, tenant_id, name, price, inventory, image_data, image_mime_type))
        
        # Delete existing fields
        cursor.execute('DELETE FROM product_fields WHERE product_id = ? AND tenant_id = ?', (product_id, tenant_id))
        
        # Insert all fields
        for field in fields:
            cursor.execute('''
                INSERT INTO product_fields 
                (product_id, tenant_id, field_name, label, value, editable, field_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_id,
                tenant_id,
                field['fieldName'],
                field['label'],
                field['value'],
                field.get('editable', 'true'),
                field.get('fieldType', 'TEXT')
            ))
        
        conn.commit()

def delete_product(product_id: str, tenant_id: str):
    """Delete a product for a tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ? AND tenant_id = ?', (product_id, tenant_id))
        conn.commit()

def get_product_image(product_id: str, tenant_id: str) -> Optional[tuple[bytes, str]]:
    """Get product image data and mime type for a tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT image_data, image_mime_type FROM products WHERE id = ? AND tenant_id = ?', (product_id, tenant_id))
        row = cursor.fetchone()
        
        if row and row['image_data']:
            return row['image_data'], row['image_mime_type']
        return None

def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a tenant without creating it"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if tenant exists
        cursor.execute('SELECT id, name, username, password FROM tenants WHERE id = ?', (tenant_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'username': row['username'],
                'password': row['password']
            }
        return None

def get_or_create_tenant(tenant_id: str, username: str = None, password: str = None) -> Optional[Dict[str, Any]]:
    """Get or create a tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    # Check if tenant_id is reserved
    if tenant_id in RESERVED_TENANT_IDS:
        return None
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if tenant exists
        cursor.execute('SELECT id, name, username, password FROM tenants WHERE id = ?', (tenant_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'username': row['username'],
                'password': row['password']
            }
        else:
            # Create new tenant with default credentials
            default_username = username or 'admin'
            default_password = password or 'admin'
            # Preserve original casing for display name
            display_name = tenant_id.replace('-', ' ').replace('_', ' ').title()
            cursor.execute('''
                INSERT INTO tenants (id, name, username, password)
                VALUES (?, ?, ?, ?)
            ''', (tenant_id, display_name, default_username, default_password))
            conn.commit()
            
            # Initialize default AR fields for the new tenant
            init_default_ar_fields(tenant_id)
            
            return {
                'id': tenant_id,
                'name': display_name,
                'username': default_username,
                'password': default_password
            }

def update_tenant_credentials(tenant_id: str, username: str, password: str):
    """Update tenant credentials"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tenants 
            SET username = ?, password = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (username, password, tenant_id))
        conn.commit()

def get_all_tenants() -> List[Dict[str, Any]]:
    """Get all tenants"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, username, created_at FROM tenants ORDER BY created_at DESC')
        
        tenants = []
        for row in cursor.fetchall():
            tenants.append({
                'id': row['id'],
                'name': row['name'],
                'username': row['username'],
                'created_at': row['created_at']
            })
        
        return tenants

def delete_tenant(tenant_id: str):
    """Delete a tenant and all associated data"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Due to ON DELETE CASCADE, this will also delete all products and product_fields
        cursor.execute('DELETE FROM tenants WHERE id = ?', (tenant_id,))
        conn.commit()

def cleanup_reserved_tenants():
    """Remove any tenants that were accidentally created with reserved IDs"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Get all tenants
        cursor.execute('SELECT id FROM tenants')
        tenants = cursor.fetchall()
        
        deleted_count = 0
        for tenant in tenants:
            tenant_id = tenant['id']
            if tenant_id.lower() in RESERVED_TENANT_IDS:
                cursor.execute('DELETE FROM tenants WHERE id = ?', (tenant_id,))
                deleted_count += 1
                print(f"Deleted reserved tenant: {tenant_id}")
        
        conn.commit()
        return deleted_count

def get_custom_ar_fields(tenant_id: str) -> List[Dict[str, Any]]:
    """Get custom AR fields for a tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, field_name, label, field_type, editable, display_order
            FROM custom_ar_fields
            WHERE tenant_id = ?
            ORDER BY display_order, field_name
        ''', (tenant_id,))
        
        fields = []
        for row in cursor.fetchall():
            fields.append({
                'id': row['id'],
                'fieldName': row['field_name'],
                'label': row['label'],
                'fieldType': row['field_type'],
                'editable': row['editable'],
                'displayOrder': row['display_order']
            })

        return fields

def save_custom_ar_field(tenant_id: str, field_data: Dict[str, Any]) -> int:
    """Save or update a custom AR field"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if 'id' in field_data:
            # Update existing field
            cursor.execute('''
                UPDATE custom_ar_fields
                SET field_name = ?, label = ?, field_type = ?, editable = ?, 
                    display_order = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND tenant_id = ?
            ''', (
                field_data['fieldName'],
                field_data['label'],
                field_data['fieldType'],
                field_data.get('editable', 'true'),
                field_data.get('displayOrder', 0),
                field_data['id'],
                tenant_id
            ))
            conn.commit()
            return field_data['id']
        else:
            # Insert new field
            cursor.execute('''
                INSERT INTO custom_ar_fields 
                (tenant_id, field_name, label, field_type, editable, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                tenant_id,
                field_data['fieldName'],
                field_data['label'],
                field_data['fieldType'],
                field_data.get('editable', 'true'),
                field_data.get('displayOrder', 0)
            ))
            conn.commit()
            return cursor.lastrowid

def delete_custom_ar_field(tenant_id: str, field_id: int):
    """Delete a custom AR field"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM custom_ar_fields
            WHERE id = ? AND tenant_id = ?
        ''', (field_id, tenant_id))
        conn.commit()

def init_default_ar_fields(tenant_id: str):
    """Initialize default AR fields for a new tenant"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    default_fields = [
        {"fieldName": "_id", "label": "Item ID", "fieldType": "TEXT", "editable": "false", "displayOrder": 1},
        {"fieldName": "_price", "label": "Sale Price", "fieldType": "TEXT", "editable": "true", "displayOrder": 2},
        {"fieldName": "_image", "label": "Image", "fieldType": "IMAGE_URI", "editable": "false", "displayOrder": 3}
    ]
    
    with get_db() as conn:
        cursor = conn.cursor()
        for field in default_fields:
            # Use INSERT OR IGNORE to avoid duplicate key errors
            cursor.execute('''
                INSERT OR IGNORE INTO custom_ar_fields 
                (tenant_id, field_name, label, field_type, editable, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                tenant_id,
                field['fieldName'],
                field['label'],
                field['fieldType'],
                field.get('editable', 'true'),
                field.get('displayOrder', 0)
            ))
        conn.commit()

def save_product_image(product_id: str, tenant_id: str, field_name: str, image_data: bytes, mime_type: str):
    """Save an image for a specific field of a product"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Delete existing image for this field if any
        cursor.execute('''
            DELETE FROM product_images 
            WHERE product_id = ? AND tenant_id = ? AND field_name = ?
        ''', (product_id, tenant_id, field_name))
        
        # Insert new image
        cursor.execute('''
            INSERT INTO product_images (product_id, tenant_id, field_name, image_data, image_mime_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, tenant_id, field_name, image_data, mime_type))
        
        conn.commit()

def get_product_image_by_field(product_id: str, tenant_id: str, field_name: str) -> Optional[tuple[bytes, str]]:
    """Get image data for a specific field of a product"""
    # Normalize tenant_id to lowercase
    tenant_id = tenant_id.lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT image_data, image_mime_type 
            FROM product_images 
            WHERE product_id = ? AND tenant_id = ? AND field_name = ?
        ''', (product_id, tenant_id, field_name))
        
        row = cursor.fetchone()
        if row and row['image_data']:
            return row['image_data'], row['image_mime_type']
        return None

def get_setting(key: str, default_value: str = None) -> Optional[str]:
    """Get a setting value by key"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        
        if row:
            return row['value']
        return default_value

def set_setting(key: str, value: str):
    """Set a setting value"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
        ''', (key, value, value))
        conn.commit()

def get_server_url() -> str:
    """Get the configured server URL or return a default"""
    return get_setting('server_url', 'http://localhost:5000')