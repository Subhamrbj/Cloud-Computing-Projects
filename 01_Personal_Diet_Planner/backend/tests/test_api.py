import pytest
from app import ai_engine, main
from app.planner import targets, rule_plan, validate_ai, unsafe_text
from app.models import User


def test_health(client):
    r=client.get('/health');assert r.status_code==200 and r.json()['database'] and r.json()['storage']

def test_register_duplicate_login(client,auth):
    h=auth()
    r=client.post('/register',json={'name':'A','email':'ASHA@example.com','password':'something-long'})
    assert r.status_code==409
    assert client.post('/login',json={'email':'asha@example.com','password':'test-password-123'}).status_code==200
    bad=[client.post('/login',json={'email':x,'password':'wrong'}).json() for x in ['asha@example.com','missing@example.com']]
    assert bad[0]==bad[1]

def test_invalid_auth(client):
    assert client.get('/dashboard').status_code==401
    assert client.get('/profile',headers={'Authorization':'Bearer fake'}).status_code==401

def test_logout(client,auth):
    h=auth();assert client.get('/profile',headers=h).status_code==200
    assert client.post('/logout',headers=h).status_code==200
    assert client.get('/profile',headers=h).status_code==401

def test_profile_validation(client,auth,profile):
    h=auth();assert client.put('/profile',json=profile,headers=h).status_code==200
    assert client.get('/profile',headers=h).json()['goal']=='balanced'
    assert client.put('/profile',json={**profile,'age':5},headers=h).status_code==422
    assert client.put('/profile',json={**profile,'allergies':['not-a-real-allergen']},headers=h).status_code==422

@pytest.mark.parametrize('goal', ['weight_management','balanced','fitness'])
def test_goal_targets(client,auth,profile,goal):
    h=auth();client.put('/profile',json={**profile,'goal':goal},headers=h)
    result=client.get('/targets',headers=h).json()
    assert result['calories']>1200 and result['protein']>0

def test_incomplete_profile(client,auth):
    h=auth();assert client.post('/generate-plan',headers=h).status_code==400

def test_generate_and_save(client,auth,profile):
    h=auth();client.put('/profile',json=profile,headers=h)
    p=client.post('/generate-plan',headers=h).json()
    assert all(k in p for k in ['breakfast','lunch','snack','dinner','nutrition_summary','disclaimer'])
    assert abs(p['nutrition_summary']['calories']-p['targets']['calories'])<p['targets']['calories']*.15
    r=client.post('/plans',json=p,headers=h);assert r.status_code==201,r.text
    id=r.json()['id'];assert len(client.get('/plans',headers=h).json())==1
    assert client.get('/plans/'+id,headers=h).status_code==200
    assert 'Educational' in client.get('/plans/'+id+'/export',headers=h).text
    assert len(client.get('/files',headers=h).json())==1
    assert client.delete('/plans/'+id,headers=h).status_code==204
    assert client.get('/plans/'+id,headers=h).status_code==404
    assert client.get('/files',headers=h).json()==[]

def test_diet_allergen_safety(client,auth,profile):
    h=auth();client.put('/profile',json={**profile,'dietary_preference':'vegan','allergies':['nuts','soy','gluten']},headers=h)
    for _ in range(20):
        p=client.post('/generate-plan',headers=h).json()
        for label in ['breakfast','lunch','snack','dinner']:
            assert p[label]['diet']=='vegan'
            assert not set(p[label]['allergens'])&{'nuts','soy','gluten'}

def test_unsafe_ai_rejected(profile):
    u=User(**profile)
    u.dietary_preference='vegan'
    t=targets(u);base=rule_plan(u,t)
    bad={label:base[label] for label in ['breakfast','lunch','snack','dinner']}
    bad['breakfast']={**bad['breakfast'],'name':'Paneer paratha'}
    with pytest.raises(ValueError,match='paneer'): validate_ai(bad,u,t)
    u.dietary_preference='vegetarian';bad['breakfast']={**bad['breakfast'],'name':'Egg toast','ingredients':['egg','bread'],'diet':'vegetarian'}
    with pytest.raises(ValueError,match='egg'): validate_ai(bad,u,t)

