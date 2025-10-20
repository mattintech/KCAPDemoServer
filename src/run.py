import os
import shutil
from app import create_app
from app.models import TenantModel

# Create application
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    with app.app_context():
        # Migrate existing data from JSON if needed (backward compatibility)
        # Note: This is for the old database.py migration - keeping for reference
        # but in the new structure, this would be handled differently

        # Clean up any accidentally created reserved tenants
        deleted_count = TenantModel.cleanup_reserved()
        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} reserved tenant(s)")

    app.run(port=5555, host="0.0.0.0", debug=True)
