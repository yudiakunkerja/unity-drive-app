import os
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import credentials, firestore

def clean_json_keys(json_str: str) -> str:
    """
    Bersihkan JSON dari spasi di key/value dan private_key.
    Menangani kasus: {"type ": "value ", "private_key ": "key\nwith spaces\n"}
    """
    if not json_str:
        return json_str
    
    # 1. Hapus spasi di sekitar : dan , dan { }
    cleaned = re.sub(r'"\s*:\s*"', '":"', json_str)
    cleaned = re.sub(r'"\s*,\s*"', '","', cleaned)
    cleaned = re.sub(r'"\s*}', '"}', cleaned)
    cleaned = re.sub(r'{\s*"', '{"', cleaned)
    
    # 2. Hapus trailing/leading spaces di dalam values (setelah parsing nanti)
    return cleaned

def _clean_creds_dict(creds: dict) -> dict:
    """
    Bersihkan dictionary credentials: strip spasi di keys dan values,
    dan khusus untuk private_key: hapus SEMUA spasi/newline yang tidak valid.
    """
    cleaned = {}
    for key, value in creds.items():
        # Strip spasi di key dan value
        clean_key = key.strip()
        clean_value = value.strip() if isinstance(value, str) else value
        
        # Khusus private_key: hapus spasi yang menyisip di tengah base64
        if clean_key == 'private_key' and isinstance(clean_value, str):
            # Hapus spasi/tab yang menyisip di dalam string private key
            # Tapi pertahankan \n yang valid untuk format PEM
            clean_value = re.sub(r'(?<!\\n)\s+(?!\\n)', '', clean_value)
        
        cleaned[clean_key] = clean_value
    return cleaned

def init_google_drive():
    """Initialize Google Drive service"""
    creds_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("GOOGLE_DRIVE_CREDENTIALS not set")
    
    try:
        creds_clean = clean_json_keys(creds_json)
        creds_info = json.loads(creds_clean)
        creds_info = _clean_creds_dict(creds_info)
        
        credentials_sa = service_account.Credentials.from_service_account_info(creds_info)
        return build('drive', 'v3', credentials=credentials_sa)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in GOOGLE_DRIVE_CREDENTIALS: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Google Drive: {e}")

def init_firebase():
    """Initialize Firebase Firestore"""
    creds_json = os.getenv("FIREBASE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("FIREBASE_CREDENTIALS not set")
    
    try:
        creds_clean = clean_json_keys(creds_json)
        creds_info = json.loads(creds_clean)
        creds_info = _clean_creds_dict(creds_info)
        
        if not firebase_admin._apps:
            cert = credentials.Certificate(creds_info)
            firebase_admin.initialize_app(cert)
        
        return firestore.client()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in FIREBASE_CREDENTIALS: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Firebase: {e}")

# Cache services per request (Vercel cold start)
_drive_service = None
_firestore_db = None

def get_drive_service():
    global _drive_service
    if _drive_service is None:
        _drive_service = init_google_drive()
    return _drive_service

def get_firestore():
    global _firestore_db
    if _firestore_db is None:
        _firestore_db = init_firebase()
    return _firestore_db
