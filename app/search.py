import re
from .data import FOODS, ALIASES

def norm(s): return re.sub(r"[^a-z0-9 ]+"," ",(s or "").lower()).strip()

def search_foods(country:str, query:str, limit:int=10):
    q=norm(query); results=[]; alias_by_food={}
    for a in ALIASES:
        if a.get("country_code")==country and q and (q in norm(a.get("alias")) or norm(a.get("alias")) in q):
            alias_by_food[a.get("pikabora_food_id")]=a.get("alias")
    for f in FOODS:
        if f.get("country_code")!=country: continue
        name=norm(f.get("source_food_name")); local=norm(f.get("local_or_french_name"))
        alias=alias_by_food.get(f.get("pikabora_food_id"))
        if q in name or q in local or alias:
            score=(3 if q==name else 2 if q in name else 1)
            results.append((score,{"food_id":f.get("pikabora_food_id"),"country":country,"name":f.get("source_food_name"),"local_name":f.get("local_or_french_name"),"matched_alias":alias,"readiness":f.get("recommendation_readiness")}))
    return [x[1] for x in sorted(results,key=lambda x:(-x[0],x[1]["name"]))[:limit]]
