package com.kirlewai.agent

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.kirlewai.agent.realtime.DialogueAdapter
import com.kirlewai.agent.realtime.RealtimeConversationClient
import com.kirlewai.agent.realtime.LowLatencyAudioCapture
import com.kirlewai.agent.wakeword.WakeWordDetector
import com.kirlewai.agent.services.ModernAuthService
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.collect

/**
 * Enhanced MainActivity with Real-Time AI Agent Capabilities
 * 
 * This implements the complete architecture described in Realtime_Humanlike_AIAgent.txt
 * for natural, continuous dialogue with advanced multimodal capabilities.
 */
class RealtimeMainActivity : AppCompatActivity() {
    
    companion object {
        private const val TAG = "RealtimeMainActivity"
        private const val PERMISSIONS_REQUEST_CODE = 1001
    }
    
    // UI Components
    private lateinit var statusText: TextView
    private lateinit var responseText: TextView
    private lateinit var conversationButton: Button
    private lateinit var dialogueRecyclerView: RecyclerView
    private lateinit var dialogueAdapter: DialogueAdapter
    private lateinit var functionCallsText: TextView
    private lateinit var wakeWordSwitch: Switch
    private lateinit var voiceLevelIndicator: ProgressBar
    
    // Real-time conversation components
    private lateinit var realtimeClient: RealtimeConversationClient
    private lateinit var audioCapture: LowLatencyAudioCapture
    private lateinit var wakeWordDetector: WakeWordDetector
    private lateinit var authService: ModernAuthService
    
    // State management
    private var isConversationActive = false
    private var currentUserId: String? = null
    private var authToken: String? = null
    
