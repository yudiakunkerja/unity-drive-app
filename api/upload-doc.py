import os
import io
import json
import datetime
from http import HTTPStatus

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore
from lib.utils import create_zip

FOLDER_ID = os.getenv("FOLDER_ID", "")

# GANTI 'main' MENJADI 'handler'
def handler(request):
    """Vercel Serverless Function for document upload"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'POST':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        form = request.form
        note = form.get('note', '')
        nominal = form.get('nominal', '')
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return (json.dumps({'error': 'No files provided'}), 400, headers)
        
        # Check total size
        files_data = []
        total_size = 0
        for file in files:
            content = file.read()
            total_size += len(content)
            files_data.append((file.filename, content))
        
        # Vercel limit: 4.5MB total (safety limit set to 4MB)
        if total_size > 4 * 1024 * 1024:
            return (json.dumps({'error': 'Total file size exceeds 4MB limit'}), 413, headers)
        
        # Prepare file for upload
        if len(files) > 5:
            # Auto ZIP
            zip_buffer = create_zip(files_data)
            filename = f"Dokumen_ZIP_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            mime_type = 'application/zip'
            file_to_upload = zip_buffer
        else:
            # Upload first file only
            filename = files[0].filename
            mime_type = files[0].content_type or 'application/octet-stream'
            file_to_upload = io.BytesIO(files_data[0][1])
        
        # Upload to Google Drive
        drive = get_drive_service()
        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID],
            'description': f"Laporan Dokumen - {note} - Nominal: {nominal}"
        }
        
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(file_to_upload, mimetype=mime_type)
        file_result = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Save to Firestore
        db = get_firestore()
        db.collection('laporan').add({
            'timestamp': datetime.datetime.now().isoformat(),
            'type': 'doc',
            'note': note,
            'nominal': nominal,
            'jumlah_file': len(files),
            'drive_id': file_result.get('id'),
            'drive_link': file_result.get('webViewLink'),
            'filename': filename
        })
        
        response = {
            'success': True,
            'message': f'Berhasil! {len(files)} file terkirim.',
            'drive_link': file_result.get('webViewLink')
        }
        
        return (json.dumps(response), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        print(f"Upload doc error: {e}")
        return (json.dumps({'error': str(e)}), 500, headers)
