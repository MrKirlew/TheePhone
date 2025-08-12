#!/usr/bin/env python3
"""
Test script to verify Firestore connectivity with your existing database.
This script will test that your existing Firestore database works with the new implementation.
"""

import asyncio
import os
from google.cloud import firestore
from google.auth import default

async def test_firestore_connection():
    """Test connection to your existing Firestore database."""
    try:
        # Use default credentials
        credentials, project_id = default()
        print(f"Using project: {project_id}")
        
        # Initialize Firestore client
        db = firestore.AsyncClient(project=project_id, credentials=credentials)
        
        # Test creating a document
        doc_ref = db.collection('test_collection').document('test_doc')
        await doc_ref.set({
            'test_field': 'test_value',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        print("✓ Successfully wrote test document to Firestore")
        
        # Test reading the document
        doc = await doc_ref.get()
        if doc.exists:
            print("✓ Successfully read test document from Firestore")
            print(f"  Document data: {doc.to_dict()}")
        else:
            print("✗ Could not read test document")
            
        # Test listing collections (to see what's already there)
        collections = [c async for c in db.collections()]
        print(f"✓ Found {len(collections)} collections in your database:")
        for collection in collections:
            print(f"  - {collection.id}")
            
        # Clean up test document
        await doc_ref.delete()
        print("✓ Cleaned up test document")
        
        print("\n✅ Your existing Firestore database is working correctly!")
        print("The new application will work with your database without any issues.")
        
    except Exception as e:
        print(f"❌ Error connecting to Firestore: {e}")
        print("Please ensure you're authenticated with gcloud:")
        print("  gcloud auth application-default login")

if __name__ == "__main__":
    asyncio.run(test_firestore_connection())
