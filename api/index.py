import os,json,sys,importlib,urllib.parse
sys.path.append(os.path.dirname(__file__)+'/..')

def handler(request):
    # CORS
    h={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, POST, DELETE, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization'}
    if request.method=='OPTIONS':return('',204,h)
    
    # Parse path
    path=request.path.strip('/')
    parts=path.split('/')
    
    # Route mapping
    routes={
        'upload-site':'upload_site',
        'upload-doc':'upload_doc', 
        'admin-login':'admin_login',
        'admin-reports':'admin_reports',
        'admin-delete':'admin_delete',
        'cleanup':'cleanup'
    }
    
    # Get module name from path
    module_name=parts[-1] if parts else None
    func_name=routes.get(module_name)
    
    if not func_name:
        return(json.dumps({'error':'not found'}),404,h)
    
    try:
        # Import module dynamically
        mod=importlib.import_module(f'api.{module_name}')
        # Call handler from that module
        return mod.handler(request)
    except Exception as e:
        print(f"Route error: {e}")
        return(json.dumps({'error':'internal'}),500,h)
