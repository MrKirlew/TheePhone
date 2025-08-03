package com.kirlewai.agent.services

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.*
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class ModernAudioRecorder(private val context: Context) {
    
    companion object {
        private const val TAG = "ModernAudioRecorder"
        private const val SAMPLE_RATE = 44100
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }
    
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordingJob: Job? = null
    private val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
    private var currentCallback: RecordingCallback? = null
    private var currentOutputFile: File? = null
    
    interface RecordingCallback {
        fun onRecordingStarted()
        fun onRecordingCompleted(file: File)
        fun onRecordingError(error: String)
    }
    
    @SuppressLint("MissingPermission")
    fun startRecording(outputFile: File, callback: RecordingCallback) {
        if (isRecording) {
            callback.onRecordingError("Recording already in progress")
            return
        }
        
        currentCallback = callback
        currentOutputFile = outputFile
        
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )
            
            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                callback.onRecordingError("AudioRecord initialization failed")
                return
            }
            
            audioRecord?.startRecording()
            isRecording = true
            callback.onRecordingStarted()
            
            recordingJob = CoroutineScope(Dispatchers.IO).launch {
                writeAudioDataToFile(outputFile, callback)
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start recording", e)
            callback.onRecordingError("Failed to start recording: ${e.message}")
        }
    }
    
    fun stopRecording() {
        if (isRecording) {
            isRecording = false
            recordingJob?.cancel()
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
            
            // Notify that recording is completed
            currentOutputFile?.let { file ->
                currentCallback?.onRecordingCompleted(file)
            }
            
            currentCallback = null
            currentOutputFile = null
            Log.d(TAG, "Recording stopped by user")
        }
    }
    
    private suspend fun writeAudioDataToFile(outputFile: File, callback: RecordingCallback) {
        val buffer = ByteArray(bufferSize)
        
        try {
            FileOutputStream(outputFile).use { outputStream ->
                while (isRecording) {
                    val bytesRead = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    
                    if (bytesRead > 0) {
                        outputStream.write(buffer, 0, bytesRead)
                    }
                }
            }
            
            withContext(Dispatchers.Main) {
                callback.onRecordingCompleted(outputFile)
            }
            
        } catch (e: IOException) {
            Log.e(TAG, "Error writing audio data", e)
            withContext(Dispatchers.Main) {
                callback.onRecordingError("Error writing audio data: ${e.message}")
            }
        }
    }
    
    fun isCurrentlyRecording(): Boolean = isRecording
}

// Legacy MediaRecorder wrapper for backward compatibility
class LegacyAudioRecorder(private val context: Context) {
    
    @Suppress("DEPRECATION")
    private var mediaRecorder: MediaRecorder? = null
    private var isRecording = false
    
    interface LegacyRecordingCallback {
        fun onRecordingStarted()
        fun onRecordingCompleted(file: File)
        fun onRecordingError(error: String)
    }
    
    @SuppressLint("MissingPermission")
    fun startRecording(outputFile: File, callback: LegacyRecordingCallback) {
        if (isRecording) {
            callback.onRecordingError("Recording already in progress")
            return
        }
        
        try {
            @Suppress("DEPRECATION")
            mediaRecorder = MediaRecorder().apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.AMR_NB)
                setAudioEncoder(MediaRecorder.AudioEncoder.AMR_NB)
                setOutputFile(outputFile.absolutePath)
                prepare()
                start()
            }
            
            isRecording = true
            callback.onRecordingStarted()
            
        } catch (e: Exception) {
            Log.e("LegacyAudioRecorder", "Failed to start recording", e)
            callback.onRecordingError("Failed to start recording: ${e.message}")
        }
    }
    
    fun stopRecording(callback: LegacyRecordingCallback, outputFile: File) {
        if (!isRecording) return
        
        try {
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
            isRecording = false
            callback.onRecordingCompleted(outputFile)
            
        } catch (e: Exception) {
            Log.e("LegacyAudioRecorder", "Error stopping recording", e)
            callback.onRecordingError("Error stopping recording: ${e.message}")
        }
    }
    
    fun isCurrentlyRecording(): Boolean = isRecording
}