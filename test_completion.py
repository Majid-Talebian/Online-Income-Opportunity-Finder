import unittest,tempfile
from pathlib import Path
import evidence,architecture,screening,calibration,service as s

class CompletionChecks(unittest.TestCase):
 def rows(self):
  text=' '.join(['customer','requires','dashboard','reporting','automation','weekly','sales','inventory','purchasing','records','quality','analysis','spreadsheet','integration','service','delivery','support','project','planning','review','dataset','financial','operations','management','business','insights','capacity','timeline','consultation','decision']*3)
  return [{'title':'dashboard request','text':text,'url':'https://one.example/job','source':'https://one.example/feed','date':s.now()}, {'title':'dashboard request copy','text':text+' Additional editorial note.','url':'https://two.example/copy','source':'https://two.example/feed','date':s.now()}]
 def test_near_republication_flag_preserves_records_and_origins(self):
  rows,_=evidence.normalize_items(self.rows());self.assertEqual(len(rows),2)
  self.assertEqual(rows[0]['republication_group'],rows[1]['republication_group']);self.assertEqual(rows[1]['similarity_review']['decision'],'human_review_required')
 def test_same_topic_different_amount_not_grouped(self):
  rows=self.rows();rows[0]['text']+=' Budget 1000';rows[1]['text']+=' Budget 5000'
  normalized,_=evidence.normalize_items(rows);self.assertNotIn('republication_group',normalized[1])
 def test_probable_mirror_does_not_increase_priority(self):
  rows,_=evidence.normalize_items(self.rows());combined=architecture._evidence(rows)
  self.assertEqual(screening.market_score(combined)['score'],screening.market_score(combined[:1])['score'])
 def test_unrelated_documents_not_grouped(self):
  rows=self.rows();rows[1]['text']='A manufacturer offers packaging supplies and logistics services for export customers. '*4
  normalized,_=evidence.normalize_items(rows);self.assertNotIn('republication_group',normalized[1])
 def test_insufficient_labels_remain_unknown(self):
  report=calibration.evaluate_feedback([]);self.assertIsNone(report['pairwise_agreement']);self.assertFalse(report['independently_validated'])
 def test_calibration_compares_same_run_and_version_only(self):
  rows=[{'run_id':'run','rubric_version':'v','priority':5,'market_score':70},{'run_id':'run','rubric_version':'v','priority':1,'market_score':20},{'run_id':'other','rubric_version':'v','priority':1,'market_score':100}]
  report=calibration.evaluate_feedback(rows);self.assertEqual(report['comparable_pairs'],1);self.assertEqual(report['pairwise_agreement'],1);self.assertFalse(report['weights_changed'])
 def test_calibration_tie_and_disagreement(self):
  rows=[{'run_id':'run','rubric_version':'v','priority':5,'market_score':20},{'run_id':'run','rubric_version':'v','priority':1,'market_score':20}]
  self.assertEqual(calibration.evaluate_feedback(rows)['pairwise_agreement'],0.5)
  rows[1]['market_score']=80;self.assertEqual(calibration.evaluate_feedback(rows)['pairwise_agreement'],0)
 def test_feedback_updates_without_duplicate_and_requires_reason(self):
  with tempfile.TemporaryDirectory() as temp:
   old=s.DB;s.DB=Path(temp)/'test.db'
   try:
    s.put('run','run',{'id':'run','opportunities':[{'id':'lead','url':'https://example.org/job','screening':{'version':screening.VERSION,'market':{'score':65}}}]})
    with self.assertRaises(ValueError):s.save_screening_feedback({'run_id':'run','opportunity_id':'lead','priority':5,'note':''})
    body={'run_id':'run','opportunity_id':'lead','priority':5,'note':'Customer needs fit current skills'};s.save_screening_feedback(body)
    s.save_screening_feedback({**body,'priority':3});self.assertEqual(len(s.all_kind('screening_feedback')),1);self.assertEqual(s.all_kind('screening_feedback')[0]['priority'],3)
   finally:s.DB=old

if __name__=='__main__':unittest.main()
