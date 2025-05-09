# Flask AR API Demo

This project is a simple Flask API for demonstrating AR content retrieval for barcode scanning applications. It simulates the Knox Capture API for AR overlays and includes endpoints for managing product attributes, including text and image URLs.

## Features

* **Login Endpoint (`/login`)**

  * Simulates a simple login with a 200 response (no authentication required for demo purposes).
* **Content Fields Endpoint (`/arcontentfields`)**

  * Returns a list of available attributes (e.g., item ID, price, image URI).
* \*\*AR Info Endpoint (`/arinfo`)

  * Returns product details for a given barcode, including image URLs.
* \*\*Static Image Server (`/images/<filename>`)

  * Serves image files from the `static/images/` directory.

## Setup

1. **Clone the Repository:**

```bash
git clone <repository_url>
cd <repository_folder>
```

2. **Create the Static Directory:**

```bash
mkdir -p static/images
```

3. **Add Sample Images:**

* Place sample product images in the `static/images/` directory.
* Ensure the filenames match the item IDs used in the app (e.g., `123456.png`, `789012.png`).

4. **Install Dependencies:**

```bash
pip install flask
```

5. **Run the Server:**

```bash
python app.py
```

6. **Test the Endpoints:**

* Login: `GET http://localhost:5555/login`
* Content Fields: `GET http://localhost:5555/arcontentfields`
* AR Info (Example): `GET http://localhost:5555/arinfo?barcode=123456`
* Image File (Example): `GET http://localhost:5555/images/123456.png`

## Future Enhancements

* Add a basic admin UI for adding and managing products.
* Store product data in a JSON file for persistence.
* Add image upload capabilities through the admin UI.
