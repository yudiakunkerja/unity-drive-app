import os
import io
import re
import zipfile
from PIL import Image, ImageDraw, ImageFont
import datetime

def sanitize_filename(filename):
    """
    Membersihkan nama file dari karakter berbahaya atau spasi yang bisa menyebabkan error.
    Hanya menyisakan huruf, angka, titik, underscore, dan dash.
    """
    # Ganti karakter aneh menjadi underscore
    clean_name = re.sub(r'[^\w\-.]', '_', filename)
    # Hapus underscore ganda yang mungkin terbentuk
    clean_name = re.sub(r'_+', '_', clean_name)
    return clean_name

def _get_font_path(size):
    """
    Mencari file font TTF yang tersedia di sistem operasi.
    Mendukung Vercel (Linux), Windows, dan macOS.
    """
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Default Vercel/Linux
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",             # Alternative Linux
        "C:/Windows/Fonts/arial.ttf",                           # Windows
        "/Library/Fonts/Arial.ttf",                             # macOS
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    
    # Jika tidak ada font ditemukan, gunakan default bawaan PIL
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Kompatibilitas versi Pillow lama yang tidak support arg 'size' di load_default
        return ImageFont.load_default()

def add_watermark(image_bytes, location_info, note):
    """Tambah watermark ke foto dengan ukuran dinamis dan penanganan transparansi"""
    try:
        # Buka gambar dan konversi ke RGBA untuk processing layer
        image = Image.open(image_bytes).convert("RGBA")
        width, height = image.size
        
        # 1. Setup Font
        font_size = max(20, int(width / 30))
        font_main = _get_font_path(font_size)
        font_sub = _get_font_path(int(font_size * 0.8))
        
        # 2. Persiapan Teks
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        lines = [
            ("PT. NUSANTARA MINERAL", font_main),
            (f"Waktu: {timestamp}", font_sub),
            (f"Lokasi: {location_info}", font_sub),
        ]
        
        if note:
            lines.append((f"Catatan: {note}", font_sub))
            
        # 3. Hitung ukuran kotak teks secara dinamis
        draw_temp = ImageDraw.Draw(image)
        max_text_width = 0
        total_text_height = 0
        padding = 20
        line_spacing = 5
        
        for text, font in lines:
            bbox = draw_temp.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            max_text_width = max(max_text_width, text_w)
            total_text_height += text_h + line_spacing
            
        # Tambahkan padding untuk kotak background
        box_height = int(total_text_height + padding * 2)
        box_width = min(width, int(max_text_width + padding * 2))
        
        # Posisi Y untuk kotak (di bagian bawah)
        box_y = height - box_height
        
        # 4. Gambar Watermark (di atas layer RGBA)
        # Gambar background kotak semi-transparan
        draw_temp.rectangle(
            [(0, box_y), (width, height)], 
            fill=(0, 0, 0, 180)
        )
        
        current_y = box_y + padding
        text_color = (255, 255, 255, 255)
        
        for text, font in lines:
            draw_temp.text((padding, current_y), text, fill=text_color, font=font)
            bbox = draw_temp.textbbox((0, 0), text, font=font)
            current_y += (bbox[3] - bbox[1]) + line_spacing
            
        # 5. Konversi ke JPEG dengan Latar Putih (Agar transparansi tidak hitam)
        # Buat canvas putih
        white_bg = Image.new("RGB", image.size, (255, 255, 255))
        
        # Paste gambar RGBA yang sudah di-watermark ke canvas putih
        # Gunakan mask=image agar alpha channel diproses dengan benar
        white_bg.paste(image, mask=image)
        
        # Simpan ke buffer
        img_byte_arr = io.BytesIO()
        white_bg.save(img_byte_arr, format='JPEG', quality=90)
        img_byte_arr.seek(0)
        
        return img_byte_arr
        
    except Exception as e:
        print(f"Watermark error: {e}")
        # Jika gagal, kembalikan gambar original tanpa watermark agar app tidak crash
        try:
            image = Image.open(image_bytes).convert("RGB")
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            return img_byte_arr
        except:
            return None

def create_zip(files_data):
    """Buat ZIP dari multiple files dengan sanitasi nama file"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, (filename, content) in enumerate(files_data):
            # Sanitasi nama file agar aman
            safe_name = sanitize_filename(filename)
            zip_file.writestr(f"file_{i+1}_{safe_name}", content)
    zip_buffer.seek(0)
    return zip_buffer
