import unittest, tempfile, math
from pathlib import Path
from unittest.mock import patch
import service as s

class Foundation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=s.DB;s.DB=Path(self.tmp.name)/'test.db';s.STOP.clear();s.ACTIVE=False
 def tearDown(self):
  s.DB=self.old;self.tmp.cleanup();s.STOP.clear();s.ACTIVE=False
 def item(self):return {'title':'dashboard project','text':'dashboard needed','url':'https://example.org/1','source':'https://example.org/feed','date':s.now()}
 def test_geography_not_invented(self):
  with patch('service.fetch',return_value=[self.item()]):r=s.scan({'topic':'dashboard','country':'Iran','city':'Tehran'})
  x=r['opportunities'][0];self.assertIsNone(x['country']);self.assertIsNone(x['city']);self.assertEqual(x['search_region']['city'],'Tehran');self.assertEqual(x['category'],'discovery_lead')
 def test_budget_is_enforced(self):
  s.save_profile({'max_searches':1})
  with patch('service.fetch',return_value=[self.item()]) as f:r=s.scan({'topic':'dashboard'})
  self.assertEqual(f.call_count,1);self.assertEqual(r['status'],'budget_exhausted');self.assertEqual(r['usage']['searches'],1)
 def test_resume_does_not_repeat_completed_source(self):
  def first(url):s.STOP.set();return [self.item()]
  with patch('service.fetch',side_effect=first):r=s.scan({'topic':'dashboard'})
  self.assertEqual(r['cursor'],1);self.assertEqual(r['status'],'stopped');s.STOP.clear()
  with patch('service.fetch',return_value=[self.item()]) as f:r=s.scan({},r['id'])
  self.assertEqual(f.call_count,2);self.assertEqual(r['usage']['searches'],3);self.assertEqual(len(r['opportunities']),1)
 def test_general_uses_saved_skills(self):
  s.save_profile({'skills_user_reported':['dashboard']})
  with patch('service.fetch',return_value=[self.item()]):r=s.scan({'discovery_mode':'general'})
  self.assertEqual(r['config']['topic'],'dashboard');self.assertEqual(len(r['opportunities']),1)
 def test_profile_patch_and_history(self):
  s.save_profile({'capital':500,'working_hours_week':10});s.save_profile({'max_searches':2})
  self.assertEqual(s.profile()['capital'],500);self.assertEqual(len(s.all_kind('profile_version')),2)
 def test_nonfinite_rejected(self):
  for value in [math.nan,math.inf,True,-1]:
   with self.assertRaises(ValueError):s.save_profile({'capital':value})
 def test_recovery_preserves_reserved_usage(self):
  r=s.new_run(s.validate_config({'topic':'dashboard'}));r.update(status='running',inflight=0);r['usage']['searches']=1;s.put(r['id'],'run',r);s.recover()
  actual=s.get(r['id']);self.assertEqual(actual['status'],'interrupted');self.assertEqual(actual['usage']['searches'],1)
 def test_forbidden_topic_rejected(self):
  s.save_profile({'forbidden_topics':['dashboard']})
  with self.assertRaises(ValueError):s.validate_config({'topic':'dashboard sales'})
 def test_partial_not_complete(self):
  with patch('service.fetch',side_effect=[[self.item()],OSError('offline'),[]]):r=s.scan({'topic':'dashboard'})
  self.assertEqual(r['status'],'partial')
 def test_invalid_source_shape_is_not_valid(self):
  with patch('service.fetch',return_value=[{}]):r=s.scan({'topic':'dashboard'})
  self.assertEqual(r['status'],'no_data');self.assertEqual(r['sources'][0]['structure'],'unverified')

if __name__=='__main__':unittest.main()
