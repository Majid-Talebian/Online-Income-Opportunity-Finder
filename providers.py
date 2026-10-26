"""Explicit, bounded adapters. No implicit cloud spending or fallback."""
import json, urllib.request, urllib.parse, urllib.error, socket
from legacy import public_url, NoRedirect
DEFAULTS={'search':'bing_rss','search_url':'','model':'','model_enabled':False}

def validate(c):
 if not isinstance(c,dict):raise ValueError('تنظیمات اتصال نامعتبر')
 out={**DEFAULTS,**{k:v for k,v in c.items() if k in DEFAULTS}}
 if out['search'] not in ['bing_rss','searxng']:raise ValueError('موتور جست‌وجو نامعتبر')
 for k in ['search_url','model']:
  if not isinstance(out[k],str) or len(out[k])>300:raise ValueError('تنظیمات متنی نامعتبر')
 if type(out['model_enabled']) is not bool:raise ValueError('فعال‌سازی مدل نامعتبر')
 if out['search']=='searxng':
  p=urllib.parse.urlsplit(out['search_url'])
  if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment:raise ValueError('نشانی پایه HTTPS بدون رمز و پارامتر لازم است')
 if out['model_enabled'] and not out['model'].strip():raise ValueError('نام مدل نصب‌شده لازم است')
 return out

def request_json(url,body=None,local=False):
 if local:
  if not url.startswith('http://127.0.0.1:11434/api/'):raise ValueError('نشانی مدل محلی نامعتبر')
 else:public_url(url)
 req=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','User-Agent':'Arman/0.5'})
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}) if local else urllib.request.ProxyHandler(),NoRedirect())
 with opener.open(req,timeout=45 if local else 12) as r:
  raw=r.read(1500001)
 if len(raw)>1500000:raise ValueError('پاسخ بیش از سقف حجم است')
 return json.loads(raw)

def search(query,config,rss_fetch):
 if config['search']=='bing_rss':return rss_fetch(query['url'])
 q=urllib.parse.parse_qs(urllib.parse.urlsplit(query['url']).query)['q'][0]
 url=config['search_url'].rstrip('/')+'/search?'+urllib.parse.urlencode({'q':q,'format':'json'})
 data=request_json(url)
 if not isinstance(data,dict) or not isinstance(data.get('results'),list):raise ValueError('ساختار نتایج جست‌وجو نامعتبر')
 out=[]
 for x in data['results'][:100]:
  if not isinstance(x,dict) or not isinstance(x.get('title'),str) or not isinstance(x.get('url'),str):raise ValueError('ردیف جست‌وجو نامعتبر')
  if urllib.parse.urlsplit(x['url']).scheme not in ['https','http']:continue
  out.append({'title':x['title'],'text':str(x.get('content') or '')[:3000],'url':x['url'],'source':url,'date':str(x.get('publishedDate') or '')})
 return out

def generate(config,prompt):
 if not config['model_enabled'] or not config['model']:raise ValueError('مدل محلی فعال و تنظیم نشده است')
 data=request_json('http://127.0.0.1:11434/api/generate',{'model':config['model'],'prompt':prompt,'stream':False,'options':{'num_predict':256,'temperature':0}},local=True)
 if not isinstance(data,dict) or data.get('done') is not True or not isinstance(data.get('response'),str) or not data['response'].strip():raise ValueError('پاسخ کامل و معتبر از مدل دریافت نشد')
 return {'text':data['response'][:6000],'input_tokens':data.get('prompt_eval_count'),'output_tokens':data.get('eval_count'),'model':config['model']}

def error_message(e):
 if isinstance(e,urllib.error.HTTPError):return 'خطای HTTP '+str(e.code)+'؛ دسترسی یا فعال‌بودن API را بررسی کنید'
 if isinstance(e,(socket.timeout,TimeoutError)):return 'زمان انتظار پایان یافت'
 if isinstance(e,(socket.gaierror,urllib.error.URLError,ConnectionError,OSError)):return 'دسترسی شبکه، DNS یا سرویس محلی برقرار نیست'
 return 'پاسخ یا تنظیمات معتبر نیست: '+str(e)[:120]
