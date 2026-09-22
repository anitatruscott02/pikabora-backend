import os
os.environ["DATABASE_URL"]="sqlite:///./test_pikabora.db"
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
client.__enter__()

def test_health(): assert client.get("/health").json()["version"]=="0.6.0"

def test_kenya_recommendation_and_state():
    p={"user_state_id":"demo","country":"KE","pregnancy_week":24,"foods_available":["maize ugali","egg","sukuma wiki","avocado"],"recent_food_groups":["FG01"]}
    r=client.post("/nutrition/recommend",json=p); assert r.status_code==200
    j=r.json(); assert len(j["recommendations"])>=1; assert j["recommendations"][0]["meal_id"].startswith("KE-")
    s=client.get("/users/demo/state"); assert s.status_code==200; assert s.json()["pregnancy_week"]==24

def test_safety_override():
    p={"user_state_id":"safe","country":"KE","pregnancy_week":24,"foods_available":["rice","beans"],"clinical_flags":["persistent vomiting"]}
    j=client.post("/nutrition/recommend",json=p).json(); assert j["data_confidence"]=="SAFETY_OVERRIDE"; assert j["recommendations"]==[]

def test_safety_terms_match_the_bot_side_list():
    # Found via the WhatsApp bot's integration script: the bot's local
    # danger-sign list (WHO-aligned: bleeding, swelling, etc.) had drifted
    # ahead of this one, so "I have severe swelling" tripped the bot's
    # immediate reply but was invisible to the backend's own audit log.
    for term in ["bleeding", "swelling", "severe headache", "blurred vision", "baby not moving"]:
        p={"user_state_id":f"safe-{term}","country":"KE","pregnancy_week":24,"foods_available":[],"clinical_flags":[f"I have {term}"]}
        j=client.post("/nutrition/recommend",json=p).json()
        assert j["data_confidence"]=="SAFETY_OVERRIDE", f"'{term}' did not trigger escalation"

def test_allergy_filter():
    p={"user_state_id":"allergy","country":"SN","pregnancy_week":20,"foods_available":["millet","milk","groundnuts"],"allergies":["groundnuts"]}
    j=client.post("/nutrition/recommend",json=p).json(); assert all("groundnut" not in x["meal_name"].lower() for x in j["recommendations"])

def test_feedback_and_metrics():
    r=client.post("/nutrition/feedback",json={"user_state_id":"demo","recommendation_id":"abc","prepared":True}); assert r.status_code==200
    m=client.get("/admin/metrics"); assert m.status_code==200; assert m.json()["feedback_events"]>=1

def test_food_search():
    r=client.get("/foods/search",params={"country":"NG","q":"Ogi"}); assert r.status_code==200
    assert isinstance(r.json(),list)

def test_life_stage_lock():
    p={"user_state_id":"cf","country":"KE","life_stage":"6-8 months","pregnancy_week":1,"foods_available":["sweet potato"]}
    r=client.post("/nutrition/recommend",json=p)
    assert r.status_code==400
    assert "LS-CF-001" in r.json()["detail"]

def test_full_kenya_dataset_loaded():
    from app.data import FOODS
    ke=[f for f in FOODS if f["country_code"]=="KE"]
    assert len(ke)>500  # was 9 before the merge; should be 572 now

def test_full_nigeria_dataset_loaded():
    from app.data import FOODS
    ng=[f for f in FOODS if f["country_code"]=="NG"]
    assert len(ng)>250  # was 10 before; should be 280 now

def test_full_senegal_dataset_loaded():
    from app.data import FOODS
    sn=[f for f in FOODS if f["country_code"]=="SN"]
    assert len(sn)>900  # was 10 before; should be 1008 now (WAFCT regional, not SN-exclusive)
    # every SN record must say plainly that it's regional, not Senegal-specific data
    assert all(f["source_scope"]=="WAFCT regional" for f in sn)

def test_blocked_language_guard_raises():
    from app.engine import assert_no_blocked_language
    import pytest
    with pytest.raises(ValueError):
        assert_no_blocked_language("This meal is nutritionally complete")

def test_local_name_resolves_via_real_data():
    # "iyan" (Yoruba for pounded yam) isn't in any hand-written synonym list --
    # it only matches because it's the food's actual local_or_french_name in
    # foods.json. This is the fix for the bug the last release had.
    p={"user_state_id":"local1","country":"NG","pregnancy_week":20,
       "foods_available":["iyan"],"recent_food_groups":[]}
    j=client.post("/nutrition/recommend",json=p).json()
    assert len(j["recommendations"])>=1
    assert "Yam" not in j["recommendations"][0]["missing_components"]

def test_zero_match_is_excluded_not_floor_scored():
    # Previously every meal got a 40-point floor score even with zero real
    # matches, so a nonsense request still returned confident-looking
    # recommendations. Now it should return none, with an honest message.
    p={"user_state_id":"nomatch1","country":"SN","pregnancy_week":20,
       "foods_available":["xyzxyz123"],"recent_food_groups":[]}
    j=client.post("/nutrition/recommend",json=p).json()
    assert j["recommendations"]==[]
    assert "matched" in j["message"].lower()

