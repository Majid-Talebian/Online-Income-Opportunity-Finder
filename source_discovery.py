"""Discover advertised RSS/Atom links on a public page; never claims API access."""
from html.parser import HTMLParser
from urllib.parse import urljoin
import urllib.request
from legacy import public_url,NoRedirect
from evidence import public_https,canonical_url

class FeedLinks(HTMLParser):
 def __init__(self,base):super().__init__();self.base=base;self.links=[]
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if tag.lower()!='link' or values.get('type','').lower() not in ['application/rss+xml','application/atom+xml']:return
  if 'alternate' not in values.get('rel','').lower().split():return
  url=urljoin(self.base,values.get('href',''))
  if public_https(url) and url not in [x['feed_url'] for x in self.links]:self.links.append({'feed_url':canonical_url(url),'title':values.get('title','خوراک معرفی‌شده')[:150]})

def discover(url):
 if not isinstance(url,str) or len(url)>1500:raise ValueError('نشانی سایت نامعتبر')
 public_url(url)
 request=urllib.request.Request(url,headers={'User-Agent':'OpportunityFinder/0.10'})
 with urllib.request.build_opener(NoRedirect()).open(request,timeout=10) as response:
  raw=response.read(1500001)
  if len(raw)>1500000:raise ValueError('حجم صفحه بیشتر از حد مجاز است')
  text=raw.decode(response.headers.get_content_charset() or 'utf-8',errors='replace')
 parser=FeedLinks(url);parser.feed(text)
 return {'page_url':url,'candidates':parser.links[:10],'status':'candidates_found' if parser.links else 'no_advertised_feed','verified_connection':False}
