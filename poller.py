import requests
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from database import init_db, insert_reading

load_dotenv()

API_KEY   = os.environ["AIRNOW_API_KEY"]
ZIP_CODE  = "59801"   # Missoula, MT
DISTANCE  = 25        # miles radius
FORMAT    = "application/json"

AIRNOW_URL = "https://www.airnowapi.org/aq/observation/zipCode/current/"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/opt/airquality/logs/poller.log"),
        logging.StreamHandler()
    ]
)

def fetch_aqi():
    params = {
        "format":      FORMAT,
        "zipCode":     ZIP_CODE,
        "distance":    DISTANCE,
        "API_KEY":     API_KEY,
    }
    response = requests.get(AIRNOW_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()

def poll():
    logging.info("Polling AirNow API...")
    try:
        data = fetch_aqi()
        if not data:
            logging.warning("No data returned from AirNow API.")
            return

        for obs in data:
            timestamp  = datetime.utcnow().isoformat()
            location   = obs.get("ReportingArea", "Missoula, MT")
            aqi        = obs.get("AQI")
            category   = obs.get("Category", {}).get("Name", "Unknown")
            pollutant  = obs.get("ParameterName", "Unknown")
            latitude   = obs.get("Latitude")
            longitude  = obs.get("Longitude")

            insert_reading(timestamp, location, aqi, category, pollutant, latitude, longitude)
            logging.info(f"Stored: {location} | {pollutant} | AQI={aqi} | {category}")

    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    os.makedirs("/opt/airquality/logs", exist_ok=True)
    init_db()
    poll()
