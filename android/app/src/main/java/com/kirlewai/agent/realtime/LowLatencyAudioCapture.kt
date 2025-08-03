package com.kirlewai.agent.realtime

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.*
import java.nio.ByteBuffer

/**
 * Low-latency audio capture implementation
 * 
 * This implements the Oboe-inspired audio capture described in
 * Realtime_Humanlike_AIAgent.txt for minimal ear-to-ear latency
 */
class LowLatencyAudioCapture(
    private val context: Context
) {
    companion object {
        private const val TAG = "LowLatencyAudio"
        private const val SAMPLE_RATE = 44100
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val BUFFER_SIZE_MULTIPLIER = 4
    }
    
    private var audioRecord: AudioRecord? = null
    private var isCapturing = false
    private var isPaused = false
    private var captureJob: Job? = null
    private val captureScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    // Calculate optimal buffer size for low latency
    private val bufferSize = AudioRecord.getMinBufferSize(
        SAMPLE_RATE,
        CHANNEL_CONFIG, 
        AUDIO_FORMAT
    ) * BUFFER_SIZE_MULTIPLIER
    
    // Audio processing parameters
    private val chunkSize = bufferSize / 4 // Small chunks for low latency
    private val audioBuffer = ByteArray(chunkSize)
    
    // Voice Activity Detection (simple threshold-based)
    private var isVoiceDetected = false
    private var silenceCounter = 0
    private val silenceThreshold = 10 // Number of silent chunks before stopping
    private val voiceThreshold = 1000 // Amplitude threshold for voice detection
    
    // Callback for audio data
    private var audioDataCallback: ((ByteArray) -> Unit)? = null
    
    /**
     * Initialize the audio capture system
     */
    @SuppressLint("MissingPermission")
    fun initialize(): Boolean {
        return try {
            // Create AudioRecord with optimal settings for low latency
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION, // Optimized for voice
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )
            
            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord initialization failed")
                return false
            }
            
            Log.i(TAG, "Low-latency audio capture initialized successfully")
            Log.d(TAG, "Buffer size: $bufferSize, Chunk size: $chunkSize")
            
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize audio capture", e)
            false
        }
    }
    
    /**
     * Start audio capture with callback
     */
    fun startCapture(callback: (ByteArray) -> Unit) {
        if (isCapturing) {
            Log.w(TAG, "Audio capture already active")
            return
        }
        
        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            if (!initialize()) {
                Log.e(TAG, "Cannot start capture: AudioRecord not initialized")
                return
            }
        }
        
        audioDataCallback = callback
        
        try {
            audioRecord?.startRecording()
            isCapturing = true
            isPaused = false
            
            // Start capture coroutine
            captureJob = captureScope.launch {
                captureAudioLoop()
            }
            
            Log.i(TAG, "Started low-latency audio capture")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start audio capture", e)
            isCapturing = false
        }
    }
    
    /**
     * Main audio capture loop with optimizations
     */
    private suspend fun captureAudioLoop() {
        val processingBuffer = ByteArray(chunkSize)
        
        while (isCapturing) {
            try {
                if (isPaused) {
                    delay(10) // Short delay when paused
                    continue
                }
                
                // Read audio data in small chunks for low latency
                val bytesRead = audioRecord?.read(processingBuffer, 0, chunkSize) ?: 0
                
                if (bytesRead > 0) {
                    // Process audio data
                    val processedAudio = processAudioChunk(processingBuffer, bytesRead)
                    
                    // Only send audio if voice is detected (optional optimization)
                    if (processedAudio != null) {
                        audioDataCallback?.invoke(processedAudio)
                    }
                }
                
                // Yield to other coroutines frequently for responsiveness
                yield()
                
            } catch (e: Exception) {
                Log.e(TAG, "Error in audio capture loop", e)
                if (e is CancellationException) break
            }
        }
        
        Log.d(TAG, "Audio capture loop ended")
    }
    
    /**
     * Process audio chunk with voice activity detection and noise reduction
     */
    private fun processAudioChunk(audioData: ByteArray, length: Int): ByteArray? {
        // Convert bytes to shorts for processing
        val audioShorts = ShortArray(length / 2)
        ByteBuffer.wrap(audioData, 0, length).asShortBuffer().get(audioShorts)
        
        // Calculate RMS (Root Mean Square) for voice activity detection
        var sum = 0L
        for (sample in audioShorts) {
            sum += (sample * sample).toLong()
        }
        val rms = kotlin.math.sqrt(sum.toDouble() / audioShorts.size)
        
        // Voice Activity Detection
        val currentlyHasVoice = rms > voiceThreshold
        
        if (currentlyHasVoice) {
            isVoiceDetected = true
            silenceCounter = 0
        } else if (isVoiceDetected) {
            silenceCounter++
            if (silenceCounter > silenceThreshold) {
                isVoiceDetected = false
                silenceCounter = 0
            }
        }
        
        // Apply simple noise gate and normalization
        val processedShorts = applyAudioProcessing(audioShorts, rms)
        
        // Convert back to bytes
        val processedBytes = ByteArray(length)
        val byteBuffer = ByteBuffer.wrap(processedBytes)
        byteBuffer.asShortBuffer().put(processedShorts)
        
        // Only return audio if voice is detected or we're in a voice segment
        return if (isVoiceDetected || currentlyHasVoice) {
            processedBytes
        } else {
            null // Skip silent audio to reduce bandwidth
        }
    }
    
    /**
     * Apply audio processing (noise gate, normalization, etc.)
     */
    private fun applyAudioProcessing(audioData: ShortArray, rms: Double): ShortArray {
        val processed = ShortArray(audioData.size)
        
        // Simple noise gate - reduce very quiet audio
        val noiseGateThreshold = voiceThreshold * 0.1
        val gainFactor = if (rms > noiseGateThreshold) 1.0 else 0.1
        
        // Apply gain and clipping protection
        for (i in audioData.indices) {
            val processed_sample = (audioData[i] * gainFactor).toInt()
            processed[i] = when {
                processed_sample > Short.MAX_VALUE -> Short.MAX_VALUE
                processed_sample < Short.MIN_VALUE -> Short.MIN_VALUE
                else -> processed_sample.toShort()
            }
        }
        
        return processed
    }
    
    /**
     * Pause audio capture
     */
    fun pauseCapture() {
        if (isCapturing) {
            isPaused = true
            Log.d(TAG, "Audio capture paused")
        }
    }
    
    /**
     * Resume audio capture
     */
    fun resumeCapture() {
        if (isCapturing && isPaused) {
            isPaused = false
            Log.d(TAG, "Audio capture resumed")
        }
    }
    
    /**
     * Stop audio capture
     */
    fun stopCapture() {
        if (!isCapturing) return
        
        try {
            isCapturing = false
            isPaused = false
            
            // Cancel capture job
            captureJob?.cancel()
            captureJob = null
            
            // Stop AudioRecord
            audioRecord?.stop()
            
            audioDataCallback = null
            
            Log.i(TAG, "Stopped audio capture")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping audio capture", e)
        }
    }
    
    /**
     * Release resources
     */
    fun release() {
        try {
            stopCapture()
            
            // Release AudioRecord
            audioRecord?.release()
            audioRecord = null
            
            // Cancel scope
            captureScope.cancel()
            
            Log.i(TAG, "Audio capture resources released")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing audio capture", e)
        }
    }
    
    /**
     * Get current audio levels for UI feedback
     */
    fun getCurrentAudioLevel(): Float {
        return if (isVoiceDetected) 1.0f else 0.0f
    }
    
    /**
     * Check if voice is currently detected
     */
    fun isVoiceActive(): Boolean = isVoiceDetected
    
    /**
     * Get capture status
     */
    fun isActive(): Boolean = isCapturing && !isPaused
}