# KKTC konumları (Open-Meteo için enlem/boylam)
# Lefkoşa varsayılan merkezdir.

LOCATIONS = {
    "Lefkoşa": {"lat": 35.1856, "lon": 33.3823},
    "Girne": {"lat": 35.3400, "lon": 33.3190},
    "Gazimağusa": {"lat": 35.1250, "lon": 33.9500},
    "Güzelyurt": {"lat": 35.2000, "lon": 32.9800},
    "İskele": {"lat": 35.2850, "lon": 33.9200},
}

# Varsayılan sistem boyutları (hane tipi)
DEFAULTS = {
    "pv_kwp": 5.0,          # Güneş kurulu gücü (kWp)
    "tracking_gain": 0.25,  # Çift eksen takip kazancı (+%25)
    "wind_kw": 3.0,         # Rüzgar türbini anma gücü (kW)
    "battery_kwh": 10.0,    # Ev bataryası kapasitesi (kWh)
    "ev_kwh": 40.0,         # EV batarya kapasitesi (kWh, V2H destekli)
    "daily_consumption_kwh": 15.0,
}
