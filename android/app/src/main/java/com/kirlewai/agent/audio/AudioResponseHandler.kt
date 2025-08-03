package com.kirlewai.agent.audio

import android.content.Context
import android.media.MediaPlayer
import android.util.Log
import java.io.File
import java.io.FileOutputStream

/**
 * Helper class to handle audio response from the server
 */
class AudioResponseHandler(private val context: Context) {
    
    private val TAG = "AudioResponseHandler"
    private var mediaPlayer: MediaPlayer? = null
    private var completionListener: (() -> Unit)? = null
    
    /**
     * Play audio from byte array (MP3 format)
     */
    fun playAudioResponse(audioData: ByteArray) {
        try {
            // Save audio data to temporary file
            val tempFile = File(context.cacheDir, "response_${System.currentTimeMillis()}.mp3")
            FileOutputStream(tempFile).use { fos ->
                fos.write(audioData)
            }
            
            // Play the audio file
            playAudioFile(tempFile)
            
        } catch (e: Exception) {
            Log.e(TAG, "Error playing audio response", e)
        }
    }
    
    /**
     * Play audio from file
     */
    fun playAudioFile(audioFile: File) {
        try {
            // Release previous player if exists
            releasePlayer()
            
            // Create and setup new player
            mediaPlayer = MediaPlayer().apply {
                setDataSource(audioFile.absolutePath)
                setOnPreparedListener { mp ->
                    mp.start()
                    Log.d(TAG, "Playing audio response")
                }
                setOnCompletionListener {
                    Log.d(TAG, "Audio playback completed")
                    completionListener?.invoke()
                    releasePlayer()
                    // Delete temp file
                    audioFile.delete()
                }
                setOnErrorListener { _, what, extra ->
                    Log.e(TAG, "MediaPlayer error: what=$what, extra=$extra")
                    false
                }
                prepareAsync()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error setting up media player", e)
        }
    }
    
    /**
     * Stop and release the media player
     */
    fun releasePlayer() {
        mediaPlayer?.apply {
            if (isPlaying) {
                stop()
            }
            release()
        }
        mediaPlayer = null
    }
    
    /**
     * Check if audio is currently playing
     */
    fun isPlaying(): Boolean = mediaPlayer?.isPlaying == true
    
    /**
     * Set a listener to be called when audio playback completes
     */
    fun setCompletionListener(listener: () -> Unit) {
        completionListener = listener
    }
}
