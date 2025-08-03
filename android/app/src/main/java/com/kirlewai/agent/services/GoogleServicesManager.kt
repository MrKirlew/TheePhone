package com.kirlewai.agent.services

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import androidx.core.app.ActivityCompat
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import com.google.android.gms.tasks.Tasks
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

class GoogleServicesManager(private val context: Context) {
    
    private var googleAccount: GoogleSignInAccount? = null
    private val fusedLocationClient: FusedLocationProviderClient = 
        LocationServices.getFusedLocationProviderClient(context)
    
    @Suppress("unused")
    fun setGoogleAccount(account: GoogleSignInAccount) {
        googleAccount = account
    }
    
    suspend fun getCurrentLocation(): Location? = withContext(Dispatchers.IO) {
        try {
            if (ActivityCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_FINE_LOCATION
                ) != PackageManager.PERMISSION_GRANTED && ActivityCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                return@withContext null
            }
            val locationTask = fusedLocationClient.lastLocation
            Tasks.await(locationTask, 5, TimeUnit.SECONDS)
        } catch (e: Exception) {
            null
        }
    }
    
    suspend fun getEnvironmentalContext(): Map<String, Any> = withContext(Dispatchers.IO) {
        val contextMap = mutableMapOf<String, Any>()
        
        // Time context
        val now = java.util.Calendar.getInstance()
        contextMap["time"] = now.time.toString()
        contextMap["hour"] = now.get(java.util.Calendar.HOUR_OF_DAY)
        contextMap["dayOfWeek"] = now.get(java.util.Calendar.DAY_OF_WEEK)
        contextMap["dayOfMonth"] = now.get(java.util.Calendar.DAY_OF_MONTH)
        contextMap["month"] = now.get(java.util.Calendar.MONTH)
        contextMap["year"] = now.get(java.util.Calendar.YEAR)
        
        // Location context
        getCurrentLocation()?.let { location ->
            contextMap["latitude"] = location.latitude
            contextMap["longitude"] = location.longitude
            contextMap["altitude"] = location.altitude
            contextMap["accuracy"] = location.accuracy
        }
        
        // Device context
        contextMap["batteryLevel"] = getBatteryLevel()
        contextMap["isCharging"] = isCharging()
        contextMap["networkType"] = getNetworkType()
        
        contextMap
    }
    
    private fun getBatteryLevel(): Float {
        val batteryIntent = context.registerReceiver(null, 
            android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        val level = batteryIntent?.getIntExtra(android.os.BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryIntent?.getIntExtra(android.os.BatteryManager.EXTRA_SCALE, -1) ?: -1
        return if (level >= 0 && scale > 0) {
            level.toFloat() / scale.toFloat() * 100
        } else {
            -1f
        }
    }
    
    private fun isCharging(): Boolean {
        val batteryIntent = context.registerReceiver(null,
            android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        val status = batteryIntent?.getIntExtra(android.os.BatteryManager.EXTRA_STATUS, -1) ?: -1
        return status == android.os.BatteryManager.BATTERY_STATUS_CHARGING ||
               status == android.os.BatteryManager.BATTERY_STATUS_FULL
    }
    
    private fun getNetworkType(): String {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) 
            as android.net.ConnectivityManager
        val network = connectivityManager.activeNetwork
        val capabilities = connectivityManager.getNetworkCapabilities(network)
        return when {
            capabilities == null -> "NONE"
            capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI) -> "WIFI"
            capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_CELLULAR) -> "CELLULAR"
            capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_ETHERNET) -> "ETHERNET"
            else -> "UNKNOWN"
        }
    }
    
    // Placeholder methods for Google API services
    // These would be implemented when the API client dependencies are properly resolved
    fun hasGoogleServicesAvailable(): Boolean {
        return googleAccount != null
    }
    
    @Suppress("unused")
    fun getGoogleAccountInfo(): Map<String, String> {
        val account = googleAccount ?: return emptyMap()
        return mapOf(
            "email" to (account.email ?: ""),
            "displayName" to (account.displayName ?: ""),
            "givenName" to (account.givenName ?: ""),
            "familyName" to (account.familyName ?: "")
        )
    }
}