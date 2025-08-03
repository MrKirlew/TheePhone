package com.kirlewai.agent.ai

import android.content.Context
import android.graphics.Bitmap
import com.kirlewai.agent.services.GoogleServicesManager
import com.kirlewai.agent.services.VisionAnalyzer
import com.kirlewai.agent.services.WeatherService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

class AIOrchestrator(private val context: Context) {
    
    private val googleServicesManager = GoogleServicesManager(context)
    private val visionAnalyzer = VisionAnalyzer(context)
    private val weatherService = WeatherService(context)
    private val nlpProcessor = NaturalLanguageProcessor(context)
    
    data class AIResponse(
        val text: String,
        val actions: List<Action>,
        val insights: Map<String, Any>,
        val suggestions: List<String>
    )
    
    data class Action(
        val type: String,
        val description: String,
        val parameters: Map<String, Any>
    )
    
    suspend fun orchestrateResponse(
        userInput: String,
        conversationHistory: List<String> = emptyList(),
        image: Bitmap? = null
    ): AIResponse = withContext(Dispatchers.IO) {
        
        val contextualData = mapOf(
            "conversationHistory" to conversationHistory.joinToString("\n"),
            "hasImage" to (image != null)
        )
        
        val responseText = nlpProcessor.processCommand(userInput, contextualData, image)
        
        AIResponse(
            text = responseText,
            actions = generateSuggestedActions(userInput),
            insights = mapOf(
                "architecture" to "Google Cloud Vertex AI",
                "security" to "Google Secret Manager",
                "model" to "Gemini 1.5 Pro"
            ),
            suggestions = generateSuggestions(userInput)
        )
    }
    
    private fun generateSuggestedActions(userInput: String): List<Action> {
        return when {
            userInput.contains("calendar", ignoreCase = true) -> listOf(
                Action("check_calendar", "Check your calendar", mapOf("timeframe" to "today"))
            )
            userInput.contains("email", ignoreCase = true) -> listOf(
                Action("check_email", "Check your emails", mapOf("filter" to "unread"))
            )
            userInput.contains("weather", ignoreCase = true) -> listOf(
                Action("get_weather", "Get weather information", mapOf("location" to "current"))
            )
            else -> listOf(
                Action("continue_conversation", "Continue the conversation", emptyMap())
            )
        }
    }
    
    private fun generateSuggestions(userInput: String): List<String> {
        return when {
            userInput.contains("hello", ignoreCase = true) -> listOf(
                "Ask about the weather",
                "Check your calendar",
                "Learn about my capabilities"
            )
            userInput.contains("weather", ignoreCase = true) -> listOf(
                "Get detailed forecast",
                "Check air quality",
                "Set weather alerts"
            )
            userInput.contains("calendar", ignoreCase = true) -> listOf(
                "Create new event",
                "Check tomorrow's schedule",
                "Find free time slots"
            )
            else -> listOf(
                "Ask about Google Cloud integration",
                "Learn about security features",
                "Explore AI capabilities"
            )
        }
    }
    
    private fun parseAIResponse(jsonResponse: String): AIResponse {
        return try {
            val json = JSONObject(jsonResponse)
            
            val actions = json.optJSONArray("actions")?.let { actionsArray ->
                (0 until actionsArray.length()).map { i ->
                    val action = actionsArray.getJSONObject(i)
                    Action(
                        type = action.optString("type", "unknown"),
                        description = action.optString("description", ""),
                        parameters = action.optJSONObject("parameters")?.let { params ->
                            params.keys().asSequence().associateWith { params.get(it) }
                        } ?: emptyMap()
                    )
                }
            } ?: emptyList()
            
            val insights = json.optJSONObject("insights")?.let { insightsObj ->
                insightsObj.keys().asSequence().associateWith { insightsObj.get(it) }
            } ?: emptyMap()
            
            val suggestions = json.optJSONArray("suggestions")?.let { suggestionsArray ->
                (0 until suggestionsArray.length()).map { suggestionsArray.getString(it) }
            } ?: emptyList()
            
            AIResponse(
                text = json.optString("response", "I processed your request."),
                actions = actions,
                insights = insights,
                suggestions = suggestions
            )
            
        } catch (e: Exception) {
            AIResponse(
                text = jsonResponse, // Fallback to raw response if not JSON
                actions = emptyList(),
                insights = emptyMap(),
                suggestions = emptyList()
            )
        }
    }
    
    suspend fun executeAction(action: Action): String = withContext(Dispatchers.IO) {
        when (action.type) {
            "calendar_check" -> {
                val timeframe = action.parameters["timeframe"] as? String ?: "today"
                "Checking calendar for $timeframe..."
            }
            "email_send" -> {
                val recipient = action.parameters["recipient"] as? String ?: ""
                val subject = action.parameters["subject"] as? String ?: ""
                "Preparing email to $recipient with subject: $subject"
            }
            "weather_check" -> {
                val location = googleServicesManager.getCurrentLocation()
                if (location != null) {
                    weatherService.getWeatherInfo(location.latitude, location.longitude)
                } else {
                    "Unable to get weather without location access"
                }
            }
            "vision_analyze" -> {
                "Ready to analyze images. Please provide an image."
            }
            else -> "Action type '${action.type}' is not yet implemented"
        }
    }
}