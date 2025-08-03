package com.kirlewai.agent

import android.content.Context
import android.util.Log
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.Scope

/**
 * Authentication compatibility helper that works with the existing deprecated APIs
 * but provides a cleaner interface and suppresses deprecation warnings
 */
@Suppress("DEPRECATION")
object AuthCompatHelper {
    
    private const val TAG = "AuthCompatHelper"
    private const val WEB_CLIENT_ID = "843267258954-mc04n5od104s75to3umjl46rva3p0r0s.apps.googleusercontent.com"
    
    /**
     * Get GoogleSignInOptions configured for server auth code
     * This suppresses the deprecation warning since we need to maintain compatibility
     */
    fun getSignInOptions(): GoogleSignInOptions {
        return GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestEmail()
            .requestIdToken(WEB_CLIENT_ID)
            .requestServerAuthCode(WEB_CLIENT_ID)
            .requestScopes(
                Scope("https://www.googleapis.com/auth/gmail.readonly"),
                Scope("https://www.googleapis.com/auth/calendar.readonly"),
                Scope("https://www.googleapis.com/auth/drive.readonly")
            )
            .build()
    }
    
    /**
     * Get the last signed in account
     */
    fun getLastSignedInAccount(context: Context): GoogleSignInAccount? {
        return GoogleSignIn.getLastSignedInAccount(context)
    }
    
    /**
     * Extract authentication tokens from account
     */
    fun getAuthTokens(account: GoogleSignInAccount?): AuthTokens {
        return AuthTokens(
            idToken = account?.idToken,
            serverAuthCode = account?.serverAuthCode,
            email = account?.email
        )
    }
    
    /**
     * Data class to hold authentication tokens
     */
    data class AuthTokens(
        val idToken: String?,
        val serverAuthCode: String?,
        val email: String?
    ) {
        val isValid: Boolean
            get() = idToken != null || serverAuthCode != null
    }
}
