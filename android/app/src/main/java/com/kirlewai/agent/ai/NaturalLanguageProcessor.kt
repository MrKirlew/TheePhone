package com.kirlewai.agent.ai

import android.content.Context
import android.graphics.Bitmap
import com.kirlewai.agent.services.GoogleServicesManager
import com.kirlewai.agent.services.VisionAnalyzer
import com.kirlewai.agent.services.WeatherService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class NaturalLanguageProcessor(private val context: Context) {
    
    private val googleServicesManager = GoogleServicesManager(context)
    private val visionAnalyzer = VisionAnalyzer(context)
    private val weatherService = WeatherService(context)
    
    data class CommandIntent(
        val action: String,
        val service: String,
        val parameters: Map<String, Any>,
        val confidence: Float
    )
    
    suspend fun processCommand(
        userInput: String, 
        contextualData: Map<String, Any> = emptyMap(),
        image: Bitmap? = null
    ): String = withContext(Dispatchers.IO) {
        
        val intent = analyzeIntent(userInput, contextualData)
        
        when (intent.service) {
            "calendar" -> processCalendarCommand(intent, userInput)
            "email" -> processEmailCommand(intent, userInput)
            "drive" -> processDriveCommand(intent, userInput)
            "weather" -> processWeatherCommand(intent, userInput)
            "vision" -> processVisionCommand(intent, userInput, image)
            "location" -> processLocationCommand(intent, userInput)
            "contacts" -> processContactsCommand(intent, userInput)
            "general" -> processGeneralCommand(userInput, contextualData, image)
            else -> processGeneralCommand(userInput, contextualData, image)
        }
    }
    
    private suspend fun analyzeIntent(userInput: String, @Suppress("UNUSED_PARAMETER") context: Map<String, Any>): CommandIntent {
        return when {
            userInput.contains("calendar", ignoreCase = true) || 
            userInput.contains("schedule", ignoreCase = true) ||
            userInput.contains("meeting", ignoreCase = true) -> 
                CommandIntent("check", "calendar", mapOf("timeframe" to "today"), 0.8f)
                
            userInput.contains("email", ignoreCase = true) ||
            userInput.contains("mail", ignoreCase = true) -> 
                CommandIntent("check", "email", mapOf("filter" to "unread"), 0.8f)
                
            userInput.contains("drive", ignoreCase = true) ||
            userInput.contains("document", ignoreCase = true) ||
            userInput.contains("file", ignoreCase = true) -> 
                CommandIntent("find", "drive", mapOf("query" to userInput), 0.8f)
                
            userInput.contains("weather", ignoreCase = true) ||
            userInput.contains("temperature", ignoreCase = true) -> 
                CommandIntent("get", "weather", emptyMap(), 0.9f)
                
            userInput.contains("location", ignoreCase = true) ||
            userInput.contains("where am i", ignoreCase = true) -> 
                CommandIntent("get", "location", emptyMap(), 0.9f)
                
            userInput.contains("contact", ignoreCase = true) ||
            userInput.contains("phone", ignoreCase = true) -> 
                CommandIntent("find", "contacts", mapOf("name" to userInput), 0.7f)
                
            else -> CommandIntent("process", "general", emptyMap(), 0.6f)
        }
    }
    
    private suspend fun processCalendarCommand(intent: CommandIntent, userInput: String): String {
        val hasServices = googleServicesManager.hasGoogleServicesAvailable()
        if (!hasServices) {
            return "Please sign in with Google to access your calendar."
        }
        
        return when (intent.action) {
            "check", "list", "get" -> {
                val timeframe = intent.parameters["timeframe"] as? String ?: "today"
                "I would check your calendar for $timeframe, but this requires the backend Google API integration to be active."
            }
            "create", "add" -> {
                "I'll help you create a calendar event. What are the details? (Note: This requires backend integration)"
            }
            else -> processGeneralCommand(userInput, emptyMap(), null)
        }
    }
    
    private suspend fun processEmailCommand(intent: CommandIntent, userInput: String): String {
        val hasServices = googleServicesManager.hasGoogleServicesAvailable()
        if (!hasServices) {
            return "Please sign in with Google to access your email."
        }
        
        return when (intent.action) {
            "check", "read" -> {
                val filter = intent.parameters["filter"] as? String ?: "unread"
                "I would check your $filter emails, but this requires the backend Google API integration to be active."
            }
            "create", "send" -> {
                val recipient = intent.parameters["recipient"] as? String ?: ""
                "I would prepare to send email to $recipient, but this requires backend integration."
            }
            else -> processGeneralCommand(userInput, emptyMap(), null)
        }
    }
    
    private suspend fun processDriveCommand(intent: CommandIntent, userInput: String): String {
        val hasServices = googleServicesManager.hasGoogleServicesAvailable()
        if (!hasServices) {
            return "Please sign in with Google to access your Drive."
        }
        
        return when (intent.action) {
            "find", "search" -> {
                val query = intent.parameters["query"] as? String ?: ""
                "I would search Drive for: $query, but this requires the backend Google API integration to be active."
            }
            "list" -> {
                "I would get your recent Drive files, but this requires backend integration."
            }
            else -> processGeneralCommand(userInput, emptyMap(), null)
        }
    }
    
    private suspend fun processWeatherCommand(@Suppress("UNUSED_PARAMETER") intent: CommandIntent, @Suppress("UNUSED_PARAMETER") userInput: String): String {
        val location = googleServicesManager.getCurrentLocation()
        return if (location != null) {
            weatherService.getWeatherInfo(location.latitude, location.longitude)
        } else {
            "Unable to get your location for weather information. Please enable location services."
        }
    }
    
    private suspend fun processVisionCommand(@Suppress("UNUSED_PARAMETER") intent: CommandIntent, userInput: String, image: Bitmap?): String {
        return if (image != null) {
            visionAnalyzer.analyzeImage(image, userInput)
        } else {
            "Please provide an image for visual analysis."
        }
    }
    
    private suspend fun processLocationCommand(@Suppress("UNUSED_PARAMETER") intent: CommandIntent, @Suppress("UNUSED_PARAMETER") userInput: String): String {
        val location = googleServicesManager.getCurrentLocation()
        return if (location != null) {
            val geocodedAddress = weatherService.getAddressFromLocation(location.latitude, location.longitude)
            "You are currently at: $geocodedAddress (${location.latitude}, ${location.longitude})"
        } else {
            "Unable to determine your current location. Please enable location services."
        }
    }
    
    private suspend fun processContactsCommand(intent: CommandIntent, userInput: String): String {
        val hasServices = googleServicesManager.hasGoogleServicesAvailable()
        if (!hasServices) {
            return "Please sign in with Google to access your contacts."
        }
        
        return when (intent.action) {
            "find", "search" -> {
                val name = intent.parameters["name"] as? String ?: ""
                "I would search contacts for: $name, but this requires backend Google API integration."
            }
            else -> processGeneralCommand(userInput, emptyMap(), null)
        }
    }
    
    private suspend fun processGeneralCommand(
        userInput: String, 
        contextualData: Map<String, Any>,
        image: Bitmap?
    ): String {
        val envContext = googleServicesManager.getEnvironmentalContext()
        val fullContext = contextualData + envContext
        
        return generateContextualResponse(userInput, fullContext, image)
    }
    
    private suspend fun generateContextualResponse(
        userInput: String,
        context: Map<String, Any>,
        image: Bitmap?
    ): String {
        val timeContext = context["hour"] as? Int ?: 12
        val location = if (context.containsKey("latitude")) {
            "at your current location"
        } else {
            ""
        }
        
        return when {
            userInput.contains("hello", ignoreCase = true) || 
            userInput.contains("hi", ignoreCase = true) -> {
                val greeting = when (timeContext) {
                    in 5..11 -> "Good morning"
                    in 12..16 -> "Good afternoon" 
                    in 17..20 -> "Good evening"
                    else -> "Hello"
                }
                "$greeting! I'm Kirlew AI Agent, powered by Google Cloud Vertex AI and Gemini 1.5 Pro. I use Google Secret Manager for secure authentication - no local API keys needed! How can I assist you today?"
            }
            
            userInput.contains("time", ignoreCase = true) -> {
                val currentTime = java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault()).format(java.util.Date())
                "The current time is $currentTime. I can provide much more contextual time and scheduling information through my Google Cloud backend integration."
            }
            
            userInput.contains("weather", ignoreCase = true) -> {
                "I can provide weather information $location! My backend integrates with Google Cloud APIs for real-time weather data through Vertex AI processing."
            }
            
            userInput.contains("what can you do", ignoreCase = true) ||
            userInput.contains("capabilities", ignoreCase = true) -> {
                """I'm Kirlew AI Agent with advanced capabilities powered by Google Cloud:
                
🧠 Advanced AI: Gemini 1.5 Pro via Vertex AI
🔒 Secure: Google Secret Manager for credentials  
📊 Smart: Environmental and contextual awareness
🌐 Connected: Google Workspace integration
🎯 Intelligent: Natural language understanding
📱 Multimodal: Text, voice, and image processing

All processing happens securely through Google Cloud infrastructure!"""
            }
            
            userInput.contains("api key", ignoreCase = true) ||
            userInput.contains("configuration", ignoreCase = true) -> {
                "Great question! I don't use local API keys for security reasons. Instead, I'm powered by Google Cloud Vertex AI with service account authentication and Google Secret Manager for credential storage. This enterprise-grade approach is much more secure than storing API keys locally!"
            }
            
            image != null -> {
                "I can see you've shared an image! My vision capabilities are powered by Gemini 1.5 Pro through Google Cloud. For full image analysis, the backend integration processes images securely using Vertex AI."
            }
            
            userInput.contains("calculate", ignoreCase = true) || 
            userInput.contains("math", ignoreCase = true) -> {
                "I can help with calculations! My mathematical reasoning is powered by Gemini 1.5 Pro running on Google Cloud infrastructure. What would you like me to calculate?"
            }
            
            else -> {
                "I understand you're asking: \"$userInput\". I'm Kirlew AI Agent, powered by Google's Gemini 1.5 Pro through Vertex AI. " +
                "I use Google Cloud's secure infrastructure with credentials managed through Google Secret Manager. " +
                "My reasoning, perception, and action capabilities are designed to work through secure backend integration. How can I help you further?"
            }
        }
    }
}