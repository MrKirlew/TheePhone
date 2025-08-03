package com.kirlewai.agent.speech

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import java.util.Locale
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

class TextToSpeechService(private val context: Context) {
    
    private var tts: TextToSpeech? = null
    private var isInitialized = false
    private val TAG = "TextToSpeechService"
    var isSpeechEnabled = true // Public property to control speech
    
    // Callback for when TTS finishes speaking
    private var onSpeechCompleteListener: (() -> Unit)? = null
    
    suspend fun initialize(): Boolean = suspendCoroutine { continuation ->
        Log.d(TAG, "Initializing TextToSpeech")
        
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                // Set language to default locale
                val result = tts?.setLanguage(Locale.getDefault())
                
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.e(TAG, "Language not supported")
                    isInitialized = false
                    continuation.resume(false)
                } else {
                    // Set up utterance progress listener
                    tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                        override fun onStart(utteranceId: String?) {
                            Log.d(TAG, "Started speaking: $utteranceId")
                        }
                        
                        override fun onDone(utteranceId: String?) {
                            Log.d(TAG, "Finished speaking: $utteranceId")
                            onSpeechCompleteListener?.invoke()
                        }
                        
                        @Deprecated("Deprecated in API level 27")
                        override fun onError(utteranceId: String?) {
                            Log.e(TAG, "Error speaking: $utteranceId")
                        }
                    })
                    
                    // Set speech rate and pitch for natural sound
                    tts?.setSpeechRate(1.0f)
                    tts?.setPitch(1.0f)
                    
                    isInitialized = true
                    Log.d(TAG, "TextToSpeech initialized successfully")
                    continuation.resume(true)
                }
            } else {
                Log.e(TAG, "TextToSpeech initialization failed with status: $status")
                isInitialized = false
                continuation.resume(false)
            }
        }
    }
    
    fun speak(text: String, onComplete: (() -> Unit)? = null) {
        if (!isSpeechEnabled) {
            Log.d(TAG, "Speech is disabled, not speaking")
            return
        }
        
        if (!isInitialized || tts == null) {
            Log.e(TAG, "TTS not initialized, cannot speak")
            return
        }
        
        // Stop any ongoing speech
        tts?.stop()
        
        // Set the completion listener
        onSpeechCompleteListener = onComplete
        
        // Generate unique utterance ID
        val utteranceId = "tts_${System.currentTimeMillis()}"
        
        // Speak the text
        val result = tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
        
        if (result == TextToSpeech.SUCCESS) {
            Log.d(TAG, "Speaking: $text")
        } else {
            Log.e(TAG, "Failed to speak text")
        }
    }
    
    fun stop() {
        tts?.stop()
        Log.d(TAG, "Stopped speaking")
    }
    
    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        isInitialized = false
        Log.d(TAG, "TTS shut down")
    }
    
    fun isSpeaking(): Boolean {
        return tts?.isSpeaking ?: false
    }
    
    fun setSpeechRate(rate: Float) {
        tts?.setSpeechRate(rate.coerceIn(0.5f, 2.0f))
    }
    
    fun setPitch(pitch: Float) {
        tts?.setPitch(pitch.coerceIn(0.5f, 2.0f))
    }
    
    fun setLanguage(locale: Locale): Boolean {
        val result = tts?.setLanguage(locale)
        return result != TextToSpeech.LANG_MISSING_DATA && result != TextToSpeech.LANG_NOT_SUPPORTED
    }
    
    fun setOnCompletionListener(listener: () -> Unit) {
        onSpeechCompleteListener = listener
    }
}