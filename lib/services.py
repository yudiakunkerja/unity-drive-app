import os
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import credentials, firestore

def clean_json_keys(json_str: str) -> str:
    """Bersihkan JSON dari spasi di key/value"""
    if not json_str:
        return json_str
    cleaned = re.sub(r'"\s*:\s*"', '":"', json_str)
    cleaned = re.sub(r'"\s*,\s*"', '","', cleaned)
    cleaned = re.sub(r'"\s*}', '"}', cleaned)
    cleaned = re.sub(r'{\s*"', '{"', cleaned)
    return cleaned

def init_google_drive():
    """Initialize Google Drive service"""
    creds_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("GOOGLE_DRIVE_CREDENTIALS not set")
    
    creds_clean = clean_json_keys(creds_json)
    creds_info = json.loads(creds_clean)
    
    credentials_sa = service_account.Credentials.from_service_account_info(creds_info)
    return build('drive', 'v3', credentials=credentials_sa)

def init_firebase():
    """Initialize Firebase Firestore"""
    creds_json = os.getenv("FIREBASE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("FIREBASE_CREDENTIALS not set")
    
    creds_clean = clean_json_keys(creds_json)
    creds_info = json.loads(creds_clean)
    
    if not firebase_admin._apps:
        cert = credentials.Certificate(creds_info)
        firebase_admin.initialize_app(cert)
    
    return firestore.client()

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
