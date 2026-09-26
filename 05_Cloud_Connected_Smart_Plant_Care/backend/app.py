"""Plant Care REST API. Single-process demo; PostgreSQL row locks protect device changes."""
import asyncio
import logging
import secrets
import time
import threading
import os
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from cloud.database_service import Base, engine, Session, initialize_database
from cloud.auth_service import current_user, token, verify_password, digest, secret, hash_password
from backend.models import User, Device, Reading, Watering, Alert, VirtualDevice, AccountSecurity, GuestAccount, RateLimit
from backend.schemas import Login, Register, Recovery, DeleteAccount, NewDevice, Settings, Sensor, WaterRequest, SimulationControl
from backend.services import uid, as_dict, latest, maintain, process, start, stop, serialize_device
from automation.plant_profiles import PROFILES
from backend.public_service import provision_garden, tick_virtual, prune, remove_account

log = logging.getLogger('plantcare')
write_lock = threading.RLock()
last_cleanup = 0

async def watchdog():
    while True:
        await asyncio.sleep(5)
        try:
            await asyncio.to_thread(sweep)
        except SQLAlchemyError:
            log.error('Heartbeat sweep failed; database unavailable')

def sweep():
    global last_cleanup
    with write_lock, Session.begin() as db:
        for device in db.scalars(select(Device).with_for_update()).all():
            tick_virtual(db, device, time.time())
            maintain(db, device, time.time())
        if time.time()-last_cleanup > 3600:
            prune(db, time.time())
            last_cleanup = time.time()

@asynccontextmanager
async def lifespan(app):
    secret()
    if os.getenv('APP_ENV') == 'production' and engine.dialect.name == 'sqlite':
        raise RuntimeError('Production requires a persistent PostgreSQL DATABASE_URL')
    initialize_database()
    task = asyncio.create_task(watchdog())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title='Cloud-Connected Smart Plant Care & Watering System', version='2.0.0', lifespan=lifespan)
attempts = defaultdict(deque)

