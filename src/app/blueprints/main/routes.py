from flask import render_template, request, redirect, flash
from . import main_bp
from app.models import TenantModel, SettingsModel

@main_bp.route('/')
def index():
    """Tenant selection page"""
    tenants = TenantModel.get_all()
    server_url = SettingsModel.get_server_url()
    return render_template('tenant_selection.html', tenants=tenants, server_url=server_url)

@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Global settings page"""
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
