from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4
import re
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .config import settings
from .db import Base, engine, get_db
from .models import User, Plan, UserFile, Intake, RevokedToken, uid
from .schemas import Register, Login, Profile, PlanData, IntakeCreate
from .auth import hash_password, verify_password, issue_token, current_user, get_claims
from .planner import targets
from .ai_engine import generate
from .storage import storage

RATE_LIMITS={'/register':120,'/login':120,'/generate-plan':60,'/upload':30}
rate_events=defaultdict(deque)
rate_lock=Lock()

Base.metadata.create_all(bind=engine)
app=FastAPI(title='AI Personal Diet Planner',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=False,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])

@app.middleware('http')
async def headers_and_errors(request: Request,call_next):
    if request.method=='POST' and request.url.path in RATE_LIMITS:
        identity=request.headers.get('authorization') or (request.client.host if request.client else 'unknown')
        key=(request.url.path,identity)
        now_clock=time.monotonic()
        with rate_lock:
            events=rate_events[key]
            while events and now_clock-events[0]>=60: events.popleft()
            if len(events)>=RATE_LIMITS[request.url.path]:
                return __import__('fastapi').responses.JSONResponse({'detail':'Rate limit exceeded. Try again shortly.'},status_code=429)
            events.append(now_clock)
    try: response=await call_next(request)
    except SQLAlchemyError: return __import__('fastapi').responses.JSONResponse({'detail':'Database temporarily unavailable. Please retry.'},status_code=503)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    return response

def user_view(u):
    return {'id':u.id,'name':u.name,'email':u.email,'age':u.age,'sex':u.sex,'height':u.height,'weight':u.weight,'activity_level':u.activity_level,'dietary_preference':u.dietary_preference,'goal':u.goal,'allergies':u.allergies or [],'cuisines':u.cuisines or []}
def plan_view(p): return {'id':p.id,'created_at':p.created_at.isoformat(),**p.data}
def file_view(f): return {'id':f.id,'filename':f.filename,'content_type':f.content_type,'size_bytes':f.size_bytes,'kind':f.kind,'plan_id':f.plan_id,'uploaded_at':f.uploaded_at.isoformat()}
def owned(db,model,id,user):
    obj=db.scalar(select(model).where(model.id==id,model.user_id==user.id))
    if not obj: raise HTTPException(404,'Not found')
    return obj

def store_error(): return HTTPException(503,'Object storage temporarily unavailable. Please retry.')

@app.get('/health')
def health(db: Session=Depends(get_db)):
    try: db.execute(text('SELECT 1')); database=True
    except Exception: database=False
    try: object_ok=storage.health()
    except Exception: object_ok=False
    return {'status':'ok' if database and object_ok else 'degraded','database':database,'storage':object_ok,'ai_api_configured':bool(settings.ai_api_key and settings.ai_api_url),'version':'1.0.0'}

@app.post('/register',status_code=201)
def register(data:Register,db:Session=Depends(get_db)):
    email=str(data.email).lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'An account with this email already exists')
    u=User(name=data.name.strip(),email=email,password_hash=hash_password(data.password),allergies=[],cuisines=[])
    db.add(u)
    try: db.commit()
    except SQLAlchemyError: db.rollback(); raise HTTPException(409,'An account with this email already exists')
    return {'token':issue_token(u),'user':user_view(u)}

@app.post('/login')
def login(data:Login,db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==str(data.email).lower()))
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Invalid email or password')
    return {'token':issue_token(u),'user':user_view(u)}

@app.post('/logout')
def logout(claims:dict=Depends(get_claims),db:Session=Depends(get_db)):
    db.add(RevokedToken(jti=claims['jti'],expires_at=datetime.fromtimestamp(claims['exp'],timezone.utc)))
    db.commit(); return {'message':'Logged out'}

@app.get('/profile')
def profile(u:User=Depends(current_user)): return user_view(u)

@app.put('/profile')
def update_profile(data:Profile,u:User=Depends(current_user),db:Session=Depends(get_db)):
    for k,v in data.model_dump().items(): setattr(u,k,v)
    db.commit(); return user_view(u)

def require_profile(u):
    if any(getattr(u,k) is None for k in ('age','sex','height','weight','activity_level','dietary_preference','goal')):
        raise HTTPException(400,'Complete your profile first')

