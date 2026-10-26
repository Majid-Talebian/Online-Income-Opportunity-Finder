"""Opportunity Scout 0.1 — standard-library local application."""
import json, sqlite3, threading, time, uuid, re, urllib.request, urllib.parse, socket, ipaddress, xml.etree.ElementTree as ET
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
ROOT=Path(__file__).parent
DB=ROOT/'scout.db'
LOCK=threading.Lock(); STOP=threading.Event(); ACTIVE=False
DEFAULT={'name':'آرمان','role':'کارشناس ارشد کشف فرصت','precision':80,'creativity':60,'max_sources':5,'max_results':20,'max_age':30}
def db():
 c=sqlite3.connect(DB); c.execute('create table if not exists records(id text primary key, body text)'); return c
def save(r):
 with LOCK, db() as c: c.execute('insert or replace into records values(?,?)',(r['id'],json.dumps(r,ensure_ascii=False)))
def history():
 with LOCK, db() as c: return [json.loads(x[0]) for x in c.execute('select body from records order by rowid desc')]
def public_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password: raise ValueError('فقط نشانی HTTPS عمومی مجاز است')
 for a in socket.getaddrinfo(p.hostname,p.port or 443):
  if not ipaddress.ip_address(a[4][0]).is_global: raise ValueError('نشانی داخلی مجاز نیست')
 return url
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args): raise ValueError('تغییر مسیر منبع مجاز نیست؛ نشانی نهایی را وارد کنید')
def fetch(url):
 public_url(url)
 with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers={'User-Agent':'OpportunityScout/0.1'}),timeout=10) as r:
  data=r.read(1500001)
 if len(data)>1500000: raise ValueError('حجم منبع بیش از حد مجاز')
 return parse(data,url)
def parse(data,source):
 if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('DTD در خوراک مجاز نیست')
 root=ET.fromstring(data)
 if root.tag not in ('rss','{http://www.w3.org/2005/Atom}feed','{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'):raise ValueError('پاسخ RSS/Atom معتبر نیست')
 out=[]
 for e in list(root.findall('.//item'))+list(root.findall('.//{http://www.w3.org/2005/Atom}entry')):
  def val(tag):
   x=e.find(tag)
   if x is None: x=e.find('{http://www.w3.org/2005/Atom}'+tag)
   return ''.join(x.itertext()).strip() if x is not None else ''
  link=val('link')
  if not link:
   x=e.find('{http://www.w3.org/2005/Atom}link'); link=x.get('href','') if x is not None else ''
  out.append({'title':val('title'),'text':re.sub('<[^>]+>',' ',val('description') or val('summary'))[:3000],'url':link,'source':source,'date':val('pubDate') or val('updated')})
 return out[:100]
def samples():
 return [{'title':t,'text':d,'url':'','source':'داده آزمایشی','date':datetime.now(timezone.utc).isoformat()} for t,d in [('نیاز به داشبورد فروش','یک فروشگاه به تحلیل داده و داشبورد اکسل نیاز دارد'),('اتوماسیون گزارش هفتگی','گزارش دستی و نیاز به اتوماسیون داده'),('خدمات طراحی محتوا','تولید محتوا برای فروشگاه آنلاین')]]
