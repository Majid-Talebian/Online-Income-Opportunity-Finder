import unittest
import reports
from demo_output import build_cases

class ReportChecks(unittest.TestCase):
 def test_loss_making_scenario_blocks_recommendation(self):
  a,title=build_cases()[1]
  self.assertEqual(a['decision']['label'],'توقف تا رفع مانع')
  self.assertTrue(any(r['id']=='negative_economics' for r in a['risks']))
 def test_actual_report_has_full_dossier_and_no_sample_banner(self):
  a,title=build_cases()[0];a.pop('sample_data');html=reports.render_report(a,title)
  self.assertNotIn('نمایش با داده کاملاً فرضی',html)
  for section in a['sections']:self.assertIn(section['name'],html)
  self.assertIn('30000000',html.replace(',',''));self.assertIn('ظرفیت اجرا',html)
 def test_sample_cannot_be_confused_with_live_sources(self):
  html=reports.render_cases(build_cases(),sample=True)
  self.assertIn('نمایش با داده کاملاً فرضی',html);self.assertNotIn('href="https://sample.example',html)
 def test_untrusted_text_escaped(self):
  a,title=build_cases()[0];a['evidence'][0]['excerpt']='<script>alert(1)</script>'
  html=reports.render_report(a,'<img src=x onerror=alert(1)>')
  self.assertNotIn('<script>alert(1)',html);self.assertNotIn('<img src=x',html);self.assertIn('&lt;script&gt;',html)
 def test_unknown_economics_stays_unknown(self):
  a,title=build_cases()[2];html=reports.render_report(a,title)
  self.assertIn('نامعلوم',html);self.assertEqual(a['economics']['status'],'unknown')

if __name__=='__main__':unittest.main()
