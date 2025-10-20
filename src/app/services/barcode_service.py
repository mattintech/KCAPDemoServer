import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

class BarcodeService:
    """Service for barcode generation"""

    @staticmethod
    def generate_qr_code(data: str) -> BytesIO:
        """Generate QR code image"""
        buffer = BytesIO()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_ean13(product_id: str) -> BytesIO:
        """Generate EAN-13 barcode"""
        buffer = BytesIO()
        # Convert product_id to numeric format if needed
        numeric_id = ''.join(filter(str.isdigit, product_id))
        if not numeric_id:
            numeric_id = str(abs(hash(product_id)) % 1000000000000)[:12]
        else:
            numeric_id = numeric_id[:12].zfill(12)

        EAN = barcode.get_barcode_class('ean13')
        ean = EAN(numeric_id, writer=ImageWriter())
        ean.write(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_code128(product_id: str) -> BytesIO:
        """Generate Code 128 barcode"""
        buffer = BytesIO()
        CODE128 = barcode.get_barcode_class('code128')
        code = CODE128(product_id, writer=ImageWriter())
        code.write(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_barcode(product_id: str, code_type: str, url: str = None) -> BytesIO:
        """Generate barcode based on type"""
        if code_type == 'qr':
            return BarcodeService.generate_qr_code(url or product_id)
        elif code_type == 'ean13':
            return BarcodeService.generate_ean13(product_id)
        elif code_type == 'code128':
            return BarcodeService.generate_code128(product_id)
        else:
            raise ValueError(f"Unsupported barcode type: {code_type}")
