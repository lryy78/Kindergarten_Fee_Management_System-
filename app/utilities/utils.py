from PIL import Image
import os

# Path for saving the processed images
UPLOAD_FOLDER = 'app/static'

def allowed_file(filename):
    """Check if a file is allowed based on its extension."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(file_path):
    try:
        # Open the image using Pillow
        img = Image.open(file_path)
        
        # Check if the image has an alpha channel (transparency)
        if img.mode == 'RGBA':
            # The image already has transparency (RGBA), so save as is
            img.save(file_path, optimize=True, quality=80)
        elif img.mode == 'P' and 'transparency' in img.info:
            # Palette-based images (P mode) with transparency should be converted to RGBA
            img = img.convert('RGBA')
            img.save(file_path, optimize=True, quality=80)
        else:
            # For non-transparent images (RGB), convert to RGB before saving
            img = img.convert('RGB')
            img.save(file_path, optimize=True, quality=80)
    except Exception as e:
        raise Exception(f"Error compressing image: {str(e)}")


# Function to convert the image to favicon.ico
def convert_to_favicon(file_path):
    try:
        # Convert the image to ICO format
        favicon_path = os.path.join(UPLOAD_FOLDER, 'favicon.ico')
        img = Image.open(file_path)
        img.save(favicon_path, format='ICO')
    except Exception as e:
        raise Exception(f"Error converting to favicon: {str(e)}")
    
    