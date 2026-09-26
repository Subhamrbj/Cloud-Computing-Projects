from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Integer, UniqueConstraint, Index
from cloud.database_service import Base

class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(Float, nullable=False)

class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), index=True, nullable=False)
    plant_name = Column(String, nullable=False)
    plant_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    moisture_threshold = Column(Float, nullable=False)
    auto_water = Column(Boolean, default=True)
    key_hash = Column(String, nullable=False)
    created_at = Column(Float, nullable=False)
    last_seen = Column(Float, default=0)
    last_watered = Column(Float, default=0)
    pump_until = Column(Float, default=0)

class Reading(Base):
    __tablename__ = 'sensor_readings'
    reading_id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'), nullable=False)
    sample_id = Column(String, nullable=False)
    soil_moisture = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    light_level = Column(Float, nullable=False)
    water_tank_level = Column(Float, nullable=False)
    timestamp = Column(Float, nullable=False)
    received_at = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint('device_id', 'sample_id'), Index('ix_readings_device_time', 'device_id', 'timestamp'))

class Watering(Base):
    __tablename__ = 'watering_events'
    event_id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'), index=True, nullable=False)
    trigger_type = Column(String, nullable=False)
    moisture_before = Column(Float, nullable=False)
    moisture_after = Column(Float)
    duration = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)
    stopped_at = Column(Float)
    stop_reason = Column(String)

class Alert(Base):
    __tablename__ = 'alerts'
    alert_id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'), index=True, nullable=False)
    alert_type = Column(String, nullable=False)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default='open')
    created_at = Column(Float, nullable=False)
    resolved_at = Column(Float)
