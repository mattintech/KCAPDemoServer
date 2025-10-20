"""User model for authentication and authorization"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from .base import get_db


class UserModel:
    """Model for managing users and their roles"""

    ROLE_USER = 'user'
    ROLE_ADMIN = 'admin'

    @staticmethod
    def create_table():
        """Create the users and user_tenants tables if they don't exist"""
        with get_db() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    azure_oid TEXT UNIQUE,
                    name TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # User-Tenant association table (users can own multiple tenants)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_tenants (
                    user_id INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, tenant_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                )
            ''')

            conn.commit()

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        """Get user by email address"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, email, azure_oid, name, role, created_at, updated_at FROM users WHERE email = ?',
                (email,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'azure_oid': row[2],
                    'name': row[3],
                    'role': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, email, azure_oid, name, role, created_at, updated_at FROM users WHERE id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'azure_oid': row[2],
                    'name': row[3],
                    'role': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None

    @staticmethod
    def get_by_azure_oid(azure_oid: str) -> Optional[Dict]:
        """Get user by Azure Object ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, email, azure_oid, name, role, created_at, updated_at FROM users WHERE azure_oid = ?',
                (azure_oid,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'azure_oid': row[2],
                    'name': row[3],
                    'role': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None

    @staticmethod
    def create(email: str, name: str = None, azure_oid: str = None, role: str = ROLE_USER) -> Dict:
        """Create a new user"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO users (email, azure_oid, name, role)
                   VALUES (?, ?, ?, ?)''',
                (email, azure_oid, name, role)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return UserModel.get_by_id(user_id)

    @staticmethod
    def update(user_id: int, **kwargs) -> Optional[Dict]:
        """Update user information"""
        allowed_fields = {'email', 'azure_oid', 'name', 'role'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not update_fields:
            return UserModel.get_by_id(user_id)

        update_fields['updated_at'] = datetime.now().isoformat()

        set_clause = ', '.join([f'{k} = ?' for k in update_fields.keys()])
        values = list(update_fields.values())
        values.append(user_id)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE users SET {set_clause} WHERE id = ?',
                values
            )
            conn.commit()
            return UserModel.get_by_id(user_id)

    @staticmethod
    def get_or_create_from_azure(email: str, name: str = None, azure_oid: str = None, default_admin_email: str = None) -> Dict:
        """Get existing user or create new one from Azure AD login"""
        # Try to find by Azure OID first
        if azure_oid:
            user = UserModel.get_by_azure_oid(azure_oid)
            if user:
                # Update email/name if changed
                if user['email'] != email or user['name'] != name:
                    return UserModel.update(user['id'], email=email, name=name)
                return user

        # Try to find by email
        user = UserModel.get_by_email(email)
        if user:
            # Update Azure OID if not set
            if azure_oid and not user['azure_oid']:
                return UserModel.update(user['id'], azure_oid=azure_oid, name=name)
            return user

        # Create new user
        # Case-insensitive comparison for admin email
        role = UserModel.ROLE_ADMIN if (default_admin_email and email.lower() == default_admin_email.lower()) else UserModel.ROLE_USER
        return UserModel.create(email=email, name=name, azure_oid=azure_oid, role=role)

    @staticmethod
    def add_tenant(user_id: int, tenant_id: str):
        """Associate a tenant with a user"""
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO user_tenants (user_id, tenant_id) VALUES (?, ?)',
                    (user_id, tenant_id)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Already exists, that's fine
                pass

    @staticmethod
    def remove_tenant(user_id: int, tenant_id: str):
        """Remove tenant association from user"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_tenants WHERE user_id = ? AND tenant_id = ?',
                (user_id, tenant_id)
            )
            conn.commit()

    @staticmethod
    def get_user_tenants(user_id: int) -> List[str]:
        """Get all tenant IDs associated with a user"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT tenant_id FROM user_tenants WHERE user_id = ?',
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def has_access_to_tenant(user_id: int, tenant_id: str) -> bool:
        """Check if user has access to a specific tenant"""
        # Admin has access to everything
        user = UserModel.get_by_id(user_id)
        if user and user['role'] == UserModel.ROLE_ADMIN:
            return True

        # Check if user owns the tenant
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM user_tenants WHERE user_id = ? AND tenant_id = ?',
                (user_id, tenant_id)
            )
            return cursor.fetchone() is not None

    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Check if user has admin role"""
        user = UserModel.get_by_id(user_id)
        return user and user['role'] == UserModel.ROLE_ADMIN

    @staticmethod
    def get_all() -> List[Dict]:
        """Get all users"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, email, azure_oid, name, role, created_at, updated_at FROM users ORDER BY email'
            )
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'email': row[1],
                'azure_oid': row[2],
                'name': row[3],
                'role': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            } for row in rows]
