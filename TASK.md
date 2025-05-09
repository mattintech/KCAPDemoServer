# Task List - Flask AR API Demo

## Phase 1: Basic Admin UI ✅

* [x] Create a simple admin UI (no authentication required for demo purposes).
* [x] Allow adding, updating, and deleting products.
* [x] Store all product data in a `products.json` file for persistence.
* [x] Store images in the `static/images/` directory.
* [x] Implement basic form validation for product fields (ID, price, image).
* [x] Add a file upload feature for product images.

## Phase 2: API Improvements

* [x] Update the `/arinfo` endpoint to read from `products.json` instead of the in-memory dictionary.
* [ ] Add support for updating product attributes via the API.
* [x] Implement error handling and input validation.
* [ ] Optimize image loading for better performance.

## Phase 3: UI Enhancements

* [x] Add a responsive design for mobile and tablet support.
* [x] Include image previews in the admin UI.
* [ ] Add sorting and search capabilities for the product list.
* [x] Add barcode and QR code generation for products.

## Implementation Notes

* The APIs and admin UI have been implemented as a single server for demonstration purposes.
* The API endpoints and admin interface are now served by the same Flask application.
* Bootstrap 5 has been used for responsive UI design.
* Basic validation has been implemented for product forms.
* Flash messages provide user feedback for actions.
* Barcode generation features support three formats:
  * QR Code: Links directly to the product's AR information endpoint
  * EAN-13: Standard barcode format for retail products
  * Code 128: High-density alphanumeric barcode
* Generated barcodes can be previewed, downloaded individually, or printed all at once.
* Barcodes are dynamically generated and stored in the `static/barcodes/` directory.

## Future Ideas

* [ ] Write basic unit tests for the API.
* [ ] Dockerize the application for easier deployment.
* [ ] Add a basic CI/CD pipeline (e.g., GitHub Actions or GitLab CI).
* [ ] Add user authentication for the admin UI.
* [ ] Implement role-based access control (RBAC).
* [ ] Add analytics for product views and updates.
* [ ] Integrate with a database for larger product catalogs.
* [ ] Add bulk import/export functionality for products.
* [ ] Implement a mobile-friendly scanner interface for testing the AR functionality.
