/*
 * MainActivity.kt
 * Enhanced KirlewPHone Android Client with API Integration
 */
@file:Suppress("DEPRECATION")

package com.kirlewai.agent

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.view.View
import android.widget.*
import android.widget.ScrollView
import java.util.Locale
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
// Modern authentication imports
import androidx.credentials.Credential
import androidx.credentials.CredentialManager
// Legacy Google Sign-In for fallback
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.kirlewai.agent.services.ModernAuthService
import com.kirlewai.agent.services.ModernAudioRecorder
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.IOException
import com.kirlewai.agent.speech.SpeechRecognitionService
import com.kirlewai.agent.speech.TextToSpeechService
import com.kirlewai.agent.audio.AudioResponseHandler
import kotlinx.coroutines.launch
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    
    companion object {
        private const val TAG = "KirlewPHone"
        private const val REQUEST_RECORD_AUDIO_PERMISSION = 200
        private const val REQUEST_CAMERA_PERMISSION = 201
        private const val RC_SIGN_IN = 9001
        private const val REQUEST_IMAGE_CAPTURE = 1001
        // Update this with your actual Cloud Functions URL
        private const val SERVER_URL = "https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator"
    }
    
    /**
     * Enhanced logger for debugging client-side interactions
     */
    class ClientLogger {
        companion object {
            private const val CLIENT_TAG = "KirlewClient"
            
            fun logApiRequest(operation: String, details: Map<String, Any?>) {
                val logData = mapOf(
                    "type" to "api_request",
                    "operation" to operation,
                    "details" to details,
                    "timestamp" to System.currentTimeMillis()
                )
                Log.i(CLIENT_TAG, "API_REQUEST: ${JSONObject(logData)}")
            }
            
            fun logApiResponse(operation: String, success: Boolean, responseSize: Int?, latencyMs: Long?) {
                val logData = mapOf(
                    "type" to "api_response",
                    "operation" to operation,
                    "success" to success,
                    "response_size_bytes" to responseSize,
                    "latency_ms" to latencyMs,
                    "timestamp" to System.currentTimeMillis()
                )
                Log.i(CLIENT_TAG, "API_RESPONSE: ${JSONObject(logData)}")
            }
            
            fun logUserAction(action: String, details: Map<String, Any?> = emptyMap()) {
                val logData = mapOf(
                    "type" to "user_action",
                    "action" to action,
                    "details" to details,
                    "timestamp" to System.currentTimeMillis()
                )
                Log.i(CLIENT_TAG, "USER_ACTION: ${JSONObject(logData)}")
            }
            
            fun logConversationTurn(userInput: String, aiResponse: String, inputType: String) {
                val logData = mapOf(
                    "type" to "conversation_turn",
                    "user_input" to userInput.take(200),
                    "ai_response" to aiResponse.take(200),
                    "input_type" to inputType,
                    "timestamp" to System.currentTimeMillis()
                )
                Log.i(CLIENT_TAG, "CONVERSATION: ${JSONObject(logData)}")
            }
            
            fun logError(operation: String, error: String, details: Map<String, Any?> = emptyMap()) {
                val logData = mapOf(
                    "type" to "error",
                    "operation" to operation,
                    "error" to error,
                    "details" to details,
                    "timestamp" to System.currentTimeMillis()
                )
                Log.e(CLIENT_TAG, "ERROR: ${JSONObject(logData)}")
            }
        }
    }
    
    // UI Elements
    private lateinit var commandInput: EditText
    private lateinit var responseText: TextView
    private lateinit var chatRecyclerView: RecyclerView
    private lateinit var chatAdapter: ChatAdapter
    private lateinit var sendCommandButton: Button
    private lateinit var recordButton: Button
    private lateinit var listenButton: Button
    private lateinit var cameraButton: Button
    private lateinit var signInButton: Button
    private lateinit var signOutButton: Button
    
    // Authentication (Modern + Legacy fallback)
    private lateinit var modernAuthService: ModernAuthService
    private lateinit var googleSignInClient: GoogleSignInClient
    
    // Audio Recording (Modern)
    private lateinit var modernAudioRecorder: ModernAudioRecorder
    private lateinit var audioFile: File
    private var isRecording = false
    
    // Camera
    private var imageUri: Uri? = null
    
    // Speech Recognition
    private lateinit var speechRecognitionService: SpeechRecognitionService
    private var isListening = false
    
    // Text to Speech
    private lateinit var ttsService: TextToSpeechService
    
    // Audio Response Handler
    private lateinit var audioResponseHandler: AudioResponseHandler
    
    // Activity Result Launchers
    private lateinit var signInLauncher: ActivityResultLauncher<Intent>
    private lateinit var cameraLauncher: ActivityResultLauncher<Intent>
    private lateinit var imagePickerLauncher: ActivityResultLauncher<Intent>
    
    // Permissions
    private val permissions = arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.CAMERA)
    private var permissionGranted = false
    
    // No longer needed - using RecyclerView for conversation history
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        initActivityResultLaunchers()
        initViews()
        initGoogleSignIn()
        initModernServices()
        requestPermissions()
        setupAudioRecording()
        initSpeechServices()
    }
    
    private fun initViews() {
        commandInput = findViewById(R.id.commandInput)
        responseText = findViewById(R.id.responseText)
        chatRecyclerView = findViewById(R.id.chatRecyclerView)
        sendCommandButton = findViewById(R.id.sendCommandButton)
        recordButton = findViewById(R.id.recordButton)
        listenButton = findViewById(R.id.listenButton)
        cameraButton = findViewById(R.id.cameraButton)
        signInButton = findViewById(R.id.signInButton)
        signOutButton = findViewById(R.id.signOutButton)
        
        // Initialize chat RecyclerView
        chatAdapter = ChatAdapter(mutableListOf())
        chatRecyclerView.adapter = chatAdapter
        chatRecyclerView.layoutManager = LinearLayoutManager(this)
        
        sendCommandButton.setOnClickListener { sendCommand() }
        recordButton.setOnClickListener { toggleRecording() }
        listenButton.setOnClickListener { toggleListening() }
        cameraButton.setOnClickListener { openCamera() }
        signInButton.setOnClickListener { signIn() }
        signOutButton.setOnClickListener { signOut() }
        
        // Navigation bar buttons
        findViewById<ImageButton>(R.id.navHome).setOnClickListener {
            // Already on home screen
        }
        findViewById<ImageButton>(R.id.navSearch).setOnClickListener {
            Toast.makeText(this, "Search feature coming soon", Toast.LENGTH_SHORT).show()
        }
        findViewById<ImageButton>(R.id.navAdd).setOnClickListener {
            Toast.makeText(this, "Add feature coming soon", Toast.LENGTH_SHORT).show()
        }
        findViewById<ImageButton>(R.id.navProfile).setOnClickListener {
            Toast.makeText(this, "Profile feature coming soon", Toast.LENGTH_SHORT).show()
        }
        
        // Settings button
        findViewById<ImageButton>(R.id.settingsButton).setOnClickListener {
            Toast.makeText(this, "Settings coming soon", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun initGoogleSignIn() {
        // Initialize modern authentication service
        modernAuthService = ModernAuthService(this)
        
        // Initialize legacy Google Sign-In as fallback
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(BuildConfig.WEB_CLIENT_ID)
            .requestEmail()
            .requestServerAuthCode(BuildConfig.WEB_CLIENT_ID)
            .requestScopes(
                com.google.android.gms.common.api.Scope("https://www.googleapis.com/auth/calendar.readonly"),
                com.google.android.gms.common.api.Scope("https://www.googleapis.com/auth/gmail.readonly"),
                com.google.android.gms.common.api.Scope("https://www.googleapis.com/auth/drive.readonly")
            )
            .build()
        googleSignInClient = GoogleSignIn.getClient(this, gso)
        
        // Check if already signed in
        val account = GoogleSignIn.getLastSignedInAccount(this)
        updateUI(account)
    }
    
    private fun updateUI(isSignedIn: Boolean, displayName: String? = null) {
        if (isSignedIn) {
            signInButton.visibility = View.GONE
            signOutButton.visibility = View.VISIBLE
            if (displayName != null) {
                Toast.makeText(this, "Signed in as: $displayName", Toast.LENGTH_SHORT).show()
            }
        } else {
            signInButton.visibility = View.VISIBLE
            signOutButton.visibility = View.GONE
        }
    }
    
    // Legacy method for compatibility
    private fun updateUI(account: Any?) {
        updateUI(account != null)
    }
    
    private fun requestPermissions() {
        val permissionsToRequest = mutableListOf<String>()
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) 
            != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.RECORD_AUDIO)
        }
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) 
            != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.CAMERA)
        }
        
        if (permissionsToRequest.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissionsToRequest.toTypedArray(), 
                REQUEST_RECORD_AUDIO_PERMISSION)
        } else {
            permissionGranted = true
        }
    }
    
    private fun setupAudioRecording() {
        audioFile = File(getExternalFilesDir(null), "recording.pcm")
        // Modern audio recorder initialized in initModernServices()
    }
    
    private fun initActivityResultLaunchers() {
        // Sign-in launcher
        signInLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                val task = GoogleSignIn.getSignedInAccountFromIntent(result.data)
                try {
                    val account = task.getResult(ApiException::class.java)
                    updateUI(account)
                } catch (e: ApiException) {
                    Log.w(TAG, "Google sign in failed", e)
                    updateUI(null)
                }
            }
        }
        
        // Camera launcher
        cameraLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            when (result.resultCode) {
                RESULT_OK -> {
                    Log.d(TAG, "Camera result OK, imageUri: $imageUri")
                    if (imageUri != null) {
                        responseText.text = "Image captured. Processing..."
                        showImageProcessingDialog()
                    } else {
                        responseText.text = "Error: No image captured"
                        Toast.makeText(this@MainActivity, "Error: No image was captured", Toast.LENGTH_SHORT).show()
                    }
                }
                RESULT_CANCELED -> {
                    responseText.text = "Image capture cancelled"
                    Log.d(TAG, "Camera capture cancelled by user")
                }
                else -> {
                    responseText.text = "Camera error occurred"
                    Log.e(TAG, "Camera capture failed with result code: ${result.resultCode}")
                    Toast.makeText(this@MainActivity, "Camera error occurred", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        // Image picker launcher
        imagePickerLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK && result.data?.data != null) {
                imageUri = result.data?.data
                responseText.text = "Image selected. Processing..."
                showImageProcessingDialog()
            } else {
                responseText.text = "Image selection cancelled"
            }
        }
    }
    
    private fun initModernServices() {
        modernAuthService = ModernAuthService(this)
        modernAudioRecorder = ModernAudioRecorder(this)
    }
    
    private fun initSpeechServices() {
        speechRecognitionService = SpeechRecognitionService(this)
        ttsService = TextToSpeechService(this)
        audioResponseHandler = AudioResponseHandler(this)
    }
    
    private fun toggleListening() {
        if (isListening) {
            stopListening()
        } else {
            startListening()
        }
    }
    
    private fun startListening() {
        if (!permissionGranted) {
            Toast.makeText(this, "Microphone permission required", Toast.LENGTH_SHORT).show()
            return
        }
        
        if (isListening) {
            // Already listening
            return
        }
        
        listenButton.text = "⏹ Stop Listening"
        
        // Don't add listening status to conversation history
        // Just update the UI to show we're listening without polluting the conversation
        Toast.makeText(this, "Listening...", Toast.LENGTH_SHORT).show()
        
        speechRecognitionService.startListening(object : SpeechRecognitionService.SpeechRecognitionListener {
            override fun onResult(text: String) {
                runOnUiThread {
                    commandInput.setText(text)
                    listenButton.text = "🎧 Listen"
                    isListening = false
                    // Automatically send the command
                    sendCommand()
                }
            }
            
            override fun onError(error: String) {
                runOnUiThread {
                    responseText.text = "Error: $error"
                    listenButton.text = "🎧 Listen"
                    isListening = false
                }
            }
            
            override fun onReadyForSpeech() {
                isListening = true
            }
            
            override fun onEndOfSpeech() {
                runOnUiThread {
                    // Don't change the conversation history, just show a toast
                    Toast.makeText(this@MainActivity, "Processing...", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }
    
    private fun stopListening() {
        speechRecognitionService.stopListening()
        listenButton.text = "🎧 Listen"
        isListening = false
    }
    
    private fun toggleRecording() {
        if (isRecording) {
            stopRecording()
        } else {
            startRecording()
        }
    }
    
    private fun startRecording() {
        if (!permissionGranted) {
            Toast.makeText(this, "Microphone permission required", Toast.LENGTH_SHORT).show()
            return
        }
        
        modernAudioRecorder.startRecording(audioFile, object : ModernAudioRecorder.RecordingCallback {
            override fun onRecordingStarted() {
                runOnUiThread {
                    isRecording = true
                    recordButton.text = "⏹ Stop Recording"
                    responseText.text = "Recording..."
                    Log.d(TAG, "Started recording with modern recorder")
                }
            }
            
            override fun onRecordingCompleted(file: File) {
                runOnUiThread {
                    isRecording = false
                    recordButton.text = "🎤 Record"
                    responseText.text = "Recording completed. Processing..."
                    Log.d(TAG, "Stopped recording")
                    
                    // Send the recorded audio to the AI
                    sendAudioCommand()
                }
            }
            
            override fun onRecordingError(error: String) {
                runOnUiThread {
                    isRecording = false
                    recordButton.text = "🎤 Record"
                    Toast.makeText(this@MainActivity, "Recording failed: $error", Toast.LENGTH_SHORT).show()
                    Log.e(TAG, "Recording error: $error")
                }
            }
        })
    }
    
    private fun stopRecording() {
        modernAudioRecorder.stopRecording()
    }
    
    private fun sendCommand() {
        val command = commandInput.text.toString().trim()
        if (command.isEmpty()) {
            Toast.makeText(this, "Please enter a command", Toast.LENGTH_SHORT).show()
            return
        }
        
        // Clear input and keep focus for continuous conversation
        commandInput.setText("")
        commandInput.requestFocus()
        
        sendCommandToAI(command)
    }
    
    private fun openCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) 
            != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Camera permission required. Please grant permission and try again.", Toast.LENGTH_LONG).show()
            // Request camera permission
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), REQUEST_CAMERA_PERMISSION)
            return
        }
        
        // Show dialog to choose between camera and document
        val options = arrayOf("Take Photo", "Choose Document/Image")
        android.app.AlertDialog.Builder(this)
            .setTitle("Select Option")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> launchCamera()
                    1 -> launchImagePicker()
                }
            }
            .show()
    }
    
    private fun launchCamera() {
        try {
            val takePictureIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            
            // Check if there's a camera app available
            if (takePictureIntent.resolveActivity(packageManager) != null) {
                // Create a file to store the image
                val photoFile = File(getExternalFilesDir(null), "photo_${System.currentTimeMillis()}.jpg")
                imageUri = Uri.fromFile(photoFile)
                takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, imageUri)
                
                Log.d(TAG, "Launching camera with output file: ${photoFile.absolutePath}")
                cameraLauncher.launch(takePictureIntent)
            } else {
                Toast.makeText(this, "No camera app found on this device", Toast.LENGTH_LONG).show()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error launching camera", e)
            Toast.makeText(this, "Error opening camera: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
    
    private fun launchImagePicker() {
        val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
            type = "image/*"
            addCategory(Intent.CATEGORY_OPENABLE)
        }
        imagePickerLauncher.launch(intent)
    }
    
    private fun signIn() {
        // Try modern authentication first, fallback to legacy
        lifecycleScope.launch {
            try {
                val webClientId = BuildConfig.WEB_CLIENT_ID
                val authResult = modernAuthService.signInWithGoogle(webClientId)
                
                runOnUiThread {
                    updateUI(true, authResult.displayName)
                }
                
            } catch (e: Exception) {
                Log.w(TAG, "Modern auth failed, using legacy Google Sign-In", e)
                runOnUiThread {
                    // Fallback to legacy Google Sign-In
                    val signInIntent = googleSignInClient.signInIntent
                    signInLauncher.launch(signInIntent)
                }
            }
        }
    }
    
    private fun signOut() {
        googleSignInClient.signOut().addOnCompleteListener(this) {
            updateUI(null)
            responseText.text = "Signed out successfully"
        }
    }
    
    private fun sendCommandToAI(command: String) {
        responseText.text = "Processing your command..."
        
        // Log user action
        ClientLogger.logUserAction("send_text_command", mapOf(
            "command_length" to command.length,
            "has_auth" to (GoogleSignIn.getLastSignedInAccount(this) != null)
        ))
        
        val startTime = System.currentTimeMillis()
        val client = OkHttpClient.Builder()
            .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .build()
        
        // Get current auth tokens
        val account = GoogleSignIn.getLastSignedInAccount(this)
        val idToken = account?.idToken ?: ""
        val serverAuthCode = account?.serverAuthCode ?: ""
        
        // Log API request
        ClientLogger.logApiRequest("send_text_command", mapOf(
            "server_url" to SERVER_URL,
            "command_preview" to command.take(50),
            "has_auth_tokens" to (idToken.isNotEmpty() && serverAuthCode.isNotEmpty())
        ))
        
        // Create form body
        val formBody = FormBody.Builder()
            .add("text_command", command)
            .add("auth_code", serverAuthCode)
            .add("id_token", idToken)
            .build()
            
        val request = Request.Builder()
            .url(SERVER_URL)
            .post(formBody)
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                val latencyMs = System.currentTimeMillis() - startTime
                
                // Log API failure
                ClientLogger.logError("send_text_command", e.message ?: "Unknown network error", mapOf(
                    "latency_ms" to latencyMs,
                    "command_preview" to command.take(50)
                ))
                ClientLogger.logApiResponse("send_text_command", false, null, latencyMs)
                
                runOnUiThread {
                    val errorMsg = "Network Error: ${e.message}"
                    Log.e(TAG, "Network request failed to $SERVER_URL", e)
                    Log.e(TAG, "Command/audio was: '$command'")
                    
                    // Add error to chat
                    chatAdapter.addUserMessage(command ?: "[Command]")
                    chatAdapter.addAgentMessage("Error: $errorMsg")
                    
                    // Scroll to bottom
                    chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                }
            }
            
            override fun onResponse(call: Call, response: Response) {
                val latencyMs = System.currentTimeMillis() - startTime
                val responseSize = response.body?.contentLength()?.toInt()
                
                // Log API response
                ClientLogger.logApiResponse("send_text_command", response.isSuccessful, responseSize, latencyMs)
                
                runOnUiThread {
                    if (response.isSuccessful) {
                        // Check if response is audio or JSON
                        val contentType = response.header("Content-Type")
                        Log.d(TAG, "sendCommandToAI - Response Content-Type: '$contentType'")
                        Log.d(TAG, "sendCommandToAI - Response size: ${response.body?.contentLength()}")
                        Log.d(TAG, "sendCommandToAI - All headers: ${response.headers}")
                        
                        if (contentType?.contains("audio") == true) {
                            // Handle audio response
                            response.body?.bytes()?.let { audioData ->
                                // Get full response text from header
                                val responseTextHeader = response.header("X-Response-Text")
                                Log.d(TAG, "X-Response-Text header: '$responseTextHeader'")
                                Log.d(TAG, "All response headers: ${response.headers}")
                                
                                val aiResponse = if (!responseTextHeader.isNullOrEmpty()) {
                                    responseTextHeader
                                } else {
                                    // If header is missing, try to extract from response body as JSON
                                    Log.w(TAG, "X-Response-Text header missing, trying to parse audio response body as JSON")
                                    try {
                                        val bodyString = String(audioData)
                                        val json = JSONObject(bodyString)
                                        json.optString("response", "AI response received (audio)")
                                    } catch (e: Exception) {
                                        Log.w(TAG, "Could not parse audio response as JSON: ${e.message}")
                                        "AI response received (audio)"
                                    }
                                }
                                
                                // Add to chat
                                chatAdapter.addUserMessage(command)
                                chatAdapter.addAgentMessage(aiResponse)
                                
                                // Log conversation turn
                                ClientLogger.logConversationTurn(command, aiResponse, "text_to_audio")
                                
                                // Scroll to bottom to show latest message
                                chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                                
                                // Play the audio
                                audioResponseHandler.playAudioResponse(audioData)
                                Log.d(TAG, "Received audio response: ${audioData.size} bytes")
                                
                                // After audio plays, automatically start listening again for continuous conversation
                                audioResponseHandler.setCompletionListener {
                                    runOnUiThread {
                                        // Check if user said stop commands (simplified check)
                                        val lastMessages = chatAdapter.messages.takeLast(3)
                                        val recentText = lastMessages.joinToString(" ") { it.text }.lowercase(Locale.ROOT)
                                        if (!recentText.contains("stop listening") &&
                                            !recentText.contains("bye") &&
                                            !recentText.contains("goodbye") &&
                                            !recentText.contains("talk to you later")) {
                                            // Auto-start listening for next command
                                            startListening()
                                        }
                                    }
                                }
                            }
                        } else {
                            // Handle text/JSON response
                            val responseBody = response.body?.string()
                            
                            try {
                                // Try to parse as JSON
                                val json = JSONObject(responseBody ?: "{}")
                                val aiResponse = json.optString("response", responseBody ?: "")
                                
                                // Add to chat
                                chatAdapter.addUserMessage(command)
                                chatAdapter.addAgentMessage(aiResponse)
                                
                                // Log conversation turn
                                ClientLogger.logConversationTurn(command, aiResponse, "text_to_text")
                                
                                // Scroll to bottom
                                chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                                
                                // Speak the response
                                ttsService.speak(aiResponse)
                                Log.d(TAG, "Command processed successfully: $aiResponse")
                                
                                // After TTS completes, automatically start listening again
                                ttsService.setOnCompletionListener {
                                    runOnUiThread {
                                        // Check if user said stop commands (simplified check)
                                        val lastMessages = chatAdapter.messages.takeLast(3)
                                        val recentText = lastMessages.joinToString(" ") { it.text }.lowercase(Locale.ROOT)
                                        if (!recentText.contains("stop listening") &&
                                            !recentText.contains("bye") &&
                                            !recentText.contains("goodbye") &&
                                            !recentText.contains("talk to you later")) {
                                            // Auto-start listening for next command
                                            startListening()
                                        }
                                    }
                                }
                            } catch (e: Exception) {
                                // Not JSON, treat as plain text
                                val aiResponse = responseBody ?: "Let me help you with that..."
                                
                                // Add to chat
                                chatAdapter.addUserMessage(command)
                                chatAdapter.addAgentMessage(aiResponse)
                                
                                // Scroll to bottom
                                chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                                
                                ttsService.speak(aiResponse)
                                Log.d(TAG, "Command processed successfully: $responseBody")
                            }
                        }
                    } else {
                        responseText.text = "You: $command\n\nError: ${response.message}"
                        Log.e(TAG, "Server returned error: ${response.code}")
                    }
                }
            }
        })
    }
    
    private fun sendAudioCommand() {
        if (!audioFile.exists()) {
            Toast.makeText(this, "No audio file to send", Toast.LENGTH_SHORT).show()
            return
        }
        
        // Get current auth tokens
        val account = GoogleSignIn.getLastSignedInAccount(this)
        val idToken = account?.idToken ?: ""
        val serverAuthCode = account?.serverAuthCode ?: ""
        
        val client = OkHttpClient.Builder()
            .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .build()
        
        // Create multipart request
        val request = Request.Builder()
            .url(SERVER_URL)
            .post(
                MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("audio_file", "recording.amr",
                        audioFile.asRequestBody("audio/amr".toMediaType()))
                    .addFormDataPart("auth_code", serverAuthCode)
                    .addFormDataPart("id_token", idToken)
                    .build()
            )
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    val errorMsg = "Network Error: ${e.message}"
                    Log.e(TAG, "sendAudioCommand - Network request failed to $SERVER_URL", e)
                    Log.e(TAG, "sendAudioCommand - Audio file error")
                    
                    // Add error to chat
                    chatAdapter.addUserMessage("[Voice Recording]")
                    chatAdapter.addAgentMessage("Error: $errorMsg")
                    
                    // Scroll to bottom
                    chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                }
            }
            
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    if (response.isSuccessful) {
                        // Check if response is audio or JSON
                        val contentType = response.header("Content-Type")
                        
                        if (contentType?.contains("audio") == true) {
                            // Handle audio response
                            response.body?.bytes()?.let { audioData ->
                                // Get transcription and response from headers if available
                                val transcription = response.header("X-User-Transcription") ?: "[Voice Command]"
                                val responseTextHeader = response.header("X-Response-Text")
                                
                                val aiResponseText = if (!responseTextHeader.isNullOrEmpty()) {
                                    responseTextHeader
                                } else {
                                    // If header is missing, try to extract from response body as JSON
                                    Log.w(TAG, "X-Response-Text header missing from voice response, trying JSON")
                                    try {
                                        val bodyString = String(audioData)
                                        val json = JSONObject(bodyString)
                                        json.optString("response", "AI response received (voice audio)")
                                    } catch (e: Exception) {
                                        Log.w(TAG, "Could not parse voice response as JSON: ${e.message}")
                                        "AI response received (voice audio)"
                                    }
                                }
                                
                                // Add to chat
                                chatAdapter.addUserMessage(transcription)
                                chatAdapter.addAgentMessage(aiResponseText)
                                
                                // Scroll to bottom
                                chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                                
                                // Play the audio
                                audioResponseHandler.playAudioResponse(audioData)
                                Log.d(TAG, "Received audio response: ${audioData.size} bytes")
                                
                                // After audio plays, automatically start listening again for continuous conversation
                                audioResponseHandler.setCompletionListener {
                                    runOnUiThread {
                                        // Check if user said stop commands (simplified check)
                                        val lastMessages = chatAdapter.messages.takeLast(3)
                                        val recentText = lastMessages.joinToString(" ") { it.text }.lowercase(Locale.ROOT)
                                        if (!recentText.contains("stop listening") &&
                                            !recentText.contains("bye") &&
                                            !recentText.contains("goodbye") &&
                                            !recentText.contains("talk to you later")) {
                                            // Auto-start listening for next command
                                            startListening()
                                        }
                                    }
                                }
                            }
                        } else {
                            // Handle text/JSON response
                            val responseBody = response.body?.string()
                            
                            try {
                                // Try to parse as JSON
                                val json = JSONObject(responseBody ?: "{}")
                                val aiResponse = json.optString("response", responseBody ?: "")
                                val userTranscription = json.optString("transcription", "[Voice Command]")
                                
                                // Add to chat
                                chatAdapter.addUserMessage(userTranscription)
                                chatAdapter.addAgentMessage(aiResponse)
                                
                                // Scroll to bottom
                                chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                                
                                // Speak the response
                                ttsService.speak(aiResponse)
                                Log.d(TAG, "Audio processed successfully: $aiResponse")
                            } catch (e: Exception) {
                                // Not JSON, treat as plain text
                                val aiResponse = responseBody ?: "Let me help you with that..."
                                
                                // Add to chat
                                chatAdapter.addUserMessage("[Voice Command]")
                                chatAdapter.addAgentMessage(aiResponse)
                                
                                // Scroll to bottom
                                chatRecyclerView.scrollToPosition(chatAdapter.itemCount - 1)
                                
                                ttsService.speak(aiResponse)
                                Log.d(TAG, "Audio processed successfully: $responseBody")
                            }
                        }
                    } else {
                        responseText.text = "Error: ${response.message}"
                        Log.e(TAG, "Server returned error: ${response.code}")
                    }
                }
            }
        })
    }
    
    private fun showImageProcessingDialog() {
        val editText = EditText(this).apply {
            hint = "What would you like to do with this image?"
            setText("Analyze this image")
        }
        
        android.app.AlertDialog.Builder(this)
            .setTitle("Image Processing")
            .setView(editText)
            .setPositiveButton("Process") { _, _ ->
                val command = editText.text.toString()
                if (command.isNotEmpty()) {
                    sendImageCommand(command)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    private fun sendImageCommand(userCommand: String = "Analyze this image") {
        if (imageUri == null) {
            Toast.makeText(this, "No image file to send", Toast.LENGTH_SHORT).show()
            return
        }
        
        responseText.text = "Processing image with command: $userCommand"
        
        val client = OkHttpClient.Builder()
            .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .build()
        
        try {
            val inputStream = contentResolver.openInputStream(imageUri!!)
            val tempFile = File(cacheDir, "temp_image.jpg")
            tempFile.outputStream().use { outputStream ->
                inputStream?.copyTo(outputStream)
            }
            
            // Create multipart request
            val request = Request.Builder()
                .url(SERVER_URL)
                .post(
                    MultipartBody.Builder()
                        .setType(MultipartBody.FORM)
                        .addFormDataPart("image_file", "image.jpg",
                            tempFile.asRequestBody("image/jpeg".toMediaType()))
                        .addFormDataPart("command", userCommand)
                        .addFormDataPart("auth_code", "your_auth_code")
                        .addFormDataPart("id_token", "your_id_token")
                        .build()
                )
                .build()
            
            client.newCall(request).enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    runOnUiThread {
                        responseText.text = "Error: ${e.message}"
                        Log.e(TAG, "Network request failed", e)
                    }
                }
                
                override fun onResponse(call: Call, response: Response) {
                    runOnUiThread {
                        if (response.isSuccessful) {
                            // Check if response is audio or JSON
                            val contentType = response.header("Content-Type")
                            
                            if (contentType?.contains("audio") == true) {
                                // Handle audio response
                                response.body?.bytes()?.let { audioData ->
                                    responseText.text = "Playing AI response..."
                                    audioResponseHandler.playAudioResponse(audioData)
                                    Log.d(TAG, "Received audio response: ${audioData.size} bytes")
                                }
                            } else {
                                // Handle text/JSON response
                                val responseBody = response.body?.string()
                                
                                try {
                                    // Try to parse as JSON
                                    val json = JSONObject(responseBody ?: "{}")
                                    val responseMessage = json.optString("response", responseBody ?: "")
                                    responseText.text = responseMessage
                                    // Speak the response
                                    ttsService.speak(responseMessage)
                                    Log.d(TAG, "Image processed successfully: $responseMessage")
                                } catch (e: Exception) {
                                    // Not JSON, treat as plain text
                                    responseText.text = responseBody ?: "Image processed successfully"
                                    ttsService.speak(responseBody ?: "Image processed successfully")
                                    Log.d(TAG, "Image processed successfully: $responseBody")
                                }
                            }
                        } else {
                            responseText.text = "Error: ${response.message}"
                            Log.e(TAG, "Server returned error: ${response.code}")
                        }
                    }
                    tempFile.delete()
                }
            })
        } catch (e: Exception) {
            responseText.text = "Error processing image: ${e.message}"
            Log.e(TAG, "Error processing image", e)
        }
    }
    
    // onActivityResult is now replaced by Activity Result API launchers
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        when (requestCode) {
            REQUEST_CAMERA_PERMISSION -> {
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    Log.d(TAG, "Camera permission granted")
                    Toast.makeText(this, "Camera permission granted. You can now use the camera.", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, "Camera permission denied. Camera features will not work.", Toast.LENGTH_LONG).show()
                }
            }
            REQUEST_RECORD_AUDIO_PERMISSION -> {
                // Check each permission individually
                for (i in permissions.indices) {
                    when (permissions[i]) {
                        Manifest.permission.RECORD_AUDIO -> {
                            if (grantResults[i] == PackageManager.PERMISSION_GRANTED) {
                                Log.d(TAG, "Audio recording permission granted")
                            }
                        }
                        Manifest.permission.CAMERA -> {
                            if (grantResults[i] == PackageManager.PERMISSION_GRANTED) {
                                Log.d(TAG, "Camera permission granted")
                            }
                        }
                    }
                }
                
                // Update global permission status
                permissionGranted = grantResults.isNotEmpty() && 
                    grantResults.all { it == PackageManager.PERMISSION_GRANTED }
                    
                if (!permissionGranted) {
                    val deniedPermissions = mutableListOf<String>()
                    for (i in permissions.indices) {
                        if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                            deniedPermissions.add(permissions[i])
                        }
                    }
                    Toast.makeText(this, "Permissions denied: ${deniedPermissions.joinToString(", ")}. Some features may not work.", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        if (isRecording) {
            modernAudioRecorder.stopRecording()
        }
        speechRecognitionService.destroy()
        ttsService.shutdown()
    }
}
