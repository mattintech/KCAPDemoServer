import os
import io
from PIL import Image, ImageDraw, ImageFont

# Try to import barcode libraries, provide fallback if not available
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
    """
    A utility class for generating QR codes and barcodes.
    """
    
    @staticmethod
    def check_dependencies():
        """
        Check if all required dependencies are installed.
        
        Returns:
            dict: Status of each dependency
        """
        return {
            'qrcode': QRCODE_AVAILABLE,
            'barcode': BARCODE_AVAILABLE,
            'pillow': True  # PIL/Pillow is imported directly at the top level
        }
    
    @staticmethod
    def generate_qr_code(data, size=10, border=4):
        """
        Generates a QR code as a PIL Image object.
        
        Args:
            data (str): The data to encode in the QR code
            size (int): The size of the QR code (1-40)
            border (int): The border size of the QR code
            
        Returns:
            PIL.Image: The generated QR code image or a placeholder image if qrcode is not available
        """
        if not QRCODE_AVAILABLE:
            return BarcodeGenerator._generate_placeholder("QR Code Unavailable\nPlease install 'qrcode' package")
        
        qr = qrcode.QRCode(
            version=size,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    
    @staticmethod
    def generate_ean13_barcode(data):
        """
        Generates an EAN-13 barcode as a PIL Image object.
        
        Args:
            data (str): The data to encode in the barcode (must be 12 digits)
            
        Returns:
            PIL.Image: The generated barcode image or a placeholder image if barcode is not available
        """
        if not BARCODE_AVAILABLE:
            return BarcodeGenerator._generate_placeholder("EAN-13 Unavailable\nPlease install 'python-barcode' package")
        
        # Pad data to 12 digits if needed
        if len(data) < 12:
            data = data.zfill(12)
        elif len(data) > 12:
            data = data[:12]
            
        # Create a BytesIO object to temporarily store the image
        buffer = io.BytesIO()
        EAN13(data, writer=ImageWriter()).write(buffer)
        
        # Create a PIL Image from the BytesIO object
        buffer.seek(0)
        image = Image.open(buffer)
        
        return image
    
    @staticmethod
    def generate_code128_barcode(data):
        """
        Generates a Code 128 barcode as a PIL Image object.
        
        Args:
            data (str): The data to encode in the barcode
            
        Returns:
            PIL.Image: The generated barcode image or a placeholder image if barcode is not available
        """
        if not BARCODE_AVAILABLE:
            return BarcodeGenerator._generate_placeholder("Code 128 Unavailable\nPlease install 'python-barcode' package")
        
        # Create a BytesIO object to temporarily store the image
        buffer = io.BytesIO()
        Code128(data, writer=ImageWriter()).write(buffer)
        
        # Create a PIL Image from the BytesIO object
        buffer.seek(0)
        image = Image.open(buffer)
        
        return image
    
    @staticmethod
    def _generate_placeholder(message):
        """
        Generates a placeholder image with a message.
        
        Args:
            message (str): Message to display on the placeholder
            
        Returns:
            PIL.Image: The generated placeholder image
        """
        # Create a placeholder image
        img = Image.new('RGB', (300, 150), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        
        # Draw a border
        d.rectangle([0, 0, 299, 149], outline=(0, 0, 0), width=2)
        
        # Add text
        try:
            # Try to use a default font
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
            
        # Center the text
        lines = message.split('\n')
        y_offset = 40
        for line in lines:
            text_width = d.textlength(line, font=font)
            d.text(((300 - text_width) // 2, y_offset), line, font=font, fill=(0, 0, 0))
            y_offset += 30
            
        return img
    
    @staticmethod
    def save_image(image, path):
        """
        Saves a PIL Image to the specified path.
        
        Args:
            image (PIL.Image): The image to save
            path (str): The path to save the image to
            
        Returns:
            str: The path where the image was saved
        """
        image.save(path)
        return path
    
    @staticmethod
    def get_image_as_bytes(image, format='PNG'):
        """
        Converts a PIL Image to bytes.
        
        Args:
            image (PIL.Image): The image to convert
            format (str): The format to save the image as
            
        Returns:
            bytes: The image as bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