def consume_rate(bucket, limit, period=60):
    now = time.time()
    key = digest(bucket+':'+str(int(now//period)))
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    insert = pg_insert if engine.dialect.name == 'postgresql' else sqlite_insert
    statement = insert(RateLimit).values(bucket=key, count=1, expires_at=now+period)
    statement = statement.on_conflict_do_update(index_elements=['bucket'], set_={'count':RateLimit.count+1}).returning(RateLimit.count)
    with write_lock, Session.begin() as db:
        return db.scalar(statement) <= limit

@app.middleware('http')
async def guard(request: Request, call_next):
    path = request.url.path
    if request.method in ('POST','PUT','DELETE','PATCH') and path.startswith('/api/'):
        origin = request.headers.get('origin')
        expected = os.getenv('PUBLIC_URL', str(request.base_url)).rstrip('/')
        if origin and origin.rstrip('/') != expected:
            return JSONResponse({'detail':'Request origin not allowed'}, status_code=403)
    limits = {'/api/auth/login':20, '/api/auth/register':5, '/api/auth/demo':5, '/api/auth/recover':5, '/api/sensors/data':600}
    if request.method == 'POST' and path in limits:
        try:
            permitted = await asyncio.to_thread(consume_rate, (request.client.host if request.client else 'unknown')+path, limits[path])
            if not permitted:
                return JSONResponse({'detail':'Too many requests. Please wait a minute.'},status_code=429,headers={'Retry-After':'60'})
        except SQLAlchemyError:
            return JSONResponse({'detail':'Storage temporarily unavailable; retry later'},status_code=503)
    try:
        too_large = int(request.headers.get('content-length', '0') or 0) > 16384
    except ValueError:
        return JSONResponse({'detail':'Invalid content length'},status_code=400)
    if too_large:
        return JSONResponse({'detail': 'Request too large'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'" if path != '/docs' else "default-src 'self' https: 'unsafe-inline'"
    if os.getenv('APP_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
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
    return {'status': 'ok', 'version': '2.0.0'}

def login_result(user, response, version=0, **extras):
    value = token(user.user_id, version)
    response.set_cookie('plantcare_session', value, httponly=True, secure=os.getenv('APP_ENV')=='production', samesite='lax', max_age=3600, path='/')
    return {'access_token':value, 'token_type':'bearer', 'name':user.name, 'expires_in':3600, **extras}

@app.post('/api/auth/login')
def login(body: Login, response: Response):
    with Session() as db:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(401, 'Invalid email or password')
        security = db.get(AccountSecurity, user.user_id)
        return login_result(user, response, security.auth_version if security else 0)

@app.post('/api/auth/register', status_code=201)
def register(body: Register, response: Response):
    if os.getenv('ALLOW_REGISTRATION', 'true').lower() != 'true':
        raise HTTPException(403, 'New accounts are currently paused')
    recovery = secrets.token_urlsafe(32)
    with write_lock, Session.begin() as db:
        if db.scalar(select(User).where(User.email == body.email)):
            raise HTTPException(409, 'This email is already registered. Sign in or recover your account.')
        if db.scalar(select(func.count()).select_from(User)) >= int(os.getenv('MAX_PUBLIC_USERS','500')):
            raise HTTPException(503, 'The demo has reached its account capacity. Please try later.')
        user = User(user_id=uid(), name=body.name, email=body.email, password_hash=hash_password(body.password), created_at=time.time())
        db.add(user)
        db.flush()
        db.add(AccountSecurity(user_id=user.user_id, recovery_hash=digest(recovery)))
        provision_garden(db, user.user_id)
        return login_result(user, response, recovery_code=recovery, is_demo=False)

@app.post('/api/auth/demo', status_code=201)
def demo(response: Response):
    with write_lock, Session.begin() as db:
        if db.scalar(select(func.count()).select_from(GuestAccount)) >= 100:
            raise HTTPException(503, 'The live demo is busy. Please try again later.')
        user_id = uid()
        user = User(user_id=user_id, name='Explorer', email=user_id+'@guest.invalid', password_hash=hash_password(secrets.token_urlsafe(40)), created_at=time.time())
        db.add(user)
        db.flush()
        db.add(GuestAccount(user_id=user_id, expires_at=time.time()+3600))
        provision_garden(db, user_id)
        return login_result(user, response, is_demo=True)

@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    with Session() as db:
        row = db.get(User, user)
        return {'name':row.name, 'email':row.email if not db.get(GuestAccount,user) else None, 'is_demo':bool(db.get(GuestAccount,user))}

@app.post('/api/auth/logout')
def logout(response: Response):
    response.delete_cookie('plantcare_session', path='/')
    return {'ok':True}

@app.post('/api/auth/recover')
def recover(body: Recovery, response: Response):
    with write_lock, Session.begin() as db:
        user = db.scalar(select(User).where(User.email == body.email).with_for_update())
        security = db.get(AccountSecurity,user.user_id) if user else None
        if not security or not secrets.compare_digest(security.recovery_hash,digest(body.recovery_code)):
            raise HTTPException(400, 'Email or recovery code is incorrect')
        user.password_hash = hash_password(body.password)
        security.auth_version += 1
        recovery = secrets.token_urlsafe(32)
        security.recovery_hash = digest(recovery)
        return login_result(user,response,security.auth_version,recovery_code=recovery,is_demo=False)

@app.delete('/api/auth/account')
def delete_account(body: DeleteAccount, response: Response, user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        row = db.get(User,user)
        if not verify_password(body.password,row.password_hash):
            raise HTTPException(401,'Incorrect password')
        remove_account(db,user)
    response.delete_cookie('plantcare_session',path='/')
    return {'ok':True}

@app.get('/api/devices')
def devices(user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        result = []
        for device in db.scalars(select(Device).where(Device.user_id == user).order_by(Device.created_at).with_for_update()).all():
            virtual = db.get(VirtualDevice,device.device_id)
            if virtual:
                virtual.active_until = time.time()+300
                tick_virtual(db,device,time.time())
            maintain(db, device, time.time())
            result.append({**serialize_device(db,device),'mode':'virtual' if virtual else 'external','simulation_running':virtual.running if virtual else False})
        return result

@app.post('/api/devices', status_code=201)
def create_device(body: NewDevice, user=Depends(current_user)):
    key = secrets.token_urlsafe(32)
    with write_lock, Session.begin() as db:
        if not db.get(User, user):
            raise HTTPException(401, 'User no longer exists')
        if db.scalar(select(func.count()).select_from(Device).where(Device.user_id==user)) >= 12:
            raise HTTPException(409,'Each garden can have up to 12 plants')
        device = Device(device_id='PLANT-'+secrets.token_hex(6).upper(), user_id=user, key_hash=digest(key), moisture_threshold=PROFILES[body.plant_type], created_at=time.time(), **body.model_dump(exclude={'mode'}))
        db.add(device)
        db.flush()
        if body.mode == 'virtual':
            now = time.time()
            device.last_seen = now
            db.add(VirtualDevice(device_id=device.device_id,running=True,last_tick=now,active_until=now+300))
            db.add(Reading(reading_id=uid(),device_id=device.device_id,sample_id=uid(),soil_moisture=55,temperature=26,humidity=62,light_level=70,water_tank_level=85,timestamp=now,received_at=now))
        return {**as_dict(device), 'device_key': key}

@app.post('/api/devices/{device_id}/simulation')
def simulation(device_id: str, body: SimulationControl, user=Depends(current_user)):
    with write_lock, Session.begin() as db:
        device = owned(db,device_id,user)
        virtual = db.get(VirtualDevice,device_id)
        if not virtual:
            raise HTTPException(409,'This device uses an external sensor')
        now=time.time()
        virtual.active_until=now+300
        if body.action in ('start','pause'):
            virtual.running=body.action=='start'
            virtual.last_tick=now
            if body.action=='pause':
                stop(db,device,now,'simulation_paused')
        else:
            previous=latest(db,device_id)
            values={k:getattr(previous,k) for k in ('soil_moisture','temperature','humidity','light_level','water_tank_level')}
            if body.action=='dry':
                values['soil_moisture']=max(0,device.moisture_threshold-4)
            else:
                values['water_tank_level']=100
            reading=Reading(reading_id=uid(),device_id=device_id,sample_id=uid(),timestamp=now,received_at=now,**values)
            db.add(reading)
            device.last_seen=now
            virtual.last_tick=now
            process(db,device,reading,now)
        return {'running':virtual.running,'action':body.action}

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
        if db.get(VirtualDevice,body.device_id):
            raise HTTPException(409,'Virtual plants use the built-in simulator. Add an external device for sensor ingestion.')
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

