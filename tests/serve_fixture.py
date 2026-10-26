"""Isolated acceptance server. External source results are explicitly synthetic."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import service as s
with tempfile.TemporaryDirectory() as temp:
 s.DB=Path(temp)/'acceptance.db'
 def fetch_fixture(url):
  return [{'title':'dashboard customer request','text':'Customer needs a dashboard and requests a quote for reports.','url':'https://buyer.example/job','source':url,'date':s.now()},
          {'title':'dashboard supplier catalog','text':'Supplier catalog lists a dashboard price.','url':'https://supplier.example/product','source':url,'date':''}]
 s.fetch=fetch_fixture
 print('ACCEPTANCE_READY',flush=True)
 s.ThreadingHTTPServer(('127.0.0.1',8765),s.Handler).serve_forever()