@app.get('/targets')
def target_route(u:User=Depends(current_user)):
    require_profile(u); return targets(u)

@app.post('/generate-plan')
async def generate_route(u:User=Depends(current_user)):
    require_profile(u)
    try: return await generate(u)
    except ValueError as exc: raise HTTPException(400,str(exc))

@app.post('/plans',status_code=201)
def save_plan(data:PlanData,u:User=Depends(current_user),db:Session=Depends(get_db)):
    require_profile(u)
    # Check submitted meals against the current profile and calorie target.
    from .planner import validate_ai
    t=targets(u)
    try: validate_ai(data.model_dump(),u,t)
    except ValueError as exc: raise HTTPException(422,str(exc))
    if data.targets.get('calories')!=t['calories']: raise HTTPException(422,'Target does not match current profile')
    p=Plan(id=uid(),user_id=u.id,data=data.model_dump())
    f=UserFile(user_id=u.id,filename='diet-plan-'+p.id+'.txt',storage_path=f'users/{u.id}/plans/{p.id}.txt',content_type='text/plain',size_bytes=0,kind='plan',plan_id=p.id)
    content=(f'One-day meal plan\n\n'+ '\n'.join(f'{label.title()}: {getattr(data,label).name} ({getattr(data,label).calories:g} kcal)' for label in ('breakfast','lunch','snack','dinner'))+
             f'\n\nTotal: {data.nutrition_summary.get("calories")} kcal\n{data.hydration}\n\n{data.disclaimer}\n').encode()
    f.size_bytes=len(content)
    try: storage.put(f.storage_path,content,f.content_type)
    except Exception: raise store_error()
    try: db.add_all([p,f]);db.commit()
    except Exception:
        db.rollback()
        try: storage.delete(f.storage_path)
        except Exception: pass
        raise
    return plan_view(p)

@app.get('/plans')
def plans(u:User=Depends(current_user),db:Session=Depends(get_db)):
    return [plan_view(x) for x in db.scalars(select(Plan).where(Plan.user_id==u.id).order_by(Plan.created_at.desc())).all()]

@app.get('/plans/{id}')
def one_plan(id:str,u:User=Depends(current_user),db:Session=Depends(get_db)):
    return plan_view(owned(db,Plan,id,u))

@app.get('/plans/{id}/export')
def export_plan(id:str,u:User=Depends(current_user),db:Session=Depends(get_db)):
    owned(db,Plan,id,u)
    f=db.scalar(select(UserFile).where(UserFile.user_id==u.id,UserFile.plan_id==id,UserFile.kind=='plan'))
    if not f: raise HTTPException(404,'Export not found')
    try: content=storage.get(f.storage_path)
    except Exception: raise store_error()
    return StreamingResponse(BytesIO(content),media_type='text/plain',headers={'Content-Disposition':f'attachment; filename="{f.filename}"'})

@app.delete('/plans/{id}',status_code=204)
def delete_plan(id:str,u:User=Depends(current_user),db:Session=Depends(get_db)):
    p=owned(db,Plan,id,u)
    files=db.scalars(select(UserFile).where(UserFile.user_id==u.id,UserFile.plan_id==id)).all()
    try:
        for f in files: storage.delete(f.storage_path)
    except Exception: raise store_error()
    for f in files: db.delete(f)
    db.delete(p);db.commit()

SIGNATURES={'.png':('image/png',lambda b:b.startswith(b'\x89PNG\r\n\x1a\n')),
            '.jpg':('image/jpeg',lambda b:b.startswith(b'\xff\xd8\xff')),
            '.jpeg':('image/jpeg',lambda b:b.startswith(b'\xff\xd8\xff')),
            '.pdf':('application/pdf',lambda b:b.startswith(b'%PDF-')),
            '.txt':('text/plain',lambda b: b'\x00' not in b and bool(b.strip()))}

