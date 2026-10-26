"""Source normalization and conservative duplicate handling; never verifies claims."""
import hashlib, html, ipaddress, re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from email.utils import parsedate_to_datetime

def canonical_url(url):
    p=urlsplit(url.strip())
    query=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/',urlencode(query),''))

def clean_text(value):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',value))).strip()

def publication_age(value, now=None):
    if not value:return None,'missing'
    try:
        try:dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError:dt=parsedate_to_datetime(value)
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        age=((now or datetime.now(timezone.utc))-dt).total_seconds()/86400
        return (None,'future') if age<0 else (age,'valid')
    except (TypeError,ValueError,OverflowError):return None,'invalid'

def public_https(url):
    try:
        p=urlsplit(url)
        if p.scheme!='https' or not p.hostname or p.username or p.password:return False
        if p.hostname.lower()=='localhost' or p.hostname.lower().endswith(('.local','.localhost')):return False
        try:return ipaddress.ip_address(p.hostname).is_global
        except ValueError:return True
    except ValueError:return False

def normalize_items(items):
    result=[]; by_url={};by_content={};rejected=[]
    for item in items:
        if not isinstance(item,dict) or any(not isinstance(item.get(k),str) for k in ('title','text','url','source','date')):
            rejected.append({'reason':'invalid_schema'});continue
        row=dict(item);row['title']=clean_text(row['title'])[:500];row['text']=clean_text(row['text'])[:5000]
        if not row['title'] or not public_https(row['url']):
            rejected.append({'reason':'missing_title_or_unsafe_url','url':row['url'][:500]});continue
        row['url']=canonical_url(row['url']);text=row['text'].casefold()
        fingerprint=hashlib.sha256(text.encode()).hexdigest() if len(text)>=80 else None
        original={'url':item['url'],'source':item['source'],'source_id':item.get('source_id'),'retrieved_at':item.get('retrieved_at'),'published_at':item['date'] or None}
        existing=by_url.get(row['url']) or (by_content.get(fingerprint) if fingerprint else None)
        if existing is not None:
            if original not in existing['origins']:existing['origins'].append(original)
            existing['duplicate_count']+=1
            if row['url']!=existing['url']:existing['possible_republication']=True
            continue
        row.update(origins=[original],duplicate_count=0,possible_republication=False,content_hash=fingerprint)
        age,status=publication_age(row['date']);row['age_days']=age;row['date_status']=status
        row['evidence_quality']={'has_date':status=='valid','has_excerpt':bool(row['text']),'has_source':public_https(row['source']),'independence':'unverified','verified_transaction':False}
        row['quality_score']=round((int(status=='valid')+int(bool(row['text']))+int(public_https(row['source'])))*100/3)
        result.append(row);by_url[row['url']]=row
        if fingerprint:by_content[fingerprint]=row
    return result,{'received':len(items),'accepted':len(result),'duplicates':sum(r['duplicate_count'] for r in result),'rejected':rejected,'policy_version':'evidence-2.0'}
