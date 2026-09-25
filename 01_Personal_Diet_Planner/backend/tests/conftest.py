import os
import tempfile
from pathlib import Path
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.gettempdir())/'daywell-test-bootstrap.db')
os.environ['STORAGE_DIR']=str(Path(tempfile.gettempdir())/'daywell-test-bootstrap-objects')
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.db import Base, make_engine, get_db
from app.main import app
from app import main
from app.storage import LocalStorage

@pytest.fixture
def client(tmp_path,monkeypatch):
    engine=make_engine('sqlite:///'+str(tmp_path/'test.db'))
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    def override():
        with factory() as session: yield session
    app.dependency_overrides[get_db]=override
    monkeypatch.setattr(main,'storage',LocalStorage(tmp_path/'objects'))
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture
def auth(client):
    def make(email='asha@example.com'):
        r=client.post('/register',json={'name':'Asha','email':email,'password':'test-password-123'})
        assert r.status_code==201,r.text
        return {'Authorization':'Bearer '+r.json()['token']}
    return make

@pytest.fixture
def profile():
    return {'age':29,'sex':'female','height':166,'weight':68,'activity_level':'moderate',
            'dietary_preference':'vegetarian','goal':'balanced','allergies':[],'cuisines':['Indian']}
