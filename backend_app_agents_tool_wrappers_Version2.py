import aiohttp, json, os
from typing import Optional

# Simple tool functions (you can adapt to ADK tool interface if using tool decorators).
# In ADK, a tool is often a callable with a signature (contextual) or explicit description.

async def call_openweather(owm_api_key: str, location: str) -> str:
    """
    Returns current weather summary for a city/location string.
    """
    # Use geocoding (if lat,lon not provided). For simplicity, let OWM geocode.
    base = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": owm_api_key, "units": "metric"}
    async with aiohttp.ClientSession() as session:
        async with session.get(base, params=params) as resp:
            if resp.status != 200:
                return f"Weather lookup failed ({resp.status})."
            data = await resp.json()
            desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            return f"Weather in {location}: {desc}, {temp}°C."

async def geocode_address(map_api_key: str, address: str) -> str:
    base = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": map_api_key}
    async with aiohttp.ClientSession() as session:
        async with session.get(base, params=params) as resp:
            if resp.status != 200:
                return f"Geocoding failed ({resp.status})."
            data = await resp.json()
            if not data.get("results"):
                return "No geocoding results."
            loc = data["results"][0]["geometry"]["location"]
            return f"Coordinates: {loc['lat']},{loc['lng']}"

async def reverse_geocode(map_api_key: str, lat: float, lng: float) -> str:
    base = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lng}", "key": map_api_key}
    async with aiohttp.ClientSession() as session:
        async with session.get(base, params=params) as resp:
            if resp.status != 200:
                return f"Reverse geocoding failed ({resp.status})."
            data = await resp.json()
            if not data.get("results"):
                return "No reverse geocoding results."
            return data["results"][0]["formatted_address"]