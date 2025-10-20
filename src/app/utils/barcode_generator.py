# Utility for barcode generation
import os
import io
from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    from barcode import EAN13, Code128
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

class BarcodeGenerator:
    @staticmethod
    def check_dependencies():
        return {
            'qrcode': QRCODE_AVAILABLE,
            'barcode': BARCODE_AVAILABLE,
            'pillow': True
        }

    @staticmethod
    def generate_qr_code(data, size=10, border=4):
        if not QRCODE_AVAILABLE:
            return BarcodeGenerator._generate_placeholder("QR Code Unavailable\nPlease install 'qrcode' package")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        return img

    @staticmethod
    def generate_ean13_barcode(data):
        if not BARCODE_AVAILABLE:
            return BarcodeGenerator._generate_placeholder("EAN-13 Unavailable\nPlease install 'python-barcode' package")
        # EAN-13 requires 12 digits (13th is checksum, auto-calculated)
        numeric = ''.join(filter(str.isdigit, str(data)))
        if len(numeric) < 12:
            numeric = numeric.zfill(12)
        elif len(numeric) > 12:
            numeric = numeric[:12]
        ean = EAN13(numeric, writer=ImageWriter())
        output = io.BytesIO()
        ean.write(output)
        output.seek(0)
        img = Image.open(output)
        return img

    @staticmethod
    def generate_code128_barcode(data):
        if not BARCODE_AVAILABLE:
            return BarcodeGenerator._generate_placeholder("Code 128 Unavailable\nPlease install 'python-barcode' package")
        code128 = Code128(str(data), writer=ImageWriter())
        output = io.BytesIO()
        code128.write(output)
        output.seek(0)
        img = Image.open(output)
        return img

    @staticmethod
    def _generate_placeholder(message):
        img = Image.new('RGB', (300, 150), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 299, 149], outline=(0, 0, 0), width=2)
        # Optionally, add multiline text
        lines = message.split('\n')
        y = 60
        for line in lines:
            d.text((20, y), line, fill=(0, 0, 0))
            y += 20
        return img

    @staticmethod
    def save_image(image, path):
        image.save(path, format='PNG')

    @staticmethod
    def get_image_as_bytes(image, format='PNG'):
        buf = io.BytesIO()
        image.save(buf, format=format)
        buf.seek(0)
        return buf.read()
