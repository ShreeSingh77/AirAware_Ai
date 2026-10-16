# AirAware AI — Fresh Location-Based Version

## Features
- Type an address, landmark, neighborhood, or city; no city dropdown.
- Resolve the typed place using OpenStreetMap Nominatim.
- Fetch model-based current air-quality estimates and hourly forecast from Open-Meteo.
- View US AQI, European AQI, PM2.5, PM10, NO2, ozone, CO, and SO2 where available.
- Download hourly forecast CSV.
- Automatically append successful lookup snapshots to `data/air_quality_history.csv`.

## Setup (Windows)
```cmd
cd /d E:\AirAwareAI_Fresh
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If you already have a working virtual environment, activate it and run:
```cmd
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Data and limitations
- No OpenAQ API key is required.
- Geocoding uses OpenStreetMap Nominatim; use it respectfully and do not send frequent automated requests.
- Air-quality values come from Open-Meteo and are model-based estimates/forecasts, not guaranteed readings from a local sensor.
- `data/air_quality_history.csv` is a collected API snapshot log. It is not ground-truth measurement data and is not automatically used to train a machine-learning model.
- AQI can vary by country/scale; the category displayed here is based on the US AQI scale.
