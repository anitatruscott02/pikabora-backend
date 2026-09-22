import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .models import RecommendRequest, RecommendResponse, FeedbackRequest, UserStateResponse, FoodSearchResult
from .engine import recommend
from .db import SessionLocal, init_db, UserState, RecommendationAudit, Feedback
from .search import search_foods

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app=FastAPI(title="Pikabora Nutrition Intelligence API",version="0.6.0",description="Pregnancy-first nutrition intelligence backend with persistence, auditability and country food search.", lifespan=lifespan)

def db_session():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def admin_guard(x_admin_key:str|None=Header(default=None)):
    expected=os.getenv("PIKABORA_ADMIN_KEY")
    if expected and x_admin_key!=expected: raise HTTPException(401,"Invalid admin key")
    return True

@app.get("/health")
def health(): return {"status":"ok","service":"pikabora-backend","version":"0.6.0"}

@app.get("/foods/search",response_model=list[FoodSearchResult])
def foods_search(country:str=Query(pattern="^(KE|NG|SN)$"),q:str=Query(min_length=1),limit:int=Query(10,ge=1,le=25)):
    return search_foods(country,q,limit)

ACTIVE_LIFE_STAGES = {"pregnancy"}  # LS-CF-001/002/003: complementary feeding is
                                     # architecture-reserved, not active in V1.

@app.post("/nutrition/recommend",response_model=RecommendResponse)
def nutrition_recommend(payload:RecommendRequest, db:Session=Depends(db_session)):
    if payload.life_stage not in ACTIVE_LIFE_STAGES:
        raise HTTPException(400, f'life_stage "{payload.life_stage}" is architecture-reserved and not active in V1 '
                                  f'(see Life Stage Rules LS-CF-001/002/003). Only "pregnancy" is live.')
    state=db.get(UserState,payload.user_state_id)
    if not state:
        state=UserState(id=payload.user_state_id,country=payload.country,language=payload.language,pregnancy_week=payload.pregnancy_week)
        db.add(state)
    state.country=payload.country; state.language=payload.language; state.pregnancy_week=payload.pregnancy_week
    state.recent_food_groups=payload.recent_food_groups; state.dietary_restrictions=payload.dietary_restrictions
    state.allergies=payload.allergies; state.supplement_status=payload.supplement_status
    response=recommend(payload)
    db.add(RecommendationAudit(user_state_id=payload.user_state_id,request_json=payload.model_dump(mode="json"),response_json=response.model_dump(mode="json"),mode=response.mode,data_confidence=response.data_confidence))
    db.commit()
    return response

@app.post("/nutrition/feedback")
def nutrition_feedback(payload:FeedbackRequest, db:Session=Depends(db_session)):
    db.add(Feedback(**payload.model_dump())); db.commit()
    return {"accepted":True,"learning_signal":{"prepared":payload.prepared,"barrier_reason":payload.barrier_reason}}

@app.get("/users/{user_state_id}/state",response_model=UserStateResponse)
def get_state(user_state_id:str, db:Session=Depends(db_session)):
    s=db.get(UserState,user_state_id)
    if not s: raise HTTPException(404,"User state not found")
    return UserStateResponse(user_state_id=s.id,country=s.country,language=s.language,pregnancy_week=s.pregnancy_week,recent_food_groups=s.recent_food_groups or [],dietary_restrictions=s.dietary_restrictions or [],allergies=s.allergies or [],supplement_status=s.supplement_status)

@app.get("/admin/metrics")
def metrics(_:bool=Depends(admin_guard), db:Session=Depends(db_session)):
    return {
      "users":db.scalar(select(func.count()).select_from(UserState)) or 0,
      "recommendation_requests":db.scalar(select(func.count()).select_from(RecommendationAudit)) or 0,
      "feedback_events":db.scalar(select(func.count()).select_from(Feedback)) or 0,
      "prepared_yes":db.scalar(select(func.count()).select_from(Feedback).where(Feedback.prepared==True)) or 0,
    }
