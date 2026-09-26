import os
import tempfile
from pathlib import Path
import time
import pytest

test_dir = tempfile.TemporaryDirectory(prefix='verdant-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(test_dir.name) / 'test.db')
os.environ['JWT_SECRET'] = 'test-secret-for-isolated-tests-only-123456789'
from fastapi.testclient import TestClient
from backend.app import app, attempts
from cloud.database_service import Base, engine, Session
from cloud.auth_service import hash_password, digest, token
from backend.models import User, Device

@pytest.fixture(scope='session', autouse=True)
def close_test_database():
    yield
    engine.dispose()
    test_dir.cleanup()

@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    attempts.clear()
    with Session.begin() as db:
        db.add_all([User(user_id=u, name=u, email=u+'@example.com', password_hash=hash_password('test-password-123'), created_at=time.time()) for u in ['alice','bob']])
        db.flush()
        db.add(Device(device_id='PLANT-001', user_id='alice', plant_name='Monstera', plant_type='indoor', location='Office', key_hash=digest('test-device-key'), moisture_threshold=30, created_at=time.time()))
    with TestClient(app) as test:
        yield test

@pytest.fixture
def auth():
    return {'Authorization':'Bearer '+token('alice')}
