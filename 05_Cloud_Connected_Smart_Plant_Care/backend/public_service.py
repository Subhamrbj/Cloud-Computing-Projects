"""Public-account provisioning and server-driven virtual telemetry."""
import math
import secrets
import time
from sqlalchemy import select, delete
from backend.models import Device, Reading, Watering, Alert, VirtualDevice, RateLimit, GuestAccount, AccountSecurity, User
from backend.services import uid, latest, process, maintain
from cloud.auth_service import digest

def provision_garden(db, user_id, now=None):
    now = now or time.time()
    for index, (name, kind, threshold, location) in enumerate([
        ('Monstera Deliciosa', 'indoor', 30, 'Living room'),
        ('Sweet Basil', 'herb', 35, 'Kitchen window'),
        ('Golden Barrel', 'succulent', 20, 'Balcony'),
    ]):
        device = Device(device_id='PLANT-'+secrets.token_hex(6).upper(), user_id=user_id,
                        plant_name=name, plant_type=kind, location=location,
                        moisture_threshold=threshold, key_hash=digest(secrets.token_urlsafe(32)),
                        created_at=now, last_seen=now)
        db.add(device)
        db.flush()
        db.add(VirtualDevice(device_id=device.device_id, running=True, last_tick=now, active_until=now+300))
        for n in range(25):
            stamp = now - (24-n)*60
            db.add(Reading(reading_id=uid(), device_id=device.device_id, sample_id=f'welcome-{n}',
                           soil_moisture=55-index*5-n*.2, temperature=26+math.sin(n/8),
                           humidity=62+3*math.cos(n/8), light_level=68+2*math.sin(n/6),
                           water_tank_level=85, timestamp=stamp, received_at=stamp))

def tick_virtual(db, device, now):
    virtual = db.get(VirtualDevice, device.device_id)
    if not virtual or not virtual.running or virtual.active_until < now:
        return
    previous = latest(db, device.device_id)
    if not previous:
        return
    elapsed = now - virtual.last_tick
    if elapsed < 2:
        return
    # Do not simulate unattended elapsed hours after a sleeping hosting process.
    elapsed = min(elapsed, 5)
    start_time = now - elapsed
    pumping = max(0, min(now, device.pump_until) - max(start_time, device.last_watered)) if device.pump_until else 0
    moisture = min(100, max(0, previous.soil_moisture + pumping*2.8 - (elapsed-pumping)*.25))
    tank = max(0, previous.water_tank_level-pumping*.25)
    reading = Reading(reading_id=uid(), device_id=device.device_id, sample_id=uid(),
                      soil_moisture=round(moisture, 2), temperature=round(26+2*math.sin(now/240), 2),
                      humidity=round(62+5*math.cos(now/300), 2), light_level=round(68+10*math.sin(now/400), 2),
                      water_tank_level=round(tank, 2), timestamp=now, received_at=now)
    db.add(reading)
    virtual.last_tick = now
    device.last_seen = now
    # Apply the final bounded pulse before reconciling command expiry.
    maintain(db, device, now)
    process(db, device, reading, now)

def prune(db, now):
    """Bound portfolio hosting storage; keep one newest sample per device."""
    for device in db.scalars(select(Device)).all():
        newest = latest(db, device.device_id)
        if newest:
            db.execute(delete(Reading).where(Reading.device_id == device.device_id,
                       Reading.timestamp < now-7*86400, Reading.reading_id != newest.reading_id))
    db.execute(delete(Watering).where(Watering.timestamp < now-90*86400, Watering.stopped_at.is_not(None)))
    db.execute(delete(Alert).where(Alert.status == 'resolved', Alert.created_at < now-90*86400))
    db.execute(delete(RateLimit).where(RateLimit.expires_at < now-60))
    for guest in db.scalars(select(GuestAccount).where(GuestAccount.expires_at < now)).all():
        remove_account(db, guest.user_id)

def remove_account(db, user_id):
    ids = select(Device.device_id).where(Device.user_id == user_id)
    for model in (Reading, Watering, Alert, VirtualDevice):
        db.execute(delete(model).where(model.device_id.in_(ids)))
    db.execute(delete(Device).where(Device.user_id == user_id))
    db.execute(delete(AccountSecurity).where(AccountSecurity.user_id == user_id))
    db.execute(delete(GuestAccount).where(GuestAccount.user_id == user_id))
    db.execute(delete(User).where(User.user_id == user_id))
