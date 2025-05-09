# Task List - Flask AR API Demo

## Phase 1: Basic Admin UI

* [ ] Create a simple admin UI (no authentication required for demo purposes).
* [ ] Allow adding, updating, and deleting products.
* [ ] Store all product data in a `products.json` file for persistence.
* [ ] Store images in the `static/images/` directory.
* [ ] Implement basic form validation for product fields (ID, price, image).
* [ ] Add a file upload feature for product images.

## Phase 2: API Improvements

* [ ] Update the `/arinfo` endpoint to read from `products.json` instead of the in-memory dictionary.
* [ ] Add support for updating product attributes via the API.
* [ ] Implement error handling and input validation.
* [ ] Optimize image loading for better performance.

## Phase 3: UI Enhancements

* [ ] Add a responsive design for mobile and tablet support.
* [ ] Include image previews in the admin UI.
* [ ] Add sorting and search capabilities for the product list.

## Future Ideas

* [ ] Write basic unit tests for the API.
* [ ] Dockerize the application for easier deployment.
* [ ] Add a basic CI/CD pipeline (e.g., GitHub Actions or GitLab CI).
* [ ] Add user authentication for the admin UI.
* [ ] Implement role-based access control (RBAC).
* [ ] Add analytics for product views and updates.
* [ ] Integrate with a database for larger product catalogs.
