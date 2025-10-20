from typing import Dict, List, Any
from app.models import ProductModel, ARFieldModel
from flask import request

class ProductService:
    """Service for product business logic"""

    @staticmethod
    def filter_and_process_fields(product_fields: List[Dict[str, Any]],
                                   tenant_id: str,
                                   custom_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter product fields to only include defined AR fields and process image URLs"""
        custom_field_names = [f['fieldName'] for f in custom_fields]
        field_types = {f['fieldName']: f['fieldType'] for f in custom_fields}
        filtered_fields = []

        for field in product_fields:
            if field['fieldName'] in custom_field_names:
                # Create absolute URL for IMAGE_URI fields
                if field_types.get(field['fieldName']) == 'IMAGE_URI' and field['value']:
                    # If it's already an absolute URL, leave it as is
                    if not field['value'].startswith('http'):
                        # Build absolute URL using request host with tenant
                        field['value'] = f"{request.url_root.rstrip('/')}/{tenant_id}{field['value']}"
                filtered_fields.append(field)

        return filtered_fields

    @staticmethod
    def get_all_products_filtered(tenant_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all products with filtered fields"""
        products = ProductModel.get_all(tenant_id)
        custom_fields = ARFieldModel.get_all(tenant_id)

        all_products = {}
        for product_id, fields in products.items():
            all_products[product_id] = ProductService.filter_and_process_fields(
                fields, tenant_id, custom_fields
            )

        return all_products

    @staticmethod
    def get_product_filtered(product_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Get a single product with filtered fields"""
        product = ProductModel.get_by_id(product_id, tenant_id)
        if not product:
            return None

        custom_fields = ARFieldModel.get_all(tenant_id)
        return ProductService.filter_and_process_fields(product, tenant_id, custom_fields)

    @staticmethod
    def allowed_file(filename: str, allowed_extensions: set) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
