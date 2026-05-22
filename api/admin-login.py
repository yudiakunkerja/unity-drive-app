import os
import json
from http import HTTPStatus

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def main(request):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'POST':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header else ''
        
        if token == ADMIN_PASSWORD:
            return (json.dumps({'success': True, 'token': token}), 200, {**headers, 'Content-Type': 'application/json'})
        
        return (json.dumps({'error': 'Invalid password'}), 401, headers)
        
    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, headers)
