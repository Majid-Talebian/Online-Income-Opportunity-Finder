"""Run on a connected computer. A failed live check has a nonzero exit status."""
import argparse,json,sys
from urllib.parse import urlsplit,urlunsplit
from datetime import datetime,timezone
from legacy import fetch
from providers import error_message

def check(url):
 p=urlsplit(url);display=urlunsplit((p.scheme,p.hostname or '',p.path,'',''))
 result={'endpoint_without_query':display,'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'RSS transport and parse only, not demand or source coverage'}
 try:
  rows=fetch(url);result.update(status='ok' if rows else 'empty',received_items=len(rows))
 except Exception as error:result.update(status='failed',error=error_message(error))
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',action='append',required=True);args=parser.parse_args()
 results=[check(url) for url in args.url];print(json.dumps({'checks':results,'all_passed':all(x['status']=='ok' for x in results)},ensure_ascii=False,indent=2))
 return 0 if all(x['status']=='ok' for x in results) else 1
if __name__=='__main__':sys.exit(main())