    // Required permissions
    private val requiredPermissions = arrayOf(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION
    )
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_realtime_main)
        
        initializeViews()
        initializeServices()
        requestPermissions()
        observeConversationState()
    }
    
    /**
     * Initialize UI components
     */
    private fun initializeViews() {
        statusText = findViewById<TextView>(R.id.statusText)
        responseText = findViewById<TextView>(R.id.responseText)
        conversationButton = findViewById<Button>(R.id.conversationButton)
        dialogueRecyclerView = findViewById<RecyclerView>(R.id.dialogueRecyclerView)
        functionCallsText = findViewById<TextView>(R.id.functionCallsText)
        wakeWordSwitch = findViewById<Switch>(R.id.wakeWordSwitch)
        voiceLevelIndicator = findViewById<ProgressBar>(R.id.voiceLevelIndicator)

        dialogueAdapter = DialogueAdapter(mutableListOf())
        dialogueRecyclerView.adapter = dialogueAdapter
        dialogueRecyclerView.layoutManager = LinearLayoutManager(this)
        
        // Set up click listeners
        conversationButton.setOnClickListener { toggleConversation() }
        wakeWordSwitch.setOnCheckedChangeListener { _, isChecked -> 
            toggleWakeWordDetection(isChecked) 
        }
        
        // Initial UI state
        updateUI(UIConversationState.DISCONNECTED)
    }
    
    /**
     * Initialize real-time services
     */
    private fun initializeServices() {
        try {
            // Initialize real-time conversation client
            realtimeClient = RealtimeConversationClient()
            
            // Initialize audio capture
            audioCapture = LowLatencyAudioCapture(this)
            audioCapture.initialize()
            
            // Initialize wake word detector
            wakeWordDetector = WakeWordDetector(this)
            
            // Initialize modern auth service
            authService = ModernAuthService(this)
            
            Log.i(TAG, "All real-time services initialized successfully")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize services", e)
            Toast.makeText(this, "Failed to initialize AI services", Toast.LENGTH_LONG).show()
        }
    }
    
    /**
     * Request required permissions
     */
    private fun requestPermissions() {
        val missingPermissions = requiredPermissions.filter { permission ->
            ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED
        }
        
        if (missingPermissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                missingPermissions.toTypedArray(),
                PERMISSIONS_REQUEST_CODE
            )
        } else {
            onPermissionsGranted()
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == PERMISSIONS_REQUEST_CODE) {
            val allGranted = grantResults.all { it == PackageManager.PERMISSION_GRANTED }
            
            if (allGranted) {
                onPermissionsGranted()
            } else {
                Toast.makeText(
                    this,
                    "Permissions required for AI voice features",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
    
    /**
     * Handle permissions granted
     */
    private fun onPermissionsGranted() {
        lifecycleScope.launch {
            try {
                // Initialize real-time client
                realtimeClient.initialize()
                
                // Authenticate user
                authenticateUser()
                
                Log.i(TAG, "Ready for real-time conversation")
                
            } catch (e: Exception) {
                Log.e(TAG, "Error during initialization", e)
                updateUI(UIConversationState.ERROR)
            }
        }
    }
    
    /**
     * Authenticate user with modern auth system
     */
    private suspend fun authenticateUser() {
        try {
            // Try modern authentication first
            val authResult = authService.signInWithGoogle(BuildConfig.WEB_CLIENT_ID)
            
            currentUserId = authResult.email ?: "anonymous"
            authToken = authResult.idToken
            
            updateUI(UIConversationState.READY)
            
            Log.i(TAG, "User authenticated: $currentUserId")
            
        } catch (e: Exception) {
            Log.e(TAG, "Authentication failed", e)
            
            // Fallback to anonymous mode
            currentUserId = "anonymous_${System.currentTimeMillis()}"
            authToken = "anonymous_token"
            
            updateUI(UIConversationState.READY)
        }
    }
    
    /**
     * Observe conversation state changes
     */
    private fun observeConversationState() {
        lifecycleScope.launch {
            realtimeClient.conversationState.collect { state ->
                // Convert RealtimeConversationClient.ConversationState to UIConversationState
                val uiState = when (state) {
                    RealtimeConversationClient.ConversationState.DISCONNECTED -> UIConversationState.DISCONNECTED
                    RealtimeConversationClient.ConversationState.CONNECTING -> UIConversationState.CONNECTING
                    RealtimeConversationClient.ConversationState.CONNECTED -> UIConversationState.CONNECTED
                    RealtimeConversationClient.ConversationState.CONVERSATION_ACTIVE -> UIConversationState.CONVERSATION_ACTIVE
                    RealtimeConversationClient.ConversationState.CONVERSATION_PAUSED -> UIConversationState.CONVERSATION_PAUSED
                    RealtimeConversationClient.ConversationState.ERROR -> UIConversationState.ERROR
                }
                updateUI(uiState)
            }
        }
        
        lifecycleScope.launch {
            realtimeClient.transcriptionFlow.collect { transcription ->
                runOnUiThread {
                    dialogueAdapter.addMessage("You: $transcription")
                    dialogueRecyclerView.scrollToPosition(dialogueAdapter.itemCount - 1)
                }
            }
        }

        lifecycleScope.launch {
            realtimeClient.aiResponseFlow.collect { response ->
                runOnUiThread {
                    dialogueAdapter.addMessage("Assistant: $response")
                    dialogueRecyclerView.scrollToPosition(dialogueAdapter.itemCount - 1)
                }
            }
        }
        
        lifecycleScope.launch {
            realtimeClient.functionCallsFlow.collect { functionCall ->
                runOnUiThread {
                    val statusText = "${functionCall.functionName}: ${functionCall.description}"
                    functionCallsText.text = statusText
                }
            }
        }
    }
    
    /**
     * Toggle conversation state
     */
    private fun toggleConversation() {
        if (isConversationActive) {
            stopConversation()
        } else {
            startConversation()
        }
    }
    
    /**
     * Start real-time conversation
     */
    private fun startConversation() {
        if (currentUserId == null || authToken == null) {
            Toast.makeText(this, "Authentication required", Toast.LENGTH_SHORT).show()
            return
        }
        
        lifecycleScope.launch {
            try {
                // Configure user preferences
                val preferences = RealtimeConversationClient.UserPreferences(
                    voicePreference = "Aoede",
                    speechRate = 1.0f,
                    enableInterruptions = true,
                    enableProactiveSuggestions = true,
                    languageCode = "en-US"
                )
                
                // Start conversation
                val success = realtimeClient.startConversation(
                    userId = currentUserId!!,
                    authToken = authToken!!,
                    preferences = preferences
                )
                
                if (success) {
                    isConversationActive = true
                    updateUI(UIConversationState.CONVERSATION_ACTIVE)
                    
                    // Start monitoring voice levels
                    startVoiceLevelMonitoring()
                    
                    Log.i(TAG, "Real-time conversation started")
                } else {
                    Toast.makeText(this@RealtimeMainActivity, "Failed to start conversation", Toast.LENGTH_SHORT).show()
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Error starting conversation", e)
                Toast.makeText(this@RealtimeMainActivity, "Conversation error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    /**
     * Stop real-time conversation
     */
    private fun stopConversation() {
        lifecycleScope.launch {
            try {
                realtimeClient.endConversation()
                isConversationActive = false
                stopVoiceLevelMonitoring()
                
                updateUI(UIConversationState.CONNECTED)
                
                Log.i(TAG, "Real-time conversation stopped")
                
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping conversation", e)
            }
        }
    }
    
    /**
     * Toggle wake word detection
     */
    private fun toggleWakeWordDetection(enabled: Boolean) {
        if (enabled) {
            startWakeWordDetection()
        } else {
            stopWakeWordDetection()
        }
    }
    
    /**
     * Start wake word detection
     */
    private fun startWakeWordDetection() {
        try {
            val config = WakeWordDetector.WakeWordConfig(
                sensitivity = 0.7f,
                enableContinuousListening = true,
                powerOptimized = true,
                customWakeWords = listOf("hey kirlew", "kirlew assistant")
            )
            
            wakeWordDetector.startDetection(
                audioSource = { 
                    // This would provide audio data from a background audio capture
                    null // Simplified for now
                },
                config = config,
                onDetected = { wakeWord ->
                    runOnUiThread {
                        if (!isConversationActive) {
                            responseText.text = "Wake word detected: $wakeWord"
                            startConversation()
                        }
                    }
                }
            )
            
            Log.i(TAG, "Wake word detection started")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error starting wake word detection", e)
            wakeWordSwitch.isChecked = false
        }
    }
    
    /**
     * Stop wake word detection
     */
    private fun stopWakeWordDetection() {
        try {
            wakeWordDetector.stopDetection()
            Log.i(TAG, "Wake word detection stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping wake word detection", e)
        }
    }
    
    /**
     * Start monitoring voice levels for UI feedback
     */
    private fun startVoiceLevelMonitoring() {
        lifecycleScope.launch {
            while (isConversationActive) {
                try {
                    val voiceLevel = if (audioCapture.isVoiceActive()) {
                        audioCapture.getCurrentAudioLevel()
                    } else {
                        0.0f
                    }
                    
                    runOnUiThread {
                        voiceLevelIndicator.progress = (voiceLevel * 100).toInt()
                    }
                    
                    kotlinx.coroutines.delay(50) // Update 20 times per second
                    
                } catch (e: Exception) {
                    Log.e(TAG, "Error monitoring voice levels", e)
                    break
                }
            }
        }
    }
    
    /**
     * Stop voice level monitoring
     */
    private fun stopVoiceLevelMonitoring() {
        voiceLevelIndicator.progress = 0
    }
    
    /**
     * Update UI based on conversation state (internal enum)
     */
    private fun updateUI(state: UIConversationState) {
        runOnUiThread {
            when (state) {
                UIConversationState.DISCONNECTED -> {
                    statusText.text = "Disconnected"
                    conversationButton.text = "Initialize"
                    conversationButton.isEnabled = false
                    wakeWordSwitch.isEnabled = false
                }
                
                UIConversationState.CONNECTING -> {
                    statusText.text = "Connecting..."
                    conversationButton.isEnabled = false
                    wakeWordSwitch.isEnabled = false
                }
                
                UIConversationState.CONNECTED, UIConversationState.READY -> {
                    statusText.text = "Ready for conversation"
                    conversationButton.text = "Start Conversation"
                    conversationButton.isEnabled = true
                    wakeWordSwitch.isEnabled = true
                }
                
                UIConversationState.CONVERSATION_ACTIVE -> {
                    statusText.text = "Conversation Active - Listening..."
                    conversationButton.text = "End Conversation"
                    conversationButton.isEnabled = true
                    wakeWordSwitch.isEnabled = false
                }
                
                UIConversationState.CONVERSATION_PAUSED -> {
                    statusText.text = "Conversation Paused"
                    conversationButton.text = "Resume Conversation"
                    conversationButton.isEnabled = true
                }
                
                UIConversationState.ERROR -> {
                    statusText.text = "Error - Please restart"
                    conversationButton.text = "Restart"
                    conversationButton.isEnabled = true
                    wakeWordSwitch.isEnabled = false
                }
            }
        }
    }

    
    override fun onPause() {
        super.onPause()
        
        // Pause conversation when app goes to background
        if (isConversationActive) {
            lifecycleScope.launch {
                realtimeClient.pauseConversation()
            }
        }
    }
    
    override fun onResume() {
        super.onResume()
        
        // Resume conversation when app comes back to foreground
        if (isConversationActive) {
            lifecycleScope.launch {
                realtimeClient.resumeConversation()
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        
        // Clean up all resources
        lifecycleScope.launch {
            try {
                if (isConversationActive) {
                    realtimeClient.endConversation()
                }
                
                realtimeClient.shutdown()
                audioCapture.release()
                wakeWordDetector.release()
                
                Log.i(TAG, "All resources cleaned up")
                
            } catch (e: Exception) {
                Log.e(TAG, "Error during cleanup", e)
            }
        }
    }
    
    // Helper enum for additional states
    enum class UIConversationState {
        DISCONNECTED,
        CONNECTING,
        CONNECTED,
        READY,
        CONVERSATION_ACTIVE,
        CONVERSATION_PAUSED,
        ERROR
    }
}