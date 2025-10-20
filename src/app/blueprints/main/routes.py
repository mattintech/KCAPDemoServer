from flask import render_template, request, redirect, flash, session
from . import main_bp
from app.models import TenantModel, SettingsModel, UserModel
from app.decorators.auth import login_required, settings_access_required

@main_bp.route('/')
@login_required
def index():
    """Tenant selection page"""
    user_id = session['user']['id']
    user = UserModel.get_by_id(user_id)

    # Admins see all tenants, users only see their own
    if user['role'] == UserModel.ROLE_ADMIN:
        tenants = TenantModel.get_all()
    else:
        tenant_ids = UserModel.get_user_tenants(user_id)
        tenants = [TenantModel.get_by_id(tid) for tid in tenant_ids if TenantModel.get_by_id(tid)]

    server_url = SettingsModel.get_server_url()
    return render_template('tenant_selection.html', tenants=tenants, server_url=server_url)

@main_bp.route('/settings', methods=['GET', 'POST'])
@settings_access_required
def settings():
    """Global settings page - admin only"""
    if request.method == 'POST':
        server_url = request.form.get('server_url', '').strip()
        if server_url:
            # Remove trailing slash for consistency
            server_url = server_url.rstrip('/')
            SettingsModel.set('server_url', server_url)
            flash('Server settings updated successfully.', 'success')
        else:
            flash('Please provide a valid server URL.', 'error')
        return redirect('/settings')

    server_url = SettingsModel.get_server_url()
    return render_template('settings.html', server_url=server_url)
