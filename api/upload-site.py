import os
import io
import json
import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore
from lib.utils import add_watermark

FOLDER_ID = os.getenv("FOLDER_ID", "")

def handler(request):
    """Vercel Serverless Function for site report upload"""
    
    # CORS headers
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    origin = request.headers.get("Origin", "")
    allow_origin = origin if origin in allowed_origins or allowed_origins == ["*"] else (allowed_origins[0] if allowed_origins else "*")
    
    headers = {
        'Access-Control-Allow-Origin': allow_origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'POST':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # Parse form data
        form = request.form
        file = request.files.get('file')
        note = form.get('note', '')
        
        try:
            latitude = float(form.get('latitude', 0))
            longitude = float(form.get('longitude', 0))
        except (ValueError, TypeError):
            return (json.dumps({'error': 'Invalid coordinates'}), 400, headers)
        
        if not file:
            return (json.dumps({'error': 'No file provided'}), 400, headers)
        
        if not file.content_type or not file.content_type.startswith('image/'):
            return (json.dumps({'error': 'Only images allowed'}), 400, headers)
        
        file_content = file.read()
        if len(file_content) > 4 * 1024 * 1024:
            return (json.dumps({'error': 'File too large (max 4MB)'}), 413, headers)
        
        # Watermark
        file_bytes = io.BytesIO(file_content)
        location_str = f"{latitude:.6f}, {longitude:.6f}"
        watermarked = add_watermark(file_bytes, location_str, note)
        
        if watermarked is None:
            return (json.dumps({'error': 'Failed to process image'}), 500, headers)
        
        # Upload to Google Drive
        drive = get_drive_service()
        filename = f"Site_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(watermarked, mimetype='image/jpeg')
        file_result = drive.files().create(
            body={'name': filename, 'parents': [FOLDER_ID]},
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Save to Firestore
        db = get_firestore()
        db.collection('laporan').add({
            'timestamp': datetime.datetime.now().isoformat(),
            'type': 'site',
            'location': location_str,
            'latitude': latitude,
            'longitude': longitude,
            'note': note,
            'drive_id': file_result.get('id'),
            'drive_link': file_result.get('webViewLink'),
            'filename': filename
        })
        
        return (json.dumps({
            'success': True,
            'message': 'Laporan Site berhasil dikirim!',
            'drive_link': file_result.get('webViewLink')
        }), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        print(f"Error: {e}")
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
