"""Authentication routes for Entra ID login/logout and no-auth mode"""
import secrets
from flask import session, redirect, url_for, request, current_app, render_template, flash
from . import auth_bp
from app.models.user import UserModel


@auth_bp.route('/login')
def login():
    """Initiate Entra ID login flow or redirect to role selection in no-auth mode"""
    # Check if we're in no-auth mode
    if current_app.config.get('AUTH_MODE') == 'none':
        return redirect(url_for('auth.select_role'))

    # Entra ID mode
    from app.services.msal_service import MSALService

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(16)
    session['auth_state'] = state

    # Store the original requested URL to redirect after login
    if 'next' not in session and request.args.get('next'):
        session['next'] = request.args.get('next')

    # Get authorization URL from MSAL
    auth_url = MSALService.get_auth_url(state=state)

    return redirect(auth_url)


@auth_bp.route('/select-role', methods=['GET', 'POST'])
def select_role():
    """Role selection page for no-auth mode"""
    # Only available in no-auth mode
    if current_app.config.get('AUTH_MODE') != 'none':
        flash('Role selection is only available in no-auth mode', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        role = request.form.get('role', 'user')

        # Validate role
        if role not in ['admin', 'user']:
            role = 'user'

        # Create a mock user for testing
        # Use a consistent ID based on role for session persistence
        user_id = f"test-{role}-user"

        # Store user in session
        session['user'] = {
            'id': user_id,
            'email': f'{role}@test.local',
            'name': f'Test {role.capitalize()}',
            'role': role
        }

        current_app.logger.info(f"No-auth mode: User selected {role} role")

        # Redirect to the originally requested page or home
        next_url = session.pop('next', None)
        if next_url:
            return redirect(next_url)

        return redirect(url_for('main.index'))

    return render_template('select_role.html')


@auth_bp.route('/callback')
def callback():
    """Handle the callback from Entra ID after authentication"""
    # Import MSAL service only when needed (Entra ID mode)
    from app.services.msal_service import MSALService

    # Verify state to prevent CSRF
    state = request.args.get('state')
    if state != session.get('auth_state'):
        current_app.logger.error("State mismatch in auth callback - possible CSRF attack")
        flash('Authentication failed: Invalid state parameter', 'error')
        return redirect(url_for('main.index'))

    # Clear the state
    session.pop('auth_state', None)

    # Check for errors
    if 'error' in request.args:
        error = request.args.get('error')
        error_description = request.args.get('error_description', 'Unknown error')
        current_app.logger.error(f"Auth error: {error} - {error_description}")
        flash(f'Authentication failed: {error_description}', 'error')
        return redirect(url_for('main.index'))

    # Get authorization code
    auth_code = request.args.get('code')
    if not auth_code:
        flash('Authentication failed: No authorization code received', 'error')
        return redirect(url_for('main.index'))

    # Exchange code for token
    token_response = MSALService.acquire_token_by_auth_code(auth_code)

    if 'error' in token_response:
        error = token_response.get('error')
        error_description = token_response.get('error_description', 'Unknown error')
        current_app.logger.error(f"Token error: {error} - {error_description}")
        flash(f'Authentication failed: {error_description}', 'error')
        return redirect(url_for('main.index'))

    # Get user info from Microsoft Graph
    access_token = token_response.get('access_token')
    user_info = MSALService.get_user_info(access_token)

    if not user_info:
        flash('Failed to retrieve user information', 'error')
        return redirect(url_for('main.index'))

    # Get or create user in database
    user = UserModel.get_or_create_from_azure(
        email=user_info['email'],
        name=user_info['name'],
        azure_oid=user_info['azure_oid'],
        default_admin_email=current_app.config['DEFAULT_ADMIN_EMAIL']
    )

    # Store user in session
    session['user'] = {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'role': user['role']
    }

    current_app.logger.info(f"User {user['email']} logged in successfully")

    # Redirect to the originally requested page or home
    next_url = session.pop('next', None)
    if next_url:
        return redirect(next_url)

    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
def logout():
    """Log out the current user"""
    if 'user' in session:
        user_email = session['user'].get('email')
        current_app.logger.info(f"User {user_email} logged out")

    # Clear session
    session.clear()

    # Check if we're in no-auth mode
    if current_app.config.get('AUTH_MODE') == 'none':
        # Just redirect to home in no-auth mode
        return redirect(url_for('main.index'))

    # Entra ID mode - logout from Azure AD
    from app.services.msal_service import MSALService

    # Remove from MSAL cache
    MSALService.remove_account()

    # Redirect to Azure AD logout
    logout_url = (
        f"{current_app.config['AUTHORITY']}{current_app.config['AZURE_TENANT_ID']}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={request.url_root}"
    )

    return redirect(logout_url)


@auth_bp.route('/unauthorized')
def unauthorized():
    """Show unauthorized access page"""
    return render_template('unauthorized.html'), 403
