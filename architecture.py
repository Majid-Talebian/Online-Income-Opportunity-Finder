"""Transparent opportunity assessment pipeline for the local-first assistant.

Signals in this module are deterministic heuristics. They organize evidence; they
do not claim to prove demand, legality, payment access, or profitability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit
import re
import math
from urllib.parse import urlunsplit, parse_qsl, urlencode

import uuid
import hashlib
import evidence as evidence_tools
from evidence import canonical_url
import screening

AGENTS = [
    {"id": "coordinator", "name": "هماهنگ‌کننده مأموریت", "stage": "workflow", "mode": "rules", "purpose": "ثبت ورودی، کنترل سقف‌ها و هدایت مراحل"},
    {"id": "source_discovery", "name": "کاشف منابع", "stage": "discovery", "mode": "connector", "purpose": "اجرای جست‌وجو از ارائه‌دهنده تنظیم‌شده"},
    {"id": "evidence_normalizer", "name": "پاک‌ساز شواهد", "stage": "evidence", "mode": "rules", "purpose": "یکسان‌سازی، حذف تکرار و حفظ پیوند منبع"},
    {"id": "demand_analyst", "name": "تحلیل‌گر تقاضا", "stage": "evidence", "mode": "rules", "purpose": "دسته‌بندی نشانه‌های نیاز و قصد خرید"},
    {"id": "supply_analyst", "name": "تحلیل‌گر عرضه و شکاف", "stage": "evidence", "mode": "rules", "purpose": "ثبت شواهد عرضه و موارد نامعلوم"},
    {"id": "competition_analyst", "name": "تحلیل‌گر رقابت و تازگی", "stage": "evidence", "mode": "rules", "purpose": "شناسایی نشانه رقبا و تازگی شواهد"},
    {"id": "market_scorer", "name": "امتیازده بازار", "stage": "screening", "mode": "rules", "purpose": "امتیاز مستقل بازار با توضیح عوامل"},
    {"id": "execution_fit", "name": "ارزیاب تناسب اجرا", "stage": "screening", "mode": "rules", "purpose": "سنجش تناسب با مهارت، زمان و سرمایه ثبت‌شده"},
    {"id": "economics", "name": "تحلیل‌گر اقتصاد", "stage": "deep_analysis", "mode": "calculation", "purpose": "محاسبه فقط از ورودی عددی صریح کاربر"},
    {"id": "risk_gate", "name": "کنترل‌گر قیود و ریسک", "stage": "deep_analysis", "mode": "rules", "purpose": "جلوگیری از عبور از مانع حل‌نشده"},
    {"id": "validation_planner", "name": "طراح آزمون کوچک", "stage": "validation", "mode": "rules", "purpose": "ساخت گام‌های کم‌هزینه برای رفع مجهولات"},
    {"id": "quality_reviewer", "name": "بازبین شواهد", "stage": "quality", "mode": "rules", "purpose": "کنترل منشأ، تازگی و وضعیت ادعاها"},
]

SECTIONS = ["منشأ ایده", "نیاز مشتری", "جغرافیا", "شواهد", "عرضه‌کنندگان", "شکاف بازار", "رقبا و تازگی", "تأمین یا تولید", "صادرات از ایران", "اقتصاد", "تناسب با شرکت", "الزامات", "ریسک", "آزمون کوچک"]

PATTERNS = {
    "purchase_intent": r"\b(buy|purchase|looking for|request|need|tender|quote|budget|hire|client|customer)\b|خرید|درخواست|نیاز|مشتری|بودجه|مناقصه|استخدام",
    "transaction": r"\b(sold|sales|orders|revenue|transaction|contract awarded)\b|فروش ثبت|معامله|سفارش ثبت|قرارداد منعقد",
    "supply": r"\b(supplier|manufacturer|provider|price|catalog|capacity|stock)\b|تأمین‌کننده|تولیدکننده|ارائه‌دهنده|قیمت|ظرفیت|موجودی",
    "competition": r"\b(competitor|alternative|marketplace|compare|similar product)\b|رقیب|جایگزین|بازارگاه|محصول مشابه",
    "problem": r"\b(problem|complaint|issue|pain point|waste|delay)\b|مشکل|شکایت|دردسر|اتلاف|تأخیر",
    "trend": r"\b(trend|launch|innovation|emerging|popular)\b|روند|نوظهور|نوآوری|محبوب|ترند",
}
GATES = [
    ("payment", "مسیر دریافت وجه", "روش پرداخت و دریافت وجه باید با وضعیت واقعی کاربر بررسی شود."),
    ("customer", "مشتری پرداخت‌کننده", "قصد خرید باید از مشتری مستقل و قابل تماس تأیید شود."),
    ("capacity", "ظرفیت اجرا یا تأمین", "ظرفیت و زمان تحویل مجری یا تأمین‌کننده باید مستند شود."),
    ("compliance", "مجوز و الزامات", "مجوز، استاندارد و مقررات مقصد باید برای مورد مشخص بررسی شود."),
    ("delivery", "تحویل و پشتیبانی", "هزینه، زمان و مسئولیت تحویل یا پشتیبانی باید روشن شود."),
]

def _now():
    return datetime.now(timezone.utc).isoformat()

def _host(url):
    try: return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except Exception: return ""

def _date(value):
    if not value: return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except Exception:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(value)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception: return None

def _age_days(item):
    dt = _date(item.get("date", ""))
    if dt is None: return None
    age = (_date(_now()) - dt).total_seconds() / 86400
    return None if age < 0 else age

def _related_items(opportunity, run):
    title_words = {w.casefold() for w in re.findall(r"[\wآ-ی]{3,}", opportunity.get("title", ""))}
    selected_url = opportunity.get("url")
    rows = []
    pool=run.get("normalized_items")
    if pool is None:pool=evidence_tools.normalize_items(run.get("raw_items", []))[0]
    for item in pool:
        body = (item.get("title", "") + " " + item.get("text", "")).casefold()
        overlap = sum(1 for w in title_words if w in body)
        if item.get("url") == selected_url or (title_words and overlap >= min(2, len(title_words))):
            rows.append(item)
    if not rows and opportunity.get("url"):
        rows = [{"title": opportunity.get("title", ""), "text": opportunity.get("text", ""), "url": opportunity["url"], "source": opportunity.get("source", ""), "date": opportunity.get("date", "")}]
    dedup, seen = [], set()
    for x in rows:
        key = canonical_url(x["url"]) if x.get("url") else (x.get("title", "").casefold(), x.get("source", ""))
        if key not in seen: seen.add(key); dedup.append(x)
    return dedup

def _evidence(items):
    out = []
    for item in items:
        body = (item.get("title", "") + " " + item.get("text", ""))[:5000]
        kinds = [name for name, pattern in PATTERNS.items() if re.search(pattern, body, re.I)]
        negative = bool(re.search(r"\b(no (?:need|budget)|not (?:buying|hiring)|do not need)\b|نیازی ندار|بودجه ندار|خریدار نیست", body, re.I))
        if negative:kinds=[k for k in kinds if k not in ('purchase_intent','transaction')]
        out.append({"negated_purchase_signal": negative, "id": hashlib.sha256((item.get("url", "")+"\n"+body).encode()).hexdigest()[:24], "title": item.get("title", ""), "url": item.get("url", ""), "host": _host(item.get("url", "")), "source": item.get("source", ""), "source_id": item.get("source_id"), "acquisition": item.get("acquisition", "unknown"), "published_at": item.get("date") or None, "retrieved_at": item.get("retrieved_at") or _now(), "republication_group": item.get("republication_group"), "similarity_review": item.get("similarity_review"), "origins": item.get("origins", []), "possible_republication": item.get("possible_republication", False), "evidence_quality": item.get("evidence_quality", {}), "categories": kinds, "excerpt": item.get("text", "")[:1200], "evidence_status": "source_observed" if item.get("url", "").startswith("https://") else "source_unverified", "verified_transaction": False, "transaction_mention": "transaction" in kinds, "age_days": _age_days(item)})
    return out

def _market_score(evidence):
    return screening.market_score(evidence)

def _execution_fit(opportunity, profile):
    return screening.execution_fit(opportunity, profile)

def _economics(inputs):
    required = ["revenue_per_sale", "variable_cost_per_sale"]
    if not isinstance(inputs, dict) or any(inputs.get(k) is None for k in required):
        return {"status": "unknown", "currency": inputs.get("currency") if isinstance(inputs, dict) else None, "message": "برای محاسبه، درآمد و هزینه متغیر هر فروش را وارد کنید؛ مقدار فرضی ساخته نمی‌شود."}
    try:
        values = [inputs[required[0]], inputs[required[1]], inputs.get("fixed_cost_period") or 0]
        if any(isinstance(v, bool) for v in values): raise ValueError
        revenue, variable, fixed = map(float, values)
        if not all(__import__("math").isfinite(v) for v in (revenue, variable, fixed)): raise ValueError
        if min(revenue, variable, fixed) < 0 or revenue <= 0: raise ValueError
        margin = revenue - variable
        return {"status": "calculated_scenario", "currency": str(inputs.get("currency") or "نامشخص"), "revenue_per_sale": revenue, "variable_cost_per_sale": variable, "fixed_cost_period": fixed, "contribution_per_sale": margin, "contribution_margin_percent": round(margin / revenue * 100, 2), "fixed_cost_known": inputs.get("fixed_cost_period") is not None, "break_even_sales": None if margin <= 0 or inputs.get("fixed_cost_period") is None else math.ceil(fixed / margin), "message": "سناریوی ورودی کاربر است؛ قیمت و سود بازار مستقلاً تأیید نشده‌اند."}
    except (TypeError, ValueError, OverflowError):
        return {"status": "invalid_inputs", "currency": inputs.get("currency"), "message": "مقادیر اقتصادی باید عددی و نامنفی باشند و درآمد هر فروش از صفر بیشتر باشد."}

def _gates(user_evidence):
    user_evidence = user_evidence if isinstance(user_evidence, dict) else {}
    result = []
    for key, title, why in GATES:
        status = user_evidence.get(key, "unknown")
        if status not in ("confirmed", "blocked", "unknown", "needs_review"): status = "unknown"
        result.append({"id": key, "title": title, "status": status, "reason": why})
    return result

def _plan(gates, economics, profile):
    tasks = []
    for gate in gates:
        if gate["status"] != "confirmed":
            tasks.append({"id": str(uuid.uuid4()), "order": len(tasks) + 1, "title": gate["title"], "action": gate["reason"], "owner": "کاربر با پشتیبانی Agent", "status": "todo", "cost": "نامعلوم تا دریافت پیشنهاد واقعی", "stop_condition": "اگر مانع حل نشد، ورود به اجرا متوقف بماند"})
    if economics.get("status") != "calculated_scenario":
        tasks.append({"id": str(uuid.uuid4()), "order": len(tasks) + 1, "title": "ثبت قیمت و هزینه واقعی", "action": "از مشتری و عرضه‌کننده قیمت قابل استناد بگیرید و هزینه تحویل/کارمزد را جدا ثبت کنید.", "owner": "کاربر با پشتیبانی Agent", "status": "todo", "cost": "نامعلوم", "stop_condition": "بدون حاشیه مشارکت مثبت، آزمون فروش متوقف شود"})
    tasks.append({"id": str(uuid.uuid4()), "order": len(tasks) + 1, "title": "مصاحبه با مشتری مستقل", "action": "حداقل با سه مشتری بالقوه درباره مسئله، راهکار فعلی، بودجه و زمان خرید گفت‌وگو کنید.", "owner": "کاربر", "status": "todo", "cost": "نیازمند تعیین کاربر", "stop_condition": "اگر هیچ مشتری حاضر به گام بعدی نیست، فرضیه بازنگری شود"})
    return tasks

def analyze_opportunity(opportunity, run, profile, user_inputs=None):
    items = _related_items(opportunity, run)
    evidence = _evidence(items)
    categories = {k: [e for e in evidence if k in e["categories"]] for k in PATTERNS}
    market = _market_score(evidence)
    fit = _execution_fit(opportunity, profile)
    economics = _economics((user_inputs or {}).get("economics", {}))
    gates = _gates((user_inputs or {}).get("gates", {}))
    risks = [{"id": g["id"], "severity": "blocking" if g["status"] == "blocked" else "open", "title": g["title"], "status": g["status"], "reason": g["reason"]} for g in gates if g["status"] != "confirmed"]
    if not evidence: risks.append({"id": "evidence", "severity": "blocking", "title": "شواهد کافی نیست", "status": "unknown", "reason": "منبع مستقل و قابل استناد برای این فرصت پیدا نشده است."})
    if economics.get("status") != "calculated_scenario": risks.append({"id": "economics", "severity": "open", "title": "اقتصاد فرصت محاسبه نشده", "status": "unknown", "reason": economics["message"]})
    if economics.get("status")=="calculated_scenario" and economics.get("contribution_per_sale",0)<=0:
        risks.append({"id":"negative_economics","severity":"blocking","title":"اقتصاد زیان‌ده یا بدون حاشیه","status":"blocked","reason":"درآمد هر فروش از هزینه متغیر بیشتر نیست؛ سناریو باید اصلاح شود."})
    decision = "توقف تا رفع مانع" if any(x["severity"] == "blocking" and x["status"] == "blocked" for x in risks) else "آزمون کوچک پس از تکمیل شواهد" if evidence else "ابتدا شواهد مستقل جمع‌آوری شود"
    sections = []
    values = {
        "منشأ ایده": {"status": "source_recorded" if evidence else "unknown", "finding": opportunity.get("title", ""), "evidence_ids": [e["id"] for e in evidence]},
        "نیاز مشتری": {"status": "signals_found" if categories["purchase_intent"] or categories["problem"] else "unknown", "finding": f"نشانه خرید/نیاز: {len(categories['purchase_intent'])}؛ مسئله: {len(categories['problem'])}؛ معامله اثبات‌شده: {sum(e['verified_transaction'] for e in evidence)}", "evidence_ids": [e["id"] for e in categories["purchase_intent"] + categories["problem"]]},
        "جغرافیا": {"status": "unknown", "finding": "محدوده جست‌وجو از محل مشتری، تأمین و تحویل تفکیک می‌شود؛ هیچ شهر یا کشور مشتری از جست‌وجو استنباط نشده است.", "evidence_ids": []},
        "شواهد": {"status": "source_observed" if evidence else "unknown", "finding": f"{len(evidence)} مدرک/سرنخ منبع‌دار ثبت شد؛ هیچ‌کدام به‌تنهایی معامله یا تقاضای قطعی را ثابت نمی‌کند.", "evidence_ids": [e["id"] for e in evidence]},
        "عرضه‌کنندگان": {"status": "signals_found" if categories["supply"] else "unknown", "finding": f"نشانه‌های عرضه: {len(categories['supply'])}؛ ظرفیت تأمین هنوز تأیید نشده است.", "evidence_ids": [e["id"] for e in categories["supply"]]},
        "شکاف بازار": {"status": "unknown", "finding": "وجود شکاف فقط پس از تطبیق نیازهای مستقل با عرضه قابل‌دسترس قابل ارزیابی است.", "evidence_ids": [e["id"] for e in evidence]},
        "رقبا و تازگی": {"status": "signals_found" if categories["competition"] else "unknown", "finding": f"نشانه‌های رقابت: {len(categories['competition'])}؛ تازگی بر اساس تاریخ منبع، در صورت موجود بودن سنجیده شده است.", "evidence_ids": [e["id"] for e in categories["competition"]]},
        "تأمین یا تولید": {"status": "unknown", "finding": "قیمت، کیفیت، ظرفیت و زمان تحویل باید برای عرضه‌کنندهٔ واقعی ثبت شود.", "evidence_ids": [e["id"] for e in categories["supply"]]},
        "صادرات از ایران": {"status": "unknown", "finding": "مقررات، محدودیت‌های پرداخت، گمرک و حمل برای کشور مقصد بررسی نشده‌اند.", "evidence_ids": []},
        "اقتصاد": {"status": economics["status"], "finding": economics["message"], "evidence_ids": []},
        "تناسب با شرکت": {"status": "assessed_low_confidence" if fit["score"] is not None else "unknown", "finding": "؛ ".join(fit["factors"]), "evidence_ids": []},
        "الزامات": {"status": "unknown", "finding": "مجوز، استاندارد و شرط پلتفرم/پرداخت هنوز از مرجع صلاحیت‌دار تأیید نشده است.", "evidence_ids": []},
        "ریسک": {"status": "open" if risks else "unknown", "finding": f"موارد باز: {len(risks)}؛ اقدام تجاری خودکار وجود ندارد.", "evidence_ids": []},
        "آزمون کوچک": {"status": "draft", "finding": "برنامه زیر صرفاً پیشنهاد اعتبارسنجی است و باید توسط کاربر اجرا و ثبت نتیجه شود.", "evidence_ids": []},
    }
    for name in SECTIONS: sections.append({"name": name, **values[name]})
    return {
        "id": str(uuid.uuid4()), "created_at": _now(), "opportunity_id": opportunity["id"], "run_id": run["id"],
        "opportunity_context": {"market_sector": run.get("config", {}).get("market_sector") or None, "business_model": run.get("config", {}).get("business_model") or None, "customer_segment": run.get("config", {}).get("customer") or None, "search_geography": {k: run.get("config", {}).get(k) or None for k in ("country", "province", "city")}, "customer_location": "unknown", "delivery_location": "unknown", "supply_location": "unknown"},
        "pipeline_version": "1.1.0", "automation_mode": "human_approved", "agents": [dict(a, status="completed" if a["stage"] in ("evidence", "screening", "deep_analysis", "validation", "quality") else "ready") for a in AGENTS],
        "evidence": evidence, "evidence_categories": {k: [e["id"] for e in v] for k, v in categories.items()},
        "scores": {"market_attractiveness": market, "execution_feasibility": fit}, "economics": economics, "gates": gates, "risks": risks,
        "decision": {"label": decision, "human_approval_required": True, "auto_action_allowed": False},
        "sections": sections, "validation_plan": _plan(gates, economics, profile),
        "quality": {"all_claims_have_source": all(s["status"] in ("unknown", "draft", "calculated_scenario", "invalid_inputs", "assessed_low_confidence", "open") or bool(s.get("evidence_ids")) for s in sections), "unknowns_preserved": True, "market_score_is_probability": False, "profitability_verified": False},
    }

def agent_snapshot(active=False, current_stage=None):
    return [{**a, "status": "active" if active and a["stage"] == current_stage else "ready", "external_action": False} for a in AGENTS]
