import os,json,sys
sys.path.append(os.path.dirname(__file__)+'/..')
from lib.services import get_firestore,get_drive_service
def handler(r):
 h={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'DELETE, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization'}
 if r.method=='OPTIONS':return('',204,h)
 if r.method!='DELETE':return(json.dumps({'error':'bad method'}),405,h)
 try:
  db=get_firestore();rid=r.args.get('id')or r.path.split('/')[-1]
  if not rid:return(json.dumps({'error':'no id'}),400,h)
  doc=db.collection('laporan').document(rid).get()
  if not doc.exists:return(json.dumps({'error':'not found'}),404,h)
  d=doc.to_dict()
  if d.get('drive_id'):
   try:get_drive_service().files().delete(fileId=d['drive_id']).execute()
   except:pass
  db.collection('laporan').document(rid).delete()
  return(json.dumps({'ok':True}),200,{**h,'Content-Type':'application/json'})
 except Exception as e:print(e);return(json.dumps({'error':'fail'}),500,h)
