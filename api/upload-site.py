import os
import io
import json
import datetime
from http import HTTPStatus
from PIL import Image
import firebase_admin
from firebase_admin import firestore

# Import shared modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore
from lib.utils import add_watermark

FOLDER_ID = os.getenv("FOLDER_ID", "")

# GANTI 'main' MENJADI 'handler' AGAR VERCEL BISA MENDETEKSINYA
def handler(request):
    """Vercel Serverless Function for site report upload"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
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
        file = form.get('file')
        note = form.get('note', '')
        latitude = float(form.get('latitude', 0))
        longitude = float(form.get('longitude', 0))
        
        if not file:
            return (json.dumps({'error': 'No file provided'}), 400, headers)
        
        # Check file size (Vercel limit: 4.5MB)
        file_content = file.read()
        if len(file_content) > 4 * 1024 * 1024:  # 4MB limit for safety
            return (json.dumps({'error': 'File too large. Max 4MB allowed.'}), 413, headers)
        
        # Add watermark
        file_bytes = io.BytesIO(file_content)
        location_str = f"{latitude:.6f}, {longitude:.6f}"
        watermarked_img = add_watermark(file_bytes, location_str, note)
        
        if not watermarked_img:
            return (json.dumps({'error': 'Failed to process image'}), 500, headers)
        
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
        
        response = {
            'success': True,
            'message': 'Laporan Site berhasil dikirim!',
            'drive_link': file_result.get('webViewLink')
        }
        
        return (json.dumps(response), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        print(f"Upload site error: {e}")
        return (json.dumps({'error': str(e)}), 500, headers)
