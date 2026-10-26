import unittest, tempfile
from pathlib import Path
from unittest.mock import patch
import architecture as a
import service as s

class AssessmentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=s.DB;s.DB=Path(self.tmp.name)/'test.db'
 def tearDown(self):
  s.DB=self.db;self.tmp.cleanup()
 def fixture(self):
  x={'id':'lead','title':'dashboard sales','text':'customer needs dashboard sales; orders sold','url':'https://example.org/item','source':'search','date':s.now()}
  run={'id':'run','opportunities':[x],'raw_items':[x,dict(x,url=x['url']+'?utm_source=copy#fragment')],'config':{},'profile_snapshot':{}}
  s.put('run','run',run);return x,run
 def test_canonical_dedup_preserves_meaningful_query(self):
  self.assertEqual(a.canonical_url('https://EXAMPLE.org/x/?utm_source=a&sku=1#x'),'https://example.org/x/?sku=1')
  x,r=self.fixture();self.assertEqual(len(a.analyze_opportunity(x,r,{})['evidence']),1)
 def test_transaction_mention_never_verified(self):
  x,r=self.fixture();report=a.analyze_opportunity(x,r,{})
  self.assertTrue(report['evidence'][0]['transaction_mention']);self.assertFalse(report['evidence'][0]['verified_transaction'])
 def test_missing_fixed_cost_does_not_imply_zero_break_even(self):
  e=a._economics({'revenue_per_sale':10,'variable_cost_per_sale':2})
  self.assertIsNone(e['break_even_sales']);self.assertFalse(e['fixed_cost_known'])
 def test_zero_fixed_cost_is_explicit(self):
  self.assertEqual(a._economics({'revenue_per_sale':10,'variable_cost_per_sale':2,'fixed_cost_period':0})['break_even_sales'],0)
 def test_invalid_economics_cannot_generate_profit(self):
  for value in [True,float('nan'),float('inf'),-1]:
   self.assertEqual(a._economics({'revenue_per_sale':value,'variable_cost_per_sale':2})['status'],'invalid_inputs')
 def test_future_date_not_counted_fresh(self):
  self.assertIsNone(a._age_days({'date':'2999-01-01T00:00:00+00:00'}))
 def test_multi_selection_cannot_reuse_same_economics(self):
  x,r=self.fixture();r['opportunities'].append(dict(x,id='other'));s.put('run','run',r)
  with self.assertRaises(ValueError):s.research('run',['lead','other'],{'economics':{'revenue_per_sale':2}})
 def test_task_audit_and_report_consistency(self):
  self.fixture();report=s.research('run',['lead']);an=report['analyses'][0];task=an['validation_plan'][0]
  with self.assertRaises(ValueError):s.update_validation_task(an['id'],task['id'],{'status':'done'})
  s.update_validation_task(an['id'],task['id'],{'status':'done','note':'Customer interview documented'})
  saved=s.get(an['id']);self.assertEqual(saved['validation_progress']['done'],1)
  self.assertEqual(saved['validation_plan'][0]['history'][0]['from'],'todo')
  self.assertEqual(s.get(report['id'])['dossiers'][0]['validation_plan'][0]['status'],'done')
 def test_blocked_gate_stops_recommendation(self):
  x,r=self.fixture();report=a.analyze_opportunity(x,r,{}, {'gates':{'payment':'blocked'}})
  self.assertEqual(report['decision']['label'],'توقف تا رفع مانع');self.assertFalse(report['decision']['auto_action_allowed'])

if __name__=='__main__':unittest.main()
