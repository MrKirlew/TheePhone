import os
import logging
from services.google_auth import GoogleAuthClient
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

async def call_openweather(location: str):
    logger.info(f"Weather request for: {location}")
    return {"weather": "Not implemented", "location": location}

async def geocode_address(address: str):
    logger.info(f"Geocoding: {address}")
    return {"lat": 0.0, "lng": 0.0, "formatted_address": address}

async def reverse_geocode(lat: float, lng: float):
    logger.info(f"Reverse geocoding: {lat}, {lng}")
    return {"address": f"{lat}, {lng}"}

async def call_google_people_api(access_token: str):
    auth_client = GoogleAuthClient(access_token)
    creds = auth_client.get_authenticated_credentials()
    service = build('people', 'v1', credentials=creds)
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=10,
        personFields='names,emailAddresses').execute()
    connections = results.get('connections', [])
    contacts = []
    for person in connections:
        names = person.get('names', [])
        if names:
            name = names[0].get('displayName')
            emails = person.get('emailAddresses', [])
            email = emails[0].get('value') if emails else 'N/A'
            contacts.append({'name': name, 'email': email})
    return {"contacts": contacts}