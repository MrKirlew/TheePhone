package com.kirlewai.agent.services

import android.content.Context
import android.util.Log
import androidx.credentials.CredentialManager
import androidx.credentials.CredentialManagerCallback
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.concurrent.Executor
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class ModernAuthService(private val context: Context) {
    
    private val credentialManager = CredentialManager.create(context)
    
    data class AuthResult(
        val idToken: String,
        val displayName: String?,
        val email: String?,
        val profilePictureUri: String?
    )
    
    suspend fun signInWithGoogle(webClientId: String): AuthResult = suspendCancellableCoroutine { continuation ->
        
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setServerClientId(webClientId)
            .setAutoSelectEnabled(true)
            .build()
        
        // Use GoogleIdTokenCredential.createFrom for proper handling
        val callback = object : CredentialManagerCallback<GetCredentialResponse, GetCredentialException> {
            override fun onResult(result: GetCredentialResponse) {
                try {
                    val credential = result.credential
                    if (credential is GoogleIdTokenCredential) {
                        val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                        val authResult = AuthResult(
                            idToken = googleIdTokenCredential.idToken,
                            displayName = googleIdTokenCredential.displayName,
                            email = googleIdTokenCredential.id,
                            profilePictureUri = googleIdTokenCredential.profilePictureUri?.toString()
                        )
                        continuation.resume(authResult)
                    } else {
                        continuation.resumeWithException(Exception("Unexpected credential type"))
                    }
                } catch (e: GoogleIdTokenParsingException) {
                    continuation.resumeWithException(e)
                }
            }
            
            override fun onError(e: GetCredentialException) {
                continuation.resumeWithException(e)
            }
        }
        
        @Suppress("UNUSED_VARIABLE")
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()
        
        // For now, use the legacy Google Sign-In as a fallback
        // The Credential Manager API is still evolving and may not be available on all devices
        try {
            // This is a placeholder - in a real implementation, you would use the Credential Manager
            // when it's fully stable and available on the target devices
            throw Exception("Modern auth not implemented yet - using legacy fallback")
        } catch (e: Exception) {
            Log.w("ModernAuthService", "Modern auth not available, use legacy Google Sign-In")
            continuation.resumeWithException(e)
        }
    }
    
    // Legacy method for backward compatibility
    suspend fun signInWithGoogleLegacy(webClientId: String): AuthResult {
        return try {
            signInWithGoogle(webClientId)
        } catch (e: Exception) {
            Log.w("ModernAuthService", "Modern auth failed, this is expected on older devices", e)
            throw e
        }
    }
}

// Extension function to simplify usage
suspend fun Context.signInWithGoogle(webClientId: String): ModernAuthService.AuthResult {
    val authService = ModernAuthService(this)
    return authService.signInWithGoogle(webClientId)
}