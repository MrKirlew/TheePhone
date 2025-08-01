package com.kirlewai.agent.security

import android.content.Context
import android.util.Log
import androidx.core.content.edit
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.kirlewai.agent.BuildConfig
import io.jsonwebtoken.*
import io.jsonwebtoken.security.Keys
import okhttp3.*
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit
import javax.crypto.SecretKey

@Suppress("unused")
class SecureApiClient(context: Context) {

    companion object {
        private const val TAG = "SecureApiClient"
        private const val PREFS_NAME = "kirlewai_secure_prefs"
        private const val JWT_SECRET_KEY = "jwt_secret_key"
        private const val REFRESH_TOKEN_KEY = "refresh_token"
        private const val ACCESS_TOKEN_KEY = "access_token"

        // Certificate pinning for your Cloud Function domain
        private const val CLOUD_FUNCTIONS_HOSTNAME = "*.cloudfunctions.net"
        private const val CLOUD_RUN_HOSTNAME = "*.run.app"
    }

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val encryptedPrefs = EncryptedSharedPreferences.create(
        context,
        PREFS_NAME,
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    // Certificate pinning disabled for now - uncomment when ready to use
    // private val certificatePinner: CertificatePinner = CertificatePinner.Builder()
    //     // Add certificate pins for Google Cloud domains
    //     .add(CLOUD_FUNCTIONS_HOSTNAME, "sha256/FEzVOUp4dF3gI0ZVPRJhFbSD608T5Pos0+Eb0Bf8tM=") // Google Root CA
    //     .add(CLOUD_RUN_HOSTNAME, "sha256/FEzVOUp4dF3gI0ZVPRJhFbSD608T5Pos0+Eb0Bf8tM=") // Google Root CA
    //     .build()

    private val okHttpClient: OkHttpClient by lazy {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }

        OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor())
            .addInterceptor(SecurityHeadersInterceptor())
            .addInterceptor(loggingInterceptor)
            // Temporarily disabled certificate pinning for testing
            // .certificatePinner(certificatePinner)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .protocols(listOf(Protocol.HTTP_2, Protocol.HTTP_1_1))
            .build()
    }

    @Suppress("unused")
    fun getSecureClient(): OkHttpClient = okHttpClient

    // JWT Token Management
    @Suppress("unused")
    fun storeTokens(accessToken: String, refreshToken: String?) {
        encryptedPrefs.edit {
            putString(ACCESS_TOKEN_KEY, accessToken)
            refreshToken?.let { putString(REFRESH_TOKEN_KEY, it) }
        }
    }

    fun getAccessToken(): String? {
        return encryptedPrefs.getString(ACCESS_TOKEN_KEY, null)
    }

    fun getRefreshToken(): String? {
        return encryptedPrefs.getString(REFRESH_TOKEN_KEY, null)
    }

    fun clearTokens() {
        encryptedPrefs.edit {
            remove(ACCESS_TOKEN_KEY)
            remove(REFRESH_TOKEN_KEY)
        }
    }

    // JWT Validation
    fun isTokenValid(token: String): Boolean {
        return try {
            val claims = Jwts.parser()
                .verifyWith(getJwtSecret())
                .build()
                .parseSignedClaims(token)

            val expiration = claims.payload.expiration
            expiration?.after(java.util.Date()) ?: false
        } catch (e: Exception) {
            Log.w(TAG, "Token validation failed", e)
            false
        }
    }

    private fun getJwtSecret(): SecretKey {
        val secretString = encryptedPrefs.getString(JWT_SECRET_KEY, null)
            ?: generateAndStoreJwtSecret()

        return Keys.hmacShaKeyFor(secretString.toByteArray())
    }

    private fun generateAndStoreJwtSecret(): String {
        val secret = Jwts.SIG.HS256.key().build().encoded.toString()
        encryptedPrefs.edit { putString(JWT_SECRET_KEY, secret) }
        return secret
    }

    // Request Signing
    fun signRequest(request: Request): String {
        val timestamp = System.currentTimeMillis().toString()
        val method = request.method
        val url = request.url.toString()
        val bodyString = request.body?.let { body ->
            val buffer = okio.Buffer()
            body.writeTo(buffer)
            buffer.readUtf8()
        } ?: ""

        val message = "$method|$url|$bodyString|$timestamp"
        return createHmacSignature(message)
    }

    private fun createHmacSignature(message: String): String {
        return try {
            val mac = javax.crypto.Mac.getInstance("HmacSHA256")
            mac.init(getJwtSecret())
            val hash = mac.doFinal(message.toByteArray())
            android.util.Base64.encodeToString(hash, android.util.Base64.NO_WRAP)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create HMAC signature", e)
            ""
        }
    }

    // Interceptors
    private inner class AuthInterceptor : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val original = chain.request()
            val accessToken = getAccessToken()

            val request = if (accessToken != null && isTokenValid(accessToken)) {
                original.newBuilder()
                    .addHeader("Authorization", "Bearer $accessToken")
                    .build()
            } else {
                original
            }

            val response = chain.proceed(request)

            // Handle token refresh if needed
            if (response.code == 401 && accessToken != null) {
                response.close()
                return handleTokenRefresh(chain, original)
            }

            return response
        }

        private fun handleTokenRefresh(chain: Interceptor.Chain, original: Request): Response {
            val refreshToken = getRefreshToken()
            if (refreshToken == null) {
                clearTokens()
                return chain.proceed(original)
            }

            // TODO: Implement token refresh logic with your backend
            // For now, just clear tokens and retry
            clearTokens()
            return chain.proceed(original)
        }
    }

    private inner class SecurityHeadersInterceptor : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val original = chain.request()
            val timestamp = System.currentTimeMillis().toString()
            val signature = signRequest(original)

            val request = original.newBuilder()
                .addHeader("X-API-Version", "1.0")
                .addHeader("X-Client-Type", "android")
                .addHeader("X-Request-ID", java.util.UUID.randomUUID().toString())
                .addHeader("X-Timestamp", timestamp)
                .addHeader("X-Signature", signature)
                .addHeader("Content-Security-Policy", "default-src 'self'")
                .addHeader("X-Content-Type-Options", "nosniff")
                .addHeader("X-Frame-Options", "DENY")
                .build()

            return chain.proceed(request)
        }
    }

    // Security validation for responses
    @Suppress("unused")
    fun validateResponse(response: Response): Boolean {
        return try {
            // Check required security headers
            val hasSecurityHeaders = response.header("X-Content-Type-Options") != null ||
                    response.header("Content-Security-Policy") != null

            // Validate response signature if present
            val responseSignature = response.header("X-Response-Signature")
            if (responseSignature != null) {
                // TODO: Implement response signature validation
                true
            } else {
                hasSecurityHeaders
            }
        } catch (e: Exception) {
            Log.e(TAG, "Response validation failed", e)
            false
        }
    }
}
