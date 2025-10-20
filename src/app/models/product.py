from typing import Dict, List, Optional, Any, Tuple
from .base import get_db

class ProductModel:
    """Model for product operations"""

    @staticmethod
    def get_all(tenant_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all products for a tenant in the legacy format"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT id FROM products WHERE tenant_id = ?', (tenant_id,))
            product_ids = [row['id'] for row in cursor.fetchall()]

            result = {}
            for product_id in product_ids:
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

                result[product_id] = fields

            return result

    @staticmethod
    def get_by_id(product_id: str, tenant_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get a single product by ID and tenant"""
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

    @staticmethod
    def save(product_id: str, tenant_id: str, fields: List[Dict[str, Any]],
             image_data: Optional[bytes] = None, image_mime_type: Optional[str] = None):
        """Save or update a product for a tenant"""
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

    @staticmethod
    def delete(product_id: str, tenant_id: str):
        """Delete a product for a tenant"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ? AND tenant_id = ?', (product_id, tenant_id))
            conn.commit()

    @staticmethod
    def get_image(product_id: str, tenant_id: str) -> Optional[Tuple[bytes, str]]:
        """Get product image data and mime type for a tenant"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT image_data, image_mime_type FROM products WHERE id = ? AND tenant_id = ?',
                          (product_id, tenant_id))
            row = cursor.fetchone()

            if row and row['image_data']:
                return row['image_data'], row['image_mime_type']
            return None

    @staticmethod
    def save_image(product_id: str, tenant_id: str, field_name: str,
                   image_data: bytes, image_mime_type: str):
        """Save an image for a specific product field"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO product_images
                (product_id, tenant_id, field_name, image_data, image_mime_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, tenant_id, field_name, image_data, image_mime_type))
            conn.commit()

    @staticmethod
    def get_image_by_field(product_id: str, tenant_id: str, field_name: str) -> Optional[Tuple[bytes, str]]:
        """Get image for a specific product field"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT image_data, image_mime_type
                FROM product_images
                WHERE product_id = ? AND tenant_id = ? AND field_name = ?
            ''', (product_id, tenant_id, field_name))
            row = cursor.fetchone()

            if row:
                return row['image_data'], row['image_mime_type']
            return None
