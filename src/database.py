import sqlite3
import json
import os
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
import base64

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'products.db')

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
        
        # Create products table with image_data as BLOB
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price TEXT,
                inventory INTEGER,
                image_data BLOB,
                image_mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create product_fields table for extensible fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_fields (
                product_id TEXT,
                field_name TEXT,
                label TEXT,
                value TEXT,
                editable TEXT,
                field_type TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                PRIMARY KEY (product_id, field_name)
            )
        ''')
        
        conn.commit()

def migrate_from_json():
    """Migrate existing JSON data to SQLite"""
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
    
    if not os.path.exists(json_path):
        return
    
    with open(json_path, 'r') as f:
        products_data = json.load(f)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
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
            
            # Insert into products table
            cursor.execute('''
                INSERT OR REPLACE INTO products (id, name, price, inventory, image_data, image_mime_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (product_id, name, price, inventory, image_data, image_mime_type))
            
            # Insert all fields into product_fields table
            for field in fields:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_fields 
                    (product_id, field_name, label, value, editable, field_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    product_id,
                    field['fieldName'],
                    field['label'],
                    field['value'],
                    field.get('editable', 'true'),
                    field.get('fieldType', 'TEXT')
                ))
        
        conn.commit()

def get_all_products() -> Dict[str, List[Dict[str, Any]]]:
    """Get all products in the legacy format"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all product IDs
        cursor.execute('SELECT id FROM products')
        product_ids = [row['id'] for row in cursor.fetchall()]
        
        result = {}
        for product_id in product_ids:
            # Get all fields for this product
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

def get_product(product_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get a single product by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        
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
        
        return fields if fields else None

def save_product(product_id: str, fields: List[Dict[str, Any]], image_data: Optional[bytes] = None, image_mime_type: Optional[str] = None):
    """Save or update a product"""
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
        cursor.execute('SELECT id FROM products WHERE id = ?', (product_id,))
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update existing product
            if image_data is not None:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, price = ?, inventory = ?, image_data = ?, image_mime_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, price, inventory, image_data, image_mime_type, product_id))
            else:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, price = ?, inventory = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, price, inventory, product_id))
        else:
            # Insert new product
            cursor.execute('''
                INSERT INTO products (id, name, price, inventory, image_data, image_mime_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (product_id, name, price, inventory, image_data, image_mime_type))
        
        # Delete existing fields
        cursor.execute('DELETE FROM product_fields WHERE product_id = ?', (product_id,))
        
        # Insert all fields
        for field in fields:
            cursor.execute('''
                INSERT INTO product_fields 
                (product_id, field_name, label, value, editable, field_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                product_id,
                field['fieldName'],
                field['label'],
                field['value'],
                field.get('editable', 'true'),
                field.get('fieldType', 'TEXT')
            ))
        
        conn.commit()

def delete_product(product_id: str):
    """Delete a product"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()

def get_product_image(product_id: str) -> Optional[tuple[bytes, str]]:
    """Get product image data and mime type"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT image_data, image_mime_type FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        
        if row and row['image_data']:
            return row['image_data'], row['image_mime_type']
        return None