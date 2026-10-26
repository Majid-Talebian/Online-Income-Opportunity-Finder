import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import service as s
class Flow(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=s.DB;s.DB=Path(self.temp.name)/'test.db';s.STOP.clear()
 def tearDown(self):s.DB=self.old;self.temp.cleanup()
 def fixture(self):return {'title':'dashboard need','text':'need data reporting','url':'https://example.com/item','source':'https://example.com/feed','date':s.now()}
 def test_scan_select_research_restart(self):
  with patch('service.fetch',return_value=[self.fixture(),self.fixture()]):r=s.scan({'topic':'dashboard','customer':'retailers','country':'Iran','exclude':''})
  self.assertEqual(len(r['opportunities']),1)
  result=s.research(r['id'],[r['opportunities'][0]['id']]);self.assertEqual(len(result['dossiers'][0]['sections']),14);self.assertFalse(result['dossiers'][0]['research_complete']);self.assertEqual(s.get(result['id']),result)
 def test_failure_no_fake_results(self):
  with patch('service.fetch',side_effect=OSError('offline')):r=s.scan({'topic':'data','country':'Iran','exclude':''})
  self.assertEqual(r['status'],'no_data');self.assertEqual(r['opportunities'],[])
 def test_scope_rejected(self):
  s.put('run','run',{'id':'run','opportunities':[]})
  with self.assertRaises(ValueError):s.research('run',['foreign'])
 def test_negative_capital(self):
  with self.assertRaises(ValueError):s.save_profile({'capital':-1})
 def test_profile_persisted(self):s.save_profile({'capital':None,'working_hours_week':10});self.assertEqual(s.profile()['working_hours_week'],10)
 def test_stop_prevents_fetch(self):
  s.STOP.set()
  with patch('service.fetch') as f:r=s.scan({'topic':'x','country':'Iran'})
  f.assert_not_called();self.assertEqual(r['status'],'stopped')
if __name__=='__main__':unittest.main()
