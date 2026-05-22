import os
import json
from http import HTTPStatus

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ⚠️ GANTI 'main' MENJADI 'handler' AGAR VERCEL BISA MENDETEKSINYA
def handler(request):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    # Handle preflight (CORS)
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'DELETE':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # Cek Authorization
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header else ''
        
        if token != ADMIN_PASSWORD:
            return (json.dumps({'error': 'Unauthorized'}), 401, headers)
        
        # Ambil report_id dari query string atau URL path
        report_id = request.args.get('id') or request.path.split('/')[-1]
        if not report_id:
            return (json.dumps({'error': 'Report ID required'}), 400, headers)
        
        db = get_firestore()
        doc_ref = db.collection('laporan').document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return (json.dumps({'error': 'Report not found'}), 404, headers)
        
        data = doc.to_dict()
        
        # 1. Hapus dari Google Drive
        try:
            drive = get_drive_service()
            drive.files().delete(fileId=data['drive_id']).execute()
            print(f"🗑️ Deleted from Drive: {data.get('filename')}")
        except Exception as e:
            print(f"⚠️ Failed to delete from Drive: {e}")
            # Lanjutkan walaupun gagal hapus di Drive
        
        # 2. Hapus dari Firestore
        doc_ref.delete()
        print(f"🗑️ Deleted from Firestore: {report_id}")
        
        return (json.dumps({'success': True, 'message': 'Report deleted'}), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return (json.dumps({'error': str(e)}), 500, headers)
