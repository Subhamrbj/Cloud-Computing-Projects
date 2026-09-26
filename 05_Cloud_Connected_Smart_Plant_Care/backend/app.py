"""Verdant REST API. Single-process demo; PostgreSQL row locks protect device changes."""
import asyncio
import logging
import secrets
import time
import threading
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from cloud.database_service import Base, engine, Session
from cloud.auth_service import current_user, token, verify_password, digest, secret
from backend.models import User, Device, Reading, Watering, Alert
from backend.schemas import Login, NewDevice, Settings, Sensor, WaterRequest
from backend.services import uid, as_dict, latest, maintain, process, start, stop, serialize_device
from automation.plant_profiles import PROFILES

log = logging.getLogger('verdant')
write_lock = threading.RLock()

async def watchdog():
    while True:
        await asyncio.sleep(5)
        try:
            await asyncio.to_thread(sweep)
        except SQLAlchemyError:
            log.error('Heartbeat sweep failed; database unavailable')

def sweep():
    with write_lock, Session.begin() as db:
        for device in db.scalars(select(Device).with_for_update()).all():
            maintain(db, device, time.time())

@asynccontextmanager
async def lifespan(app):
    secret()
    Base.metadata.create_all(engine)
    task = asyncio.create_task(watchdog())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title='Verdant Plant Cloud', version='1.0.0', lifespan=lifespan)
attempts = defaultdict(deque)

