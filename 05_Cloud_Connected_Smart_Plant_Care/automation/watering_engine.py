"""Pure decision rules; the API persists each bounded watering command."""
MAX_DURATION = 15
COOLDOWN = 60
OFFLINE_AFTER = 45

def blocked(device, reading, now):
    if not reading or now - device.last_seen > OFFLINE_AFTER:
        return 'Device offline or no fresh reading'
    if reading.water_tank_level <= 15:
        return 'Water tank too low'
    if reading.soil_moisture >= min(device.moisture_threshold + 15, 95):
        return 'Soil already sufficiently moist'
    if device.pump_until > now:
        return 'Pump already active'
    if now - device.last_watered < COOLDOWN:
        return 'Pump cooling down'
    return None
