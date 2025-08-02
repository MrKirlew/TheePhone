package com.kirlewai.agent

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import com.google.android.material.button.MaterialButton
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.android.gms.common.api.Scope
import com.kirlewai.agent.databinding.ActivityMainBinding
import com.kirlewai.agent.network.SecureMultimodalService
import com.kirlewai.agent.network.GeminiService
import com.kirlewai.agent.speech.AudioRecorder
import com.kirlewai.agent.speech.TextToSpeechService
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var signInLauncher: ActivityResultLauncher<Intent>
    private lateinit var cameraLauncher: ActivityResultLauncher<Intent>

    private var googleSignInAccount: GoogleSignInAccount? = null
    private var audioRecorder: AudioRecorder? = null
    private var audioFile: File? = null
    private var imageFile: File? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    private lateinit var ttsService: TextToSpeechService

    // UI Components
    private lateinit var statusTextView: TextView
    private lateinit var recordButton: MaterialButton
    private lateinit var captureButton: MaterialButton
    private lateinit var sendTextButton: MaterialButton
    private lateinit var signInButton: MaterialButton
    private lateinit var listenButton: MaterialButton
    private lateinit var toggleCameraButton: MaterialButton
    private lateinit var conversationText: TextView
    private lateinit var signOutButton: MaterialButton
    private lateinit var userInfo: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Initialize Speech Recognizer
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            Log.d("MainActivity", "Speech recognition is available, creating SpeechRecognizer")
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
            setupSpeechRecognizer()
            Log.d("MainActivity", "SpeechRecognizer setup complete")
        } else {
            Log.e("MainActivity", "Speech recognition not available on this device")
        }

        // Initialize UI Components
        statusTextView = binding.statusText
        recordButton = binding.recordButton
        captureButton = binding.captureButton
        sendTextButton = binding.sendTextButton
        signInButton = binding.signInButton
        listenButton = binding.listenButton
        toggleCameraButton = binding.toggleCameraButton
        conversationText = binding.conversationText
        signOutButton = binding.signOutButton
        userInfo = binding.userInfo

        // Initialize AudioRecorder
        audioRecorder = AudioRecorder(this)
        
        // Initialize TextToSpeech
        ttsService = TextToSpeechService(this)
        lifecycleScope.launch {
            val ttsInitialized = ttsService.initialize()
            if (!ttsInitialized) {
                Log.e("MainActivity", "Failed to initialize Text-to-Speech")
            }
        }

        // Setup ActivityResultLaunchers
        setupSignInLauncher()
        setupCameraLauncher()

        // Setup button listeners
        recordButton.setOnClickListener { toggleRecording() }
        captureButton.setOnClickListener { captureImage() }
        sendTextButton.setOnClickListener { sendData() }
        signInButton.setOnClickListener { signIn() }
        listenButton.setOnClickListener { 
            Log.d("MainActivity", "Listen button clicked")
            startListening() 
        }
        toggleCameraButton.setOnClickListener { toggleCamera() }
        signOutButton.setOnClickListener { signOut() }

        // Check for initial sign-in state
        googleSignInAccount = GoogleSignIn.getLastSignedInAccount(this)
        
        // Ensure sign-in button is visible initially
        signInButton.visibility = View.VISIBLE
        Log.d("MainActivity", "Sign-in button should be visible now")
        
        updateUI()
    }

    private fun setupSignInLauncher() {
        signInLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val task = GoogleSignIn.getSignedInAccountFromIntent(result.data)
                try {
                    googleSignInAccount = task.getResult(ApiException::class.java)
                    updateUI()
                } catch (e: ApiException) {
                    Log.w("AuthError", "signInResult:failed code=" + e.statusCode)
                    Toast.makeText(this, "Sign-in failed.", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun setupCameraLauncher() {
        cameraLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val imageUri = result.data?.data
                imageFile = imageUri?.let { File(getRealPathFromURI(it)) }
                // Handle the captured image
                // You can display it in the preview view or process it
            }
        }
    }

    private fun toggleRecording() {
        if (audioRecorder?.isRecording == true) {
            audioFile = audioRecorder?.stopRecording()
            recordButton.text = getString(R.string.start_recording)
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                audioRecorder?.startRecording()
                recordButton.text = getString(R.string.stop_recording)
            } else {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 0)
            }
        }
    }

    private fun captureImage() {
        val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        cameraLauncher.launch(intent)
    }

    private fun sendData() {
        if (googleSignInAccount == null) {
            signIn()
            return
        }

        // Get text input
        val textInput = binding.textInput.text?.toString()?.trim()
        if (textInput.isNullOrEmpty() && audioFile == null) {
            Toast.makeText(this, "Please enter text or record audio first.", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                statusTextView.text = "🤔 Thinking..."
                
                val userMessage = textInput ?: "Audio message"
                conversationText.append("\nYou: $userMessage")
                
                // Get user context
                val userContext = "User: ${googleSignInAccount?.displayName}, Email: ${googleSignInAccount?.email}"
                
                val response = GeminiService.generateResponse(userMessage, userContext)
                
                conversationText.append("\nAI: $response")
                
                // Update status to show if speaking
                if (ttsService.isSpeechEnabled) {
                    statusTextView.text = "🔊 Speaking..."
                    ttsService.speak(response) {
                        // Called when speech is complete
                        runOnUiThread {
                            statusTextView.text = getString(R.string.ready)
                        }
                    }
                } else {
                    statusTextView.text = getString(R.string.ready)
                }
                
                // Clear text input
                binding.textInput.text?.clear()
                
                // Scroll to bottom
                binding.conversationScroll.post {
                    binding.conversationScroll.fullScroll(android.view.View.FOCUS_DOWN)
                }
                
            } catch (e: Exception) {
                statusTextView.text = getString(R.string.error_format, e.message)
                Log.e("NetworkError", "Error sending data", e)
            }
        }
    }

    private fun signIn() {
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestEmail()
            .requestScopes(Scope("https://www.googleapis.com/auth/calendar.readonly"))
            .requestServerAuthCode(getString(R.string.web_client_id))
            .build()
        val signInIntent = GoogleSignIn.getClient(this, gso).signInIntent
        signInLauncher.launch(signInIntent)
    }

    private fun updateUI() {
        if (googleSignInAccount != null) {
            Log.d("MainActivity", "User is signed in: ${googleSignInAccount?.displayName}")
            sendTextButton.isEnabled = true
            signInButton.visibility = View.GONE
            signOutButton.visibility = View.VISIBLE
            userInfo.text = getString(R.string.signed_in_as, googleSignInAccount?.displayName ?: "User")
            conversationText.text = getString(R.string.welcome_message, googleSignInAccount?.displayName ?: "User")
            recordButton.isEnabled = true
            captureButton.isEnabled = true
        } else {
            Log.d("MainActivity", "User is NOT signed in - showing sign-in button")
            sendTextButton.isEnabled = false
            signInButton.visibility = View.VISIBLE
            signOutButton.visibility = View.GONE
            userInfo.text = getString(R.string.welcome_sign_in)
            conversationText.text = getString(R.string.welcome_default)
            recordButton.isEnabled = false
            captureButton.isEnabled = false
        }
    }

    private fun getRealPathFromURI(uri: android.net.Uri): String {
        val cursor = contentResolver.query(uri, null, null, null, null)
        cursor?.moveToFirst()
        val idx = cursor?.getColumnIndex(MediaStore.Images.ImageColumns.DATA)
        val path = idx?.let { cursor.getString(it) } ?: ""
        cursor?.close()
        return path
    }
    
    private fun startListening() {
        Log.d("MainActivity", "startListening() called, isListening: $isListening")
        
        if (!isListening) {
            // Check if speech recognition is available
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                Log.e("MainActivity", "Speech recognition not available")
                Toast.makeText(this, "Speech recognition not available on this device", Toast.LENGTH_LONG).show()
                return
            }
            
            // Check permissions
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                Log.d("MainActivity", "Requesting RECORD_AUDIO permission")
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 1)
                return
            }
            
            Log.d("MainActivity", "Starting speech recognition")
            
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
            }
            
            try {
                speechRecognizer?.startListening(intent)
                isListening = true
                listenButton.text = getString(R.string.stop_listening_button)
                statusTextView.text = getString(R.string.listening_status)
                Log.d("MainActivity", "Speech recognition started successfully")
            } catch (e: Exception) {
                Log.e("MainActivity", "Error starting speech recognition", e)
                Toast.makeText(this, "Error starting speech recognition: ${e.message}", Toast.LENGTH_LONG).show()
            }
        } else {
            Log.d("MainActivity", "Stopping listening")
            stopListening()
        }
    }
    
    private fun stopListening() {
        speechRecognizer?.stopListening()
        isListening = false
        listenButton.text = getString(R.string.listen_button)
        statusTextView.text = getString(R.string.ready)
    }
    
    private fun setupSpeechRecognizer() {
        Log.d("MainActivity", "Setting up speech recognizer callbacks")
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                Log.d("MainActivity", "onReadyForSpeech")
                statusTextView.text = getString(R.string.speak_now)
            }
            
            override fun onBeginningOfSpeech() {
                Log.d("MainActivity", "onBeginningOfSpeech")
            }
            
            override fun onRmsChanged(rmsdB: Float) {}
            
            override fun onBufferReceived(buffer: ByteArray?) {}
            
            override fun onEndOfSpeech() {
                Log.d("MainActivity", "onEndOfSpeech")
                statusTextView.text = getString(R.string.processing)
            }
            
            override fun onError(error: Int) {
                Log.e("MainActivity", "Speech recognition error: $error")
                val errorMessage = when (error) {
                    SpeechRecognizer.ERROR_AUDIO -> "Audio error"
                    SpeechRecognizer.ERROR_CLIENT -> "Client error"
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Insufficient permissions"
                    SpeechRecognizer.ERROR_NETWORK -> "Network error"
                    SpeechRecognizer.ERROR_NO_MATCH -> "No match found"
                    SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
                    SpeechRecognizer.ERROR_SERVER -> "Server error"
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Speech timeout"
                    else -> "Unknown error"
                }
                statusTextView.text = "Error: $errorMessage"
                stopListening()
            }
            
            override fun onResults(results: Bundle?) {
                Log.d("MainActivity", "onResults called")
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    val text = matches[0]
                    conversationText.append("\nYou: $text")
                    // Process the recognized text
                    processVoiceCommand(text)
                }
                // Reset listening state after processing
                isListening = false
                listenButton.text = getString(R.string.listen_button)
                statusTextView.text = getString(R.string.ready)
            }
            
            override fun onPartialResults(partialResults: Bundle?) {
                Log.d("MainActivity", "onPartialResults")
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    statusTextView.text = "Hearing: ${matches[0]}"
                }
            }
            
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
    }
    
    private fun processVoiceCommand(command: String) {
        Log.d("MainActivity", "processVoiceCommand called with: '$command'")
        
        // Send to AI agent
        lifecycleScope.launch {
            try {
                Log.d("MainActivity", "Starting AI processing in coroutine")
                
                // Add the user's message to conversation first
                conversationText.append("\nYou: $command")
                conversationText.append("\nAI: 🤔 Thinking...")
                
                // Get user context if signed in
                val userContext = if (googleSignInAccount != null) {
                    "User: ${googleSignInAccount?.displayName}, Email: ${googleSignInAccount?.email}"
                } else {
                    ""
                }
                
                Log.d("MainActivity", "Calling GeminiService.generateResponse")
                // Call Gemini API directly for fast response
                val response = GeminiService.generateResponse(command, userContext)
                Log.d("MainActivity", "Got response from GeminiService: '$response'")
                
                // Update conversation with AI response
                Log.d("MainActivity", "Updating conversation with AI response")
                val finalText = conversationText.text.toString().replace("\nAI: 🤔 Thinking...", "\nAI: $response")
                conversationText.text = finalText
                
                // Speak the AI response with status update
                if (ttsService.isSpeechEnabled) {
                    statusTextView.text = "🔊 Speaking..."
                    ttsService.speak(response) {
                        // Called when speech is complete
                        runOnUiThread {
                            statusTextView.text = getString(R.string.ready)
                        }
                    }
                } else {
                    statusTextView.text = getString(R.string.ready)
                }
                
                // Scroll to bottom to show new response
                binding.conversationScroll.post {
                    binding.conversationScroll.fullScroll(android.view.View.FOCUS_DOWN)
                }
                
                Log.d("MainActivity", "Voice command processing completed successfully")
                
            } catch (e: Exception) {
                Log.e("MainActivity", "Error processing voice command", e)
                val errorText = conversationText.text.toString().replace(
                    "\nAI: 🤔 Thinking...", 
                    "\nAI: Sorry, I encountered an error: ${e.message}"
                )
                conversationText.text = errorText
            }
        }
    }
    
    private fun toggleCamera() {
        val previewView = binding.previewView
        if (previewView.visibility == View.GONE) {
            previewView.visibility = View.VISIBLE
            toggleCameraButton.text = getString(R.string.hide_camera)
            captureButton.visibility = View.VISIBLE
        } else {
            previewView.visibility = View.GONE
            toggleCameraButton.text = getString(R.string.show_camera)
            captureButton.visibility = View.GONE
        }
    }
    
    private fun signOut() {
        GoogleSignIn.getClient(this, GoogleSignInOptions.DEFAULT_SIGN_IN).signOut().addOnCompleteListener {
            googleSignInAccount = null
            updateUI()
            Toast.makeText(this, getString(R.string.signed_out_success), Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        Log.d("MainActivity", "onRequestPermissionsResult: requestCode=$requestCode")
        
        when (requestCode) {
            1 -> { // RECORD_AUDIO permission
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    Log.d("MainActivity", "RECORD_AUDIO permission granted, starting listening")
                    startListening()
                } else {
                    Log.w("MainActivity", "RECORD_AUDIO permission denied")
                    Toast.makeText(this, "Microphone permission is required for voice commands", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer?.destroy()
        ttsService.shutdown()
    }
}
