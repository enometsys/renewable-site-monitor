from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "weather.db"

PAST_DAYS = 30
TIMEZONE = "Asia/Manila"  # all sites are PH

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = ["shortwave_radiation", "wind_speed_10m"]
WIND_SPEED_UNIT = "ms"

# physical caps for cleaning; anything past these is a bad reading
SOLAR_MAX_WM2 = 1400.0
WIND_MAX_MS = 75.0

SITES = [
    {"site_id": "burgos", "name": "Burgos Wind Farm",
     "region": "Ilocos Norte (Luzon)", "latitude": 18.5176, "longitude": 120.6360},
    {"site_id": "cadiz", "name": "Cadiz Solar Power Plant",
     "region": "Negros Occidental (Visayas)", "latitude": 10.9499, "longitude": 123.3010},
    {"site_id": "nabas", "name": "Nabas Wind Farm",
     "region": "Aklan (Panay)", "latitude": 11.8300, "longitude": 122.1000},
]
