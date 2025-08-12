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
  }) async {
    final url = Uri.parse('$baseUrl/conversation');
    final body = {
      'session_id': sessionId,
      'message': message,
      if (imageBase64 != null) 'image_base64': imageBase64,
    };

    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['response'] ?? 'No response';
    } else {
      throw Exception('Failed to send message: ${response.statusCode}');
    }
  }

  Future<void> sendFeedback({
    required String userId,
    required String sessionId,
    required String messageId,
    required String feedbackType,
  }) async {
    final url = Uri.parse('$baseUrl/feedback');
    final body = {
      'user_id': userId,
      'session_id': sessionId,
      'message_id': messageId,
      'feedback_type': feedbackType,
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
}