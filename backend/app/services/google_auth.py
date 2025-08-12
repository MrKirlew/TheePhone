from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials

class GoogleAuthClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def get_authenticated_credentials(self) -> Credentials:
        return OAuth2Credentials(token=self.access_token)

    def get_authenticated_request(self):
        creds = self.get_authenticated_credentials()
        return Request(creds)
