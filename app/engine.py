import re, uuid
from .data import FOODS, MEALS, COUNTRY_NAME
from .models import RecommendRequest, Recommendation, RecommendResponse

# From "Candidate Ranking" sheet's own Blocked_Language column. This is a
# runtime guard, not just a style rule -- a future edit that reintroduces one
# of these should fail loudly, not ship.
BLOCKED_PHRASES = [
    "meets all your pregnancy nutrient requirements",
    "prevents deficiency",
    "nutritionally complete",
    "bad meal", "unhealthy meal",
    "exact % of pregnancy needs",
]

def assert_no_blocked_language(text: str | None) -> str | None:
    if not text: return text
    low = text.lower()
    hit = next((p for p in BLOCKED_PHRASES if p in low), None)
    if hit:
        raise ValueError(f'Generated text contains blocked phrase "{hit}" -- fix the template, do not ship this string: {text!r}')
    return text

CLINICAL_TERMS={"severe anaemia","severe anemia","gestational diabetes","diabetes","hypertension","high blood pressure","kidney disease","kidney problem","persistent vomiting","can't keep food down","severe illness","danger sign","allergic","allergy","bleeding","severe pain","swelling","baby not moving","can't feel the baby move","severe headache","blurred vision"}

def norm(s:str)->str:
    return re.sub(r"[^a-z0-9 ]+"," ",s.lower()).strip()

def tokens(s:str)->set[str]:
    return {x for x in norm(s).split() if len(x)>2}

def clinical_gate(req):
    flags=[]
    for f in req.clinical_flags:
        n=norm(f)
        if any(t in n for t in CLINICAL_TERMS): flags.append(f)
    return flags

# ---------------------------------------------------------------------------
# Data-grounded name resolution. The old approach only matched a fixed,
# hand-written list of English category words -- a real user typing "iyan",
# "ewedu", "eja" (Yoruba for pounded yam, jute-leaf soup, fish) matched
# nothing, even though the exact food exists in our own data with that exact
# local name. This builds the lookup from the real, extracted food database
# instead of guessing synonyms by hand.
# ---------------------------------------------------------------------------
_FOOD_INDEX: dict[str, list[tuple[set[str], str]]] = {}
def _build_food_index():
    for f in FOODS:
        cc = f.get("country_code")
        names = [f.get("source_food_name"), f.get("local_or_french_name")]
        for n in names:
            if not n: continue
            t = tokens(n)
            if t:
                _FOOD_INDEX.setdefault(cc, []).append((t, f.get("food_group") or ""))
_build_food_index()

def resolve_food_group(term:str, country:str) -> set[str]:
    """Look up a user-typed food term against the real database (English or
    local/French name) for this country and return the matched food_group(s)."""
    tt = tokens(term)
    if not tt: return set()
    groups = set()
    for name_tokens, group in _FOOD_INDEX.get(country, []):
        if tt & name_tokens:
            groups.add(group)
    return groups

_GROUP_KEYWORDS = {
    "Cereals": {"maize","ugali","rice","millet","sorghum","wheat","ogi","pilau","jollof","couscous","porridge"},
    "Roots & tubers": {"yam","cassava","eba","potato","plantain","fufu"},
    "Legumes": {"bean","beans","cowpea","cowpeas","gram","grams","lentil","moimoi","moi","groundnut"},
    "Vegetables": {"leafy","vegetable","vegetables","sukuma","kale","amaranth","moringa","greens","ewedu","okra"},
    "Fruits": {"avocado","fruit","banana","papaya","mango","orange","guava","baobab"},
    "Fish": {"fish"},
    "Eggs": {"egg","eggs"},
    "Milk And Dairy Products": {"milk","yoghurt","yogurt"},
    "Nuts And Seeds": {"groundnut","groundnuts","nut","nuts","seed","seeds"},
}
def component_expected_groups(component_text:str) -> set[str]:
    ct = tokens(component_text)
    return {g for g, kws in _GROUP_KEYWORDS.items() if ct & kws}

def component_match(component:str, available:list[str], country:str)->bool:
    ct=tokens(component)
    if not ct: return False
    expected_groups = component_expected_groups(component)
    for food in available:
        ft=tokens(food)
        if ct & ft: return True
        # broad, hand-written category matching (kept as a fast-path; the
        # data-grounded lookup below is the real fix for anything this misses)
        pairs=[({"bean","beans","cowpea","cowpeas","gram","grams"},{"bean","beans","cowpea","cowpeas","gram","grams"}),
               ({"leafy","vegetable","vegetables","sukuma","kale","amaranth","moringa"},{"leafy","vegetable","vegetables","sukuma","kale","amaranth","moringa"}),
               ({"fruit","avocado","banana","papaya","mango","orange","guava"},{"fruit","avocado","banana","papaya","mango","orange","guava"}),
               ({"egg","eggs"},{"egg","eggs"}),({"fish","sardine","tilapia","omena"},{"fish","sardine","tilapia","omena"}),
               ({"rice"},{"rice"}),({"yam"},{"yam"}),({"ugali","maize"},{"ugali","maize"}),({"millet"},{"millet"}),({"milk","yoghurt","yogurt"},{"milk","yoghurt","yogurt"})]
        if any(ct&a and ft&b for a,b in pairs): return True
        # data-grounded: does this available term resolve to a real food whose
        # food_group matches what this component expects?
        if expected_groups and resolve_food_group(food, country) & expected_groups:
            return True
    return False