@app.middleware('http')
async def guard(request: Request, call_next):
    # Per-process demo limiter. Add a gateway/distributed limiter before scaling out.
    if request.method == 'POST' and request.url.path in ('/api/auth/login', '/api/sensors/data'):
        key = (request.client.host, request.url.path)
        now = time.monotonic()
        queue = attempts[key]
        while queue and queue[0] < now - 60:
            queue.popleft()
        limit = 20 if request.url.path.endswith('login') else 600
        if len(queue) >= limit:
            return JSONResponse({'detail': 'Too many requests'}, status_code=429, headers={'Retry-After': '60'})
        queue.append(now)
    if int(request.headers.get('content-length', '0') or 0) > 16384:
        return JSONResponse({'detail': 'Request too large'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api') else 'public, max-age=60'
    return response

@app.exception_handler(SQLAlchemyError)
async def db_error(request, exc):
    log.error('Database operation failed: %s', type(exc).__name__)
    return JSONResponse({'detail': 'Storage temporarily unavailable; retry later'}, status_code=503)

def owned(db, device_id, user_id):
    device = db.scalar(select(Device).where(Device.device_id == device_id, Device.user_id == user_id).with_for_update())
    if not device:
        raise HTTPException(404, 'Device not found')
    return device

def device_auth(db, device_id, key):
    device = db.scalar(select(Device).where(Device.device_id == device_id).with_for_update())
    if not device or not secrets.compare_digest(device.key_hash, digest(key)):
        raise HTTPException(401, 'Invalid device credentials')
    return device

def command(device):
    return {'pump_on': device.pump_until > time.time(), 'pump_until': device.pump_until, 'target_moisture': min(device.moisture_threshold+15, 95), 'server_time': time.time()}

@app.get('/api/health')
def health():
    with Session() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ok', 'version': '1.0.0'}

@app.post('/api/auth/login')
def login(body: Login):
    with Session() as db:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(401, 'Invalid email or password')
        return {'access_token': token(user.user_id), 'token_type': 'bearer', 'name': user.name, 'expires_in': 3600}

@app.get('/api/devices')
def devices(user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        result = []
        for device in db.scalars(select(Device).where(Device.user_id == user).order_by(Device.created_at).with_for_update()).all():
            maintain(db, device, time.time())
            result.append(serialize_device(db, device))
        return result

@app.post('/api/devices', status_code=201)
def create_device(body: NewDevice, user=Depends(current_user)):
    key = secrets.token_urlsafe(32)
    with Session.begin() as db:
        if not db.get(User, user):
            raise HTTPException(401, 'User no longer exists')
        device = Device(device_id='PLANT-'+secrets.token_hex(4).upper(), user_id=user, key_hash=digest(key), moisture_threshold=PROFILES[body.plant_type], created_at=time.time(), **body.model_dump())
        db.add(device)
        db.flush()
        return {**as_dict(device), 'device_key': key}

@app.get('/api/devices/{device_id}')
def get_device(device_id: str, user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        device = owned(db, device_id, user)
        maintain(db, device, time.time())
        return serialize_device(db, device)

@app.get('/api/devices/{device_id}/latest')
def get_latest(device_id: str, user=Depends(current_user)):
    with Session() as db:
        owned(db, device_id, user)
        row = latest(db, device_id)
        if not row:
            raise HTTPException(404, 'No sensor data yet')
        return as_dict(row)

@app.get('/api/devices/{device_id}/history')
def history(device_id: str, limit: int=Query(100, ge=1, le=1000), before: float | None=None, user=Depends(current_user)):
    with Session() as db:
        owned(db, device_id, user)
        query = select(Reading).where(Reading.device_id == device_id)
        if before is not None:
            query = query.where(Reading.timestamp < before)
        rows = db.scalars(query.order_by(Reading.timestamp.desc()).limit(limit)).all()
        return [as_dict(row) for row in reversed(rows)]

@app.put('/api/devices/{device_id}/threshold')
def update(device_id: str, body: Settings, user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        device = owned(db, device_id, user)
        device.moisture_threshold, device.auto_water = body.moisture_threshold, body.auto_water
        if not body.auto_water:
            stop(db, device, time.time(), 'automation_disabled')
        return as_dict(device)

@app.post('/api/devices/{device_id}/water')
def water(device_id: str, body: WaterRequest, user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        device = owned(db, device_id, user)
        maintain(db, device, time.time())
        reason = start(db, device, latest(db, device_id), time.time(), 'manual', body.duration)
        if reason:
            raise HTTPException(409, reason)
        return command(device)

@app.post('/api/devices/{device_id}/stop')
def stop_pump(device_id: str, user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        device = owned(db, device_id, user)
        stop(db, device, time.time(), 'user_stop')
        return command(device)

@app.get('/api/devices/{device_id}/command')
def get_command(device_id: str, x_device_key: str=Header(default='')):
    with write_lock, Session.begin() as db:
        device = device_auth(db, device_id, x_device_key)
        maintain(db, device, time.time())
        return command(device)

@app.post('/api/sensors/data')
def ingest(body: Sensor, x_device_key: str=Header(default='')):
    with write_lock, Session.begin() as db:
        device = device_auth(db, body.device_id, x_device_key)
        existing = db.scalar(select(Reading).where(Reading.device_id == body.device_id, Reading.sample_id == body.sample_id))
        now = time.time()
        maintain(db, device, now)
        if existing:
            return {'duplicate': True, **command(device)}
        previous = latest(db, body.device_id)
        timestamp = body.timestamp.timestamp()
        if previous and timestamp <= previous.timestamp:
            raise HTTPException(409, 'Out-of-order reading; send a fresh sample')
        values = body.model_dump(exclude={'timestamp'})
        reading = Reading(reading_id=uid(), received_at=now, timestamp=timestamp, **values)
        db.add(reading)
        device.last_seen = now
        process(db, device, reading, now)
        return {'duplicate': False, **command(device)}

@app.get('/api/devices/{device_id}/watering-history')
def watering_history(device_id: str, user=Depends(current_user)):
    with Session() as db:
        owned(db, device_id, user)
        return [as_dict(row) for row in db.scalars(select(Watering).where(Watering.device_id == device_id).order_by(Watering.timestamp.desc()).limit(100)).all()]

@app.get('/api/alerts')
def alerts(user=Depends(current_user)):
    with Session() as db:
        rows = db.scalars(select(Alert).join(Device).where(Device.user_id == user).order_by(Alert.created_at.desc()).limit(100)).all()
        return [as_dict(row) for row in rows]

@app.put('/api/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id: str, user=Depends(current_user)):
    with Session.begin() as db:
        row = db.scalar(select(Alert).join(Device).where(Alert.alert_id == alert_id, Device.user_id == user))
        if not row:
            raise HTTPException(404, 'Alert not found')
        if row.status == 'open':
            row.status = 'acknowledged'
        return as_dict(row)

dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='dashboard')
