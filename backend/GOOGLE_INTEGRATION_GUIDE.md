# Google API Integration Guide

Your Cloud Function now properly uses the `auth_code` and `id_token` from your mobile app to access Google APIs on behalf of users and feed that data to Gemini for intelligent responses.

## How It Works

### 1. Authentication Flow
```
Mobile App → Cloud Function → Google APIs → Gemini → Response
     ↓              ↑              ↓          ↓
  auth_code    Exchange for    Real Data   Natural
  id_token     Credentials                Language
```

### 2. Example Interactions

#### Calendar Queries
**User says:** "What's on my calendar today?"

**Flow:**
1. Cloud Function receives auth_code and id_token
2. Intent detector identifies: `calendar: ["today_events"]`
3. Exchanges auth_code for Google credentials
4. Calls Google Calendar API for today's events
5. Feeds calendar data to Gemini
6. Gemini responds: "You have 3 meetings today: Team standup at 9 AM, Client call at 2 PM, and Project review at 4 PM."

#### Email Queries
**User says:** "Do I have any unread emails from John?"

**Flow:**
1. Intent detector identifies: `email: ["emails_from_sender"]`, `sender: "john"`
2. Calls Gmail API with query: `from:john is:unread`
3. Gemini responds with specific email details

#### Drive Queries
**User says:** "Show me recent documents"

**Flow:**
1. Intent detector identifies: `drive: ["recent_documents"]`
2. Calls Google Drive API for recently modified files
3. Gemini responds with file names and modification dates

## Key Components

### 1. GoogleAPIService (`google_api_service.py`)
- Exchanges auth_code for OAuth2 credentials
- Provides authenticated access to Calendar, Gmail, Drive APIs
- Formats data for Gemini consumption

### 2. IntentDetector (`intent_detector.py`)
- Uses Gemini to intelligently detect user intents
- Maps natural language to specific API actions
- Extracts parameters like time frames, search terms

### 3. MultimodalHandler (`multimodal_handler.py`)
- Orchestrates the complete flow
- Fetches Google data based on detected intent
- Augments user input with real data before sending to Gemini

## Configuration Required

### Environment Variables
```bash
# In Cloud Function environment
GOOGLE_CLIENT_ID="your-oauth2-client-id"
GOOGLE_CLIENT_SECRET="your-oauth2-client-secret"
GEMINI_API_KEY="your-gemini-api-key"
```

### Mobile App Configuration
Make sure your Android app is configured with the correct OAuth2 scopes:
```kotlin
val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
    .requestScopes(Scope("https://www.googleapis.com/auth/calendar.readonly"))
    .requestScopes(Scope("https://www.googleapis.com/auth/gmail.readonly"))
    .requestScopes(Scope("https://www.googleapis.com/auth/drive.readonly"))
    .requestScopes(Scope("https://www.googleapis.com/auth/documents.readonly"))
    .requestScopes(Scope("https://www.googleapis.com/auth/spreadsheets.readonly"))
    .requestServerAuthCode(WEB_CLIENT_ID)  // This is crucial!
    .requestIdToken(WEB_CLIENT_ID)
    .requestEmail()
    .build()
```

## Supported Queries

### Calendar
- "What's on my calendar today?"
- "Do I have any meetings tomorrow?"
- "What's my schedule this week?"
- "When is my next appointment?"
- "Am I free at 3 PM?"

### Email  
- "Check my unread emails"
- "Any emails from Sarah?"
- "Show me recent messages"
- "Do I have any important emails?"

### Drive
- "Find my recent documents"
- "Show me files modified this week"
- "List my Google Docs"
- "Find presentation files"

## Error Handling

The system gracefully handles:
- Invalid auth codes
- API rate limits
- Missing permissions
- Network timeouts
- Malformed requests

## Security Features

1. **Token Validation**: id_token is validated for authenticity
2. **Scope Restriction**: Only accesses data with granted permissions
3. **Data Minimization**: Only fetches relevant data based on query
4. **Audit Logging**: All API calls are logged for security

## Testing

You can test the integration by:

1. **Deploy the updated Cloud Function**
2. **Send a request from your mobile app with:**
   ```
   auth_code: [valid server auth code]
   id_token: [valid id token]
   voice_command: "What's on my calendar today?"
   ```
3. **Check logs for:**
   - Intent detection results
   - Google API calls
   - Data retrieval success
   - Gemini response generation

## Example Log Output

```
Intent detected: User wants to check today's calendar events
Executing calendar actions: ['today_events']
Retrieved 3 calendar events
Gemini response generated for session: abc123, model: gemini-pro
```

## Advanced Features

### Smart Context Awareness
Gemini can now provide contextual responses like:
- "You have a conflict - the client call overlaps with your team meeting"
- "Based on your recent emails, the project deadline has been moved to Friday"
- "I see you have the Johnson presentation in your Drive, want me to summarize it?"

### Multi-API Integration
Single queries can trigger multiple API calls:
- "Prepare me for my 2 PM meeting" → Calendar + Drive + Email data
- "What do I need to do today?" → Calendar events + unread emails + recent files

Your Cloud Function is now a powerful multimodal agent that can act on your behalf across all your Google services!