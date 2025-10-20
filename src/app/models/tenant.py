from .base import get_db
from flask import current_app

class TenantModel:
    """Model for tenant operations"""

    @staticmethod
    def get_all():
        """Get all tenants"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tenants ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(tenant_id):
        """Get tenant by ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tenants WHERE id = ?', (tenant_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(tenant_id, name=None):
        """Create a new tenant"""
        # Check if tenant_id is reserved
        if tenant_id.lower() in current_app.config['RESERVED_TENANT_IDS']:
            return None

        if name is None:
            name = tenant_id

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO tenants (id, name, username, password) VALUES (?, ?, ?, ?)',
                    (tenant_id, name, 'admin', 'password')
                )
                conn.commit()
                return TenantModel.get_by_id(tenant_id)
            except Exception:
                return None

    @staticmethod
    def get_or_create(tenant_id):
        """Get existing tenant or create new one"""
        tenant = TenantModel.get_by_id(tenant_id)
        if tenant:
            return tenant
        return TenantModel.create(tenant_id)

    @staticmethod
    def update_credentials(tenant_id, username, password):
        """Update tenant credentials"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tenants SET username = ?, password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (username, password, tenant_id)
            )
            conn.commit()

    @staticmethod
    def update_barcode_type(tenant_id, barcode_type):
        """Update tenant barcode type preference"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tenants SET barcode_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (barcode_type, tenant_id)
            )
            conn.commit()

    @staticmethod
    def delete(tenant_id):
        """Delete a tenant and all associated data"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tenants WHERE id = ?', (tenant_id,))
            conn.commit()

    @staticmethod
    def cleanup_reserved():
        """Clean up any accidentally created reserved tenants"""
        reserved = current_app.config['RESERVED_TENANT_IDS']
        with get_db() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(reserved))
            cursor.execute(
                f'DELETE FROM tenants WHERE LOWER(id) IN ({placeholders})',
                tuple(reserved)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