def test_ai_timeout_fallback(client,auth,profile,monkeypatch):
    from dataclasses import replace
    monkeypatch.setattr(ai_engine,'settings',replace(ai_engine.settings,ai_api_url='https://invalid.example/chat',ai_api_key='mock-key'))
    class Broken:
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
        async def post(self,*a,**kw): raise TimeoutError('simulated')
    monkeypatch.setattr(ai_engine.httpx,'AsyncClient',lambda **kw:Broken())
    h=auth();client.put('/profile',json=profile,headers=h)
    p=client.post('/generate-plan',headers=h).json()
    assert p['source']=='rule-based' and p['fallback_reason']

def test_upload_validate_download(client,auth):
    h=auth();content=b'\x89PNG\r\n\x1a\nabc'
    r=client.post('/upload',files={'file':('my meal.png',content,'image/png')},headers=h)
    assert r.status_code==201,r.text
    f=r.json();assert f['filename']=='my_meal.png'
    assert client.get('/files/'+f['id']+'/download',headers=h).content==content
    assert client.delete('/files/'+f['id'],headers=h).status_code==204
    assert client.get('/files',headers=h).json()==[]

@pytest.mark.parametrize('name,content,status',[('x.exe',b'abc',415),('x.png',b'bad',400),('x.txt',b'',400),('x.txt',b'a'* (5*1024*1024+1),413)])
def test_bad_upload(client,auth,name,content,status):
    h=auth();assert client.post('/upload',files={'file':(name,content)},headers=h).status_code==status
    assert client.get('/files',headers=h).json()==[]

def test_cross_user_isolation(client,auth,profile):
    a=auth();b=auth('other@example.com');client.put('/profile',json=profile,headers=a)
    p=client.post('/generate-plan',headers=a).json();pid=client.post('/plans',json=p,headers=a).json()['id']
    fid=client.get('/files',headers=a).json()[0]['id']
    iid=client.post('/intake',json={'food':'Apple','calories':100},headers=a).json()['id']
    for path in ['/plans/'+pid,'/plans/'+pid+'/export','/files/'+fid+'/download']:
        assert client.get(path,headers=b).status_code==404
    for path in ['/plans/'+pid,'/files/'+fid,'/intake/'+iid]:
        assert client.delete(path,headers=b).status_code==404
    assert client.get('/plans',headers=b).json()==[]
    assert client.get('/files',headers=b).json()==[]
    assert client.get('/plans/'+pid,headers=a).status_code==200

def test_intake_progress_dashboard(client,auth,profile):
    h=auth();client.put('/profile',json=profile,headers=h)
    for calories in [125,170]: assert client.post('/intake',json={'food':'Food','calories':calories},headers=h).status_code==201
    assert len(client.get('/intake',headers=h).json())==2
    series=client.get('/progress',headers=h).json()
    assert len(series)==7 and series[-1]['calories']==295
    dash=client.get('/dashboard',headers=h).json()
    assert dash['today']['calories']==295 and dash['profile_complete']

def test_storage_outage_no_orphan(client,auth,monkeypatch):
    h=auth()
    def fail(*args): raise OSError('unavailable')
    monkeypatch.setattr(main.storage,'put',fail)
    assert client.post('/upload',files={'file':('a.txt',b'abc')},headers=h).status_code==503
    assert client.get('/files',headers=h).json()==[]

def test_input_validation(client,auth):
    assert client.post('/register',json={'name':'A','email':'bad','password':'short'}).status_code==422
    h=auth();assert client.post('/intake',json={'food':'x','calories':-5},headers=h).status_code==422

def test_goal_order(profile):
    u=User(**profile)
    values=[]
    for goal in ('weight_management','balanced','fitness'):
        u.goal=goal;values.append(targets(u)['calories'])
    assert values[0]<values[1]<values[2]

