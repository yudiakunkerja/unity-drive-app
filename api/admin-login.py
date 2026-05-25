import os
import json
import hashlib
import uuid
import datetime
from lib.services import get_firestore

def hash_password(password: str, salt: str = None):
    """Hash password dengan SHA-256 & salt unik"""
    if salt is None:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return pwd_hash.hex(), salt

def handler(request):
    """Unified Auth Handler: Login & Register dengan 5x gagal -> auto delete"""
    
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
                
            pwd_hash, salt = hash_password(password)
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
                # Gunakan pesan generik untuk mencegah enumerasi username
                return (json.dumps({'error': 'Username atau password salah'}), 401, headers)
                
            user_data = doc.to_dict()
            
            if user_data.get('failed_attempts', 0) >= 5:
                doc_ref.delete()
                return (json.dumps({
                    'error': 'Akun telah dihapus karena 5x percobaan gagal. Silakan daftar ulang.'
                }), 403, headers)
                
            # Verifikasi password
            calc_hash, _ = hash_password(password, user_data['salt'])
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
                    
            # Login sukses
            token = uuid.uuid4().hex  # Token unik per sesi
            doc_ref.update({'failed_attempts': 0}) # Reset counter
            
            return (json.dumps({
                'success': True,
                'message': 'Login berhasil',
                'token': token,
                'username': username
            }), 200, {**headers, 'Content-Type': 'application/json'})
            
        else:
            return (json.dumps({'error': 'Invalid action type. Use "login" or "register".'}), 400, headers)
            
    except Exception as e:
        # Sanitized error message
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
