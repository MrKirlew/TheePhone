package com.kirlewai.agent

import android.content.Context
import android.util.Log
import androidx.credentials.*
import androidx.credentials.exceptions.*
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Modern authentication helper using Credential Manager API
 * This replaces the deprecated GoogleSignIn API
 */
class ModernAuthHelper(private val context: Context) {
    
    companion object {
        private const val TAG = "ModernAuthHelper"
        private const val WEB_CLIENT_ID = "843267258954-mc04n5od104s75to3umjl46rva3p0r0s.apps.googleusercontent.com"
    }
    
    private val credentialManager = CredentialManager.create(context)
    private var currentIdToken: String? = null
    private var currentServerAuthCode: String? = null
    
    /**
     * Sign in using Credential Manager API
     */
    fun signIn(
        onSuccess: (idToken: String?, serverAuthCode: String?) -> Unit,
        onError: (String) -> Unit
    ) {
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val googleIdOption = GetGoogleIdOption.Builder()
                    .setFilterByAuthorizedAccounts(false)
                    .setServerClientId(WEB_CLIENT_ID)
                    .setAutoSelectEnabled(true)
                    .setNonce(null) // Generate nonce if needed for security
                    .build()
                
                val request = GetCredentialRequest.Builder()
                    .addCredentialOption(googleIdOption)
                    .build()
                
                val result = withContext(Dispatchers.IO) {
                    credentialManager.getCredential(
                        request = request,
                        context = context
                    )
                }
                
                handleSignInResult(result, onSuccess, onError)
                
            } catch (e: NoCredentialException) {
                Log.e(TAG, "No credentials available", e)
                onError("No credentials available. Please sign in.")
            } catch (e: GetCredentialCancellationException) {
                Log.e(TAG, "Sign-in cancelled", e)
                onError("Sign-in cancelled")
            } catch (e: GetCredentialException) {
                Log.e(TAG, "Sign-in failed", e)
                onError("Sign-in failed: ${e.message}")
            } catch (e: Exception) {
                Log.e(TAG, "Unexpected error during sign-in", e)
                onError("Unexpected error: ${e.message}")
            }
        }
    }
    
    /**
     * Handle the sign-in result
     */
    private fun handleSignInResult(
        result: GetCredentialResponse,
        onSuccess: (idToken: String?, serverAuthCode: String?) -> Unit,
        onError: (String) -> Unit
    ) {
        when (val credential = result.credential) {
            is GoogleIdTokenCredential -> {
                try {
                    // Use GoogleIdTokenCredential.createFrom as recommended
                    val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                    currentIdToken = googleIdTokenCredential.idToken
                    // Note: Server auth code is not directly available in the new API
                    // You'll need to use ID token for backend authentication
                    Log.d(TAG, "Successfully signed in with Google")
                    onSuccess(currentIdToken, null)
                } catch (e: GoogleIdTokenParsingException) {
                    Log.e(TAG, "Failed to parse Google ID token", e)
                    onError("Failed to parse authentication data")
                }
            }
            else -> {
                Log.e(TAG, "Unexpected credential type: ${credential.type}")
                onError("Unexpected credential type")
            }
        }
    }
    
    /**
     * Sign out the user
     */
    suspend fun signOut() {
        try {
            credentialManager.clearCredentialState(
                ClearCredentialStateRequest()
            )
            currentIdToken = null
            currentServerAuthCode = null
            Log.d(TAG, "Successfully signed out")
        } catch (e: Exception) {
            Log.e(TAG, "Error during sign out", e)
        }
    }
    
    /**
     * Check if user is signed in
     */
    fun isSignedIn(): Boolean = currentIdToken != null
    
    /**
     * Get current ID token
     */
    fun getIdToken(): String? = currentIdToken
    
    /**
     * Get server auth code (for backward compatibility)
     * Note: In the new API, use ID token instead
     */
    fun getServerAuthCode(): String? = currentServerAuthCode
}
