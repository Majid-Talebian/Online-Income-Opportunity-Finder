"""Generate a reviewable sample using the application's actual analysis/report code."""
import argparse
from pathlib import Path
import architecture,reports

def build_cases():
 specs=[('داشبورد مدیریتی فروش','فروش خدمت',30000000,18000000,10000000,{}),('اتوماسیون گزارش مالی','فروش خدمت',20000000,24000000,10000000,{}),('بسته‌بندی صادراتی خشکبار','فروش کالا',None,None,None,{'payment':'blocked'})]
 cases=[]
 for index,(title,model,revenue,cost,fixed,gates) in enumerate(specs):
  lead={'id':'sample-'+str(index),'title':title,'text':title+' — Customer needs a tailored solution and requests a budget quote. These are synthetic review inputs, not a real purchase.','url':'https://sample.example/need/'+str(index),'source':'https://sample.example/feed','date':'2026-10-25T00:00:00Z'}
  supplier={'title':title+' / عرضه نمونه','text':title+' — Supplier offers a similar product; capacity and delivery are not verified. Synthetic sample.','url':'https://supplier.example/offer/'+str(index),'source':'https://supplier.example/feed','date':''}
  run={'id':'sample-run-'+str(index),'raw_items':[lead,supplier],'config':{'market_sector':'خدمات داده و گزارش' if index<2 else 'کالا و بسته‌بندی','business_model':model,'customer':'شرکت کوچک / مشتری فرضی' if index<2 else 'واردکننده فرضی','country':'Iran'}}
  analysis=architecture.analyze_opportunity(lead,run,{'skills_user_reported':['داشبورد','گزارش مالی'],'working_hours_week':10,'capital':None},{'economics':{'revenue_per_sale':revenue,'variable_cost_per_sale':cost,'fixed_cost_period':fixed,'currency':'IRR'},'gates':gates})
  analysis['sample_data']=True
  for evidence in analysis['evidence']:evidence['evidence_status']='synthetic'
  cases.append((analysis,title))
 return cases

def main():
 parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(reports.render_cases(build_cases(),sample=True),encoding='utf-8')
if __name__=='__main__':main()
