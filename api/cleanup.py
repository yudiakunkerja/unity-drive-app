import os
import json
import datetime
from http import HTTPStatus

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.services import get_drive_service, get_firestore

def main(request):
    """Vercel Cron Job: Delete reports older than 30 days"""
    
    # Security: Only allow requests from Vercel Cron
    cron_secret = os.getenv("CRON_SECRET", "")
    header_secret = request.headers.get('x-vercel-cron-secret', '')
    
    if cron_secret and header_secret != cron_secret:
        return (json.dumps({'error': 'Unauthorized'}), 401, {'Content-Type': 'application/json'})
    
    try:
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        db = get_firestore()
        drive = get_drive_service()
        
        docs = db.collection('laporan').where('timestamp', '<', thirty_days_ago.isoformat()).stream()
        
        deleted_count = 0
        for doc in docs:
            data = doc.to_dict()
            try:
                drive.files().delete(fileId=data['drive_id']).execute()
            except:
                pass
            doc.reference.delete()
            deleted_count += 1
        
        return (json.dumps({
            'success': True,
            'message': f'Cleanup completed: {deleted_count} reports deleted'
        }), 200, {'Content-Type': 'application/json'})
        
    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'})
