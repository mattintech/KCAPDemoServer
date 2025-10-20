# Flask AR API Demo

This project is a simple Flask API for demonstrating AR content retrieval for barcode scanning applications. It simulates the Knox Capture API for AR overlays and includes endpoints for managing product attributes, including text and image URLs. The application includes a full admin interface for product management and barcode generation.

## Features

### API Endpoints

* **Login Endpoint (`/login`)**
  * Simulates a simple login with a 200 response (no authentication required for demo purposes).

* **Content Fields Endpoint (`/arcontentfields`)**
  * Returns a list of available attributes (e.g., item ID, price, image URI).

* **AR Info Endpoint (`/arinfo?barcode=<id>`)**
  * Returns product details for a given barcode, including image URLs.

* **Static Image Server (`/images/<filename>`)**
  * Serves image files from the `static/images/` directory.

* **Barcode Image Server (`/barcodes/<filename>`)**
  * Serves generated barcode images from the `static/barcodes/` directory.

### Admin Interface

* **Product Management**
  * Add, edit, and delete products
  * Upload product images
  * View product details

* **Barcode Generation**
  * Generate QR codes linking to product AR info
  * Generate EAN-13 barcodes for retail use
  * Generate Code 128 barcodes for general use
  * Download or print all barcode formats

## Setup

### Option 1: Docker (Recommended)

1. **Clone the Repository:**

```bash
git clone <repository_url>
cd <repository_folder>
```

2. **Configure Environment:**

Copy `.env.example` to `.env` and update with your Azure AD credentials:

```bash
cp .env.example .env
```

Edit `.env` and set your Azure AD configuration values.

3. **Run with Docker Compose:**

```bash
docker-compose up -d
```

The application will be available at `http://localhost:5555`

4. **View Logs:**

```bash
docker-compose logs -f
```

5. **Stop the Application:**

```bash
docker-compose down
```

### Option 2: Local Python Setup

1. **Clone the Repository:**

```bash
git clone <repository_url>
cd <repository_folder>
```

2. **Install Dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure Environment:**

Copy `.env.example` to `.env` and update with your configuration.

4. **Run the Server:**

```bash
python src/run.py
```

The application will automatically create the necessary directories and initialize the database if it doesn't exist.

### Accessing the Application

**Admin Interface:**
```
http://localhost:5555/admin
```

**API Endpoints:**
* Login: `GET http://localhost:5555/login`
* Content Fields: `GET http://localhost:5555/arcontentfields`
* AR Info (Example): `GET http://localhost:5555/arinfo?barcode=123456`
* Image File (Example): `GET http://localhost:5555/images/123456.png`

## Using Barcode Generation

1. Navigate to the admin interface at `/admin`
2. Find the product you want to generate barcodes for
3. Click the "Barcodes" button in the Actions column
4. View, download, or print the generated barcodes

The following barcode types are available:
* **QR Code**: Contains a link to the product's AR info endpoint
* **EAN-13**: Standard barcode format used in retail
* **Code 128**: High-density alphanumeric barcode format

## Project Structure

```
/
├── app.py                # Main Flask application
├── admin.py              # Admin blueprint with routes
├── barcode_generator.py  # Barcode generation utilities
├── requirements.txt      # Python dependencies
├── static/
│   ├── images/           # Product images
│   ├── barcodes/         # Generated barcode images
│   └── products.json     # Product data storage
└── templates/
    ├── index.html        # Home page
    ├── layout.html       # Base template
    └── admin/            # Admin interface templates
        ├── index.html            # Product list
        ├── add_product.html      # Add product form
        ├── edit_product.html     # Edit product form
        └── generate_barcode.html # Barcode generation page
```

## Implementation Notes

* The application is designed as a single server hosting both the API endpoints and admin interface.
* Product data is stored in a JSON file (products.json) for simplicity and easy demonstration.
* All features are implemented without authentication for demo purposes.
* The application uses Bootstrap 5 for responsive UI design.
