"""Create a local owner and three virtual devices. Never runs on API startup."""
import json
import os
import secrets
import time
import math
from pathlib import Path
from cloud.database_service import Base, engine, Session
from cloud.auth_service import hash_password, digest
from backend.models import User, Device, Reading, Watering
from backend.services import uid

def main():
    if not Path('.env').exists():
        Path('.env').write_text('JWT_SECRET='+secrets.token_urlsafe(48)+'\nDATABASE_URL=sqlite:///./plantcare.db\n', encoding='utf-8')
    Base.metadata.create_all(engine)
    credentials = {'email': os.getenv('DEMO_EMAIL', 'gardener@example.com'), 'password': secrets.token_urlsafe(15), 'devices': []}
    with Session.begin() as db:
        if db.get(User, 'demo-owner'):
            print('Demo already exists. Credentials are in .demo-credentials.json. No changes made.')
            return
        now = time.time()
        db.add(User(user_id='demo-owner', name='Garden studio', email=credentials['email'], password_hash=hash_password(credentials['password']), created_at=now))
        db.flush()
        for index, (name, kind, threshold, location) in enumerate([('Monstera Deliciosa', 'indoor', 30, 'Living room'), ('Sweet Basil', 'herb', 35, 'Kitchen window'), ('Golden Barrel', 'succulent', 20, 'Balcony')]):
            device_id, key = f'PLANT-{index+1:03}', secrets.token_urlsafe(32)
            db.add(Device(device_id=device_id, user_id='demo-owner', plant_name=name, plant_type=kind, location=location, moisture_threshold=threshold, created_at=now-86400, key_hash=digest(key), last_seen=now))
            db.flush()
            for n in range(96):
                # Seeded synthetic history is presentation data, not physical measurements.
                stamp = now-(95-n)*900
                moisture = 57-index*8-(n%30)*.65
                db.add(Reading(reading_id=uid(), device_id=device_id, sample_id=f'seed-{n}', soil_moisture=moisture, temperature=25+2*math.sin(n/15), humidity=62+7*math.cos(n/20), light_level=max(5, 65*math.sin(n/30)**2), water_tank_level=82, timestamp=stamp, received_at=stamp))
            for n in range(3):
                stamp=now-(n+1)*24000
                db.add(Watering(event_id=uid(), device_id=device_id, trigger_type='demo_seed', moisture_before=threshold-3, moisture_after=threshold+15, duration=10, timestamp=stamp, stopped_at=stamp+10, stop_reason='synthetic_history'))
            credentials['devices'].append({'device_id': device_id, 'device_key': key})
    Path('.demo-credentials.json').write_text(json.dumps(credentials, indent=2), encoding='utf-8')
    print('Demo initialized. Open .demo-credentials.json for your generated login and device keys. Keep this file private.')

if __name__ == '__main__':
    main()
