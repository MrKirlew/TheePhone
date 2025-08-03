package com.kirlewai.agent

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.IOException
import android.util.Log
import android.widget.Toast
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInOptions

/**
 * Helper object to fix the 404 error by properly handling authentication
 * and using the correct API endpoint
 */
object ApiHelper {
    private const val TAG = "ApiHelper"
    private const val SERVER_URL = "https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator"
    private const val WEB_CLIENT_ID = "843267258954-mc04n5od104s75to3umjl46rva3p0r0s.apps.googleusercontent.com"
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .build()
    
    /**
     * Get GoogleSignInOptions configured for server auth code
     */
    fun getSignInOptions(): GoogleSignInOptions {
        return AuthCompatHelper.getSignInOptions()
    }
    
    /**
     * Send audio command to the server with proper authentication
     */
    fun sendAudioCommand(
        audioFile: File,
        googleAccount: GoogleSignInAccount?,
        callback: (success: Boolean, response: String) -> Unit
    ) {
        if (!audioFile.exists()) {
            callback(false, "No audio file to send")
            return
        }
        
        val authCode = googleAccount?.serverAuthCode
        val idToken = googleAccount?.idToken
        
        if (authCode == null || idToken == null) {
            Log.w(TAG, "Missing authentication. Auth code: ${authCode != null}, ID token: ${idToken != null}")
            // Continue anyway for testing, but warn the user
        }
        
        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("audio_file", "recording.amr",
                audioFile.asRequestBody("audio/amr".toMediaType()))
            .apply {
                // Add auth tokens if available
                authCode?.let { addFormDataPart("auth_code", it) }
                idToken?.let { addFormDataPart("id_token", it) }
            }
            .build()
        
        val request = Request.Builder()
            .url(SERVER_URL)
            .post(requestBody)
            .build()
        
        Log.d(TAG, "Sending audio to: $SERVER_URL")
        Log.d(TAG, "Auth present: ${authCode != null}")
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Network failure: ${e.message}", e)
                callback(false, "Network error: ${e.message}")
            }
            
            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                Log.d(TAG, "Response code: ${response.code}")
                Log.d(TAG, "Response body: $responseBody")
                
                if (response.isSuccessful) {
                    // Check if response is audio (MP3) or JSON
                    val contentType = response.header("Content-Type")
                    if (contentType?.contains("audio") == true) {
                        // Handle audio response
                        callback(true, "Audio response received (${response.body?.contentLength()} bytes)")
                    } else {
                        // Handle text/JSON response
                        callback(true, responseBody ?: "Success")
                    }
                } else {
                    Log.e(TAG, "Server error ${response.code}: $responseBody")
                    callback(false, "Server error ${response.code}: ${response.message}")
                }
            }
        })
    }
    
    /**
     * Send text command to the server
     */
    fun sendTextCommand(
        text: String,
        googleAccount: GoogleSignInAccount?,
        callback: (success: Boolean, response: String) -> Unit
    ) {
        val authCode = googleAccount?.serverAuthCode
        val idToken = googleAccount?.idToken
        
        val requestBody = FormBody.Builder()
            .add("text_command", text)
            .apply {
                authCode?.let { add("auth_code", it) }
                idToken?.let { add("id_token", it) }
            }
            .build()
        
        val request = Request.Builder()
            .url(SERVER_URL)
            .post(requestBody)
            .build()
        
        Log.d(TAG, "Sending text command to: $SERVER_URL")
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Network failure: ${e.message}", e)
                callback(false, "Network error: ${e.message}")
            }
            
            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                Log.d(TAG, "Response code: ${response.code}")
                Log.d(TAG, "Response body: $responseBody")
                
                if (response.isSuccessful) {
                    callback(true, responseBody ?: "Success")
                } else {
                    Log.e(TAG, "Server error ${response.code}: $responseBody")
                    callback(false, "Server error ${response.code}: ${response.message}")
                }
            }
        })
    }
    
    /**
     * Test the API endpoint directly
     */
    fun testEndpoint(callback: (success: Boolean, response: String) -> Unit) {
        val testBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("text_command", "Hello, this is a test")
            .build()
        
        val request = Request.Builder()
            .url(SERVER_URL)
            .post(testBody)
            .build()
        
        Log.d(TAG, "Testing endpoint: $SERVER_URL")
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Test failed: ${e.message}", e)
                callback(false, "Network error: ${e.message}")
            }
            
            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                Log.d(TAG, "Test response code: ${response.code}")
                Log.d(TAG, "Test response body: $responseBody")
                
                callback(
                    response.code != 404,
                    "HTTP ${response.code}: ${responseBody ?: response.message}"
                )
            }
        })
    }
}
