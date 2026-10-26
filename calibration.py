"""Agreement with user priority labels; not proof of market success or profitability."""
from itertools import combinations

def evaluate_feedback(rows):
    valid=[r for r in rows if type(r.get('priority')) is int and 1<=r['priority']<=5]
    comparable=0;agreement=0;ties=0
    for a,b in combinations(valid,2):
        if a.get('run_id')!=b.get('run_id') or a.get('rubric_version')!=b.get('rubric_version') or a['priority']==b['priority']:continue
        av,bv=a.get('market_score'),b.get('market_score')
        if av is None or bv is None:continue
        comparable+=1
        if av==bv:ties+=1;agreement+=0.5
        elif (av-bv)*(a['priority']-b['priority'])>0:agreement+=1
    return {'labelled_cases':len(valid),'comparable_pairs':comparable,'tied_predictions':ties,'pairwise_agreement':round(agreement/comparable,4) if comparable else None,'status':'measured_user_label_agreement' if comparable else 'insufficient_comparable_labels','label_source':'user_self_reported','independently_validated':False,'weights_changed':False,'limitations':'Agreement with user labels only. Not empirical validation of demand, income or profitability.'}
