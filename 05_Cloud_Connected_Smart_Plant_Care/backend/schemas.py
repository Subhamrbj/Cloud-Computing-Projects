from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal
import re

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Login(Strict):
    email: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=10, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value

class Register(Login):
    name: str = Field(min_length=2, max_length=60)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Enter at least two characters')
        return value

class Recovery(Login):
    recovery_code: str = Field(min_length=20, max_length=128)

class DeleteAccount(Strict):
    password: str = Field(min_length=10, max_length=128)

class NewDevice(Strict):
    plant_name: str = Field(min_length=1, max_length=60)
    plant_type: Literal['succulent', 'tomato', 'herb', 'indoor'] = 'indoor'
    location: str = Field(min_length=1, max_length=80)
    mode: Literal['virtual', 'external'] = 'virtual'

class SimulationControl(Strict):
    action: Literal['start', 'pause', 'dry', 'refill']

class Settings(Strict):
    moisture_threshold: float = Field(ge=5, le=80)
    auto_water: bool

class Sensor(Strict):
    device_id: str = Field(max_length=60)
    sample_id: str = Field(min_length=1, max_length=64)
    soil_moisture: float = Field(ge=0, le=100)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    light_level: float = Field(ge=0, le=100)
    water_tank_level: float = Field(ge=0, le=100)
    timestamp: datetime

    @field_validator('timestamp')
    @classmethod
    def timestamp_window(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timestamp must include timezone')
        if abs((datetime.now(timezone.utc) - value).total_seconds()) > 300:
            raise ValueError('Reading must be within five minutes of server time')
        return value

class WaterRequest(Strict):
    duration: int = Field(default=10, ge=1, le=15)
