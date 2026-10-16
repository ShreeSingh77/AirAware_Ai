from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import time

import pandas as pd
import requests
import streamlit as st

# Fresh AirAware AI: location input -> geocode -> Open-Meteo air-quality forecast.
# No city dropdown and no API key required for Open-Meteo's non-commercial API use.

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
HISTORY_FILE = DATA_DIR / "air_quality_history.csv"

GEOCODING_URL = "https://nominatim.openstreetmap.org/search"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

st.set_page_config(
    page_title="AirAware AI",
    page_icon="🌍",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1150px; padding-top: 2rem; padding-bottom: 3rem;}
    div[data-testid="stMetric"] {
        background: rgba(128,128,128,0.08);
        border: 1px solid rgba(128,128,128,0.18);
        padding: 1rem; border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(ttl=3600, show_spinner=False)
def geocode_location(query: str):
    """Use OpenStreetMap Nominatim to resolve a typed place/address to coordinates."""
    response = requests.get(
        GEOCODING_URL,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        },
        headers={"User-Agent": "AirAwareAIStudentProject/1.0 (location air-quality dashboard)"},
        timeout=25,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    result = results[0]
    return {
        "display_name": result.get("display_name", query),
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
    }

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_air_quality(latitude: float, longitude: float, timezone: str = "auto"):
    response = requests.get(
        AIR_QUALITY_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm10,pm2_5,us_aqi,european_aqi,nitrogen_dioxide,ozone,carbon_monoxide,sulphur_dioxide",
            "hourly": "pm2_5,pm10,us_aqi,european_aqi",
            "timezone": timezone,
            "forecast_days": 2,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def number_or_none(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

def fmt(value, suffix="", decimals=1):
    value = number_or_none(value)
    return f"{value:.{decimals}f}{suffix}" if value is not None else "N/A"

def us_aqi_category(value):
    value = number_or_none(value)
    if value is None:
        return "Unavailable"
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 150:
        return "Unhealthy for Sensitive Groups"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very Unhealthy"
    return "Hazardous"

def save_snapshot(location, payload):
    """Append the current API snapshot to a local CSV for project data collection."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = payload.get("current", {})
    row = {
        "fetched_at_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "location": location["display_name"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "api_time": current.get("time"),
        "pm2_5_ug_m3": current.get("pm2_5"),
        "pm10_ug_m3": current.get("pm10"),
        "us_aqi": current.get("us_aqi"),
        "european_aqi": current.get("european_aqi"),
        "nitrogen_dioxide": current.get("nitrogen_dioxide"),
        "ozone": current.get("ozone"),
        "carbon_monoxide": current.get("carbon_monoxide"),
        "sulphur_dioxide": current.get("sulphur_dioxide"),
        "data_source": "Open-Meteo model-based air-quality API",
    }
    frame = pd.DataFrame([row])
    if HISTORY_FILE.exists():
        frame.to_csv(HISTORY_FILE, mode="a", header=False, index=False)
    else:
        frame.to_csv(HISTORY_FILE, index=False)

st.title("🌍 AirAware AI")
st.subheader("Location-Based Air Quality & Forecast")
st.write(
    "Enter the place, address, landmark, or coordinates for the area you want to check. "
    "The app resolves the location and fetches air-quality estimates for its coordinates."
)

with st.form("location_search", clear_on_submit=False):
    location_query = st.text_input(
        "Enter your location",
        placeholder="Example: BIET Lucknow, Gomti Nagar Lucknow, India",
        help="You can enter an address, landmark, area, city, or coordinates as a place query.",
    )
    submitted = st.form_submit_button("Check Air Quality", type="primary", use_container_width=True)

if submitted:
    query = location_query.strip()
    if not query:
        st.warning("Please enter a location first.")
    else:
        try:
            with st.spinner("Finding the location..."):
                found = geocode_location(query)
            if not found:
                st.error("Location not found. Try a clearer address, landmark, area, or city name.")
            else:
                st.session_state["airaware_location"] = found
                st.session_state.pop("airaware_payload", None)
                with st.spinner("Fetching air-quality data..."):
                    payload = fetch_air_quality(found["latitude"], found["longitude"])
                st.session_state["airaware_payload"] = payload
                try:
                    save_snapshot(found, payload)
                except (OSError, PermissionError) as error:
                    st.warning(f"Data displayed, but local CSV logging failed: {error}")
        except requests.RequestException as error:
            st.error(
                "Could not connect to the location or air-quality service. "
                f"Check your internet connection and try again. Details: {error}"
            )
        except (ValueError, KeyError) as error:
            st.error(f"Could not process the API response: {error}")

location = st.session_state.get("airaware_location")
payload = st.session_state.get("airaware_payload")

if location and payload:
    current = payload.get("current", {})
    st.divider()
    st.header("📍 Results")
    st.caption(location["display_name"])
    st.caption(
        f"Coordinates: {location['latitude']:.5f}, {location['longitude']:.5f} "
        f"· API timestamp: {current.get('time', 'Unavailable')}"
    )

    aqi = number_or_none(current.get("us_aqi"))
    category = us_aqi_category(aqi)
    if aqi is not None:
        if aqi <= 50:
            st.success(f"US AQI category: **{category}**")
        elif aqi <= 100:
            st.info(f"US AQI category: **{category}**")
        elif aqi <= 150:
            st.warning(f"US AQI category: **{category}**")
        else:
            st.error(f"US AQI category: **{category}**")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("US AQI", fmt(current.get("us_aqi"), decimals=0))
    c2.metric("PM2.5", fmt(current.get("pm2_5"), " µg/m³"))
    c3.metric("PM10", fmt(current.get("pm10"), " µg/m³"))
    c4.metric("European AQI", fmt(current.get("european_aqi"), decimals=0))

    with st.expander("More pollutants"):
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("NO₂", fmt(current.get("nitrogen_dioxide"), " µg/m³"))
        p2.metric("Ozone", fmt(current.get("ozone"), " µg/m³"))
        p3.metric("CO", fmt(current.get("carbon_monoxide"), " µg/m³"))
        p4.metric("SO₂", fmt(current.get("sulphur_dioxide"), " µg/m³"))

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if times:
        forecast = pd.DataFrame({
            "Time": pd.to_datetime(times),
            "PM2.5 (µg/m³)": hourly.get("pm2_5", []),
            "PM10 (µg/m³)": hourly.get("pm10", []),
            "US AQI": hourly.get("us_aqi", [None] * len(times)),
        })
        api_time = pd.to_datetime(current.get("time", times[0]))
        forecast = forecast[forecast["Time"] >= api_time].head(24).copy()

        st.header("📈 Next 24 Hours")
        if not forecast.empty:
            chart = forecast.set_index("Time")[["PM2.5 (µg/m³)", "PM10 (µg/m³)"]]
            st.line_chart(chart)
            st.dataframe(forecast, use_container_width=True, hide_index=True)
            csv_bytes = forecast.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download this forecast as CSV",
                data=csv_bytes,
                file_name="airaware_location_forecast.csv",
                mime="text/csv",
            )
        else:
            st.info("Hourly forecast is not available for this response.")

    st.caption(
        "Data source: Open-Meteo Air Quality API. Values are model-based estimates/forecasts "
        "and may differ from nearby official monitoring stations. The location is geocoded "
        "through OpenStreetMap Nominatim; the air-quality grid can represent a nearby area, "
        "not the exact air at your doorstep."
    )

st.divider()
st.subheader("📁 Project Dataset")
st.write(
    "Every successful location lookup appends a snapshot to "
    "`data/air_quality_history.csv`. This is a collected API dataset for project analysis, "
    "not ground-truth sensor data or a separately trained ML dataset."
)

if HISTORY_FILE.exists():
    history = pd.read_csv(HISTORY_FILE)
    st.metric("Saved location snapshots", len(history))
    st.dataframe(history.tail(10), use_container_width=True, hide_index=True)
    st.download_button(
        "Download collected dataset CSV",
        data=HISTORY_FILE.read_bytes(),
        file_name="air_quality_history.csv",
        mime="text/csv",
    )
else:
    st.info("No records yet. Search a location above to create your first dataset row.")

st.divider()
st.caption("AirAware AI | OpenStreetMap geocoding + Open-Meteo Air Quality API")
