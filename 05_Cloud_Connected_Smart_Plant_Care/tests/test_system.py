import time
from datetime import datetime, timezone, timedelta
import httpx
import pytest
from sqlalchemy import select, func
from cloud.database_service import Session
from cloud.auth_service import token
from backend.models import Device, Reading, Alert, Watering
from backend.app import sweep
from sensor_simulator.simulator import VirtualPlant, transmit

def sample(**overrides):
    import uuid
    return {'device_id':'PLANT-001','sample_id':str(uuid.uuid4()),'soil_moisture':55,'temperature':26,'humidity':61,'light_level':72,'water_tank_level':80,'timestamp':datetime.now(timezone.utc).isoformat(),**overrides}

def post(client, **overrides):
    return client.post('/api/sensors/data',json=sample(**overrides),headers={'X-Device-Key':'test-device-key'})

def test_login(client):
    result=client.post('/api/auth/login',json={'email':'alice@example.com','password':'test-password-123'})
    assert result.status_code==200 and result.json()['access_token']

def test_wrong_password(client):
    assert client.post('/api/auth/login',json={'email':'alice@example.com','password':'incorrect-password'}).status_code==401

def test_unauthorized(client):
    assert client.get('/api/devices').status_code==401
    assert client.post('/api/sensors/data',json=sample()).status_code==401

def test_owner_isolation(client):
    auth={'Authorization':'Bearer '+token('bob')}
    assert client.get('/api/devices',headers=auth).json()==[]
    assert client.get('/api/devices/PLANT-001/history',headers=auth).status_code==404
    assert client.post('/api/devices/PLANT-001/water',json={},headers=auth).status_code==404

def test_ingestion_storage_latest_history(client,auth):
    assert post(client).status_code==200
    latest=client.get('/api/devices/PLANT-001/latest',headers=auth).json()
    assert latest['soil_moisture']==55
    assert len(client.get('/api/devices/PLANT-001/history',headers=auth).json())==1
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Reading))==1

@pytest.mark.parametrize('field,value',[('soil_moisture',101),('soil_moisture',-1),('humidity',101),('temperature',70),('light_level',-1),('water_tank_level',-2)])
def test_invalid_sensor_values(client,field,value):
    assert post(client,**{field:value}).status_code==422

def test_timestamp_validation(client):
    assert post(client,timestamp=datetime.now().isoformat()).status_code==422
    assert post(client,timestamp=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()).status_code==422

def test_above_threshold(client):
    assert not post(client).json()['pump_on']

def test_threshold_boundary(client):
    assert not post(client,soil_moisture=30).json()['pump_on']

def test_auto_start_and_stop(client,auth):
    assert post(client,soil_moisture=29).json()['pump_on']
    assert not post(client,soil_moisture=46).json()['pump_on']
    events=client.get('/api/devices/PLANT-001/watering-history',headers=auth).json()
    assert len(events)==1 and events[0]['stop_reason']=='target_reached'
    assert events[0]['moisture_after']==46

def test_cooldown(client,auth):
    post(client,soil_moisture=29)
    post(client,soil_moisture=46)
    assert not post(client,soil_moisture=29).json()['pump_on']
    assert len(client.get('/api/devices/PLANT-001/watering-history',headers=auth).json())==1

def test_low_tank_blocks_and_stops(client):
    assert not post(client,soil_moisture=20,water_tank_level=10).json()['pump_on']
    assert post(client,soil_moisture=20,water_tank_level=80).json()['pump_on']
    assert not post(client,soil_moisture=20,water_tank_level=10).json()['pump_on']

def test_manual_watering_and_stop(client,auth):
    post(client,soil_moisture=40)
    assert client.post('/api/devices/PLANT-001/water',json={'duration':5},headers=auth).json()['pump_on']
    assert not client.post('/api/devices/PLANT-001/stop',headers=auth).json()['pump_on']

def test_manual_overwater_block(client,auth):
    post(client,soil_moisture=80)
    assert client.post('/api/devices/PLANT-001/water',json={},headers=auth).status_code==409

def test_duration_bound(client,auth):
    assert client.post('/api/devices/PLANT-001/water',json={'duration':16},headers=auth).status_code==422

