import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
import evidence,architecture,screening,source_discovery
import service as s

class PhaseAcceptance(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=s.DB;s.DB=Path(self.temp.name)/'state.db';s.STOP.clear();s.ACTIVE=False
 def tearDown(self):s.DB=self.old;self.temp.cleanup();s.STOP.clear();s.ACTIVE=False
 def item(self,**kw):
  return dict(dict(title='dashboard request',text='customer needs dashboard report',url='https://example.org/job',source='https://example.org/feed',date=s.now()),**kw)
 def test_profile_boundaries_and_restart(self):
  s.save_profile({'working_hours_week':168,'capital':0,'max_results':100,'max_age':365,'target_countries':['Iran']})
  self.assertEqual(s.profile()['capital'],0)
  for v in [0,101,True]:
   with self.assertRaises(ValueError):s.save_profile({'max_results':v})
  self.assertEqual(s.profile()['max_results'],100)
 def test_mission_draft_retains_fields(self):
  draft={'topic':'dashboard','source_mode':'search','discovery_mode':'topic','country':'Iran','province':'test','city':'test','market_sector':'retail','business_model':'service','customer':'shops','exclude':'gambling','source_ids':[]}
  s.save_mission_draft(draft)
  for k,v in draft.items():self.assertEqual(s.mission_draft()[k],v)
  with self.assertRaises(ValueError):s.save_mission_draft({**draft,'topic':12})
  self.assertEqual(s.mission_draft()['topic'],'dashboard')
 def test_client_cannot_inject_discovery_topics(self):
  c=s.validate_config({'topic':'dashboard','discovery_topics':['forbidden']})
  self.assertNotIn('discovery_topics',c)
 def test_general_skips_forbidden_and_shares_budget(self):
  s.save_profile({'skills_user_reported':['forbidden','dashboard','Excel'],'forbidden_topics':['forbidden']})
  c=s.validate_config({'discovery_mode':'general'})
  self.assertEqual(c['topic'],'dashboard');r=s.new_run(c)
  self.assertEqual([q['topic'] for q in r['queries'][:2]],['dashboard','Excel'])
 def test_result_limit_and_exclusions_effective(self):
  s.save_profile({'max_results':1,'forbidden_topics':['gambling']})
  items=[self.item(url='https://example.org/'+str(i)) for i in range(3)]+[self.item(title='dashboard gambling',url='https://example.org/bad')]
  with patch('service.fetch',return_value=items):r=s.scan({'topic':'dashboard'})
  self.assertEqual(len(r['opportunities']),1)
  self.assertNotIn('gambling',r['opportunities'][0]['title'])
 def test_syndication_does_not_inflate_evidence(self):
  text='Customer needs a bespoke dashboard. This long paragraph has been copied across several publishing domains unchanged.'
  rows,report=evidence.normalize_items([self.item(text=text,url='https://one.example/job'),self.item(text=text,url='https://two.example/mirror')])
  self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['origins']),2)
  self.assertTrue(rows[0]['possible_republication']);self.assertEqual(report['duplicates'],1)
 def test_unsafe_urls_and_empty_title_rejected(self):
  rows,report=evidence.normalize_items([self.item(url='javascript:alert(1)'),self.item(url='https://127.0.0.1/x'),self.item(title='')])
  self.assertEqual(rows,[]);self.assertEqual(len(report['rejected']),3)
 def test_date_quality_states(self):
  self.assertEqual(evidence.publication_age('nonsense')[1],'invalid')
  self.assertEqual(evidence.publication_age('')[1],'missing')
  self.assertEqual(evidence.publication_age('2999-01-01T00:00:00Z')[1],'future')
 def test_negative_purchase_signal_not_counted(self):
  ev=architecture._evidence([self.item(text='No budget; not hiring and do not need a dashboard')])
  self.assertNotIn('purchase_intent',ev[0]['categories']);self.assertIsNone(screening.market_score(ev)['score'])
 def test_score_responds_to_freshness_not_republication(self):
  fresh=architecture._evidence([self.item()]);old=architecture._evidence([self.item(date=(datetime.now(timezone.utc)-timedelta(days=200)).isoformat())])
  self.assertGreater(screening.market_score(fresh)['score'],screening.market_score(old)['score'])
  market=screening.market_score(fresh)
  self.assertEqual(sum(x['points'] or 0 for x in market['components']),market['score'])
 def test_no_money_bonus_without_cost_requirement(self):
  report=screening.execution_fit(self.item(),{'capital':1000000,'working_hours_week':40})
  self.assertIsNone(report['score']);self.assertEqual(report['coverage_percent'],0)
 def test_requirements_compared_to_capacity(self):
  x=self.item(required_capital=100,required_hours_week=8)
  self.assertGreater(screening.execution_fit(x,{'capital':100,'working_hours_week':8})['score'],screening.execution_fit(x,{'capital':0,'working_hours_week':2})['score'])
 def test_feed_discovery_ignores_unsafe_and_duplicate(self):
  parser=source_discovery.FeedLinks('https://example.org/blog')
  parser.feed('<link rel="alternate" type="application/rss+xml" href="/feed"><link rel="alternate" type="application/rss+xml" href="javascript:x"><link rel="alternate" type="application/rss+xml" href="/feed">')
  self.assertEqual([x['feed_url'] for x in parser.links],['https://example.org/feed'])
 def test_source_archive_preserves_old_run(self):
  source=s.save_source({'name':'test','feed_url':'https://example.org/feed','enabled':True})
  r=s.new_run(s.validate_config({'topic':'dashboard','source_mode':'feeds','source_ids':[source['id']]}))
  s.archive_source(source['id'])
  with self.assertRaises(ValueError):s.source_by_id(source['id'])
  self.assertEqual(s.get(r['id'])['queries'][0]['source_id'],source['id'])
 def test_failed_source_no_replacement_and_saved_screening(self):
  with patch('service.fetch',side_effect=OSError('offline')):r=s.scan({'topic':'dashboard'})
  self.assertEqual(r['opportunities'],[])
  with patch('service.fetch',return_value=[self.item()]):r=s.scan({'topic':'dashboard'})
  self.assertEqual(r['opportunities'][0]['screening']['version'],screening.VERSION)
  self.assertEqual(s.get(r['id'])['opportunities'][0]['screening'],r['opportunities'][0]['screening'])

