"""
Tool: Weather
Fetches current weather for any city using the free Open-Meteo API.
No API key is required — it geocodes the city name via the Open-Meteo
geocoding endpoint, then pulls the current conditions.
"""

import httpx
from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """
    Get the current weather for a given city.
    Returns temperature (°C), wind speed, and a human-readable condition.

    Args:
        city: Name of the city, e.g. 'London' or 'New York'.
    """
    try:
        # Step 1: Geocode the city name → lat/lon
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = httpx.get(geo_url, params={"name": city, "count": 1}, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"Could not find location: '{city}'. Please try a different city name."

        result = geo_data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        display_name = result.get("name", city)

        # Step 2: Fetch current weather at those coordinates
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_resp = httpx.get(
            weather_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "relativehumidity_2m",  # grab humidity too
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

        cw = weather_data["current_weather"]
        temp = cw["temperature"]
        wind = cw["windspeed"]
        code = cw["weathercode"]

        # WMO weather codes → readable descriptions
        condition = _wmo_to_description(code)

        return (
            f"Current weather in {display_name}:\n"
            f"  🌡️  Temperature : {temp}°C\n"
            f"  💨  Wind speed  : {wind} km/h\n"
            f"  🌤️  Condition   : {condition}"
        )

    except httpx.HTTPError as e:
        return f"Weather API error: {e}"
    except Exception as e:
        return f"Unexpected error fetching weather: {e}"


def _wmo_to_description(code: int) -> str:
    """Convert a WMO weather interpretation code to a human-readable string."""
    mapping = {
        0: "Clear sky",
        1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        77: "Snow grains",
        80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, f"Unknown condition (code {code})")