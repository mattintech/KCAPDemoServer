from typing import Optional
from .base import get_db

class SettingsModel:
    """Model for application settings"""

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    @staticmethod
    def set(key: str, value: str):
        """Set a setting value"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()

    @staticmethod
    def get_server_url() -> str:
        """Get server URL setting"""
        return SettingsModel.get('server_url', 'http://localhost:5555')