def assess(items,mission,profile,mode):
 words=[x.strip().lower() for x in mission['keywords'].split(',') if x.strip()]
 excluded=[x.strip().lower() for x in mission.get('exclude','').split(',') if x.strip()]
 seen=set(); result=[]
 for x in items:
  key=x['url'] or x['title'].strip().lower()
  if key in seen: continue
  seen.add(key); body=(x['title']+' '+x['text']).lower()
  if any(w in body for w in excluded): continue
  matches=[w for w in words if w in body]
  if not matches: continue
  fresh=False
  try:
   from email.utils import parsedate_to_datetime
   try: dt=datetime.fromisoformat(x['date'].replace('Z','+00:00'))
   except ValueError: dt=parsedate_to_datetime(x['date'])
   if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
   age=(datetime.now(timezone.utc)-dt).total_seconds()/86400; fresh=0<=age<=profile['max_age']
  except Exception: pass
  score=round(100*len(matches)/len(words))
  status='فرضی — نیازمند ارزیابی' if mode=='demo' else ('سرنخ — نیازمند تأیید تقاضا' if fresh and x['url'].startswith('https://') else 'شواهد ناکافی یا قدیمی')
  result.append({**x,'score':score,'matches':matches,'status':status,'reason':'تطابق واژه‌ها: '+ '، '.join(matches),'next':'بررسی مشتری، تقاضای واقعی، امکان اجرا و دریافت وجه','verified':False})
 return sorted(result,key=lambda x:x['score'],reverse=True)[:profile['max_results']]
def run(m):
 global ACTIVE
 r={'id':str(uuid.uuid4()),'started':datetime.now(timezone.utc).isoformat(),'state':'در حال اجرا','mission':m,'log':[],'results':[],'profile':m.get('profile',DEFAULT),'cost':0}
 def log(s): r['log'].append(s);save(r)
 try:
  p={**DEFAULT,**m.get('profile',{})};r['profile']=p
  for k,lo,hi in [('max_sources',1,10),('max_results',1,100),('max_age',1,365),('precision',0,100),('creativity',0,100)]:
   p[k]=max(lo,min(hi,int(p[k])))
  log('مأموریت ثبت شد؛ این نسخه تحلیل قاعده‌محور دارد و مدل زبانی متصل نیست.')
  if not m.get('keywords','').strip(): raise ValueError('کلیدواژه لازم است')
  items=[]
  if m['mode']=='demo': items=samples();log('شواهد آزمایشی بارگذاری شد')
  elif m['mode']=='rss':
   sources=[s.strip() for s in m.get('sources','').splitlines() if s.strip()]
   if not sources: raise ValueError('حداقل یک منبع RSS لازم است')
   for s in sources[:p['max_sources']]:
    if STOP.is_set(): break
    try: items+=fetch(s);log('دریافت منبع: '+s)
    except Exception as e: log('خطای منبع: '+str(e))
  else: raise ValueError('حالت نامعتبر')
  if STOP.is_set(): r['state']='متوقف'
  else:
   r['results']=assess(items,m,p,m['mode']);r['state']='تکمیل' if items else 'بدون داده';log('حذف تکراری، تطبیق و کنترل تازگی انجام شد')
 except Exception as e: r['state']='خطا';r['log'].append(str(e))
 finally:
  save(r)
  with LOCK: ACTIVE=False
class Handler(BaseHTTPRequestHandler):
 def send(self,obj,code=200):
  raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if self.path=='/api': return self.send({'active':ACTIVE,'runs':history(),'defaults':DEFAULT})
  if self.path=='/':
   self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write((ROOT/'index.html').read_bytes());return
  self.send({'error':'not found'},404)
 def do_POST(self):
  global ACTIVE
  if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765','http://localhost:8765'): return self.send({'error':'origin'},403)
  if self.headers.get('Content-Type')!='application/json': return self.send({'error':'JSON required'},400)
  n=int(self.headers.get('Content-Length',0))
  if n>100000: return self.send({'error':'too large'},413)
  try: m=json.loads(self.rfile.read(n))
  except Exception: return self.send({'error':'invalid JSON'},400)
  if self.path=='/stop': STOP.set();return self.send({'ok':True})
  if self.path!='/run': return self.send({'error':'not found'},404)
  with LOCK:
   if ACTIVE: return self.send({'error':'یک مأموریت در حال اجراست'},409)
   ACTIVE=True;STOP.clear()
  threading.Thread(target=run,args=(m,),daemon=True).start();self.send({'ok':True})
 def log_message(self,*a): pass
if __name__=='__main__':
 print('Open http://127.0.0.1:8765 — Ctrl+C to stop')
 HTTPServer(('127.0.0.1',8765),Handler).serve_forever()
