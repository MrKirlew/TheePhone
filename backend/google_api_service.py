"""
Google API Service Manager
Handles authenticated access to Google APIs using auth_code and id_token
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

logger = logging.getLogger(__name__)

class GoogleAPIService:
    """Service for accessing Google APIs on behalf of users"""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        """Initialize Google API service"""
        self.client_id = client_id or os.environ.get('GOOGLE_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('GOOGLE_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth2 credentials not configured")
        
        # OAuth2 scopes
        self.scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        
        # Cache for credentials
        self._credentials_cache = {}
        
        logger.info("Google API service initialized")
    
    def get_credentials_from_auth_code(self, auth_code: str) -> Credentials:
        """Exchange auth code for credentials"""
        try:
            # Create OAuth2 flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                    }
                },
                scopes=self.scopes
            )
            
            # Exchange auth code for tokens
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            
            logger.info("Successfully exchanged auth code for credentials")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to exchange auth code: {e}")
            raise
    
    def get_calendar_service(self, auth_code: str):
        """Get authenticated Calendar service"""
        credentials = self.get_credentials_from_auth_code(auth_code)
        return build('calendar', 'v3', credentials=credentials)
    
    def get_gmail_service(self, auth_code: str):
        """Get authenticated Gmail service"""
        credentials = self.get_credentials_from_auth_code(auth_code)
        return build('gmail', 'v1', credentials=credentials)
    
    def get_drive_service(self, auth_code: str):
        """Get authenticated Drive service"""
        credentials = self.get_credentials_from_auth_code(auth_code)
        return build('drive', 'v3', credentials=credentials)
    
    async def get_calendar_events(
        self, 
        auth_code: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get calendar events for the user"""
        try:
            service = self.get_calendar_service(auth_code)
            
            # Default to next 7 days if not specified
            if not time_min:
                time_min = datetime.utcnow()
            if not time_max:
                time_max = time_min + timedelta(days=7)
            
            # Format times for API
            time_min_str = time_min.isoformat() + 'Z'
            time_max_str = time_max.isoformat() + 'Z'
            
            # Get events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events
            processed_events = []
            for event in events:
                processed_events.append({
                    'summary': event.get('summary', 'No title'),
                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                    'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                    'attendees': [att.get('email') for att in event.get('attendees', [])]
                })
            
            logger.info(f"Retrieved {len(processed_events)} calendar events")
            return processed_events
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            raise
    
    async def get_gmail_messages(
        self,
        auth_code: str,
        query: str = 'is:unread',
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get Gmail messages for the user"""
        try:
            service = self.get_gmail_service(auth_code)
            
            # List messages
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get message details
            processed_messages = []
            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                # Extract headers
                headers = msg_data['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Extract body
                body = self._extract_email_body(msg_data['payload'])
                
                processed_messages.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'snippet': msg_data.get('snippet', ''),
                    'body': body[:500] if body else '',  # Limit body length
                    'is_unread': 'UNREAD' in msg_data.get('labelIds', [])
                })
            
            logger.info(f"Retrieved {len(processed_messages)} Gmail messages")
            return processed_messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting Gmail messages: {e}")
            raise
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = self._decode_base64(data)
                    break
        elif payload['body'].get('data'):
            body = self._decode_base64(payload['body']['data'])
        
        return body
    
    def _decode_base64(self, data: str) -> str:
        """Decode base64 data"""
        import base64
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    async def get_drive_files(
        self,
        auth_code: str,
        query: str = "mimeType != 'application/vnd.google-apps.folder'",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get Google Drive files for the user"""
        try:
            service = self.get_drive_service(auth_code)
            
            # List files
            results = service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            # Process files
            processed_files = []
            for file in files:
                processed_files.append({
                    'id': file['id'],
                    'name': file['name'],
                    'mimeType': file['mimeType'],
                    'modifiedTime': file.get('modifiedTime', ''),
                    'size': file.get('size', 0),
                    'webViewLink': file.get('webViewLink', '')
                })
            
            logger.info(f"Retrieved {len(processed_files)} Drive files")
            return processed_files
            
        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting Drive files: {e}")
            raise
    
    async def search_emails_by_topic(self, auth_code: str, topic: str) -> List[Dict[str, Any]]:
        """Search emails related to a specific topic"""
        query = f'subject:{topic} OR from:{topic} OR to:{topic}'
        return await self.get_gmail_messages(auth_code, query=query)
    
    async def get_today_events(self, auth_code: str) -> List[Dict[str, Any]]:
        """Get today's calendar events"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        return await self.get_calendar_events(auth_code, time_min=today_start, time_max=today_end)
    
    async def get_upcoming_meetings(self, auth_code: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming meetings within specified hours"""
        time_min = datetime.utcnow()
        time_max = time_min + timedelta(hours=hours)
        events = await self.get_calendar_events(auth_code, time_min=time_min, time_max=time_max)
        
        # Filter for meetings (events with attendees)
        meetings = [e for e in events if e.get('attendees')]
        return meetings
    
    async def get_recent_documents(self, auth_code: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recently modified documents"""
        date_str = (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'
        query = f"modifiedTime > '{date_str}' and (mimeType contains 'document' or mimeType contains 'spreadsheet' or mimeType contains 'presentation')"
        return await self.get_drive_files(auth_code, query=query)
    
    def format_events_for_gemini(self, events: List[Dict[str, Any]]) -> str:
        """Format calendar events for Gemini processing"""
        if not events:
            return "No events found."
        
        formatted = "Calendar Events:\n"
        for event in events:
            formatted += f"\n- {event['summary']}"
            if event.get('start'):
                formatted += f" at {event['start']}"
            if event.get('location'):
                formatted += f" in {event['location']}"
            if event.get('attendees'):
                formatted += f" with {len(event['attendees'])} attendees"
        
        return formatted
    
    def format_emails_for_gemini(self, emails: List[Dict[str, Any]]) -> str:
        """Format emails for Gemini processing"""
        if not emails:
            return "No emails found."
        
        formatted = "Email Messages:\n"
        for email in emails:
            formatted += f"\n- From: {email['sender']}"
            formatted += f"\n  Subject: {email['subject']}"
            formatted += f"\n  Preview: {email['snippet'][:100]}..."
            if email['is_unread']:
                formatted += " (UNREAD)"
        
        return formatted
    
    def format_files_for_gemini(self, files: List[Dict[str, Any]]) -> str:
        """Format files for Gemini processing"""
        if not files:
            return "No files found."
        
        formatted = "Drive Files:\n"
        for file in files:
            formatted += f"\n- {file['name']} ({file['mimeType'].split('.')[-1]})"
            if file.get('modifiedTime'):
                formatted += f" modified {file['modifiedTime']}"
        
        return formatted