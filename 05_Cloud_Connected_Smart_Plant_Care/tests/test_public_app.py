import time
import pytest
from sqlalchemy import select, func
from backend.app import sweep
from backend.models import User, Device, Reading, VirtualDevice, GuestAccount, AccountSecurity
from backend.public_service import prune
from cloud.database_service import Session

def register(client, email='new@example.com'):
    return client.post('/api/auth/register',json={'name':'New Gardener','email':email,'password':'A-long-test-password'})

def test_signup_private_garden_and_cookie(client):
    result=register(client)
    assert result.status_code==201
    assert len(result.json()['recovery_code'])>30
    assert 'HttpOnly' in result.headers['set-cookie']
    assert client.get('/api/auth/me').json()['name']=='New Gardener'
    devices=client.get('/api/devices').json()
    assert len(devices)==3 and all(d['mode']=='virtual' for d in devices)
    assert all(d['user_id']!='alice' for d in devices)
    assert len(client.get('/api/devices/'+devices[0]['device_id']+'/history').json())>=25

def test_duplicate_email_and_normalization(client):
    assert register(client,'  NEW@EXAMPLE.COM  ').status_code==201
    assert register(client,'new@example.com').status_code==409

@pytest.mark.parametrize('email',['invalid','x@@example.com','someone@ localhost'])
def test_email_validation(client,email):
    assert register(client,email).status_code==422

def test_logout_clears_browser_session(client):
    register(client)
    assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/auth/me').status_code==401

def test_guest_isolated_and_expiring(client):
    one=client.post('/api/auth/demo')
    assert one.status_code==201 and one.json()['is_demo']
    first=client.get('/api/devices').json()
    two=client.post('/api/auth/demo')
    assert two.status_code==201
    second=client.get('/api/devices').json()
    assert first[0]['user_id']!=second[0]['user_id']
    assert client.get('/api/devices/'+first[0]['device_id']).status_code==404
    with Session.begin() as db:
        db.get(GuestAccount,second[0]['user_id']).expires_at=time.time()-1
    assert client.get('/api/auth/me').status_code==401

def test_recovery_revokes_existing_token_and_rotates_code(client):
    data=register(client).json()
    recovered=client.post('/api/auth/recover',json={'email':'new@example.com','password':'A-new-test-password','recovery_code':data['recovery_code']})
    assert recovered.status_code==200
    assert recovered.json()['recovery_code']!=data['recovery_code']
    assert client.get('/api/devices',headers={'Authorization':'Bearer '+data['access_token']}).status_code==401
    assert client.post('/api/auth/recover',json={'email':'new@example.com','password':'A-new-test-password','recovery_code':data['recovery_code']}).status_code==400
    assert client.post('/api/auth/login',json={'email':'new@example.com','password':'A-new-test-password'}).status_code==200

def test_invalid_recovery(client):
    register(client)
    assert client.post('/api/auth/recover',json={'email':'new@example.com','password':'A-new-test-password','recovery_code':'x'*32}).status_code==400

def test_account_delete_cascades(client):
    register(client)
    device=client.get('/api/devices').json()[0]
    assert client.request('DELETE','/api/auth/account',json={'password':'incorrect-password'}).status_code==401
    assert client.request('DELETE','/api/auth/account',json={'password':'A-long-test-password'}).status_code==200
    with Session() as db:
        assert db.get(User,device['user_id']) is None
        assert db.get(Device,device['device_id']) is None
        assert db.scalar(select(func.count()).select_from(Reading).where(Reading.device_id==device['device_id']))==0
    assert client.get('/api/auth/me').status_code==401

def test_cross_origin_write_rejected(client):
    assert client.post('/api/auth/demo',headers={'Origin':'https://attacker.example'}).status_code==403
    assert client.post('/api/auth/demo',headers={'Origin':'http://testserver'}).status_code==201

def test_public_limits(client):
    for _ in range(5):
        assert client.post('/api/auth/demo').status_code==201
    assert client.post('/api/auth/demo').status_code==429

def test_virtual_cycle_dry_pause_refill(client):
    register(client)
    device=client.get('/api/devices').json()[0]
    path='/api/devices/'+device['device_id']
    assert client.post(path+'/simulation',json={'action':'dry'}).status_code==200
    assert client.get(path).json()['pump_on']
    with Session.begin() as db:
        db.get(VirtualDevice,device['device_id']).last_tick=time.time()-4
        db.get(Device,device['device_id']).last_watered=time.time()-4
    sweep()
    assert client.get(path+'/latest').json()['soil_moisture']>26
    assert client.post(path+'/simulation',json={'action':'pause'}).status_code==200
    assert not client.get(path).json()['pump_on']
    assert client.post(path+'/simulation',json={'action':'refill'}).status_code==200
    assert client.get(path+'/latest').json()['water_tank_level']==100

def test_virtual_controls_owner_only(client,auth):
    register(client)
    device=client.get('/api/devices').json()[0]
    assert client.post('/api/devices/'+device['device_id']+'/simulation',json={'action':'dry'},headers=auth).status_code==404

def test_visitor_inactivity_stops_virtual_ticks(client):
    register(client)
    device=client.get('/api/devices').json()[0]
    with Session.begin() as db:
        virtual=db.get(VirtualDevice,device['device_id'])
        virtual.active_until=time.time()-1
        virtual.last_tick=time.time()-20
    before=client.get('/api/devices/'+device['device_id']+'/latest').json()['reading_id']
    sweep()
    after=client.get('/api/devices/'+device['device_id']+'/latest').json()['reading_id']
    assert before==after

def test_guest_cleanup(client):
    client.post('/api/auth/demo')
    device=client.get('/api/devices').json()[0]
    with Session.begin() as db:
        db.get(GuestAccount,device['user_id']).expires_at=time.time()-1
        db.flush()
        prune(db,time.time())
    with Session() as db:
        assert db.get(User,device['user_id']) is None

def test_existing_external_devices_unchanged(client,auth):
    device=client.get('/api/devices',headers=auth).json()[0]
    assert device['mode']=='external'
    assert client.post('/api/devices/PLANT-001/simulation',json={'action':'start'},headers=auth).status_code==409

def test_session_survives_page_reload(client):
    register(client)
    assert client.get('/').status_code in (200,404)
    assert client.get('/api/auth/me').status_code==200

def test_registration_can_be_disabled(client,monkeypatch):
    monkeypatch.setenv('ALLOW_REGISTRATION','false')
    assert register(client).status_code==403
