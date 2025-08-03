package com.kirlewai.agent.wakeword

import android.content.Context
import android.util.Log
import kotlinx.coroutines.*
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Wake Word Detection System for Hands-Free Activation
 * 
 * This implements the always-on listener described in Realtime_Humanlike_AIAgent.txt
 * 
 * Note: This is a research implementation. For production, consider integrating
 * with openWakeWord, Picovoice Porcupine, or similar proven solutions.
 */
class WakeWordDetector(
    private val context: Context
) {
    companion object {
        private const val TAG = "WakeWordDetector"
        private const val SAMPLE_RATE = 16000 // Optimal for wake word detection
        private const val FRAME_SIZE_MS = 30 // 30ms frames
        private const val FRAME_SIZE_SAMPLES = SAMPLE_RATE * FRAME_SIZE_MS / 1000
        private const val ENERGY_THRESHOLD = 0.01f // Minimum energy to consider
        private const val DETECTION_WINDOW_MS = 2000 // 2 second detection window
    }
    
    // Wake word patterns (simplified approach - in production use ML models)
    private val wakeWords = listOf(
        "hey kirlew",
        "kirlew",
        "ok kirlew",
        "listen kirlew"
    )
    
    // Detection state
    private var isListening = false
    private var detectionJob: Job? = null
    private val detectionScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    // Audio analysis
    private val audioBuffer = mutableListOf<Float>()
    private val maxBufferSize = SAMPLE_RATE * 5 // 5 seconds of audio
    
    // Wake word detection callback
    private var onWakeWordDetected: ((String) -> Unit)? = null
    
    // Simple pattern matching state
    private var currentPattern = ""
    private var patternStartTime = 0L
    
    /**
     * Wake word detection configuration
     */
    data class WakeWordConfig(
        val sensitivity: Float = 0.7f, // Detection threshold (0.0 - 1.0)
        val enableContinuousListening: Boolean = true,
        val powerOptimized: Boolean = true,
        val customWakeWords: List<String> = emptyList()
    )
    
    /**
     * Start wake word detection
     */
    fun startDetection(
        audioSource: suspend () -> ByteArray?,
        config: WakeWordConfig = WakeWordConfig(),
        onDetected: (String) -> Unit
    ) {
        if (isListening) {
            Log.w(TAG, "Wake word detection already active")
            return
        }
        
        onWakeWordDetected = onDetected
        isListening = true
        
        detectionJob = detectionScope.launch {
            try {
                detectWakeWordLoop(audioSource, config)
            } catch (e: Exception) {
                Log.e(TAG, "Error in wake word detection", e)
            }
        }
        
        Log.i(TAG, "Started wake word detection")
    }
    
    /**
     * Main wake word detection loop
     */
    private suspend fun detectWakeWordLoop(
        audioSource: suspend () -> ByteArray?,
        config: WakeWordConfig
    ) {
        val frameBuffer = FloatArray(FRAME_SIZE_SAMPLES)
        var frameIndex = 0
        
        while (isListening) {
            try {
                // Get audio data
                val audioData = audioSource() ?: continue
                
                // Convert to float array for processing
                val audioFloats = bytesToFloats(audioData)
                
                // Process in frames
                for (sample in audioFloats) {
                    frameBuffer[frameIndex] = sample
                    frameIndex++
                    
                    if (frameIndex >= FRAME_SIZE_SAMPLES) {
                        // Process complete frame
                        processAudioFrame(frameBuffer, config)
                        frameIndex = 0
                    }
                }
                
                // Yield to prevent blocking
                yield()
                
            } catch (e: CancellationException) {
                break
            } catch (e: Exception) {
                Log.e(TAG, "Error processing wake word audio", e)
                delay(100) // Brief delay before retrying
            }
        }
    }
    
    /**
     * Process audio frame for wake word detection
     */
    private fun processAudioFrame(audioFrame: FloatArray, config: WakeWordConfig) {
        // Calculate energy level
        val energy = calculateEnergy(audioFrame)
        
        // Skip processing if energy is too low (silence)
        if (energy < ENERGY_THRESHOLD) {
            return
        }
        
        // Add to rolling buffer
        audioBuffer.addAll(audioFrame.toList())
        if (audioBuffer.size > maxBufferSize) {
            // Remove oldest samples
            val removeCount = audioBuffer.size - maxBufferSize
            repeat(removeCount) { audioBuffer.removeAt(0) }
        }
        
        // Perform wake word detection
        val detectedWord = detectWakeWordInBuffer(config)
        if (detectedWord != null) {
            Log.i(TAG, "Wake word detected: $detectedWord")
            onWakeWordDetected?.invoke(detectedWord)
            
            // Clear buffer to avoid duplicate detections
            audioBuffer.clear()
        }
    }
    
    /**
     * Detect wake word in audio buffer
     * 
     * Note: This is a simplified implementation. For production use,
     * integrate with ML-based solutions like openWakeWord or Porcupine.
     */
    private fun detectWakeWordInBuffer(config: WakeWordConfig): String? {
        if (audioBuffer.size < SAMPLE_RATE) { // Need at least 1 second
            return null
        }
        
        // Convert audio to simple features for pattern matching
        val features = extractSimpleFeatures(audioBuffer)
        
        // Check against known wake word patterns
        val allWakeWords = wakeWords + config.customWakeWords
        
        for (wakeWord in allWakeWords) {
            val confidence = matchWakeWordPattern(features, wakeWord, config.sensitivity)
            if (confidence > config.sensitivity) {
                return wakeWord
            }
        }
        
        return null
    }
    
    /**
     * Extract simple audio features for wake word matching
     */
    private fun extractSimpleFeatures(audioData: List<Float>): AudioFeatures {
        val windowSize = SAMPLE_RATE / 4 // 250ms windows
        val windows = audioData.chunked(windowSize)
        
        val energies = windows.map { window ->
            calculateEnergy(window.toFloatArray())
        }
        
        val zeroCrossings = windows.map { window ->
            calculateZeroCrossings(window.toFloatArray())
        }
        
        val spectralCentroids = windows.map { window ->
            calculateSpectralCentroid(window.toFloatArray())
        }
        
        return AudioFeatures(
            energies = energies,
            zeroCrossings = zeroCrossings,
            spectralCentroids = spectralCentroids,
            duration = audioData.size.toFloat() / SAMPLE_RATE
        )
    }
    
    /**
     * Match audio features against wake word pattern
     */
    private fun matchWakeWordPattern(features: AudioFeatures, wakeWord: String, @Suppress("UNUSED_PARAMETER") threshold: Float): Float {
        // Simplified pattern matching based on audio characteristics
        // In production, this would use trained ML models
        
        val expectedDuration = estimateWakeWordDuration(wakeWord)
        val durationMatch = 1.0f - kotlin.math.abs(features.duration - expectedDuration) / expectedDuration
        
        // Check for voice activity pattern
        val voiceActivityScore = calculateVoiceActivityScore(features)
        
        // Check for speech-like characteristics
        val speechScore = calculateSpeechScore(features)
        
        // Combine scores
        val confidence = (durationMatch * 0.3f + voiceActivityScore * 0.4f + speechScore * 0.3f)
        
        return confidence
    }
    
    /**
     * Calculate energy (RMS) of audio frame
     */
    private fun calculateEnergy(audioFrame: FloatArray): Float {
        var sum = 0.0
        for (sample in audioFrame) {
            sum += sample * sample
        }
        return kotlin.math.sqrt(sum / audioFrame.size).toFloat()
    }
    
    /**
     * Calculate zero crossing rate
     */
    private fun calculateZeroCrossings(audioFrame: FloatArray): Float {
        var crossings = 0
        for (i in 1 until audioFrame.size) {
            if ((audioFrame[i-1] >= 0 && audioFrame[i] < 0) || 
                (audioFrame[i-1] < 0 && audioFrame[i] >= 0)) {
                crossings++
            }
        }
        return crossings.toFloat() / audioFrame.size
    }
    
    /**
     * Calculate spectral centroid (simplified)
     */
    private fun calculateSpectralCentroid(audioFrame: FloatArray): Float {
        // Simplified spectral centroid calculation
        // In production, use proper FFT analysis
        val highFreqEnergy = audioFrame.filterIndexed { index, _ -> 
            index > audioFrame.size / 2 
        }.map { it * it }.sum()
        
        val totalEnergy = audioFrame.map { it * it }.sum()
        
        return if (totalEnergy > 0) highFreqEnergy / totalEnergy else 0f
    }
    
    /**
     * Estimate wake word duration
     */
    private fun estimateWakeWordDuration(wakeWord: String): Float {
        // Rough estimate: 0.3 seconds per syllable
        val syllableCount = wakeWord.split(" ").sumOf { word ->
            kotlin.math.max(1, word.length / 3) // Very rough syllable estimation
        }
        return syllableCount * 0.3f
    }
    
    /**
     * Calculate voice activity score
     */
    private fun calculateVoiceActivityScore(features: AudioFeatures): Float {
        val avgEnergy = features.energies.average().toFloat()
        val energyVariance = features.energies.map { (it - avgEnergy) * (it - avgEnergy) }.average().toFloat()
        
        // Voice has moderate energy with some variation
        val energyScore = if (avgEnergy > 0.005f && avgEnergy < 0.5f) 1.0f else 0.0f
        val varianceScore = if (energyVariance > 0.001f) 1.0f else 0.5f
        
        return (energyScore + varianceScore) / 2.0f
    }
    
    /**
     * Calculate speech-like characteristics score
     */
    private fun calculateSpeechScore(features: AudioFeatures): Float {
        val avgZeroCrossings = features.zeroCrossings.average().toFloat()
        val avgSpectralCentroid = features.spectralCentroids.average().toFloat()
        
        // Speech typically has moderate zero crossing rate and spectral characteristics
        val zcrScore = if (avgZeroCrossings > 0.01f && avgZeroCrossings < 0.1f) 1.0f else 0.5f
        val spectralScore = if (avgSpectralCentroid > 0.1f && avgSpectralCentroid < 0.6f) 1.0f else 0.5f
        
        return (zcrScore + spectralScore) / 2.0f
    }
    
    /**
     * Convert byte array to float array
     */
    private fun bytesToFloats(bytes: ByteArray): FloatArray {
        val floats = FloatArray(bytes.size / 2)
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        
        for (i in floats.indices) {
            floats[i] = buffer.short.toFloat() / Short.MAX_VALUE
        }
        
        return floats
    }
    
    /**
     * Stop wake word detection
     */
    fun stopDetection() {
        if (!isListening) return
        
        try {
            isListening = false
            detectionJob?.cancel()
            detectionJob = null
            audioBuffer.clear()
            
            Log.i(TAG, "Stopped wake word detection")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping wake word detection", e)
        }
    }
    
    /**
     * Release resources
     */
    fun release() {
        try {
            stopDetection()
            detectionScope.cancel()
            
            Log.i(TAG, "Wake word detector resources released")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing wake word detector", e)
        }
    }
    
    /**
     * Check if wake word detection is active
     */
    fun isActive(): Boolean = isListening
    
    // Data classes for audio features
    private data class AudioFeatures(
        val energies: List<Float>,
        val zeroCrossings: List<Float>,
        val spectralCentroids: List<Float>,
        val duration: Float
    )
}

/**
 * Factory for creating optimized wake word detectors
 */
object WakeWordDetectorFactory {
    
    /**
     * Create a power-optimized wake word detector
     */
    fun createPowerOptimizedDetector(context: Context): WakeWordDetector {
        return WakeWordDetector(context)
    }
    
    /**
     * Create a high-accuracy wake word detector
     */
    fun createHighAccuracyDetector(context: Context): WakeWordDetector {
        return WakeWordDetector(context)
    }
    
    /**
     * Integration point for future ML-based detectors
     */
    fun createMLBasedDetector(context: Context, @Suppress("UNUSED_PARAMETER") modelPath: String): WakeWordDetector {
        // TODO: Implement integration with openWakeWord or Porcupine
        // This would load the ML model and use it for detection
        return WakeWordDetector(context)
    }
}