package com.kirlewai.agent.network

import android.graphics.Bitmap
import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.content
import com.kirlewai.agent.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object GeminiService {
    
    // API key is securely stored in BuildConfig from local.properties
    private val model: GenerativeModel? by lazy {
        try {
            if (BuildConfig.GEMINI_API_KEY.isNotBlank() && 
                !BuildConfig.GEMINI_API_KEY.startsWith("YOUR_GEMINI")) {
                GenerativeModel(
                    modelName = "gemini-1.5-flash",
                    apiKey = BuildConfig.GEMINI_API_KEY
                )
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }
    
    suspend fun generateResponse(userInput: String, context: String = ""): String {
        return withContext(Dispatchers.IO) {
            try {
                android.util.Log.d("GeminiService", "generateResponse called with: '$userInput'")
                
                // Check if API key is configured
                val geminiModel = model
                if (geminiModel == null) {
                    android.util.Log.d("GeminiService", "No API key configured, using mock response")
                    return@withContext generateMockResponse(userInput)
                }
                
                val prompt = buildString {
                    append("You are Kirlew AI Agent, a powerful multimodal AI assistant. ")
                    append("You can help with tasks, answer questions, and provide assistance. ")
                    if (context.isNotEmpty()) {
                        append("Context: $context ")
                    }
                    append("User: $userInput")
                }
                
                val response = geminiModel.generateContent(prompt)
                response.text ?: "I couldn't generate a response right now."
                
            } catch (e: Exception) {
                "I'm experiencing some technical difficulties. Error: ${e.message}"
            }
        }
    }
    
    @Suppress("unused")
    suspend fun generateResponseWithImage(userInput: String, bitmap: Bitmap): String {
        return withContext(Dispatchers.IO) {
            try {
                val geminiModel = model ?: return@withContext "Image analysis requires a configured Gemini API key. Currently running in demo mode."
                
                val prompt = content {
                    text("You are Kirlew AI Agent. Analyze this image and respond to: $userInput")
                    image(bitmap)
                }
                
                val response = geminiModel.generateContent(prompt)
                response.text ?: "I couldn't analyze the image right now."
                
            } catch (e: Exception) {
                "I'm having trouble analyzing the image. Error: ${e.message}"
            }
        }
    }
    
    private fun generateMockResponse(userInput: String): String {
        android.util.Log.d("GeminiService", "generateMockResponse called with: '$userInput'")
        // Generate intelligent mock responses based on user input
        val response = when {
            userInput.contains("hello", ignoreCase = true) || 
            userInput.contains("hi", ignoreCase = true) -> 
                "Hello! I'm Kirlew AI Agent. I'm ready to help you with any questions or tasks. What can I do for you today?"
                
            userInput.contains("weather", ignoreCase = true) -> 
                "I'd love to help you with weather information! However, I need access to weather APIs to provide current conditions. You can check your local weather app for the most accurate forecast."
                
            userInput.contains("time", ignoreCase = true) -> 
                "The current time is ${java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault()).format(java.util.Date())}."
                
            userInput.contains("thank", ignoreCase = true) -> 
                "You're very welcome! I'm here whenever you need assistance. Is there anything else I can help you with?"
                
            userInput.contains("what", ignoreCase = true) && userInput.contains("do", ignoreCase = true) -> 
                "I'm Kirlew AI Agent! I can help you with various tasks like answering questions, providing information, helping with calculations, and much more. I can also process images and voice commands. What would you like to explore?"
                
            userInput.contains("calculate", ignoreCase = true) || userInput.contains("math", ignoreCase = true) -> 
                "I can help with calculations! Please provide the math problem you'd like me to solve."
                
            else -> 
                "That's an interesting question! I understand you're asking about: \"$userInput\". " +
                "While I'm currently running in demo mode, I'm designed to be a powerful AI assistant. " +
                "To unlock my full capabilities including real-time information and advanced reasoning, " +
                "you'll need to configure the Gemini API key. Is there anything else I can help you with using my current capabilities?"
        }
        
        android.util.Log.d("GeminiService", "Generated mock response: '$response'")
        return response
    }
}