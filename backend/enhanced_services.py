# enhanced_services.py - Additional Google Cloud API integrations for KirlewPHone

import logging
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
import requests
import pytz

logger = logging.getLogger(__name__)

# Google Cloud imports
try:
    from google.cloud import vision
    from googleapiclient.discovery import build
    import googlemaps
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Required libraries not available: {e}")
    SERVICES_AVAILABLE = False

class EnhancedGoogleServices:
    """Enhanced Google Services integration for KirlewPHone AI Agent"""
    
    def __init__(self, credentials=None, api_key=None):
        self.credentials = credentials
        self.api_key = api_key or self._get_api_key()
        self._init_clients()
    
    def _get_api_key(self):
        """Get API key from environment or Secret Manager"""
        import os
        return os.environ.get('GOOGLE_API_KEY', '')
    
    def _init_clients(self):
        """Initialize all service clients"""
        try:
            # Vision API client
            self.vision_client = vision.ImageAnnotatorClient() if SERVICES_AVAILABLE else None
            
            # Maps client (requires API key)
            self.maps_client = googlemaps.Client(key=self.api_key) if self.api_key else None
            
            # People API client (requires OAuth credentials)
            if self.credentials:
                self.people_service = build('people', 'v1', credentials=self.credentials)
            else:
                self.people_service = None
                
            logger.info("Enhanced services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced services: {e}")
    
    # Weather API Integration
    def fetch_weather_data(self, location: str = None, lat: float = None, lon: float = None) -> Dict:
        """
        Fetch weather data using OpenWeatherMap or Google's Weather API
        Note: Google doesn't have a public Weather API, so we'll use OpenWeatherMap
        """
        try:
            # For production, use environment variable for API key
            weather_api_key = "your_openweather_api_key"
            base_url = "https://api.openweathermap.org/data/2.5/weather"
            
            params = {
                'appid': weather_api_key,
                'units': 'metric'
            }
            
            if location:
                params['q'] = location
            elif lat and lon:
                params['lat'] = lat
                params['lon'] = lon
            else:
                return {"error": "No location provided"}
            
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "location": data.get('name', 'Unknown'),
                    "temperature": data['main']['temp'],
                    "feels_like": data['main']['feels_like'],
                    "description": data['weather'][0]['description'],
                    "humidity": data['main']['humidity'],
                    "wind_speed": data['wind']['speed'],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": f"Weather API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return {"error": str(e)}
    
    # Cloud Vision API Integration
    def analyze_image(self, image_content: bytes) -> Dict:
        """Analyze image using Cloud Vision API"""
        if not self.vision_client:
            return {"error": "Vision API client not initialized"}
        
        try:
            image = vision.Image(content=image_content)
            
            # Perform multiple detection types
            response = self.vision_client.annotate_image({
                'image': image,
                'features': [
                    {'type_': vision.Feature.Type.TEXT_DETECTION},
                    {'type_': vision.Feature.Type.LABEL_DETECTION},
                    {'type_': vision.Feature.Type.FACE_DETECTION},
                    {'type_': vision.Feature.Type.LANDMARK_DETECTION},
                    {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
                    {'type_': vision.Feature.Type.DOCUMENT_TEXT_DETECTION}
                ]
            })
            
            results = {
                "text": self._extract_text(response),
                "labels": self._extract_labels(response),
                "faces": len(response.face_annotations),
                "landmarks": self._extract_landmarks(response),
                "objects": self._extract_objects(response),
                "document_text": self._extract_document_text(response)
            }
            
            logger.info(f"Vision API analysis complete: {len(results['labels'])} labels found")
            return results
            
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return {"error": str(e)}
    
    def _extract_text(self, response):
        """Extract text from vision response"""
        texts = response.text_annotations
        return texts[0].description if texts else ""
    
    def _extract_labels(self, response):
        """Extract labels from vision response"""
        return [{"description": label.description, "score": label.score} 
                for label in response.label_annotations]
    
    def _extract_landmarks(self, response):
        """Extract landmarks from vision response"""
        return [{"description": landmark.description, "score": landmark.score}
                for landmark in response.landmark_annotations]
    
    def _extract_objects(self, response):
        """Extract objects from vision response"""
        return [{"name": obj.name, "score": obj.score}
                for obj in response.localized_object_annotations]
    
    def _extract_document_text(self, response):
        """Extract structured document text"""
        if response.full_text_annotation:
            return response.full_text_annotation.text
        return ""
    
    # Geolocation API Integration
    def get_location_from_ip(self) -> Dict:
        """Get approximate location from IP address"""
        try:
            response = requests.get('https://ipapi.co/json/')
            if response.status_code == 200:
                data = response.json()
                return {
                    "city": data.get('city'),
                    "region": data.get('region'),
                    "country": data.get('country_name'),
                    "latitude": data.get('latitude'),
                    "longitude": data.get('longitude'),
                    "timezone": data.get('timezone')
                }
            return {"error": "Failed to get location"}
        except Exception as e:
            logger.error(f"Geolocation error: {e}")
            return {"error": str(e)}
    
    # Time Zone API Integration
    def get_timezone_info(self, lat: float, lon: float, timestamp: int = None) -> Dict:
        """Get timezone information for coordinates"""
        if not self.api_key:
            return {"error": "API key required for timezone API"}
        
        try:
            url = "https://maps.googleapis.com/maps/api/timezone/json"
            params = {
                'location': f'{lat},{lon}',
                'timestamp': timestamp or int(datetime.now().timestamp()),
                'key': self.api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return {"error": f"Timezone API error: {response.status_code}"}
            
        except Exception as e:
            logger.error(f"Timezone API error: {e}")
            return {"error": str(e)}
    
    # People API Integration
    def get_frequent_contacts(self, max_results: int = 10) -> List[Dict]:
        """Get frequently contacted people"""
        if not self.people_service:
            return []
        
        try:
            results = self.people_service.people().connections().list(
                resourceName='people/me',
                pageSize=max_results,
                personFields='names,emailAddresses,phoneNumbers,photos',
                sortOrder='LAST_MODIFIED_DESCENDING'
            ).execute()
            
            connections = results.get('connections', [])
            contacts = []
            
            for person in connections:
                contact = {
                    'resourceName': person.get('resourceName'),
                    'names': person.get('names', []),
                    'emails': person.get('emailAddresses', []),
                    'phones': person.get('phoneNumbers', []),
                    'photos': person.get('photos', [])
                }
                contacts.append(contact)
            
            logger.info(f"Fetched {len(contacts)} contacts")
            return contacts
            
        except Exception as e:
            logger.error(f"People API error: {e}")
            return []
    
    # Maps/Places API Integration
    def search_nearby_places(self, location: str, place_type: str = None, radius: int = 5000) -> List[Dict]:
        """Search for nearby places"""
        if not self.maps_client:
            return []
        
        try:
            # Geocode the location first
            geocode_result = self.maps_client.geocode(location)
            if not geocode_result:
                return []
            
            lat_lng = geocode_result[0]['geometry']['location']
            
            # Search nearby places
            places_result = self.maps_client.places_nearby(
                location=lat_lng,
                radius=radius,
                type=place_type
            )
            
            places = []
            for place in places_result.get('results', []):
                places.append({
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'rating': place.get('rating'),
                    'types': place.get('types', []),
                    'place_id': place.get('place_id')
                })
            
            return places
            
        except Exception as e:
            logger.error(f"Places API error: {e}")
            return []
    
    # Pollen API Integration (when available)
    def get_pollen_data(self, lat: float, lon: float) -> Dict:
        """Get pollen count data for location"""
        # Note: Google's Pollen API is in preview. This is a placeholder
        try:
            # When API is available, implement like this:
            # url = f"https://pollen.googleapis.com/v1/forecast:lookup"
            # params = {'location': {'latitude': lat, 'longitude': lon}, 'key': self.api_key}
            
            # For now, return mock data
            return {
                "location": {"lat": lat, "lon": lon},
                "pollen_levels": {
                    "tree": "moderate",
                    "grass": "low", 
                    "weed": "high"
                },
                "overall": "moderate",
                "forecast_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Pollen API error: {e}")
            return {"error": str(e)}
    
    # Integrated Context Builder
    def build_enhanced_context(self, location: str = None) -> Dict:
        """Build comprehensive context using all available APIs"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "location": {},
            "weather": {},
            "timezone": {},
            "contacts": [],
            "nearby_places": []
        }
        
        # Get location
        if not location:
            location_data = self.get_location_from_ip()
            if not location_data.get('error'):
                context['location'] = location_data
                lat, lon = location_data['latitude'], location_data['longitude']
                
                # Get weather
                context['weather'] = self.fetch_weather_data(lat=lat, lon=lon)
                
                # Get timezone
                context['timezone'] = self.get_timezone_info(lat, lon)
                
                # Get pollen data
                context['pollen'] = self.get_pollen_data(lat, lon)
                
                # Get nearby places
                if location_data.get('city'):
                    context['nearby_places'] = self.search_nearby_places(
                        location_data['city'], 
                        place_type='restaurant'
                    )[:5]
        
        # Get contacts
        context['contacts'] = self.get_frequent_contacts(5)
        
        return context


# Utility function to integrate with main.py
def enhance_user_context(base_context: Dict, credentials=None, api_key=None) -> Dict:
    """Enhance the base context with additional API data"""
    try:
        services = EnhancedGoogleServices(credentials, api_key)
        enhanced_context = services.build_enhanced_context()
        
        # Merge with base context
        base_context.update(enhanced_context)
        
        return base_context
        
    except Exception as e:
        logger.error(f"Failed to enhance context: {e}")
        return base_context