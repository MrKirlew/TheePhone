#!/usr/bin/env python3
"""
Test script to verify conversational improvements in KirlewPHone AI Agent
"""

import requests
import json
import sys

# Backend URL
SERVER_URL = "https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator"

def test_conversation(query):
    """Test a conversational query"""
    print(f"\n{'='*60}")
    print(f"Testing: '{query}'")
    print('='*60)
    
    try:
        # Send request
        response = requests.post(
            SERVER_URL,
            data={
                'text_command': query,
                'auth_code': 'test_auth',
                'id_token': 'test_token'
            },
            timeout=30
        )
        
        # Check response
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                response_text = response.headers.get('X-Response-Text', '[Audio response]')
                print(f"✓ Success (Audio Response)")
                print(f"Response: {response_text}")
            else:
                # JSON response
                data = response.json()
                print(f"✓ Success (Text Response)")
                print(f"Response: {data.get('response', 'No response text')}")
                
                if 'intent_reasoning' in data:
                    print(f"Intent: {data['intent_reasoning']}")
        else:
            print(f"✗ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    """Run conversation tests"""
    print("\nKirlewPHone Conversation Test Suite")
    print("Testing natural conversation capabilities...")
    
    # Test cases covering different conversation types
    test_cases = [
        # Greetings
        "Hello",
        "Hi there!",
        "Good morning",
        "How are you?",
        
        # Calendar queries
        "What's on my calendar today?",
        "Do I have any meetings this afternoon?",
        "Check my schedule for tomorrow",
        
        # Email queries
        "Do I have any new emails?",
        "Check my inbox",
        "Any urgent messages from my manager?",
        
        # Document queries
        "Find my budget spreadsheet",
        "What documents did I work on yesterday?",
        "Show me recent files",
        
        # Mixed/Complex queries
        "What's my schedule like today and do I have any important emails?",
        "I need to prepare for my meetings, what's coming up?",
        
        # Capability questions
        "What can you help me with?",
        "What are you capable of?"
    ]
    
    # Run tests
    for query in test_cases:
        test_conversation(query)
        
    print(f"\n{'='*60}")
    print("Test suite completed!")
    print("Check the responses above to verify:")
    print("1. Greetings are handled naturally")
    print("2. Calendar/email/doc queries get specific responses")
    print("3. Responses are conversational, not robotic")
    print("4. No 'Playing AI response' messages")
    print('='*60)

if __name__ == "__main__":
    main()