import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import service as s
import legacy

class SourcesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=s.DB;s.DB=Path(self.tmp.name)/'test.db';s.ACTIVE=False;s.STOP.clear()
 def tearDown(self):
  s.DB=self.old;self.tmp.cleanup();s.ACTIVE=False;s.STOP.clear()
 def source(self):return s.save_source({'name':'Example feed','feed_url':'https://example.org/feed','enabled':True})
 def config(self,source):return {'topic':'dashboard','source_mode':'feeds','source_ids':[source['id']]}
 def test_registration_does_not_claim_connection(self):
  source=self.source();self.assertEqual(s.source_by_id(source['id'])['health']['status'],'not_tested')
  with self.assertRaises(ValueError):self.source()
 def test_reject_private_and_credentials(self):
  for url in ['http://example.org/feed','https://127.0.0.1/feed','https://localhost/feed','https://user:password@example.org/feed']:
   with self.assertRaises(ValueError):s.save_source({'name':'x','feed_url':url})
 def test_disabled_source_cannot_run(self):
  source=self.source();s.save_source({'id':source['id'],'enabled':False})
  with self.assertRaises(ValueError):s.validate_config(self.config(source))
 def test_probe_failure_persisted_not_success(self):
  source=self.source()
  with patch('service.fetch',side_effect=OSError('offline')):result=s.probe_source(source['id'])
  self.assertEqual(result['status'],'failed');self.assertEqual(s.source_by_id(source['id'])['health']['status'],'failed')
 def test_direct_feed_avoids_search_provider_and_tracks_source(self):
  source=self.source();item={'title':'dashboard needed','text':'dashboard request','url':'https://buyer.example/job','source':source['feed_url'],'date':s.now()}
  with patch('service.fetch',return_value=[item]) as fetch,patch('providers.search') as search:r=s.scan(self.config(source))
  search.assert_not_called();fetch.assert_called_once_with(source['feed_url'])
  self.assertEqual(r['status'],'completed');self.assertEqual(r['raw_items'][0]['source_id'],source['id']);self.assertEqual(r['usage']['searches'],1)
 def test_resume_uses_original_source_snapshot(self):
  source=self.source();r=s.new_run(s.validate_config(self.config(source)))
  s.save_source({'id':source['id'],'feed_url':'https://example.org/new-feed'})
  with patch('service.fetch',return_value=[]) as fetch:s.scan({},r['id'])
  fetch.assert_called_once_with('https://example.org/feed')
 def test_html_xml_does_not_pass_as_empty_feed(self):
  with self.assertRaises(ValueError):legacy.parse(b'<html><body>Login</body></html>','https://example.org')
  self.assertEqual(legacy.parse(b'<rss><channel/></rss>','https://example.org'),[])
 def test_feed_endpoint_change_invalidates_health(self):
  source=self.source()
  with patch('service.fetch',return_value=[]):s.probe_source(source['id'])
  self.assertEqual(s.source_by_id(source['id'])['health']['status'],'empty')
  s.save_source({'id':source['id'],'feed_url':'https://example.org/new'})
  self.assertEqual(s.source_by_id(source['id'])['health']['status'],'not_tested')

if __name__=='__main__':unittest.main()
