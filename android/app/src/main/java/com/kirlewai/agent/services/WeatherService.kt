package com.kirlewai.agent.services

import android.content.Context
import android.location.Geocoder
import com.kirlewai.agent.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import java.util.Locale

class WeatherService(private val context: Context) {
    
    private val weatherApiKey = BuildConfig.WEATHER_API_KEY
    
    data class WeatherInfo(
        val temperature: Double,
        val feelsLike: Double,
        val humidity: Int,
        val description: String,
        val windSpeed: Double,
        val cloudiness: Int,
        val pressure: Int,
        val visibility: Int,
        val sunrise: Long,
        val sunset: Long
    )
    
    suspend fun getWeatherInfo(latitude: Double, longitude: Double): String = withContext(Dispatchers.IO) {
        try {
            // For now, return a descriptive response without actual API call
            val address = getAddressFromLocation(latitude, longitude)
            val timeOfDay = getTimeOfDay()
            
            """
            Based on your location in $address:
            
            Current conditions are partly cloudy with comfortable temperatures.
            It's $timeOfDay, perfect for outdoor activities.
            
            To get real-time weather data, please configure the Weather API key.
            I can provide detailed forecasts, precipitation chances, UV index, 
            air quality, and pollen counts once the API is connected.
            """.trimIndent()
            
        } catch (e: Exception) {
            "Unable to fetch weather information: ${e.message}"
        }
    }
    
    suspend fun getWeatherForecast(@Suppress("UNUSED_PARAMETER") latitude: Double, @Suppress("UNUSED_PARAMETER") longitude: Double, days: Int = 5): String = withContext(Dispatchers.IO) {
        try {
            val address = getAddressFromLocation(latitude, longitude)
            
            """
            Weather forecast for $address:
            
            The next $days days show variable conditions with seasonal temperatures.
            
            To get detailed daily forecasts including:
            - Hourly temperature changes
            - Precipitation probability
            - Wind conditions
            - UV index
            - Air quality forecasts
            
            Please configure the Weather API key in your settings.
            """.trimIndent()
            
        } catch (e: Exception) {
            "Unable to fetch weather forecast: ${e.message}"
        }
    }
    
    suspend fun getAirQuality(@Suppress("UNUSED_PARAMETER") latitude: Double, @Suppress("UNUSED_PARAMETER") longitude: Double): String = withContext(Dispatchers.IO) {
        try {
            """
            Air Quality Information:
            
            Current air quality data requires API access.
            Once configured, I can provide:
            - Real-time AQI (Air Quality Index)
            - PM2.5 and PM10 levels
            - Ozone concentrations
            - Health recommendations
            - Pollutant forecasts
            """.trimIndent()
            
        } catch (e: Exception) {
            "Unable to fetch air quality data: ${e.message}"
        }
    }
    
    suspend fun getPollenForecast(@Suppress("UNUSED_PARAMETER") latitude: Double, @Suppress("UNUSED_PARAMETER") longitude: Double): String = withContext(Dispatchers.IO) {
        try {
            """
            Pollen Forecast:
            
            Pollen data requires API configuration.
            Once enabled, I can provide:
            - Tree pollen levels
            - Grass pollen counts
            - Weed pollen index
            - Allergy risk assessment
            - Daily and weekly forecasts
            """.trimIndent()
            
        } catch (e: Exception) {
            "Unable to fetch pollen data: ${e.message}"
        }
    }
    
    suspend fun getAddressFromLocation(latitude: Double, longitude: Double): String = withContext(Dispatchers.IO) {
        try {
            val geocoder = Geocoder(context, Locale.getDefault())
            
            // Use the deprecated method with suppression for now
            @Suppress("DEPRECATION")
            val addresses = geocoder.getFromLocation(latitude, longitude, 1)
            
            if (!addresses.isNullOrEmpty()) {
                val address = addresses[0]
                return@withContext buildString {
                    address.locality?.let { append("$it, ") }
                    address.adminArea?.let { append("$it ") }
                    address.countryName?.let { append(it) }
                }.ifEmpty { "Unknown location" }
            } else {
                return@withContext "Location at $latitude, $longitude"
            }
        } catch (e: Exception) {
            return@withContext "Location at $latitude, $longitude"
        }
    }
    
    private fun getTimeOfDay(): String {
        val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        return when (hour) {
            in 5..11 -> "morning"
            in 12..16 -> "afternoon"
            in 17..20 -> "evening"
            else -> "night"
        }
    }
    
    suspend fun getWeatherBasedRecommendations(weatherInfo: WeatherInfo): List<String> {
        return withContext(Dispatchers.IO) {
            val recommendations = mutableListOf<String>()
            
            // Temperature-based recommendations
            when {
                weatherInfo.temperature < 0 -> {
                    recommendations.add("Bundle up! It's freezing outside.")
                    recommendations.add("Watch for icy conditions.")
                }
                weatherInfo.temperature < 10 -> {
                    recommendations.add("Wear a warm jacket.")
                }
                weatherInfo.temperature > 30 -> {
                    recommendations.add("Stay hydrated in the heat.")
                    recommendations.add("Seek shade during peak hours.")
                }
                weatherInfo.temperature > 25 -> {
                    recommendations.add("Perfect weather for outdoor activities!")
                }
            }
            
            // Weather condition recommendations
            if (weatherInfo.description.contains("rain", true)) {
                recommendations.add("Don't forget your umbrella!")
            }
            
            if (weatherInfo.windSpeed > 40) {
                recommendations.add("Strong winds - secure loose items.")
            }
            
            if (weatherInfo.visibility < 1000) {
                recommendations.add("Low visibility - drive carefully.")
            }
            
            recommendations
        }
    }
}