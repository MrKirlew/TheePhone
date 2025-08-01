package com.kirlewai.agent.network

import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

object SecureMultimodalService {

    private val client = OkHttpClient()
    private const val BACKEND_URL = "https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator" // Replace with your actual backend URL

    fun send(serverAuthCode: String?, audioFile: File, imageFile: File?): String {
        if (serverAuthCode == null) {
            return "Error: Not signed in."
        }

        val requestBodyBuilder = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("auth_code", serverAuthCode)
            .addFormDataPart(
                "audio_file",
                audioFile.name,
                audioFile.asRequestBody("audio/3gpp".toMediaTypeOrNull())
            )

        imageFile?.let {
            requestBodyBuilder.addFormDataPart(
                "image_file",
                it.name,
                it.asRequestBody("image/jpeg".toMediaTypeOrNull())
            )
        }

        val request = Request.Builder()
            .url(BACKEND_URL)
            .post(requestBodyBuilder.build())
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                return "Error: ${response.code}"
            }
            return response.body?.string() ?: ""
        }
    }
}
