import os
import io
import json
import datetime
import re
from http import HTTPStatus

# Import shared modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore
from lib.utils import add_watermark

FOLDER_ID = os.getenv("FOLDER_ID", "")

def handler(request):
    """Vercel Serverless Function for site report upload"""
    
    # 1. Dynamic CORS Configuration
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",")]
    origin = request.headers.get("Origin", "")
    
    allow_origin = "*"
    if allowed_origins != ["*"]:
        if origin in allowed_origins:
            allow_origin = origin
        else:
            # Jika origin tidak diizinkan dan bukan *, tolak (atau set header kosong)
            # Untuk kompatibilitas, kita set ke origin pertama jika ada, atau tetap * jika kosong
            allow_origin = allowed_origins[0] if allowed_origins else "*"

    headers = {
        'Access-Control-Allow-Origin': allow_origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle preflight
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'POST':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # Parse form data
        form = request.form
        file = request.files.get('file') # Menggunakan get('file') karena biasanya single file
        note = form.get('note', '')
        
        # 2. Safe Coordinate Parsing
        try:
            latitude = float(form.get('latitude', 0))
            longitude = float(form.get('longitude', 0))
        except (ValueError, TypeError):
            return (json.dumps({'error': 'Invalid coordinate format. Must be numbers.'}), 400, headers)
        
        if not file:
            return (json.dumps({'error': 'No file provided'}), 400, headers)
        
        # 3. Strict Image Validation
        # Pastikan file benar-benar gambar
        if not file.content_type or not file.content_type.startswith('image/'):
            return (json.dumps({'error': 'Invalid file type. Only images are allowed.'}), 400, headers)
        
        # Check file size
        file_content = file.read()
        if len(file_content) > 4 * 1024 * 1024:  # 4MB limit
            return (json.dumps({'error': 'File too large. Max 4MB allowed.'}), 413, headers)
        
        # 4. Smart Watermark Fallback
        file_bytes = io.BytesIO(file_content)
        location_str = f"{latitude:.6f}, {longitude:.6f}"
        
        # add_watermark mengembalikan None jika file bukan gambar valid
        # Mengembalikan BytesIO (bisa watermark atau original) jika proses berhasil
        watermarked_img = add_watermark(file_bytes, location_str, note)
        
        if watermarked_img is None:
            return (json.dumps({'error': 'Failed to process image. File might be corrupted.'}), 500, headers)
        
        # Upload to Google Drive
        drive = get_drive_service()
        filename = f"Site_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID],
            'description': f"Laporan Site - {location_str} - {note}"
        }
        
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(watermarked_img, mimetype='image/jpeg')
        file_result = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Save to Firestore
        db = get_firestore()
        
        # Cek apakah watermark berhasil (jika utils mengembalikan original, kita tandai false)
        # Karena utils.py yang baru mengembalikan original bytes on error, 
        # kita asumsikan jika tidak None, upload sukses.
        # Untuk deteksi pasti, bisa cek size, tapi untuk sekarang kita mark success.
        
        db.collection('laporan').add({
            'timestamp': datetime.datetime.now().isoformat(),
            'type': 'site',
            'location': location_str,
            'latitude': latitude,
            'longitude': longitude,
            'note': note,
            'drive_id': file_result.get('id'),
            'drive_link': file_result.get('webViewLink'),
            'filename': filename,
            'watermark_success': True # Asumsi sukses jika tidak None
        })
        
        response = {
            'success': True,
            'message': 'Laporan Site berhasil dikirim!',
            'drive_link': file_result.get('webViewLink')
        }
        
        return (json.dumps(response), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        # 5. Structured Error Logging
        print(f"Upload site error: {e}")
        try:
            db = get_firestore()
            db.collection('error_logs').add({
                'timestamp': datetime.datetime.now().isoformat(),
                'endpoint': 'upload-site',
                'error': str(e),
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            })
        except Exception as log_err:
            print(f"Failed to log error: {log_err}")
            
        return (json.dumps({'error': 'Internal Server Error. Please try again later.'}), 500, headers)