@app.post('/upload',status_code=201)
async def upload(file:UploadFile=File(...),u:User=Depends(current_user),db:Session=Depends(get_db)):
    name=re.sub(r'[^A-Za-z0-9._-]','_',file.filename.split('/')[-1].split('\\')[-1])[:120]
    ext='.'+name.rsplit('.',1)[-1].lower() if '.' in name else ''
    if ext not in SIGNATURES: raise HTTPException(415,'Unsupported file type')
    content=await file.read(settings.max_upload_bytes+1)
    if len(content)>settings.max_upload_bytes: raise HTTPException(413,'File too large')
    if not content or not SIGNATURES[ext][1](content): raise HTTPException(400,'Empty file or invalid file signature')
    f=UserFile(user_id=u.id,filename=name,storage_path=f'users/{u.id}/uploads/{uuid4()}_{name}',content_type=SIGNATURES[ext][0],size_bytes=len(content),kind='upload')
    try: storage.put(f.storage_path,content,f.content_type)
    except Exception: raise store_error()
    try: db.add(f);db.commit()
    except Exception:
        db.rollback()
        try: storage.delete(f.storage_path)
        except Exception: pass
        raise
    return file_view(f)

@app.get('/files')
def files(u:User=Depends(current_user),db:Session=Depends(get_db)):
    return [file_view(f) for f in db.scalars(select(UserFile).where(UserFile.user_id==u.id).order_by(UserFile.uploaded_at.desc())).all()]

@app.get('/files/{id}/download')
def download(id:str,u:User=Depends(current_user),db:Session=Depends(get_db)):
    f=owned(db,UserFile,id,u)
    try: content=storage.get(f.storage_path)
    except Exception: raise store_error()
    return StreamingResponse(BytesIO(content),media_type=f.content_type,headers={'Content-Disposition':f'attachment; filename="{f.filename}"'})

@app.delete('/files/{id}',status_code=204)
def delete_file(id:str,u:User=Depends(current_user),db:Session=Depends(get_db)):
    f=owned(db,UserFile,id,u)
    if f.kind=='plan': raise HTTPException(400,'Delete the related plan to remove its export')
    try: storage.delete(f.storage_path)
    except Exception: raise store_error()
    db.delete(f);db.commit()

@app.post('/intake',status_code=201)
def log_intake(data:IntakeCreate,u:User=Depends(current_user),db:Session=Depends(get_db)):
    row=Intake(user_id=u.id,**data.model_dump());db.add(row);db.commit();return intake_view(row)

def intake_view(row): return {'id':row.id,'food':row.food,'calories':row.calories,'protein':row.protein,'carbs':row.carbs,'fat':row.fat,'created_at':row.created_at.isoformat()}
@app.get('/intake')
def intake(u:User=Depends(current_user),db:Session=Depends(get_db)):
    return [intake_view(x) for x in db.scalars(select(Intake).where(Intake.user_id==u.id).order_by(Intake.created_at.desc())).all()]
@app.delete('/intake/{id}',status_code=204)
def delete_intake(id:str,u:User=Depends(current_user),db:Session=Depends(get_db)):
    db.delete(owned(db,Intake,id,u));db.commit()

def today_rows(db,u):
    today=datetime.now(timezone.utc).date()
    return [r for r in db.scalars(select(Intake).where(Intake.user_id==u.id)).all() if r.created_at.date()==today]
def totals(rows): return {k:round(sum(getattr(x,k) for x in rows),1) for k in ('calories','protein','carbs','fat')}
@app.get('/progress')
def progress(u:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Intake).where(Intake.user_id==u.id)).all()
    today=datetime.now(timezone.utc).date()
    return [{'date':(today-timedelta(days=n)).isoformat(),**totals([x for x in rows if x.created_at.date()==today-timedelta(days=n)])} for n in range(6,-1,-1)]
@app.get('/dashboard')
def dashboard(u:User=Depends(current_user),db:Session=Depends(get_db)):
    latest=db.scalar(select(Plan).where(Plan.user_id==u.id).order_by(Plan.created_at.desc()))
    return {'profile_complete':all(getattr(u,k) is not None for k in ('age','sex','height','weight','activity_level','dietary_preference','goal')),
            'latest_plan':plan_view(latest) if latest else None,
            'plan_count':db.scalar(select(func.count()).select_from(Plan).where(Plan.user_id==u.id)),
            'file_count':db.scalar(select(func.count()).select_from(UserFile).where(UserFile.user_id==u.id)),
            'today':totals(today_rows(db,u))}
