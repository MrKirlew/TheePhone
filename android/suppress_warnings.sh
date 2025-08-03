#!/bin/bash

# Quick script to suppress deprecation warnings in MainActivity.kt

echo "🔧 Suppressing deprecation warnings in MainActivity.kt..."

# Add @Suppress("DEPRECATION") to the GoogleSignIn imports section
sed -i '/@Suppress("DEPRECATION")/!s/import com.google.android.gms.auth.api.signin.GoogleSignIn/@Suppress("DEPRECATION")\nimport com.google.android.gms.auth.api.signin.GoogleSignIn/' ../app/src/main/java/com/kirlewai/agent/MainActivity.kt

# Or add it to specific methods
sed -i '/private fun initGoogleSignIn/i\    @Suppress("DEPRECATION")' ../app/src/main/java/com/kirlewai/agent/MainActivity.kt

echo "✅ Done! Rebuild the app and the warnings should be suppressed."
echo ""
echo "Alternative: Add this at the very top of MainActivity.kt:"
echo '@file:Suppress("DEPRECATION")'
echo ""
echo "Note: The warnings don't affect functionality - your app will work fine!"
