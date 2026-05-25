import os
import json
import time
import hmac
import hashlib
import base64
import datetime
from http import HTTPStatus

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore

# ================= TOKEN VERIFICATION (Standar sama dengan login & reports) =================
def _get_secret_key() -> str:
    return os.getenv("TOKEN_SECRET_KEY", os.urandom(32).hex())

def verify_token(token: str) -> dict | None:
    try:
        decoded = base64.urlsafe_b64decode(token).decode()
        payload, sig = decoded.rsplit('.', 1)
        
        expected_sig = hmac.new(
            _get_secret_key().encode(), 
            payload.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(sig, expected_sig):
            return None
            
        username, expires_at = payload.split(':')
        if int(time.time()) > int(expires_at):
            return None
            
        return {"username": username, "expires_at": int(expires_at)}
    except Exception:
        return None

# ================= HANDLER UTAMA =================
def handler(request):
    """Endpoint untuk menghapus laporan & file di Google Drive"""
    
    # 1. Dynamic CORS
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",")]
    origin = request.headers.get("Origin", "")
    allow_origin = origin if origin in allowed_origins or allowed_origins == ["*"] else allowed_origins[0]

    headers = {
        'Access-Control-Allow-Origin': allow_origin,
        'Access-Control-Allow-Methods': 'DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'DELETE':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # 2. Verifikasi Token Admin
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header else ''
        
        user = verify_token(token)
        if not user:
            return (json.dumps({'error': 'Unauthorized. Token expired or invalid.'}), 401, headers)
        
        # 3. Ambil Report ID
        report_id = request.args.get('id') or request.path.split('/')[-1]
        if not report_id:
            return (json.dumps({'error': 'Report ID is required'}), 400, headers)
        
        db = get_firestore()
        doc_ref = db.collection('laporan').document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return (json.dumps({'error': 'Report not found'}), 404, headers)
        
        data = doc.to_dict()
        drive_id = data.get('drive_id')
        
        # 4. Safe Delete dari Google Drive
        if drive_id:
            try:
                drive = get_drive_service()
                drive.files().delete(fileId=drive_id).execute()
            except Exception as drive_err:
                # Log kegagalan hapus di Drive, tapi LANJUTKAN hapus di Firestore
                print(f"Drive delete failed for {report_id}: {drive_err}")
                try:
                    db.collection('error_logs').add({
                        'timestamp': datetime.datetime.now().isoformat(),
                        'endpoint': 'admin-delete',
                        'type': 'drive_delete_failed',
                        'report_id': report_id,
                        'drive_id': drive_id,
                        'error': str(drive_err),
                        'admin': user.get('username')
                    })
                except:
                    pass
        
        # 5. Hapus dari Firestore
        doc_ref.delete()
        
        return (json.dumps({
            'success': True, 
            'message': 'Report & associated files deleted successfully.'
        }), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        print(f"Admin Delete Error: {e}")
        try:
            db = get_firestore()
            db.collection('error_logs').add({
                'timestamp': datetime.datetime.now().isoformat(),
                'endpoint': 'admin-delete',
                'error': str(e)
            })
        except:
            pass
        return (json.dumps({'error': 'Failed to delete report'}), 500, headers)
