import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl;

  ApiClient(this.baseUrl);

  Future<String> sendMessage({
    required String userId,
    required String sessionId,
    required String message,
    String? imageBase64,
    bool getContacts = false,
    String? accessToken,
  }) async {
    final url = Uri.parse('$baseUrl/chat'); // Changed to /chat
    final body = {
      'user_id': userId, // Added user_id
      'session_id': sessionId,
      'message': message,
      if (imageBase64 != null) 'image_base64': imageBase64,
      if (getContacts) 'get_contacts': true,
      if (accessToken != null) 'access_token': accessToken,
    };

    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );

    if (response.statusCode == 200) {
      // The backend now streams responses, so we need to handle chunks
      // For simplicity, we'll just return the final response for now.
      // A more robust solution would involve streaming the UI.
      final data = json.decode(response.body);
      return data['data'] ?? 'No response'; // Changed to data['data']
    } else {
      throw Exception('Failed to send message: ${response.statusCode}');
    }
  }

  Future<void> sendFeedback({
    required String userId,
    required String sessionId,
    required int rating,
    String? notes,
  }) async {
    final url = Uri.parse('$baseUrl/feedback');
    final body = {
      'user_id': userId,
      'session_id': sessionId,
      'rating': rating,
      if (notes != null) 'notes': notes,
    };

    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to send feedback: ${response.statusCode}');
    }
  }

  Future<void> addMemory({
    required String userId,
    required String text,
  }) async {
    final url = Uri.parse('$baseUrl/memory');
    final body = {
      'user_id': userId,
      'text': text,
    };

    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to add memory: ${response.statusCode}');
    }
  }
}