if __name__=='__main__':unittest.main()

class ParserAcceptance(unittest.TestCase):
 def test_atom_alternate_relative_link_and_published(self):
  import legacy
  data=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Test</title><link rel="self" href="/api"/><link rel="alternate" href="/job"/><published>2026-01-01</published><content>Need dashboard</content></entry></feed>'
  row=legacy.parse(data,'https://example.org/feed')[0]
  self.assertEqual(row['url'],'https://example.org/job');self.assertEqual(row['date'],'2026-01-01');self.assertEqual(row['text'],'Need dashboard')
 def test_rss_one_namespaces(self):
  import legacy
  data=b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"><item><title>Test</title><link>https://example.org/job</link><description>dashboard</description></item></rdf:RDF>'
  self.assertEqual(legacy.parse(data,'https://example.org/feed')[0]['title'],'Test')

class TrustAcceptance(unittest.TestCase):
 def test_discovery_network_error_is_structured(self):
  with patch('source_discovery.discover',side_effect=OSError('offline')):result=s.discover_source({'url':'https://example.org'})
  self.assertEqual(result['status'],'failed');self.assertFalse(result['verified_connection']);self.assertEqual(result['candidates'],[])
 def test_document_identity_is_repeatable(self):
  item={'title':'Need dashboard','text':'Customer needs dashboard','source':'https://example.org/feed','url':'https://example.org/job','date':''}
  self.assertEqual(architecture._evidence([item])[0]['id'],architecture._evidence([item])[0]['id'])
