import unittest,threading,tempfile,json,urllib.request,urllib.error
from pathlib import Path
import service as s
class HTTP(unittest.TestCase):
 def test_api_and_request_protection(self):
  with tempfile.TemporaryDirectory() as d:
   old=s.DB;s.DB=Path(d)/'x.db'
   server=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
   url='http://127.0.0.1:'+str(server.server_port)
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   try:
    req=urllib.request.Request(url+'/api',headers={'Host':'127.0.0.1:8765'})
    self.assertFalse(json.load(opener.open(req))['capabilities']['deep_research'])
    req=urllib.request.Request(url+'/profile',data=b'{}',headers={'Host':'127.0.0.1:8765'})
    with self.assertRaises(urllib.error.HTTPError) as e:opener.open(req)
    self.assertEqual(e.exception.code,403)
    req=urllib.request.Request(url+'/profile',data=b'{"capital":null,"working_hours_week":null}',headers={'Host':'127.0.0.1:8765','X-Arman-Token':s.TOKEN})
    self.assertIsNone(json.load(opener.open(req))['capital'])
   finally:server.shutdown();server.server_close();s.DB=old
if __name__=='__main__':unittest.main()
