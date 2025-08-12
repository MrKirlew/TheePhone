# ADK Mobile Conversational AI App

A mobile conversational AI application built with Flutter (client) and Google Cloud (backend) using the Google ADK framework.

## Features

- **Multi-Agent Architecture**: Intent classification, planning, reflection, memory, perception, and conversation agents
- **Natural Conversation**: Human-like dialogue with varied responses
- **Multimodal Capabilities**: Text, image, and audio support
- **Memory Management**: Short-term session context and long-term user preferences
- **Continuous Learning**: Feedback loop for improving responses
- **Tool Integration**: Weather, location, document retrieval, and custom tools
- **Offline Caching**: Local conversation caching for offline access
- **Push Notifications**: Firebase Cloud Messaging for proactive updates
- **Cost Control**: Budget constraints and usage monitoring
- **RAG Implementation**: Retrieval-Augmented Generation for document search

## Architecture

```
Client (Flutter) ↔ Backend (Cloud Run/Python ADK) ↔ Google Cloud APIs
```

### Backend Agents

1. **IntentAgent**: Classifies user queries into specific intents
2. **PlanningAgent**: Creates step-by-step execution plans
3. **PerceptionAgent**: Handles image understanding
4. **MemoryAgent**: Manages user context and preferences
5. **ConversationAgent**: Generates natural language responses
6. **ReflectionAgent**: Reviews response quality and suggests improvements
7. **OrchestratorAgent**: Coordinates all agents in a defined workflow

### Services

- **RAG Store**: Document indexing and retrieval for enhanced knowledge
- **Embedding Service**: Gemini-based text embeddings
- **Budget Guard**: Cost control and usage monitoring
- **Firestore Services**: Session management and data persistence

## Setup and Deployment

### Prerequisites

- Google Cloud Project with billing enabled
- Flutter development environment
- Google Cloud SDK

### Backend Deployment

1. Enable required APIs in Google Cloud Console
2. Set up Firestore in Native mode
3. Create API keys for Google services
4. Store secrets in Secret Manager
5. Deploy to Cloud Run using the provided cloudbuild.yaml

### Flutter Client Setup

1. Update `pubspec.yaml` with your project dependencies
2. Configure Firebase for push notifications
3. Update the backend URL in `api_client.dart`
4. Build and run the app

## Cost Management

Approximate monthly costs:
- Gemini 2.0 Flash: Well below $20 (500-1000 requests)
- Firestore: Few MB storage (<$5)
- Maps Geocoding: Cached queries (<$5)
- Cloud Run: Autoscaling ($5-10)
- Total: ~$50/month

## Security Features

- OAuth / Firebase Auth for user authentication
- Image validation and content type checking
- Rate limiting per IP address
- CORS policy configuration

## Extending the Application

The modular architecture allows for easy addition of:
- New tool agents for custom APIs
- Enhanced perception capabilities
- Advanced memory management
- Custom intent classification models
- Additional document processing services

## Development Guidelines

- Follow the existing agent pattern for new functionality
- Use Firestore for persistent data storage
- Implement proper error handling and logging
- Maintain the budget guard for cost control
- Test all features thoroughly before deployment

## Future Improvements

- Advanced intent classification with ML models
- Enhanced embedding similarity search
- Multi-turn tool chains with planning and reflection
- Offline caching for all client-side features
- Proactive notifications based on user preferences
