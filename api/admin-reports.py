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
from lib.services import get_firestore

# ================= TOKEN VERIFICATION LOGIC (Sama dengan admin-login.py) =================
def _get_secret_key() -> str:
    """Ambil secret key dari env, atau generate aman untuk development"""
    return os.getenv("TOKEN_SECRET_KEY", os.urandom(32).hex())

def verify_token(token: str) -> dict | None:
    """Verifikasi token & kembalikan data user jika valid & belum expired"""
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
    """
    Endpoint untuk mengambil daftar laporan.
    Wajib autentikasi token & membatasi jumlah data (limit 100).
    """
    
    # 1. Dynamic CORS
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",")]
    origin = request.headers.get("Origin", "")
    allow_origin = origin if origin in allowed_origins or allowed_origins == ["*"] else allowed_origins[0]

    headers = {
        'Access-Control-Allow-Origin': allow_origin,
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'GET':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # 2. Verifikasi Token Admin
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header else ''
        
        user = verify_token(token)
        if not user:
            return (json.dumps({'error': 'Unauthorized. Token expired or invalid.'}), 401, headers)
        
        # 3. Ambil Data dari Firestore (Dibatasi 100 Data Terakhir)
        db = get_firestore()
        
        # Order by timestamp descending, limit 100
        docs = db.collection('laporan')\
                 .order_by('timestamp', direction='DESCENDING')\
                 .limit(100)\
                 .stream()
        
        reports = []
        for doc in docs:
            data = doc.to_dict()
            # Tambahkan ID dokumen agar bisa dihapus/referensi nanti
            data['doc_id'] = doc.id
            reports.append(data)
        
        return (json.dumps({
            'success': True, 
            'reports': reports,
            'count': len(reports)
        }), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        print(f"Admin Reports Error: {e}")
        try:
            db = get_firestore()
            db.collection('error_logs').add({
                'timestamp': datetime.datetime.now().isoformat(),
                'endpoint': 'admin-reports',
                'error': str(e)
            })
        except:
            pass
        return (json.dumps({'error': 'Failed to load reports'}), 500, headers)
