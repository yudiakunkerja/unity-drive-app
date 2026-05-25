import os,json,time,hmac,hashlib,base64,datetime,sys
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from lib.services import get_drive_service,get_firestore
def _sk():return os.getenv("TOKEN_SECRET_KEY",os.urandom(32).hex())
def _vt(t):
 try:
  d=base64.urlsafe_b64decode(t).decode();p,s=d.rsplit('.',1)
  if not hmac.compare_digest(s,hmac.new(_sk().encode(),p.encode(),hashlib.sha256).hexdigest()):return None
  u,e=p.split(':');return{"username":u}if int(time.time())<=int(e)else None
 except:return None
def handler(r):
 ao=os.getenv("ALLOWED_ORIGINS","*");aos=[x.strip()for x in ao.split(",")];og=r.headers.get("Origin","")
 aoh=og if og in aos or aos==["*"]else(aos[0]if aos else"*")
 h={'Access-Control-Allow-Origin':aoh,'Access-Control-Allow-Methods':'DELETE, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization'}
 if r.method=='OPTIONS':return('',204,h)
 if r.method!='DELETE':return(json.dumps({'error':'Method not allowed'}),405,h)
 try:
  ah=r.headers.get('Authorization','');tk=ah.replace('Bearer ','')if ah else''
  if not _vt(tk):return(json.dumps({'error':'Unauthorized'}),401,h)
  rid=r.args.get('id')or(r.path.strip('/').split('/')[-1]if r.path.strip('/')else None)
  if not rid:return(json.dumps({'error':'Report ID required'}),400,h)
  db=get_firestore();dr=db.collection('laporan').document(rid);dc=dr.get()
  if not dc.exists:return(json.dumps({'error':'Report not found'}),404,h)
  dt=dc.to_dict();did=dt.get('drive_id')
  if did:
   try:get_drive_service().files().delete(fileId=did).execute()
   except:pass
  dr.delete()
  return(json.dumps({'success':True}),200,{**h,'Content-Type':'application/json'})
 except Exception as e:print(f"Err:{e}");return(json.dumps({'error':'Internal error'}),500,h)
