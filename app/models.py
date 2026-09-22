from pydantic import BaseModel, Field
from typing import Literal
Country = Literal["KE","NG","SN"]

class Portion(BaseModel):
    food: str
    grams: float | None = Field(default=None, gt=0)
    household_measure: str | None = None

class RecommendRequest(BaseModel):
    user_state_id: str = Field(min_length=1,max_length=128)
    country: Country
    language: str = "en"
    life_stage: str = "pregnancy"
    pregnancy_week: int = Field(ge=1, le=45)
    foods_available: list[str] = Field(default_factory=list)
    portions: list[Portion] = Field(default_factory=list)
    budget: float | None = Field(default=None, ge=0)
    currency: str | None = None
    recent_food_groups: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    clinical_flags: list[str] = Field(default_factory=list)
    supplement_status: str | None = None

class FeedbackRequest(BaseModel):
    user_state_id: str
    recommendation_id: str
    prepared: bool
    barrier_reason: str | None = None

class Recommendation(BaseModel):
    recommendation_id: str
    meal_id: str
    meal_name: str
    local_name: str | None = None
    score: float
    strengths: list[str]
    possible_gaps: list[str]
    improvement: str | None = None
    missing_components: list[str] = Field(default_factory=list)

class RecommendResponse(BaseModel):
    mode: Literal["QUALITATIVE","QUANTITATIVE"]
    data_confidence: str
    recommendations: list[Recommendation]
    safety_flags: list[str]
    message: str

class UserStateResponse(BaseModel):
    user_state_id: str
    country: str
    language: str
    pregnancy_week: int
    recent_food_groups: list[str]
    dietary_restrictions: list[str]
    allergies: list[str]
    supplement_status: str | None

class FoodSearchResult(BaseModel):
    food_id: str
    country: str
    name: str
    local_name: str | None = None
    matched_alias: str | None = None
    readiness: str | None = None
