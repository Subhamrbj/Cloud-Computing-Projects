"""Trend-based synthetic device with bounded commands and idempotent retries."""
import argparse
import json
import logging
import math
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import httpx
from sensor_simulator.config import API_URL, INTERVAL

log = logging.getLogger('sensor')

class VirtualPlant:
    def __init__(self, device_id, moisture=55, seed=42):
        self.device_id, self.moisture = device_id, moisture
        self.tank, self.elapsed, self.pump_until = 85., 0., 0.
        self.rng = random.Random(seed)

    def sample(self, seconds, accelerated=False):
        self.elapsed += seconds
        on = time.monotonic() < self.pump_until and self.tank > 15
        self.moisture = max(0, min(100, self.moisture + (2.2*seconds if on else -seconds*(.3 if accelerated else .015))))
        if on:
            self.tank = max(0, self.tank-seconds*.3)
        return {'sample_id': str(uuid.uuid4()), 'device_id': self.device_id, 'soil_moisture': round(self.moisture, 2), 'temperature': round(26+3*math.sin(self.elapsed/300)+self.rng.uniform(-.1,.1), 2), 'humidity': round(60+8*math.cos(self.elapsed/400), 2), 'light_level': round(max(0, 80*math.sin((self.elapsed/3600+8)*math.pi/24)), 2), 'water_tank_level': round(self.tank, 2), 'timestamp': datetime.now(timezone.utc).isoformat()}

    def apply(self, response):
        remaining = max(0, min(15, response['pump_until']-response['server_time'])) if response['pump_on'] else 0
        self.pump_until = time.monotonic()+remaining

def transmit(client, url, sample, key, sleeper=time.sleep):
    for attempt in range(4):
        try:
            response = client.post(url+'/api/sensors/data', json=sample, headers={'X-Device-Key': key})
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            elif response.status_code >= 400:
                log.error('Rejected sample: HTTP %s', response.status_code)
                return None
            return response.json()
        except (httpx.TransportError, httpx.HTTPStatusError):
            log.warning('Network/API failure; retry %s/4', attempt+1)
            if attempt < 3:
                sleeper(min(2**attempt, 8))
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=API_URL)
    parser.add_argument('--interval', type=float, default=INTERVAL)
    parser.add_argument('--device', default='PLANT-001')
    parser.add_argument('--key')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--accelerated', action='store_true')
    parser.add_argument('--steps', type=int, default=0)
    args = parser.parse_args()
    if not .2 <= args.interval <= 30:
        parser.error('Interval must be between 0.2 and 30 seconds')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    devices = [{'device_id': args.device, 'device_key': args.key or ''}]
    if not args.offline and not args.key:
        stored = json.loads(Path('.demo-credentials.json').read_text())['devices']
        devices = stored if args.all else [d for d in stored if d['device_id'] == args.device]
    if not devices:
        parser.error('Device not found in credentials')
    plants = [(VirtualPlant(d['device_id'], 55-i*8, i), d['device_key']) for i,d in enumerate(devices)]
    with httpx.Client(timeout=5) as client:
        count = 0
        while not args.steps or count < args.steps:
            for plant, key in plants:
                sample = plant.sample(args.interval, args.accelerated)
                if args.offline:
                    print(json.dumps(sample))
                else:
                    result = transmit(client, args.url, sample, key)
                    if result:
                        plant.apply(result)
                    else:
                        plant.pump_until = 0  # fail closed when communication fails
                    log.info('%s soil=%s%% pump=%s', plant.device_id, sample['soil_moisture'], time.monotonic() < plant.pump_until)
            count += 1
            if not args.steps or count < args.steps:
                time.sleep(args.interval)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log.info('Simulator stopped; virtual pump off')
