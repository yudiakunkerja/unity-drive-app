import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import datetime

def add_watermark(image_bytes, location_info, note):
    """Tambah watermark ke foto"""
    try:
        image = Image.open(image_bytes).convert("RGBA")
        width, height = image.size
        draw = ImageDraw.Draw(image)
        
        font_size = max(20, int(width / 30))
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size - 4)
        except:
            font = ImageFont.load_default()
            font_small = font

        txt_box_height = font_size * 6
        draw.rectangle([(0, height - txt_box_height), (width, height)], fill=(0, 0, 0, 180))
        
        text_white = (255, 255, 255, 255)
        margin = 20
        y_offset = height - txt_box_height + 10
        
        draw.text((margin, y_offset), "PT. NUSANTARA MINERAL", fill=text_white, font=font)
        draw.text((margin, y_offset + font_size), f"Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=text_white, font=font_small)
        draw.text((margin, y_offset + font_size*2), f"Lokasi: {location_info}", fill=text_white, font=font_small)
        if note:
            draw.text((margin, y_offset + font_size*3), f"Catatan: {note}", fill=text_white, font=font_small)
        
        img_byte_arr = io.BytesIO()
        image.convert("RGB").save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception as e:
        print(f"Watermark error: {e}")
        return None

def create_zip(files_data):
    """Buat ZIP dari multiple files"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, (filename, content) in enumerate(files_data):
            zip_file.writestr(f"file_{i+1}_{filename}", content)
    zip_buffer.seek(0)
    return zip_buffer
