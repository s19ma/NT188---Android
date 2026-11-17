"""Build a sanitized production read-only API inventory; no response secrets are saved."""
import json, os
from pathlib import Path
import requests
from scripts.verify_production_backup_local import unprotect_key

BASE = 'https://englishvideoapi20261114.eastasia.cloudapp.azure.com'
s = requests.Session()
spec = s.get(BASE + '/openapi.json', timeout=20).json()
p = Path(os.environ['LOCALAPPDATA']) / 'EnglishThroughVideo/production-backups/production-smoketest-password-reset.dpapi'
login = s.post(BASE+'/api/v1/users/login', data={'username':'vietbactqd@gmail.com', 'password':unprotect_key(p.read_bytes()).decode()}, timeout=20)
login.raise_for_status()
headers = {'Authorization':'Bearer '+login.json()['access_token']}
results = {('post','/api/v1/users/login'): 'PASS — HTTP 200, tài khoản test'}
videos = s.get(BASE+'/api/v1/videos',timeout=20); videos.raise_for_status()
items = videos.json(); vid = items[0]['id'] if items else None
words = s.get(BASE+'/api/v1/vocabulary',timeout=20); words.raise_for_status()
vocab = words.json(); wordid = vocab[0]['id'] if isinstance(vocab,list) and vocab else None
safe = ['/','/health','/health/db','/health/models','/api/v1/users/me','/api/v1/videos','/api/v1/vocabulary','/api/v1/vocabulary/search','/api/v1/users/me/vocabulary','/api/v1/users/me/flashcards/overview','/api/v1/users/me/flashcards','/api/v1/users/me/progress','/api/v1/users/me/streak','/api/v1/users/me/statistics','/api/v1/quizzes/default','/api/v1/quizzes/history','/api/v1/admin/overview','/api/v1/admin/videos']
paths = {x:x for x in safe}
paths['/api/v1/vocabulary/search'] += '?q=salt'
if vid:
 for x in ['/api/v1/videos/{video_id}','/api/v1/videos/{video_id}/summary','/api/v1/videos/{video_id}/playback','/api/v1/videos/{video_id}/subtitles','/api/v1/videos/{video_id}/vocabulary','/api/v1/users/me/progress/{video_id}']:
  paths[x]=x.replace('{video_id}',vid)
if wordid: paths['/api/v1/vocabulary/{vocabulary_id}']='/api/v1/vocabulary/'+wordid
for templ,path in paths.items():
 try:
  r=s.get(BASE+path,headers=headers,timeout=20)
  expected = (403,) if '/admin/' in path else ((200,404) if path.endswith('/summary') or '/progress/' in path else (200,))
  if '/admin/' in path and r.status_code == 403:
   results['get',templ]='BLOCKED — learner HTTP 403 đúng; chưa kiểm thử quyền Admin'
  elif '/progress/' in path and r.status_code == 404:
   results['get',templ]='BLOCKED — HTTP 404, video không có progress; chưa thử response 200'
  else:
   results['get',templ]=('PASS' if r.status_code in expected else 'FAIL')+f' — HTTP {r.status_code}'
 except requests.RequestException as exc: results['get',templ]='BLOCKED — '+type(exc).__name__
for token in (None,'invalid-token'):
 r=s.get(BASE+'/api/v1/users/me',headers={'Authorization':'Bearer '+token} if token else {},timeout=20)
 results.setdefault(('get','/api/v1/users/me'),'')
 results['get','/api/v1/users/me']+=f'; JWT {"invalid" if token else "missing"}: {r.status_code}'
lines=['# Full API test matrix — 16/11/2026','',f'{sum(m in ("get","post","put","patch","delete") for x in spec["paths"].values() for m in x)} operations; production read-only + login; no response bodies or credentials retained.','', '| Method | Path | Tag | Auth (OpenAPI) | Request → Response | Effect / access | Result |','|---|---|---|---|---|---|---|']
for path,ops in spec['paths'].items():
 for method,op in ops.items():
  if method not in ('get','post','put','patch','delete'): continue
  auth='JWT' if op.get('security') else 'public / xem source'
  content=op.get('requestBody',{}).get('content',{})
  req=', '.join(f"{mime} {v.get('schema',{}).get('$ref','inline').split('/')[-1]}" for mime,v in content.items()) or ', '.join(p.get('name','') for p in op.get('parameters',[])) or 'none'
  rsp=', '.join(f"{code} {next(iter(value.get('content',{}).values()),{}).get('schema',{}).get('$ref','inline').split('/')[-1]}" for code,value in op.get('responses',{}).items())
  if method=='get' and '/dictionary/' in path: effect='Có thể ghi dictionary cache; không chạy'; status='NOT EXECUTED'
  elif method!='get' and not path.endswith('/login'): effect='Mutation; admin/email/user'; status='NOT EXECUTED'
  else: effect='Read-only; admin nếu /admin/'; status=results.get((method,path),'BLOCKED — thiếu fixture')
  lines.append(f'| {method.upper()} | `{path}` | {", ".join(op.get("tags",[])) or "health"} | {auth} | {req} → {rsp} | {effect} | {status} |')
out=Path(__file__).resolve().parents[1]/'FULL_API_TEST_MATRIX.md'; out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('operations',len(lines)-6,'tested',len(results),'videos',len(items))
