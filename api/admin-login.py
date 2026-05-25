import os
import json
import hashlib
import datetime
import hmac
import time
import base64

from lib.services import get_firestore

# ================= TOKEN UTILS (Otomatis Expiry 24 Jam) =================
def _get_secret_key() -> str:
    """Ambil secret key dari env, atau generate aman untuk development"""
    return os.getenv("TOKEN_SECRET_KEY", os.urandom(32).hex())

def create_token(username: str) -> str:
    """Buat token terenkripsi yang otomatis expire setelah 24 jam"""
    expires_at = int(time.time()) + 86400  # 24 jam dalam detik
    payload = f"{username}:{expires_at}"
    signature = hmac.new(
        _get_secret_key().encode(), 
        payload.encode(), 
        hashlib.sha256
    ).hexdigest()
    # Format: base64(payload.signature)
    return base64.urlsafe_b64encode(f"{payload}.{signature}".encode()).decode()

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

# ================= AUTH HANDLER =================
def handler(request):
    """Unified Auth Handler: Register, Login, Token Management"""
    
    # 1. Dynamic CORS
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",")]
    origin = request.headers.get("Origin", "")
    allow_origin = origin if origin in allowed_origins or allowed_origins == ["*"] else allowed_origins[0]

    headers = {
        'Access-Control-Allow-Origin': allow_origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'POST':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        # Parse JSON body
        try:
            data = request.get_json(force=True)
        except Exception:
            return (json.dumps({'error': 'Invalid JSON payload'}), 400, headers)
            
        action = data.get('type', 'login').lower()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return (json.dumps({'error': 'Username dan password wajib diisi'}), 400, headers)
            
        db = get_firestore()
        doc_ref = db.collection('admin_users').document(username)
        doc = doc_ref.get()
        
        # ================= REGISTER =================
        if action == 'register':
            if doc.exists:
                return (json.dumps({'error': 'Username sudah terdaftar'}), 409, headers)
                
            # Hash password dengan salt unik
            salt = os.urandom(16).hex()
            pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
            
            doc_ref.set({
                'username': username,
                'password_hash': pwd_hash,
                'salt': salt,
                'failed_attempts': 0,
                'created_at': datetime.datetime.now().isoformat()
            })
            
            return (json.dumps({
                'success': True, 
                'message': 'Akun berhasil dibuat. Silakan login.'
            }), 201, {**headers, 'Content-Type': 'application/json'})
            
        # ================= LOGIN =================
        elif action == 'login':
            if not doc.exists:
                return (json.dumps({'error': 'Username atau password salah'}), 401, headers)
                
            user_data = doc.to_dict()
            
            # Cek batas 5x gagal
            if user_data.get('failed_attempts', 0) >= 5:
                doc_ref.delete()
                return (json.dumps({
                    'error': 'Akun telah dihapus karena 5x percobaan gagal. Silakan daftar ulang.'
                }), 403, headers)
                
            # Verifikasi password
            calc_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), user_data['salt'].encode('utf-8'), 100000).hex()
            
            if calc_hash != user_data['password_hash']:
                new_attempts = user_data.get('failed_attempts', 0) + 1
                if new_attempts >= 5:
                    doc_ref.delete()
                    return (json.dumps({
                        'error': 'Akun telah dihapus karena 5x percobaan gagal. Silakan daftar ulang.'
                    }), 403, headers)
                else:
                    doc_ref.update({'failed_attempts': new_attempts})
                    return (json.dumps({'error': 'Username atau password salah'}), 401, headers)
                    
            # Login sukses → Reset counter & generate token 24 jam
            doc_ref.update({'failed_attempts': 0})
            token = create_token(username)
            
            return (json.dumps({
                'success': True,
                'message': 'Login berhasil',
                'token': token,
                'username': username,
                'expires_in_hours': 24
            }), 200, {**headers, 'Content-Type': 'application/json'})
            
        else:
            return (json.dumps({'error': 'Invalid action. Gunakan "login" atau "register".'}), 400, headers)
            
    except Exception as e:
        print(f"Auth error: {e}")
        try:
            db = get_firestore()
            db.collection('error_logs').add({
                'timestamp': datetime.datetime.now().isoformat(),
                'endpoint': 'admin-login',
                'error': str(e)
            })
        except:
            pass
        return (json.dumps({'error': 'Terjadi kesalahan internal. Silakan coba lagi.'}), 500, headers)
