import os
import json
from http import HTTPStatus

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_firestore

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# GANTI 'main' MENJADI 'handler'
def handler(request):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'GET':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header else ''
        
        if token != ADMIN_PASSWORD:
            return (json.dumps({'error': 'Unauthorized'}), 401, headers)
        
        db = get_firestore()
        docs = db.collection('laporan').order_by('timestamp', direction='DESCENDING').stream()
        
        reports = []
        for doc in docs:
            reports.append({'id': doc.id, **doc.to_dict()})
        
        return (json.dumps({'success': True, 'reports': reports}), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, headers)