def test_expiry(client):
    post(client,soil_moisture=20)
    with Session.begin() as db:
        db.get(Device,'PLANT-001').pump_until=time.time()-1
    sweep()
    assert not client.get('/api/devices/PLANT-001/command',headers={'X-Device-Key':'test-device-key'}).json()['pump_on']
    with Session() as db:
        assert db.scalar(select(Watering)).stop_reason=='duration_limit'

def test_alert_lifecycle(client,auth):
    post(client,soil_moisture=29,temperature=39)
    alerts=client.get('/api/alerts',headers=auth).json()
    assert len(alerts)==2
    aid=next(a['alert_id'] for a in alerts if a['alert_type']=='low_moisture')
    assert client.put('/api/alerts/'+aid+'/acknowledge',headers=auth).json()['status']=='acknowledged'
    post(client,soil_moisture=25)
    assert len(client.get('/api/alerts',headers=auth).json())==2
    post(client,soil_moisture=55)
    assert all(a['status']=='resolved' for a in client.get('/api/alerts',headers=auth).json())

def test_offline_detection(client,auth):
    post(client)
    with Session.begin() as db:
        db.get(Device,'PLANT-001').last_seen=time.time()-60
    sweep()
    assert not client.get('/api/devices',headers=auth).json()[0]['online']
    assert any(a['alert_type']=='offline' for a in client.get('/api/alerts',headers=auth).json())
    assert client.post('/api/devices/PLANT-001/water',json={},headers=auth).status_code==409

def test_duplicate(client,auth):
    body=sample(soil_moisture=20)
    for _ in range(3):
        result=client.post('/api/sensors/data',json=body,headers={'X-Device-Key':'test-device-key'})
        assert result.status_code==200
    assert result.json()['duplicate']
    assert len(client.get('/api/devices/PLANT-001/history',headers=auth).json())==1
    assert len(client.get('/api/devices/PLANT-001/watering-history',headers=auth).json())==1

def test_out_of_order(client):
    post(client)
    assert post(client,timestamp=(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()).status_code==409

def test_settings_and_automation_disabled(client,auth):
    response=client.put('/api/devices/PLANT-001/threshold',json={'moisture_threshold':40,'auto_water':False},headers=auth)
    assert response.status_code==200
    assert not post(client,soil_moisture=20).json()['pump_on']

def test_multiple_devices_and_key_scope(client,auth):
    created=client.post('/api/devices',json={'plant_name':'Basil','plant_type':'herb','location':'Kitchen'},headers=auth)
    assert created.status_code==201 and created.json()['moisture_threshold']==35
    assert len(client.get('/api/devices',headers=auth).json())==2
    assert client.post('/api/sensors/data',json=sample(device_id=created.json()['device_id']),headers={'X-Device-Key':'test-device-key'}).status_code==401

def test_no_key_leaks(client,auth):
    assert 'key_hash' not in client.get('/api/devices',headers=auth).text

def test_simulator_dry_and_wet():
    plant=VirtualPlant('test')
    a=plant.sample(2)
    b=plant.sample(2)
    assert b['soil_moisture']<a['soil_moisture']
    plant.apply({'pump_on':True,'pump_until':time.time()+10,'server_time':time.time()})
    assert plant.sample(2)['soil_moisture']>b['soil_moisture']
    assert 15<a['temperature']<40 and 30<a['humidity']<90

def test_simulator_retry_same_sample():
    calls=[]
    def handler(request):
        calls.append(request.content)
        return httpx.Response(503 if len(calls)<3 else 200,json={'ok':True})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert transmit(client,'http://test',sample(),'key',sleeper=lambda _:None)=={'ok':True}
    assert len(calls)==3 and calls[0]==calls[2]

def test_simulator_gives_up():
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(503))) as client:
        assert transmit(client,'http://test',sample(),'key',sleeper=lambda _:None) is None

def test_database_failure(client,monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session as OrmSession
    def fail(*args,**kwargs):
        raise OperationalError('SELECT 1',{},Exception('unavailable'))
    monkeypatch.setattr(OrmSession,'execute',fail)
    assert client.get('/api/health').status_code==503

def test_login_rate_limit(client):
    for _ in range(20):
        client.post('/api/auth/login',json={'email':'nobody@example.com','password':'wrong-password'})
    assert client.post('/api/auth/login',json={'email':'nobody@example.com','password':'wrong-password'}).status_code==429
