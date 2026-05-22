import os
import json

# ⚠️ WAJIB: Nama fungsi HARUS 'handler' agar Vercel bisa menjalankannya
def handler(request):
    # Import dilakukan DI DALAM fungsi agar Vercel bisa mendeteksi handler
    from http import HTTPStatus
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    try:
        from lib.services import get_drive_service, get_firestore
    except ImportError as e:
        return (json.dumps({'error': f'Import failed: {str(e)}'}), 500, {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        })

    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method != 'DELETE':
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
    
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header else ''
        
        if token != ADMIN_PASSWORD:
            return (json.dumps({'error': 'Unauthorized'}), 401, headers)
        
        report_id = request.args.get('id') or request.path.split('/')[-1]
        if not report_id:
            return (json.dumps({'error': 'Report ID required'}), 400, headers)
        
        db = get_firestore()
        doc_ref = db.collection('laporan').document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return (json.dumps({'error': 'Report not found'}), 404, headers)
        
        data = doc.to_dict()
        
        try:
            drive = get_drive_service()
            drive.files().delete(fileId=data['drive_id']).execute()
        except:
            pass
        
        doc_ref.delete()
        
        return (json.dumps({'success': True, 'message': 'Report deleted'}), 200, {**headers, 'Content-Type': 'application/json'})
        
    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, headers)
