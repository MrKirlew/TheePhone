## Fix for KirlewPHone 404 Error

### Problem Summary
The app is getting a 404 error because:
1. The MainActivity was using an old placeholder URL instead of the correct Cloud Functions endpoint
2. Authentication tokens (auth_code and id_token) were hardcoded as placeholders
3. The app wasn't properly extracting the server auth code from Google Sign-In

### Changes Made

1. **Fixed the SERVER_URL** in MainActivity.kt:
   - Changed from: `https://us-central1-your-project-id.cloudfunctions.net/processCommand`
   - Changed to: `https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator`

2. **Created ApiHelper.kt** to properly handle:
   - Google Sign-In configuration with server auth code request
   - Proper authentication token extraction and usage
   - Better error handling and logging
   - Support for both audio and text commands

### How to Apply the Fix

1. The SERVER_URL in MainActivity.kt has already been updated.

2. Add the ApiHelper.kt file to your project (already created).

3. Update MainActivity to use ApiHelper for authentication:

```kotlin
// In MainActivity.kt, update the initGoogleSignIn() method:
private fun initGoogleSignIn() {
    // Use the helper to get properly configured sign-in options
    val gso = ApiHelper.getSignInOptions()
    googleSignInClient = GoogleSignIn.getClient(this, gso)
    
    // Check if already signed in
    val account = GoogleSignIn.getLastSignedInAccount(this)
    updateUI(account != null)
}

// Update sendAudioCommand() method:
private fun sendAudioCommand() {
    val account = GoogleSignIn.getLastSignedInAccount(this)
    
    ApiHelper.sendAudioCommand(audioFile, account) { success, response ->
        runOnUiThread {
            if (success) {
                responseText.text = response
                ttsService.speak(response)
                Log.d(TAG, "Audio processed successfully: $response")
            } else {
                responseText.text = "Error: $response"
                Log.e(TAG, "Server error: $response")
            }
        }
    }
}
```

4. To test if the endpoint is working:
```kotlin
// Add this test function to MainActivity
private fun testApiEndpoint() {
    ApiHelper.testEndpoint { success, response ->
        runOnUiThread {
            Toast.makeText(this, 
                if (success) "API is working! $response" 
                else "API error: $response", 
                Toast.LENGTH_LONG
            ).show()
        }
    }
}
```

### Important Notes

1. **The Cloud Function IS deployed and working** - we tested it and got a 400 response (not 404), which means it exists but expects proper form data.

2. **Authentication is important** - The backend expects auth_code and id_token from Google Sign-In. Make sure users sign in first.

3. **Audio format** - The app records in AMR format and the backend expects this format.

### Testing Steps

1. Build and run the app
2. Sign in with Google first (important!)
3. Try speaking a command
4. Check the logcat for detailed error messages

### If You Still Get Errors

Run this command to check the function status:
```bash
gcloud functions describe multimodal-agent-orchestrator --region=us-central1
```

The function should be:
- Name: multimodal-agent-orchestrator
- Region: us-central1
- Project: twothreeatefi
- State: ACTIVE
