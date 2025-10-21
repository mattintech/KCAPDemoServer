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

### Option 1: Docker Hub (Recommended)

Pull and run the pre-built image from Docker Hub:

```bash
# Pull the latest image
docker pull mattintech/kcapdemoserver:latest

# Run the container
docker run -p 5555:5000 \
  -e SECRET_KEY=your-secret-key-here \
  -e DATABASE_URL=sqlite:///data/kcap_demo.db \
  -v $(pwd)/data:/app/data \
  mattintech/kcapdemoserver:latest
```

Or use a specific version:

```bash
docker pull mattintech/kcapdemoserver:v1.0.0
docker run -p 5555:5000 --env-file .env mattintech/kcapdemoserver:v1.0.0
```

### Option 2: Docker Compose

1. **Clone the Repository:**

```bash
git clone https://github.com/mattintech/KCAPDemoServer.git
cd KCAPDemoServer
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

### Option 3: Local Python Setup

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

## Docker Hub

Pre-built Docker images are automatically published to Docker Hub on each release:

**Repository**: [mattintech/kcapdemoserver](https://hub.docker.com/r/mattintech/kcapdemoserver)

**Available Tags**:
- `latest` - Most recent release
- `v1.0.0`, `v1.0.1`, etc. - Specific version releases

For maintainers: See [DOCKER_HUB_SETUP.md](DOCKER_HUB_SETUP.md) for information on configuring automated builds.

## Implementation Notes

* The application is designed as a single server hosting both the API endpoints and admin interface.
* Product data is stored in a JSON file (products.json) for simplicity and easy demonstration.
* All features are implemented without authentication for demo purposes.
* The application uses Bootstrap 5 for responsive UI design.
