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
