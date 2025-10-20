import base64
from app.models import TenantModel

class AuthService:
    """Service for authentication logic"""

    @staticmethod
    def check_basic_auth(auth_header: str, tenant_id: str) -> bool:
        """Validate Basic authentication credentials for a tenant"""
        if not auth_header or not auth_header.startswith('Basic '):
            return False

        try:
            # Decode the base64 credentials
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)

            # Get tenant credentials from database (without creating)
            tenant = TenantModel.get_by_id(tenant_id)
            if tenant and username == tenant['username'] and password == tenant['password']:
                return True
        except Exception:
            pass

        return False
