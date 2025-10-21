from typing import Dict, List, Any
from .base import get_db

class ARFieldModel:
    """Model for custom AR field operations"""

    @staticmethod
    def get_all(tenant_id: str) -> List[Dict[str, Any]]:
        """Get all custom AR fields for a tenant"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, field_name, label, field_type, editable, display_order
                FROM custom_ar_fields
                WHERE tenant_id = ?
                ORDER BY display_order, id
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

    @staticmethod
    def save(tenant_id: str, field_data: Dict[str, Any]):
        """Save or update a custom AR field"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()

            if 'id' in field_data and field_data['id']:
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
                    field_data['editable'],
                    field_data['displayOrder'],
                    field_data['id'],
                    tenant_id
                ))
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
                    field_data['editable'],
                    field_data['displayOrder']
                ))

            conn.commit()

    @staticmethod
    def delete(tenant_id: str, field_id: int):
        """Delete a custom AR field"""
        tenant_id = tenant_id.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM custom_ar_fields WHERE id = ? AND tenant_id = ?',
                          (field_id, tenant_id))
            conn.commit()

    @staticmethod
    def create_default_fields(tenant_id: str):
        """Create default product fields for a new tenant"""
        tenant_id = tenant_id.lower()

        default_fields = [
            {
                'fieldName': '_name',
                'label': 'Product Name',
                'fieldType': 'TEXT',
                'editable': 'true',
                'displayOrder': 0
            },
            {
                'fieldName': '_id',
                'label': 'Item ID',
                'fieldType': 'TEXT',
                'editable': 'false',
                'displayOrder': 1
            },
            {
                'fieldName': '_price',
                'label': 'Sale Price',
                'fieldType': 'TEXT',
                'editable': 'true',
                'displayOrder': 2
            },
            {
                'fieldName': '_image',
                'label': 'Image',
                'fieldType': 'IMAGE_URI',
                'editable': 'true',
                'displayOrder': 3
            }
        ]

        with get_db() as conn:
            cursor = conn.cursor()
            for field in default_fields:
                cursor.execute('''
                    INSERT INTO custom_ar_fields
                    (tenant_id, field_name, label, field_type, editable, display_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tenant_id,
                    field['fieldName'],
                    field['label'],
                    field['fieldType'],
                    field['editable'],
                    field['displayOrder']
                ))
            conn.commit()
