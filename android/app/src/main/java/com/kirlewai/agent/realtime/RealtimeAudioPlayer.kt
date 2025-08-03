package com.kirlewai.agent.realtime

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import android.util.Log
import kotlinx.coroutines.*
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * Real-time audio player for streaming AI responses
 * 
 * Implements low-latency audio playback with interruption support
 * as described in Realtime_Humanlike_AIAgent.txt
 */
class RealtimeAudioPlayer(
    private val context: Context
) {
    companion object {
        private const val TAG = "RealtimeAudioPlayer"
        private const val SAMPLE_RATE = 44100
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_OUT_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val BUFFER_SIZE_MULTIPLIER = 4
    }
    
    private var audioTrack: AudioTrack? = null
    private var isPlaying = false
    private var isPaused = false
    private var playbackJob: Job? = null
    private val playbackScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    // Audio buffer management
    private val audioQueue = ConcurrentLinkedQueue<ByteArray>()
    private val maxQueueSize = 50 // Limit queue size to prevent memory issues
    
    // Calculate optimal buffer size
    private val bufferSize = AudioTrack.getMinBufferSize(
        SAMPLE_RATE,
        CHANNEL_CONFIG,
        AUDIO_FORMAT
    ) * BUFFER_SIZE_MULTIPLIER
    
    // Interruption handling
    private var canBeInterrupted = true
    
    /**
     * Initialize the audio player
     */
    fun initialize(): Boolean {
        return try {
            // Create AudioTrack with low latency settings (API level compatible)
            val audioAttributes = AudioAttributes.Builder()
                .setUsage(
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        AudioAttributes.USAGE_ASSISTANT
                    } else {
                        AudioAttributes.USAGE_MEDIA
                    }
                )
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .apply {
                    @Suppress("DEPRECATION")
                    setFlags(AudioAttributes.FLAG_LOW_LATENCY) // Using for compatibility
                }
                .build()
            
            val audioFormat = AudioFormat.Builder()
                .setSampleRate(SAMPLE_RATE)
                .setChannelMask(CHANNEL_CONFIG)
                .setEncoding(AUDIO_FORMAT)
                .build()
            
            audioTrack = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                AudioTrack.Builder()
                    .setAudioAttributes(audioAttributes)
                    .setAudioFormat(audioFormat)
                    .setBufferSizeInBytes(bufferSize)
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY)
                    .build()
            } else {
                // Fallback for API < 26
                @Suppress("DEPRECATION")
                AudioTrack(
                    AudioManager.STREAM_MUSIC,
                    SAMPLE_RATE,
                    CHANNEL_CONFIG,
                    AUDIO_FORMAT,
                    bufferSize,
                    AudioTrack.MODE_STREAM
                )
            }
            
            if (audioTrack?.state != AudioTrack.STATE_INITIALIZED) {
                Log.e(TAG, "AudioTrack initialization failed")
                return false
            }
            
            Log.i(TAG, "Real-time audio player initialized successfully")
            Log.d(TAG, "Buffer size: $bufferSize")
            
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize audio player", e)
            false
        }
    }
    
    /**
     * Start audio playback system
     */
    fun startPlayback() {
        if (isPlaying) {
            Log.w(TAG, "Audio playback already active")
            return
        }
        
        if (audioTrack?.state != AudioTrack.STATE_INITIALIZED) {
            if (!initialize()) {
                Log.e(TAG, "Cannot start playback: AudioTrack not initialized")
                return
            }
        }
        
        try {
            audioTrack?.play()
            isPlaying = true
            isPaused = false
            
            // Start playback coroutine
            playbackJob = playbackScope.launch {
                playbackLoop()
            }
            
            Log.i(TAG, "Started real-time audio playback")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start audio playback", e)
            isPlaying = false
        }
    }
    
    /**
     * Main audio playback loop
     */
    private suspend fun playbackLoop() {
        while (isPlaying) {
            try {
                if (isPaused) {
                    delay(10) // Short delay when paused
                    continue
                }
                
                // Get next audio chunk from queue
                val audioChunk = audioQueue.poll()
                
                if (audioChunk != null) {
                    // Write audio data to AudioTrack
                    val bytesWritten = audioTrack?.write(audioChunk, 0, audioChunk.size) ?: 0
                    
                    if (bytesWritten < 0) {
                        Log.e(TAG, "Error writing audio data: $bytesWritten")
                    }
                } else {
                    // No audio data available, short delay
                    delay(5)
                }
                
                // Yield to other coroutines
                yield()
                
            } catch (e: Exception) {
                Log.e(TAG, "Error in playback loop", e)
                if (e is CancellationException) break
            }
        }
        
        Log.d(TAG, "Audio playback loop ended")
    }
    
    /**
     * Play audio chunk immediately (streaming)
     */
    fun playAudioChunk(audioData: ByteArray) {
        if (!isPlaying) {
            startPlayback()
        }
        
        // Add to queue if there's space
        if (audioQueue.size < maxQueueSize) {
            audioQueue.offer(audioData)
        } else {
            // Queue is full, remove oldest chunk and add new one
            audioQueue.poll()
            audioQueue.offer(audioData)
            Log.w(TAG, "Audio queue overflow, dropping oldest chunk")
        }
    }
    
    /**
     * Clear audio queue (for interruptions)
     */
    fun clearQueue() {
        if (canBeInterrupted) {
            audioQueue.clear()
            Log.d(TAG, "Audio queue cleared for interruption")
        }
    }
    
    /**
     * Stop current audio immediately (for interruptions)
     */
    fun interrupt() {
        if (canBeInterrupted && isPlaying) {
            try {
                // Clear queue and stop current audio
                clearQueue()
                audioTrack?.pause()
                audioTrack?.flush() // Clear internal buffer
                audioTrack?.play() // Resume for new audio
                
                Log.d(TAG, "Audio playback interrupted")
                
            } catch (e: Exception) {
                Log.e(TAG, "Error interrupting audio", e)
            }
        }
    }
    
    /**
     * Pause audio playback
     */
    fun pause() {
        if (isPlaying && !isPaused) {
            try {
                isPaused = true
                audioTrack?.pause()
                Log.d(TAG, "Audio playback paused")
            } catch (e: Exception) {
                Log.e(TAG, "Error pausing audio", e)
            }
        }
    }
    
    /**
     * Resume audio playback
     */
    fun resume() {
        if (isPlaying && isPaused) {
            try {
                isPaused = false
                audioTrack?.play()
                Log.d(TAG, "Audio playback resumed")
            } catch (e: Exception) {
                Log.e(TAG, "Error resuming audio", e)
            }
        }
    }
    
    /**
     * Stop audio playback
     */
    fun stop() {
        if (!isPlaying) return
        
        try {
            isPlaying = false
            isPaused = false
            
            // Cancel playback job
            playbackJob?.cancel()
            playbackJob = null
            
            // Stop AudioTrack
            audioTrack?.stop()
            audioTrack?.flush()
            
            // Clear queue
            audioQueue.clear()
            
            Log.i(TAG, "Stopped audio playback")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping audio playback", e)
        }
    }
    
    /**
     * Release resources
     */
    fun release() {
        try {
            stop()
            
            // Release AudioTrack
            audioTrack?.release()
            audioTrack = null
            
            // Cancel scope
            playbackScope.cancel()
            
            Log.i(TAG, "Audio player resources released")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing audio player", e)
        }
    }
    
    /**
     * Set volume level
     */
    fun setVolume(volume: Float) {
        try {
            val clampedVolume = volume.coerceIn(0.0f, 1.0f)
            audioTrack?.setVolume(clampedVolume)
        } catch (e: Exception) {
            Log.e(TAG, "Error setting volume", e)
        }
    }
    
    /**
     * Enable/disable interruption capability
     */
    fun setInterruptible(interruptible: Boolean) {
        canBeInterrupted = interruptible
    }
    
    /**
     * Get current playback state
     */
    fun isActive(): Boolean = isPlaying && !isPaused
    
    /**
     * Get queue size for monitoring
     */
    fun getQueueSize(): Int = audioQueue.size
    
    /**
     * Check if audio is currently being played
     */
    fun hasActiveAudio(): Boolean = isPlaying && audioQueue.isNotEmpty()
}