def test_ai_success(client,auth,profile,monkeypatch):
    from dataclasses import replace
    u=User(**profile)
    plan=rule_plan(u,targets(u))
    meals={k:plan[k] for k in ('breakfast','lunch','snack','dinner')}
    monkeypatch.setattr(ai_engine,'settings',replace(ai_engine.settings,ai_api_url='https://mock.example',ai_api_key='mock'))
    class Response:
        def raise_for_status(self): pass
        def json(self):
            import json
            return {'choices':[{'message':{'content':json.dumps(meals)}}]}
    class Mock:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs): return Response()
    monkeypatch.setattr(ai_engine.httpx,'AsyncClient',lambda **kw:Mock())
    h=auth();client.put('/profile',json=profile,headers=h)
    result=client.post('/generate-plan',headers=h)
    assert result.status_code==200 and result.json()['source'].startswith('ai:')

def test_ai_unsafe_fallback(client,auth,profile,monkeypatch):
    from dataclasses import replace
    import json
    u=User(**{**profile,'dietary_preference':'vegan'})
    p=rule_plan(u,targets(u))
    meals={k:p[k] for k in ('breakfast','lunch','snack','dinner')}
    meals['breakfast']['name']='Paneer paratha'
    monkeypatch.setattr(ai_engine,'settings',replace(ai_engine.settings,ai_api_url='https://mock.example',ai_api_key='mock'))
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices':[{'message':{'content':json.dumps(meals)}}]}
    class Mock:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs): return Response()
    monkeypatch.setattr(ai_engine.httpx,'AsyncClient',lambda **kw:Mock())
    h=auth();client.put('/profile',json={**profile,'dietary_preference':'vegan'},headers=h)
    r=client.post('/generate-plan',headers=h)
    assert r.status_code==200 and r.json()['source']=='rule-based'
    assert all('paneer' not in r.json()[m]['name'].lower() for m in meals)

def test_save_rejects_wrong_target(client,auth,profile):
    h=auth();client.put('/profile',json=profile,headers=h)
    p=client.post('/generate-plan',headers=h).json();p['targets']['calories']+=500
    assert client.post('/plans',json=p,headers=h).status_code==422
    assert client.get('/plans',headers=h).json()==[]

def test_save_rejects_unsafe_meal(client,auth,profile):
    h=auth();client.put('/profile',json={**profile,'dietary_preference':'vegan'},headers=h)
    p=client.post('/generate-plan',headers=h).json();p['breakfast']['ingredients'].append('cheese')
    assert client.post('/plans',json=p,headers=h).status_code==422

def test_plan_export_cannot_delete_independently(client,auth,profile):
    h=auth();client.put('/profile',json=profile,headers=h)
    p=client.post('/generate-plan',headers=h).json()
    client.post('/plans',json=p,headers=h)
    fid=client.get('/files',headers=h).json()[0]['id']
    assert client.delete('/files/'+fid,headers=h).status_code==400
    assert len(client.get('/files',headers=h).json())==1

def test_upload_filename_strips_paths(client,auth):
    h=auth();r=client.post('/upload',files={'file':('../private.txt',b'demo')},headers=h)
    assert r.status_code==201 and r.json()['filename']=='private.txt'

def test_storage_path_guard(tmp_path):
    from app.storage import LocalStorage
    with pytest.raises(ValueError): LocalStorage(tmp_path).put('../outside.txt',b'no')

def test_security_headers(client):
    r=client.get('/health')
    assert r.headers['x-content-type-options']=='nosniff'
    assert r.headers['x-frame-options']=='DENY'
    assert 'secret' not in str(r.json()).lower()

def test_rate_limit(client,monkeypatch):
    monkeypatch.setitem(main.RATE_LIMITS,'/login',2)
    main.rate_events.clear()
    body={'email':'nobody@example.com','password':'wrong'}
    assert client.post('/login',json=body).status_code==401
    assert client.post('/login',json=body).status_code==401
    assert client.post('/login',json=body).status_code==429
    main.rate_events.clear()

def test_duplicate_email_case_insensitive(client,auth):
    auth('someone@example.com')
    r=client.post('/register',json={'name':'Second','email':'SOMEONE@EXAMPLE.COM','password':'long-password'})
    assert r.status_code==409
