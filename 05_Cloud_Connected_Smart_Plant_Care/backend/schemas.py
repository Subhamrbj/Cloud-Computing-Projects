from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Login(Strict):
    email: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=10, max_length=128)

class NewDevice(Strict):
    plant_name: str = Field(min_length=1, max_length=60)
    plant_type: Literal['succulent', 'tomato', 'herb', 'indoor'] = 'indoor'
    location: str = Field(min_length=1, max_length=80)

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
