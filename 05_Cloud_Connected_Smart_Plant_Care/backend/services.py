import time
import uuid
from sqlalchemy import select
from backend.models import Device, Reading, Alert, Watering
from automation.watering_engine import blocked, OFFLINE_AFTER

def uid():
    return str(uuid.uuid4())

def latest(db, device_id):
    return db.scalar(select(Reading).where(Reading.device_id == device_id).order_by(Reading.timestamp.desc()).limit(1))

def as_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in ('key_hash', 'password_hash')}

def alert(db, device, kind, active, message, level='warning'):
    existing = db.scalars(select(Alert).where(Alert.device_id == device.device_id, Alert.alert_type == kind, Alert.status != 'resolved')).all()
    if active and not existing:
        db.add(Alert(alert_id=uid(), device_id=device.device_id, alert_type=kind, level=level, message=message, created_at=time.time()))
    if not active:
        for item in existing:
            item.status, item.resolved_at = 'resolved', time.time()

def stop(db, device, now, reason, reading=None):
    device.pump_until = 0
    for event in db.scalars(select(Watering).where(Watering.device_id == device.device_id, Watering.stopped_at.is_(None))).all():
        event.stopped_at, event.stop_reason = now, reason
        if reading:
            event.moisture_after = reading.soil_moisture

def maintain(db, device, now):
    offline = now - (device.last_seen or device.created_at) > OFFLINE_AFTER
    alert(db, device, 'offline', offline, f'{device.plant_name}: no recent sensor heartbeat', 'critical')
    if device.pump_until and (now >= device.pump_until or offline):
        stop(db, device, now, 'offline' if offline else 'duration_limit')

def start(db, device, reading, now, trigger, duration=10):
    reason = blocked(device, reading, now)
    if reason:
        return reason
    device.pump_until, device.last_watered = now + duration, now
    db.add(Watering(event_id=uid(), device_id=device.device_id, trigger_type=trigger, moisture_before=reading.soil_moisture, duration=duration, timestamp=now))
    return None

def process(db, device, reading, now):
    alert(db, device, 'offline', False, '')
    alert(db, device, 'low_moisture', reading.soil_moisture < device.moisture_threshold, f'{device.plant_name}: soil below {device.moisture_threshold:g}%')
    alert(db, device, 'high_temperature', reading.temperature > 35, f'{device.plant_name}: temperature above 35 C')
    alert(db, device, 'low_tank', reading.water_tank_level <= 15, f'{device.plant_name}: refill water tank', 'critical')
    if device.pump_until and (reading.soil_moisture >= min(device.moisture_threshold + 15, 95) or reading.water_tank_level <= 15):
        stop(db, device, now, 'target_reached' if reading.water_tank_level > 15 else 'low_tank', reading)
    if device.auto_water and reading.soil_moisture < device.moisture_threshold:
        start(db, device, reading, now, 'automatic')

def serialize_device(db, device):
    now = time.time()
    reading = latest(db, device.device_id)
    result = as_dict(device)
    result.update(latest=as_dict(reading) if reading else None, online=bool(device.last_seen and now-device.last_seen <= OFFLINE_AFTER), pump_on=device.pump_until > now)
    return result
