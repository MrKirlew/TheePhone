# Certificate Pinning Configuration Guide

## Current Status
✅ Certificate pinning is temporarily disabled for testing
✅ App should now connect to your backend without certificate errors

## How to Get the Correct Certificate SHA-256 Hash

### Method 1: Using OpenSSL (Recommended)
```bash
# Replace with your actual Cloud Function URL domain
echo | openssl s_client -servername us-central1-twothreeatefi.cloudfunctions.net -connect us-central1-twothreeatefi.cloudfunctions.net:443 2>/dev/null | openssl x509 -pubkey -noout | openssl rsa -pubin -outform der 2>/dev/null | openssl dgst -sha256 -binary | openssl enc -base64
```

### Method 2: Using Chrome Browser
1. Visit your Cloud Function URL in Chrome
2. Click the padlock icon → Connection is secure → Certificate is valid
3. Go to Details tab → Export certificate
4. Calculate SHA-256 hash of the public key

### Method 3: Using Android Debug Logs
1. Keep certificate pinning disabled
2. Add logging to capture the certificate:

```kotlin
// Add this to SecureApiClient.kt temporarily
private fun logCertificateChain(url: String) {
    try {
        val connection = URL(url).openConnection() as HttpsURLConnection
        connection.connect()
        val certificates = connection.serverCertificates
        
        certificates.forEach { cert ->
            val publicKey = cert.publicKey
            val encoded = publicKey.encoded
            val sha256 = MessageDigest.getInstance("SHA-256").digest(encoded)
            val hash = Base64.encodeToString(sha256, Base64.NO_WRAP)
            Log.d(TAG, "Certificate pin for $url: sha256/$hash")
        }
    } catch (e: Exception) {
        Log.e(TAG, "Failed to get certificate", e)
    }
}
```

## Re-enabling Certificate Pinning

Once you have the correct SHA-256 hashes:

1. Update `SecureApiClient.kt`:
```kotlin
private val certificatePinner: CertificatePinner = CertificatePinner.Builder()
    // Replace with your actual domain and SHA-256 hash
    .add("us-central1-twothreeatefi.cloudfunctions.net", "sha256/YOUR_ACTUAL_HASH_HERE")
    // You can add multiple pins for certificate rotation
    .add("us-central1-twothreeatefi.cloudfunctions.net", "sha256/BACKUP_HASH_HERE")
    .build()
```

2. Re-enable certificate pinning in the OkHttpClient:
```kotlin
OkHttpClient.Builder()
    .addInterceptor(AuthInterceptor())
    .addInterceptor(SecurityHeadersInterceptor())
    .addInterceptor(loggingInterceptor)
    .certificatePinner(certificatePinner)  // Uncomment this line
    // ... rest of configuration
```

## Google Cloud Functions Certificates

Google Cloud Functions typically use certificates from:
- Google Trust Services LLC
- GlobalSign

Common pins you might encounter:
- GTS Root R1: `sha256/Vjs8r4z+80wjNcr1YKepWQboSIRi63WsWXhIMN+eWys=`
- GlobalSign Root CA: `sha256/K87oWBWM9UZfyddvDfoxL+8lpNyoUB2ptGtn0fv6G2Q=`

## Security Best Practices

1. **Pin to intermediate certificates** rather than leaf certificates (they rotate less frequently)
2. **Include backup pins** to prevent lockout during certificate rotation
3. **Test thoroughly** before deploying to production
4. **Have a killswitch** to disable pinning remotely if needed
5. **Monitor for pin validation failures** in your analytics

## Troubleshooting

If you still get certificate pinning errors after re-enabling:
1. Verify the domain matches exactly (including subdomains)
2. Check if you're behind a corporate proxy that might be intercepting SSL
3. Ensure the certificate chain is complete
4. Try pinning to different certificates in the chain (root, intermediate, or leaf)

## Important Note

Certificate pinning is disabled in the current build to allow testing. 
For production, you MUST re-enable it with the correct pins for security.