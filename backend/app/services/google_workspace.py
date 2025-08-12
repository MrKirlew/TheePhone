from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import io

class GoogleWorkspaceService:
    """Service for interacting with Google Workspace APIs"""
    
    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self._services = {}
    
    def _get_service(self, service_name: str, version: str):
        """Get or create a Google API service"""
        key = f"{service_name}_{version}"
        if key not in self._services:
            self._services[key] = build(service_name, version, credentials=self.credentials)
        return self._services[key]
    
    # Google Docs
    def get_doc_content(self, doc_id: str) -> str:
        """Get content from a Google Doc"""
        try:
            service = self._get_service('docs', 'v1')
            doc = service.documents().get(documentId=doc_id).execute()
            
            # Extract text from document
            content = ""
            for element in doc.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for paragraph_element in element['paragraph'].get('elements', []):
                        if 'textRun' in paragraph_element:
                            content += paragraph_element['textRun'].get('content', '')
            return content
        except Exception as e:
            return f"Error reading document: {str(e)}"
    
    # Google Sheets
    def get_sheet_values(self, spreadsheet_id: str, range_name: str = "A1:Z1000") -> List[List]:
        """Get values from a Google Sheet"""
        try:
            service = self._get_service('sheets', 'v4')
            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except Exception as e:
            return [[f"Error reading sheet: {str(e)}"]]
    
    # Google Drive
    def list_files(self, query: str = None) -> List[Dict]:
        """List files in Google Drive"""
        try:
            service = self._get_service('drive', 'v3')
            results = service.files().list(
                q=query,
                pageSize=10,
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            return results.get('files', [])
        except Exception as e:
            return [{'name': f"Error listing files: {str(e)}", 'id': ''}]
    
    def get_file_content(self, file_id: str) -> str:
        """Get content of a Drive file"""
        try:
            service = self._get_service('drive', 'v3')
            request = service.files().get_media(fileId=file_id)
            # For text files, we could download content
            # This is a simplified implementation
            return f"File content for {file_id} would be retrieved here"
        except Exception as e:
            return f"Error getting file content: {str(e)}"
    
    # Gmail
    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email using Gmail"""
        try:
            service = self._get_service('gmail', 'v1')
            
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_string().encode()).decode()
            
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return f"Email sent successfully. Message ID: {result['id']}"
        except Exception as e:
            return f"Error sending email: {str(e)}"
    
    def list_emails(self, max_results: int = 5) -> List[Dict]:
        """List recent emails"""
        try:
            service = self._get_service('gmail', 'v1')
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q='in:inbox'
            ).execute()
            
            messages = results.get('messages', [])
            email_data = []
            
            for message in messages:
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id']
                ).execute()
                
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                
                email_data.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'snippet': msg.get('snippet', '')[:100] + '...'
                })
            
            return email_data
        except Exception as e:
            return [{'subject': f"Error listing emails: {str(e)}", 'sender': '', 'snippet': ''}]
    
    # Calendar
    def list_upcoming_events(self, max_results: int = 10) -> List[Dict]:
        """List upcoming calendar events"""
        try:
            service = self._get_service('calendar', 'v3')
            import datetime
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            event_data = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                event_data.append({
                    'summary': event.get('summary', 'No Title'),
                    'start': start,
                    'id': event['id']
                })
            
            return event_data
        except Exception as e:
            return [{'summary': f"Error listing events: {str(e)}", 'start': '', 'id': ''}]
    
    def create_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> str:
        """Create a calendar event"""
        try:
            service = self._get_service('calendar', 'v3')
            
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
            }
            
            event = service.events().insert(calendarId='primary', body=event).execute()
            return f"Event created: {event.get('htmlLink')}"
        except Exception as e:
            return f"Error creating event: {str(e)}"
    
    # Contacts and People
    def list_contacts(self, max_results: int = 10) -> List[Dict]:
        """List Google Contacts"""
        try:
            service = self._get_service('people', 'v1')
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=max_results,
                personFields='names,emailAddresses,phoneNumbers'
            ).execute()
            
            connections = results.get('connections', [])
            contacts = []
            
            for person in connections:
                names = person.get('names', [])
                name = names[0].get('displayName', 'No Name') if names else 'No Name'
                
                emails = person.get('emailAddresses', [])
                email = emails[0].get('value', 'No Email') if emails else 'No Email'
                
                contacts.append({
                    'name': name,
                    'email': email,
                    'resourceName': person.get('resourceName', '')
                })
            
            return contacts
        except Exception as e:
            return [{'name': f"Error listing contacts: {str(e)}", 'email': '', 'resourceName': ''}]