def quantitative_allowed(req):
    if not req.portions: return False
    if any(p.grams is None for p in req.portions): return False
    # v0.7 contract: only expose quantitative mode when mapped source data are verified.
    for p in req.portions:
        q=norm(p.food); candidates=[f for f in FOODS if f.get("country_code")==req.country and q in norm(f.get("source_food_name") or "")]
        if not candidates or not all((f.get("value_status") or "").startswith("PUBLISHED") for f in candidates): return False
    return True

def recommend(req:RecommendRequest)->RecommendResponse:
    danger=clinical_gate(req)
    if danger:
        return RecommendResponse(mode="QUALITATIVE",data_confidence="SAFETY_OVERRIDE",recommendations=[],safety_flags=danger,message="A clinical or safety flag was reported. Pikabora should not optimise this as an ordinary meal; please use the appropriate antenatal or clinical care pathway.")
    country=COUNTRY_NAME[req.country]
    candidates=[m for m in MEALS if m.get("Country")==country and str(m.get("Engine_Ready","")).startswith("YES")]
    recs=[]
    available=req.foods_available
    allergy_tokens=set().union(*(tokens(a) for a in req.allergies)) if req.allergies else set()
    restriction_tokens=set().union(*(tokens(a) for a in req.dietary_restrictions)) if req.dietary_restrictions else set()
    for m in candidates:
        comps=[m.get("Primary_Staple") or "",m.get("Protein_Component") or "",m.get("Vegetable_Fruit_Component") or ""]
        alltext=" ".join(comps+[m.get("Optional_Addition") or "",m.get("Meal_Name") or ""])
        mt=tokens(alltext)
        if allergy_tokens & mt or restriction_tokens & mt: continue
        matched=sum(component_match(c,available,req.country) for c in comps if c)
        total=sum(bool(c) for c in comps) or 1
        # Hard gate (Quantitative Scoring sheet, "Availability fit"): a meal
        # with NONE of its components matched is not a candidate, not just a
        # low-scoring one. The old code gave every meal a 40-point floor
        # regardless, so an unmatched request still returned confident-looking
        # recommendations with everything marked "missing" -- exactly the
        # false-precision failure this project's own rules exist to prevent.
        if matched==0:
            continue
        availability=matched/total
        score=40+availability*45
        # small diversity bonus when meal includes categories not already reported; never diagnostic
        if req.recent_food_groups and ("leaf" in norm(alltext) or "vegetable" in norm(alltext) or "fruit" in norm(alltext)): score+=5
        if m.get("Budget_Band") in ("Low","Low–Medium","Low-Medium"): score+=5
        missing=[c for c in comps if c and not component_match(c,available,req.country)]
        strengths_text=[assert_no_blocked_language(m.get("Maternal_Nutrition_Strength") or "Culturally familiar meal pattern")]
        gaps_text=[assert_no_blocked_language(m.get("Likely_Gap"))] if m.get("Likely_Gap") else []
        improvement_text=assert_no_blocked_language(m.get("Improvement_Action"))
        recs.append(Recommendation(recommendation_id=str(uuid.uuid4()),meal_id=m["Meal_ID"],meal_name=m["Meal_Name"],local_name=m.get("Local_Name"),score=round(min(score,100),1),strengths=strengths_text,possible_gaps=gaps_text,improvement=improvement_text,missing_components=missing))
    recs=sorted(recs,key=lambda x:x.score,reverse=True)[:3]
    mode="QUANTITATIVE" if quantitative_allowed(req) else "QUALITATIVE"
    confidence="VERIFIED_INPUTS" if mode=="QUANTITATIVE" else "PORTION_OR_SOURCE_GATED"
    if candidates and not recs:
        msg="None of the foods you listed matched a known meal pattern for this country yet. Try naming individual foods (e.g. \"rice, beans, fish\") rather than a dish name, or check the spelling."
    else:
        msg="Recommendations are ranked from the foods you reported, country meal patterns, recent diet context and safety rules."
        if mode=="QUALITATIVE": msg+=" Exact nutrient adequacy percentages are withheld because one or more portion/source inputs are not fully validated."
    return RecommendResponse(mode=mode,data_confidence=confidence,recommendations=recs,safety_flags=[],message=msg)

