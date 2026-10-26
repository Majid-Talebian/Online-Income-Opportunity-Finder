"""Versioned, deterministic research-priority rubric. No calibrated success probability."""
import re
VERSION='screening-2.0'

def market_score(evidence):
    demand=[e for e in evidence if set(e['categories']) & {'purchase_intent','transaction','problem'}]
    if not demand:return {'score':None,'confidence':'insufficient','factors':['هیچ نشانه مرتبط از نیاز ثبت نشده'],'reason':'داده ناکافی برای رتبه پژوهشی','rubric_version':VERSION,'components':[]}
    fresh=[e for e in demand if e['age_days'] is not None and e['age_days']<=90]
    dated=[e for e in demand if e['age_days'] is not None]
    # Different domains can republish the same story; they are never independent buyers.
    hosts={e['host'] for e in demand if e['host']}
    components=[{'name':'نشانه مرتبط از مسئله یا قصد خرید','points':min(40,len(demand)*10),'maximum':40},
                {'name':'سهم شواهد تا ۹۰ روز','points':round(30*len(fresh)/len(demand)) if dated else None,'maximum':30},
                {'name':'تنوع دامنه؛ استقلال تأیید نشده','points':min(15,len(hosts)*5),'maximum':15},
                {'name':'قابلیت پیگیری منبع','points':round(15*sum(bool(e.get('url')) for e in demand)/len(demand)),'maximum':15}]
    score=sum(c['points'] or 0 for c in components)
    return {'score':score,'confidence':'low' if len(demand)<3 or not dated else 'medium','factors':[c['name']+': '+str(c['points'] if c['points'] is not None else 'نامعلوم')+' / '+str(c['maximum']) for c in components],'components':components,'rubric_version':VERSION,'reason':'امتیاز اولویت بررسی؛ قواعد با آزمون‌های مرزی بررسی شده‌اند و با نتایج بازار واقعی کالیبره نشده‌اند.'}

def execution_fit(opportunity,profile):
    body=(opportunity.get('title','')+' '+opportunity.get('text','')).casefold()
    skills=[s.casefold() for s in profile.get('skills_user_reported',[])]
    words=set(re.findall(r'[\wآ-ی]{3,}',body))
    hits=[s for s in skills if s in body or len(set(re.findall(r'[\wآ-ی]{3,}',s)) & words)>=2]
    components=[]
    components.append({'name':'تناسب مهارت ثبت‌شده','points':(60 if hits else 0) if skills else None,'maximum':60})
    for key,available,weight,title in [('required_hours_week',profile.get('working_hours_week'),20,'زمان موردنیاز نسبت به زمان موجود'),('required_capital',profile.get('capital'),20,'سرمایه موردنیاز نسبت به سرمایه موجود')]:
        required=opportunity.get(key)
        known=isinstance(required,(int,float)) and not isinstance(required,bool) and required>=0 and available is not None
        components.append({'name':title,'points':weight if known and available>=required else 0 if known else None,'maximum':weight})
    known=[c for c in components if c['points'] is not None]
    score=round(100*sum(c['points'] for c in known)/sum(c['maximum'] for c in known)) if known else None
    return {'score':score,'confidence':'low' if len(known)<3 else 'medium','matched_skills':hits,'components':components,'coverage_percent':sum(c['maximum'] for c in known),'rubric_version':VERSION,'factors':[c['name']+': '+('نامعلوم' if c['points'] is None else str(c['points'])+' / '+str(c['maximum'])) for c in components]}
