from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator

Allergen = Literal['nuts','peanuts','dairy','eggs','soy','gluten','sesame','shellfish','fish']
Diet = Literal['omnivore','vegetarian','vegan']
Goal = Literal['weight_management','balanced','fitness']

class Register(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    email: EmailStr
    password: str = Field(min_length=8,max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

class Profile(BaseModel):
    age: int = Field(ge=18,le=100)
    sex: Literal['male','female']
    height: float = Field(ge=100,le=250)
    weight: float = Field(ge=30,le=350)
    activity_level: Literal['sedentary','light','moderate','active','very_active']
    dietary_preference: Diet
    goal: Goal
    allergies: list[Allergen] = Field(default_factory=list,max_length=9)
    cuisines: list[str] = Field(default_factory=list,max_length=10)

    @field_validator('cuisines')
    @classmethod
    def check_cuisine(cls, v):
        if any(len(x)>30 or not x.strip() for x in v): raise ValueError('Invalid cuisine')
        return v

class Meal(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    calories: float = Field(gt=0,le=2000)
    protein: float = Field(ge=0,le=200)
    carbs: float = Field(ge=0,le=300)
    fat: float = Field(ge=0,le=150)
    ingredients: list[str] = Field(min_length=1,max_length=20)
    diet: Diet
    allergens: list[Allergen] = Field(default_factory=list)

class PlanData(BaseModel):
    breakfast: Meal
    lunch: Meal
    snack: Meal
    dinner: Meal
    nutrition_summary: dict
    targets: dict
    hydration: str
    source: str
    disclaimer: str
    fallback_reason: str | None = None

class IntakeCreate(BaseModel):
    food: str = Field(min_length=1,max_length=150)
    calories: float = Field(ge=0,le=5000)
    protein: float = Field(default=0,ge=0,le=1000)
    carbs: float = Field(default=0,ge=0,le=1000)
    fat: float = Field(default=0,ge=0,le=1000)
