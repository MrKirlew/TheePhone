#!/usr/bin/env python3
"""
Test script to verify the KirlewPHone backend is working correctly
"""

import requests
import os
import json

# Backend URL
SERVER_URL = "https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator"

def test_endpoint():
    """Test the endpoint with various payloads"""
    
    print("🔍 Testing KirlewPHone Backend...")
    print(f"URL: {SERVER_URL}")
    print("-" * 50)
    
    # Test 1: Empty POST request
    print("\n📋 Test 1: Empty POST request")
    try:
        response = requests.post(SERVER_URL, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: POST with form data (text command)
    print("\n📋 Test 2: Text command")
    try:
        data = {
            'text_command': 'Hello, this is a test message'
        }
        response = requests.post(SERVER_URL, data=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: POST with multipart form data
    print("\n📋 Test 3: Multipart form data")
    try:
        # Create a dummy audio file
        dummy_audio = b'DUMMY_AUDIO_DATA'
        files = {
            'audio_file': ('test.amr', dummy_audio, 'audio/amr')
        }
        data = {
            'text_command': 'Test with audio file'
        }
        response = requests.post(SERVER_URL, files=files, data=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Check response headers
    print("\n📋 Test 4: Response headers check")
    try:
        response = requests.post(SERVER_URL, data={'text_command': 'test'}, timeout=10)
        print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        print(f"X-AI-Model: {response.headers.get('X-AI-Model', 'Not specified')}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "-" * 50)
    print("✅ Test Summary:")
    print("- If you see 400 errors, the backend is working but expects valid input")
    print("- If you see 404 errors, the function is not deployed")
    print("- If you see 500 errors, there's a backend issue")
    print("- If you see 200 with a response, everything is working!")

if __name__ == "__main__":
    test_endpoint()
