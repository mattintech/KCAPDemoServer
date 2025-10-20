"""Authentication and authorization decorators"""
from functools import wraps
from flask import session, redirect, url_for, request, abort, current_app
from app.models.user import UserModel


def login_required(f):
    """
    Decorator to require user authentication.
    Redirects to login if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Store the requested URL to redirect back after login
            session['next'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin role.
    Returns 403 if user is not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        user_id = session['user'].get('id')
        if not UserModel.is_admin(user_id):
            current_app.logger.warning(f"User {user_id} attempted to access admin route without permission")
            abort(403, description="Admin access required")

        return f(*args, **kwargs)
    return decorated_function


def tenant_access_required(f):
    """
    Decorator to require access to the specific tenant in the URL.
    User must either be an admin or have explicit access to the tenant.
    Admins can see server settings, regular users cannot.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        user_id = session['user'].get('id')
        tenant_id = kwargs.get('tenant_id')

        if not tenant_id:
            # No tenant in URL, allow access (e.g., global settings for admins only)
            return f(*args, **kwargs)

        # Check if user has access to this tenant
        if not UserModel.has_access_to_tenant(user_id, tenant_id):
            current_app.logger.warning(
                f"User {user_id} attempted to access tenant {tenant_id} without permission"
            )
            abort(403, description="You don't have access to this tenant")

        return f(*args, **kwargs)
    return decorated_function


def settings_access_required(f):
    """
    Decorator for server settings pages - admin only.
    Regular users cannot see server settings.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        user_id = session['user'].get('id')
        if not UserModel.is_admin(user_id):
            current_app.logger.warning(
                f"User {user_id} attempted to access server settings without admin permission"
            )
            abort(403, description="Admin access required to view server settings")

        return f(*args, **kwargs)
    return decorated_function
